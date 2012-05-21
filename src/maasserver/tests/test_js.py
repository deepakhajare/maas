# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI3 unit tests with SST (http://testutils.org/sst/)."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from abc import (
    ABCMeta,
    abstractmethod,
    )
from glob import glob
import json
import logging
import os
from os.path import (
    abspath,
    dirname,
    join,
    )
from urlparse import urljoin

from fixtures import Fixture
from maastesting import yui3
from maastesting.httpd import HTTPServerFixture
from maastesting.saucelabs import (
    SauceConnectFixture,
    SSTOnDemandFixture,
    )
from maastesting.testcase import TestCase
from maastesting.utils import extract_word_list
from nose.tools import nottest
from pyvirtualdisplay import Display
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from sst.actions import (
    assert_text,
    get_element,
    go_to,
    start,
    stop,
    wait_for,
    )
from testtools import clone_test_with_new_id

# Base path where the HTML files will be searched.
BASE_PATH = 'src/maasserver/static/js/tests/'


# Nose is over-zealous.
nottest(clone_test_with_new_id)


class LoggerSilencerFixture(Fixture):
    """Fixture to change the log level of loggers.

    All the loggers with names self.logger_names will have their log level
    changed to self.level (logging.ERROR by default).
    """

    def __init__(self, names, level=logging.ERROR):
        super(LoggerSilencerFixture, self).__init__()
        self.names = names
        self.level = level

    def setUp(self):
        super(LoggerSilencerFixture, self).setUp()
        for name in self.names:
            logger = logging.getLogger(name)
            self.addCleanup(logger.setLevel, logger.level)
            logger.setLevel(self.level)


class DisplayFixture(Fixture):
    """Fixture to create a virtual display with pyvirtualdisplay.Display."""

    logger_names = ['easyprocess', 'pyvirtualdisplay']

    def __init__(self, visible=False, size=(1280, 1024)):
        super(DisplayFixture, self).__init__()
        self.visible = visible
        self.size = size

    def setUp(self):
        super(DisplayFixture, self).setUp()
        self.useFixture(LoggerSilencerFixture(self.logger_names))
        self.display = Display(
            visible=self.visible, size=self.size)
        self.display.start()
        self.addCleanup(self.display.stop)


class SSTFixture(Fixture):
    """Setup a javascript-enabled testing browser instance with SST."""

    logger_names = ['selenium.webdriver.remote.remote_connection']

    def __init__(self, browser_name):
        self.browser_name = browser_name

    def setUp(self):
        super(SSTFixture, self).setUp()
        start(self.browser_name)
        self.useFixture(LoggerSilencerFixture(self.logger_names))
        self.addCleanup(stop)


project_home = dirname(dirname(dirname(dirname(__file__))))


def get_browser_names_from_env():
    """Parse the environment variable ``MAAS_TEST_BROWSERS`` to get a list of
    the browsers to use for the JavaScript tests.

    Returns ['Firefox'] if the environment variable is not present.
    """
    names = os.environ.get('MAAS_TEST_BROWSERS', 'Firefox')
    return extract_word_list(names)


# See <https://saucelabs.com/docs/ondemand/browsers/env/python/se2/linux> for
# more information on browser/platform choices.
remote_browsers = {
    "ie7": dict(
        DesiredCapabilities.INTERNETEXPLORER,
        version="7", platform="XP"),
    "ie8": dict(
        DesiredCapabilities.INTERNETEXPLORER,
        version="8", platform="XP"),
    "ie9": dict(
        DesiredCapabilities.INTERNETEXPLORER,
        version="9", platform="VISTA"),
    "chrome": dict(
        DesiredCapabilities.CHROME,
        platform="VISTA"),
    }


def get_remote_browser_names_from_env():
    """Parse the environment variable ``MAAS_REMOTE_TEST_BROWSERS`` to get a
    list of the browsers to use for the JavaScript tests.

    Returns [] if the environment variable is not present.
    """
    names = os.environ.get('MAAS_REMOTE_TEST_BROWSERS', '')
    names = [name.lower() for name in extract_word_list(names)]
    unrecognised = set(names).difference(remote_browsers)
    if len(unrecognised) > 0:
        raise ValueError("Unrecognised browsers: %r" % unrecognised)
    return names


class YUIUnitBase:

    __metaclass__ = ABCMeta

    test_paths = glob(join(BASE_PATH, "*.html"))

    # Indicates if this test has been cloned.
    cloned = False

    def clone(self, suffix):
        # Clone this test with a new suffix.
        test = clone_test_with_new_id(
            self, "%s#%s" % (self.id(), suffix))
        test.cloned = True
        return test

    @abstractmethod
    def multiply(self, result):
        """Run the test for each of a specified range of browsers.

        This method should sort out shared fixtures.
        """

    def __call__(self, result=None):
        if self.cloned:
            # This test has been cloned; just call-up to run the test.
            super(YUIUnitBase, self).__call__(result)
        else:
            self.multiply(result)

    def test_YUI3_unit_tests(self):
        # Load the page and then wait for #suite to contain
        # 'done'.  Read the results in '#test_results'.
        go_to(self.test_url)
        wait_for(assert_text, 'suite', 'done')
        results = json.loads(get_element(id='test_results').text)
        if results['failed'] != 0:
            message = '%d test(s) failed.\n\n%s' % (
                results['failed'], yui3.get_failed_tests_message(results))
            self.fail(message)


class YUIUnitTestsLocal(YUIUnitBase, TestCase):

    scenarios = tuple(
        (path, {"test_url": "file://%s" % abspath(path)})
        for path in YUIUnitBase.test_paths)

    def multiply(self, result):
        # Run this test locally for each browser requested. Use the same
        # display fixture for all browsers. This is done here so that all
        # scenarios are played out for each browser in turn; starting and
        # stopping browsers is costly.
        with DisplayFixture():
            for browser_name in get_browser_names_from_env():
                browser_test = self.clone("local:%s" % browser_name)
                with SSTFixture(browser_name):
                    browser_test.__call__(result)


class YUIUnitTestsRemote(YUIUnitBase, TestCase):

    def multiply(self, result):
        # Now run this test remotely for each requested Sauce OnDemand
        # browser requested.
        browser_names = get_remote_browser_names_from_env()
        if len(browser_names) == 0:
            return

        # A web server is needed so the OnDemand service can obtain local
        # tests. Be careful when choosing web server ports:
        #
        #   Sauce Connect proxies localhost ports 80, 443, 888, 2000, 2001,
        #   2020, 2222, 3000, 3001, 3030, 3333, 4000, 4001, 4040, 4502, 4503,
        #   5000, 5001, 5050, 5555, 6000, 6001, 6060, 6666, 7000, 7070, 7777,
        #   8000, 8001, 8003, 8080, 8888, 9000, 9001, 9090, 9999 so when you
        #   use it, your local web apps are available to test as if the cloud
        #   was your local machine. Easy!
        #
        # From <https://saucelabs.com/docs/ondemand/connect>.
        with HTTPServerFixture(port=5555) as httpd:
            scenarios = tuple(
                (path, {"test_url": urljoin(httpd.url, path)})
                for path in self.test_paths)
            with SauceConnectFixture() as sauce_connect:
                for browser_name in browser_names:
                    capabilities = remote_browsers[browser_name]
                    sst_ondemand = SSTOnDemandFixture(
                        capabilities, sauce_connect.control_url)
                    with sst_ondemand:
                        browser_test = self.clone("remote:%s" % browser_name)
                        browser_test.scenarios = scenarios
                        browser_test(result)
