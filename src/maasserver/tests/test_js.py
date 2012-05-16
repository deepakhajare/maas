# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI3 unit tests with SST (http://testutils.org/sst/)."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'TestYUIUnitTests',
    ]

import BaseHTTPServer
from glob import iglob
import json
import logging
import os
from os.path import (
    abspath,
    dirname,
    join,
    )
import SimpleHTTPServer
import SocketServer
import string

from fixtures import Fixture
from maastesting.testcase import TestCase
from nose.tools import nottest
from pyvirtualdisplay import Display
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


class ThreadingHTTPServer(SocketServer.ThreadingMixIn,
                          BaseHTTPServer.HTTPServer):
    """A simple HTTP Server that whill run in it's own thread."""


class SilentHTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    # SimpleHTTPRequestHandler logs to stdout: silence it.
    log_request = lambda *args, **kwargs: None
    log_error = lambda *args, **kwargs: None


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
    return map(
        string.strip,
        os.environ.get('MAAS_TEST_BROWSERS', 'Firefox').split(','))


@nottest
def get_failed_tests_message(results):
    """Return a readable error message with the list of the failed tests.

    Given a YUI3 results_ json object, return a readable error message.

    .. _results: http://yuilibrary.com/yui/docs/test/
    """
    result = []
    suites = [item for item in results.values() if isinstance(item, dict)]
    for suite in suites:
        if suite['failed'] != 0:
            tests = [item for item in suite.values()
                     if isinstance(item, dict)]
            for test in tests:
                if test['result'] != 'pass':
                    result.append('\n%s.%s: %s\n' % (
                        suite['name'], test['name'], test['message']))
    return ''.join(result)


class TestYUIUnitTests(TestCase):

    scenarios = [
        (test_page, {"test_page": abspath(test_page)})
        for test_page in iglob(join(BASE_PATH, "*.html"))
        ]

    # Indicates if this test has been cloned.
    clone = False

    def __call__(self, result=None):
        if self.clone:
            # This test has been cloned; just call-up to run the test.
            super(TestYUIUnitTests, self).__call__(result)
        else:
            # Run this test for each browser requested. Use the same display
            # fixture for all browsers. This is done here so that all
            # scenarios are played out for each browser in turn; starting and
            # stopping browsers is costly.
            with DisplayFixture():
                for browser_name in get_browser_names_from_env():
                    browser_test = clone_test_with_new_id(
                        self, "%s#%s" % (self.id(), browser_name))
                    browser_test.clone = True
                    with SSTFixture(browser_name):
                        browser_test.__call__(result)

    def test_YUI3_unit_tests(self):
        # Load the page and then wait for #suite to contain
        # 'done'.  Read the results in '#test_results'.
        go_to('file://%s' % self.test_page)
        wait_for(assert_text, 'suite', 'done')
        results = json.loads(get_element(id='test_results').text)
        if results['failed'] != 0:
            message = '%d test(s) failed.\n%s' % (
                results['failed'], get_failed_tests_message(results))
            self.fail(message)
