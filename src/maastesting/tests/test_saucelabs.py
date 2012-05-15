# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maastesting.saucelabs`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from os import (
    environ,
    path,
    )

from maastesting.factory import factory
from maastesting.saucelabs import (
    SauceConnectFixture,
    SauceOnDemandFixture,
    )
from maastesting.testcase import TestCase
from selenium import webdriver
from testtools.matchers import (
    DirExists,
    Not,
    )


class TestSauceConnectFixture(TestCase):

    def test_init(self):
        port = factory.getRandomPort()
        fixture = SauceConnectFixture(
            "path/to/jar", "jaz", "youth", port)
        self.assertEqual(
            path.abspath("path/to/jar"), fixture.jarfile)
        self.assertEqual("jaz", fixture.username)
        self.assertEqual("youth", fixture.api_key)
        self.assertEqual(port, fixture.se_port)

    def test_setUp_and_cleanUp(self):
        port = factory.getRandomPort()
        fixture = SauceConnectFixture(
            "path/to/jar", "jaz", "youth", port)
        calls = []
        self.patch(fixture, "start", lambda: calls.append("start"))
        self.patch(fixture, "stop", lambda: calls.append("stop"))
        # Setting up the fixture allocates a working directory, the command to
        # run, and calls start().
        fixture.setUp()
        self.assertThat(fixture.workdir, DirExists())
        self.assertEqual(
            "connect.log", path.relpath(
                fixture.logfile, fixture.workdir))
        self.assertEqual(
            "ready", path.relpath(
                fixture.readyfile, fixture.workdir))
        self.assertEqual(
            ("java", "-jar", path.abspath("path/to/jar"),
             "jaz", "youth", "--se-port", "%d" % port,
            "--readyfile", fixture.readyfile),
            fixture.command)
        self.assertEqual(["start"], calls)
        # Tearing down the fixture calls stop() and removes the working
        # directory.
        fixture.cleanUp()
        self.assertThat(fixture.workdir, Not(DirExists()))
        self.assertEqual(["start", "stop"], calls)


class TestSauceOnDemandFixture(TestCase):

    def test_basic_functionality(self):
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
