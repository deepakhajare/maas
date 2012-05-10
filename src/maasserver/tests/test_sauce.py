# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""..."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "TestSauce",
    ]

from getpass import (
    getpass,
    getuser,
    )
import json
from os import environ
from textwrap import dedent
from unittest import SkipTest
from urlparse import urlparse

from fixtures import Fixture
from maastesting.testcase import TestCase
from selenium import (
    selenium,
    webdriver,
    )


class SauceLabsFixture(Fixture):

    env_var = 'UI_TEST_SAUCELABS_URL'

    help_text = dedent("""\
        Set %s to the URL for SauceLabs or a Sauce Connect instance, including
        username and access-key, e.g. http://username:access-key@example.com.
        """ % env_var)

    @classmethod
    def fromEnvironment(cls, start_url="http://localhost/"):
        url = environ.get(cls.env_var)
        if url is None:
            raise SkipTest(cls.help_text)
        urlparts = urlparse(url)
        return cls(
            start_url=start_url,
            username=(urlparts.username or getuser()),
            password=(urlparts.password or getpass()),
            hostname=(urlparts.hostname or 'localhost'),
            port=(urlparts.port or 4445))

    def __init__(self, start_url, username, password, hostname, port):
        super(SauceLabsFixture, self).__init__()
        self.start_url = start_url
        self.username = username
        self.password = password
        self.hostname = hostname
        self.port = port

    def setUp(self):
        super(SauceLabsFixture, self).setUp()
        settings = {
            "username": self.username,
            "access-key": self.password,
            "os": "Windows 2003",
            "browser": "firefox",
            "browser-version": "7",
            "name": "Testing Selenium 1 in Python at Sauce",
            }
        self.browser = selenium(
            self.hostname, self.port, json.dumps(settings), self.start_url)
        self.browser.start()
        self.addCleanup(self.browser.stop)
        self.browser.set_timeout(90000)


class SauceOnDemandFixture(Fixture):
    """Start up a driver for SauceLabs' Sauce OnDemand service.

    See `Getting Started`_, the `Available Browsers List`_, and `Additional
    Configuration`_ to help configure this fixture.

    .. _Getting Started:
      http://saucelabs.com/docs/ondemand/getting-started/env/python/se2/linux

    .. _Available Browsers List:
      http://saucelabs.com/docs/ondemand/browsers/env/python/se2/linux

    .. _Additional Configuration:
      http://saucelabs.com/docs/ondemand/additional-config

    """

    # Default capabilities
    capabilities = {
        "video-upload-on-pass": False,
        "record-screenshots": False,
        "record-video": False,
        }

    def __init__(self, capabilities, control_url):
        """
        @param capabilities: A member of `webdriver.DesiredCapabilities`, plus
            any additional configuration.
        @param control_url: The URL, including username and password (aka
            access-key) for the Sauce OnDemand service, or a local Sauce
            Connect service.
        """
        super(SauceOnDemandFixture, self).__init__()
        self.capabilities = self.capabilities.copy()
        self.capabilities.update(capabilities)
        self.control_url = control_url

    def setUp(self):
        super(SauceOnDemandFixture, self).setUp()
        self.browser = webdriver.Remote(
            desired_capabilities=self.capabilities,
            command_executor=self.control_url.encode("ascii"))
        self.browser.implicitly_wait(30)  # TODO: Is this always needed?
        self.addCleanup(self.browser.quit)


class TestSauce(TestCase):

    def test_SauceLabsFixture(self):
        saucelabs = SauceLabsFixture.fromEnvironment()
        browser = self.useFixture(saucelabs).browser
        browser.open("http://localhost/")
        browser.wait_for_page_to_load(10000)
        self.assertTrue(browser.is_text_present("It works!"))

    def test_SauceOnDemandFixture(self):
        # Browser and platform choices
        # <http://saucelabs.com/docs/ondemand/browsers/env/python/se2/linux>.
        capabilities = webdriver.DesiredCapabilities.FIREFOX.copy()
        capabilities["platform"] = "LINUX"
        ondemand = SauceOnDemandFixture(
            control_url=environ.get("UI_TEST_SAUCE_ONDEMAND_URL"),
            capabilities=capabilities)
        browser = self.useFixture(ondemand).browser
        browser.get("http://localhost/")
        h1 = browser.find_element_by_xpath('//h1')
        self.assertEqual("It works!", h1.text)
