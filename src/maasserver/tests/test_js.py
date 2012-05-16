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
from contextlib import contextmanager
from glob import glob
import json
import logging
import os
from os.path import (
    abspath,
    dirname,
    join,
    )
import re
import SimpleHTTPServer
import SocketServer
import threading

from fixtures import Fixture
from maastesting.saucelabs import (
    SauceConnectFixture,
    SauceOnDemandFixture,
    )
from maastesting.testcase import TestCase
from nose.tools import nottest
from pyvirtualdisplay import Display
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from sst import actions
from sst.actions import (
    assert_text,
    get_element,
    go_to,
    start,
    stop,
    wait_for,
    )
from testtools import clone_test_with_new_id
from testtools.monkey import MonkeyPatcher

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


@contextmanager
def web_server(host="localhost", port=5555):
    server = ThreadingHTTPServer(
        (host, port), SilentHTTPRequestHandler)
    threading.Thread(target=server.serve_forever).start()
    try:
        yield server
    finally:
        server.shutdown()


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


def extract_word_list(string):
    return re.findall("[^,;\s]+", string)


def get_browser_names_from_env():
    """Parse the environment variable ``MAAS_TEST_BROWSERS`` to get a list of
    the browsers to use for the JavaScript tests.

    Returns ['Firefox'] if the environment variable is not present.
    """
    names = os.environ.get('MAAS_TEST_BROWSERS', 'Firefox')
    return extract_word_list(names)


remote_browsers = {
    "ie7": dict(DesiredCapabilities.INTERNETEXPLORER, version="7"),
    "ie8": dict(DesiredCapabilities.INTERNETEXPLORER, version="8"),
    "ie9": dict(DesiredCapabilities.INTERNETEXPLORER, version="9"),
    "chrome": dict(DesiredCapabilities.CHROME),
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


class YUIUnitBase:

    test_paths = glob(join(BASE_PATH, "*.html"))

    # Indicates if this test has been cloned.
    clone = False

    def __call__(self, result=None):
        if self.clone:
            # This test has been cloned; just call-up to run the test.
            super(YUIUnitBase, self).__call__(result)
        else:
            self.execute(result)

    def test_YUI3_unit_tests(self):
        # Load the page and then wait for #suite to contain
        # 'done'.  Read the results in '#test_results'.
        go_to(self.test_url)
        wait_for(assert_text, 'suite', 'done')
        results = json.loads(get_element(id='test_results').text)
        if results['failed'] != 0:
            message = '%d test(s) failed.\n%s' % (
                results['failed'], get_failed_tests_message(results))
            self.fail(message)


class YUIUnitTestsLocal(YUIUnitBase, TestCase):

    scenarios = [
        (path, {"test_url": "file://%s" % abspath(path)})
        for path in YUIUnitBase.test_paths
        ]

    def execute(self, result):
        # Run this test locally for each browser requested. Use the same
        # display fixture for all browsers. This is done here so that all
        # scenarios are played out for each browser in turn; starting and
        # stopping browsers is costly.
        with DisplayFixture():
            for browser_name in get_browser_names_from_env():
                browser_test = clone_test_with_new_id(
                    self, "%s#local:%s" % (self.id(), browser_name))
                browser_test.clone = True
                with SSTFixture(browser_name):
                    browser_test.__call__(result)


class YUIUnitTestsRemote(YUIUnitBase, TestCase):

    def execute(self, result):
        # Now run this test remotely for each requested Sauce OnDemand
        # browser requested.
        browser_names = get_remote_browser_names_from_env()
        if len(browser_names) == 0:
            return

        ondemand_args = {
            "jarfile": "saucelabs/connect/Sauce-Connect.jar",
            "username": "...",
            "api_key": "...",
            }

        with web_server() as webserv:
            url_form = "http://%s:%d/%%s" % webserv.server_address
            with SauceConnectFixture(**ondemand_args) as connect:
                control_url = (
                    "http://%(username)s:%(api_key)s@"
                    "localhost:%(port)d/wd/hub" % dict(
                        ondemand_args, port=connect.se_port))
                for browser_name in browser_names:
                    capabilities = remote_browsers[browser_name]
                    ondemand = SauceOnDemandFixture(capabilities, control_url)
                    with ondemand:
                        browser_test = clone_test_with_new_id(
                            self, "%s#remote:%s" % (self.id(), browser_name))
                        browser_test.clone = True
                        browser_test.scenarios = [
                            (path, {"test_url": url_form % path})
                            for path in YUIUnitBase.test_paths
                            ]
                        patcher = MonkeyPatcher(
                            (actions, "browser", ondemand.driver),
                            (actions, "browsermob_proxy", None))
                        patcher.run_with_patches(browser_test, result)
