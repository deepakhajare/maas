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
    devnull,
    environ,
    path,
    )
import subprocess

from maastesting import saucelabs
from maastesting.factory import factory
from maastesting.saucelabs import (
    SauceConnectFixture,
    SauceOnDemandFixture,
    TimeoutException,
    )
from maastesting.testcase import TestCase
from selenium import webdriver
from testtools.matchers import (
    DirExists,
    Not,
    )


def touch(filename):
    open(filename, "ab").close()


class FakeProcess:

    returncode = None

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.events = []

    def poll(self):
        return self.returncode

    def terminate(self):
        self.events.append("terminate")

    def kill(self):
        self.events.append("kill")


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

    def test_start(self):
        fixture = SauceConnectFixture(
            factory.getRandomString(), factory.getRandomString(),
            factory.getRandomString(), factory.getRandomPort())

        start = fixture.start
        self.patch(fixture, "start", lambda: None)
        self.patch(fixture, "stop", lambda: None)
        self.patch(subprocess, "Popen", FakeProcess)

        with fixture:
            # Create the readyfile to simulate a successful start.
            touch(fixture.readyfile)
            # Start using the real start method.
            start()
            self.assertEqual((fixture.command,), fixture.process.args)
            kwargs = fixture.process.kwargs
            self.assertEqual(fixture.workdir, kwargs["cwd"])
            self.assertIs(saucelabs.preexec_fn, kwargs["preexec_fn"])
            self.assertEqual(devnull, kwargs["stdin"].name)
            self.assertEqual(fixture.logfile, kwargs["stdout"].name)
            self.assertEqual(fixture.logfile, kwargs["stderr"].name)
            self.assertEqual([], fixture.process.events)

    def test_start_failure(self):
        fixture = SauceConnectFixture(
            factory.getRandomString(), factory.getRandomString(),
            factory.getRandomString(), factory.getRandomPort())

        start = fixture.start
        self.patch(fixture, "start", lambda: None)
        self.patch(fixture, "stop", lambda: None)
        self.patch(subprocess, "Popen", FakeProcess)

        # Pretend that processes immediately fail with return code 1.
        self.patch(FakeProcess, "returncode", 1)

        with fixture:
            error = self.assertRaises(
                subprocess.CalledProcessError, start)
            self.assertEqual(1, error.returncode)
            self.assertEqual(fixture.command, error.cmd)
            self.assertEqual([], fixture.process.events)

    def test_start_timeout(self):
        fixture = SauceConnectFixture(
            factory.getRandomString(), factory.getRandomString(),
            factory.getRandomString(), factory.getRandomPort())

        calls = []
        start = fixture.start
        self.patch(fixture, "start", lambda: None)
        self.patch(fixture, "stop", lambda: calls.append("stop"))
        self.patch(subprocess, "Popen", FakeProcess)
        # Make retries() end after a single iteration.
        self.patch(saucelabs, "retries", lambda timeout: [(timeout, 0)])

        with fixture:
            self.assertRaises(TimeoutException, start)
            # stop() has also been called.
            self.assertEqual(["stop"], calls)

    def test_stop(self):
        fixture = SauceConnectFixture(
            factory.getRandomString(), factory.getRandomString(),
            factory.getRandomString(), factory.getRandomPort())

        def terminate():
            # Simulate a successful stop.
            fixture.process.returncode = 0

        fixture.process = FakeProcess()
        fixture.process.terminate = terminate
        fixture.stop()

        # terminate() has been called during shutdown.
        self.assertEqual(0, fixture.process.returncode)

    def test_stop_failure(self):
        fixture = SauceConnectFixture(
            factory.getRandomString(), factory.getRandomString(),
            factory.getRandomString(), factory.getRandomPort())

        def terminate():
            # Simulate a failure.
            fixture.process.returncode = 34

        fixture.process = FakeProcess()
        fixture.process.terminate = terminate
        fixture.command = object()

        error = self.assertRaises(
            subprocess.CalledProcessError, fixture.stop)
        self.assertEqual(34, error.returncode)
        self.assertEqual(fixture.command, error.cmd)
        self.assertEqual([], fixture.process.events)

    def test_stop_timeout(self):
        fixture = SauceConnectFixture(
            factory.getRandomString(), factory.getRandomString(),
            factory.getRandomString(), factory.getRandomPort())

        # Make retries() end after a single iteration.
        self.patch(saucelabs, "retries", lambda timeout: [(timeout, 0)])

        fixture.process = FakeProcess()
        fixture.command = object()

        self.assertRaises(TimeoutException, fixture.stop)
        # terminate() and kill() were both called to ensure shutdown.
        self.assertEqual(["terminate", "kill"], fixture.process.events)


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
