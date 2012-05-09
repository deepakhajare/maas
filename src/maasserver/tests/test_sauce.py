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
from selenium import selenium


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


class TestSauce(TestCase):

    def test_sauce(self):
        saucelabs = SauceLabsFixture.fromEnvironment()
        browser = self.useFixture(saucelabs).browser
        browser.open("http://localhost/")
        browser.wait_for_page_to_load(10000)
        self.assertTrue(browser.is_text_present("It works!"))
