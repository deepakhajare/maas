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


def one_retry(timeout, delay=1):
    """Testing variant of `retries` that iterates once."""
    yield timeout, 0


def make_SauceConnectFixture(
    jarfile=None, username=None, api_key=None, se_port=None):
    """
    Create a `SauceConnectFixture`, using random values unless specified
    otherwise.
    """
    if jarfile is None:
        jarfile = factory.getRandomString()
    if username is None:
        username = factory.getRandomString()
    if api_key is None:
        api_key = factory.getRandomString()
    if se_port is None:
        se_port = factory.getRandomPort()
    return SauceConnectFixture(
        jarfile=jarfile, username=username, api_key=api_key,
        se_port=se_port)


class FakeProcess:
    """A rudimentary fake for `subprocess.Popen`."""

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
        fixture = make_SauceConnectFixture("pth/to/jar", "jaz", "youth", port)
        self.assertEqual(path.abspath("pth/to/jar"), fixture.jarfile)
        self.assertEqual("jaz", fixture.username)
        self.assertEqual("youth", fixture.api_key)
        self.assertEqual(port, fixture.se_port)

    def test_setUp_and_cleanUp(self):
        calls = []
        port = factory.getRandomPort()
        fixture = make_SauceConnectFixture("pth/to/jar", "jaz", "youth", port)
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
            ("java", "-jar", path.abspath("pth/to/jar"), "jaz", "youth",
             "--se-port", "%d" % port, "--readyfile", fixture.readyfile),
            fixture.command)
        self.assertEqual(["start"], calls)
        # Tearing down the fixture calls stop() and removes the working
        # directory.
        fixture.cleanUp()
        self.assertThat(fixture.workdir, Not(DirExists()))
        self.assertEqual(["start", "stop"], calls)

    def test_start(self):
        fixture = make_SauceConnectFixture()
        start = fixture.start
        self.patch(fixture, "start", lambda: None)
        self.patch(fixture, "stop", lambda: None)
        self.patch(subprocess, "Popen", FakeProcess)
        fixture.setUp()
        # Create the readyfile to simulate a successful start.
        touch(fixture.readyfile)
        # Use the real start() method.
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
        fixture = make_SauceConnectFixture()
        start = fixture.start
        self.patch(fixture, "start", lambda: None)
        self.patch(fixture, "stop", lambda: None)
        self.patch(subprocess, "Popen", FakeProcess)
        # Pretend that processes immediately fail with return code 1.
        self.patch(FakeProcess, "returncode", 1)
        fixture.setUp()
        error = self.assertRaises(subprocess.CalledProcessError, start)
        self.assertEqual(1, error.returncode)
        self.assertEqual(fixture.command, error.cmd)
        self.assertEqual([], fixture.process.events)

    def test_start_timeout(self):
        calls = []
        fixture = make_SauceConnectFixture()
        start = fixture.start
        self.patch(fixture, "start", lambda: None)
        self.patch(fixture, "stop", lambda: calls.append("stop"))
        self.patch(subprocess, "Popen", FakeProcess)
        self.patch(saucelabs, "retries", one_retry)
        fixture.setUp()
        self.assertRaises(TimeoutException, start)
        # stop() has also been called.
        self.assertEqual(["stop"], calls)

    def test_stop(self):

        def terminate():
            # Simulate a successful stop.
            fixture.process.returncode = 0

        fixture = make_SauceConnectFixture()
        fixture.process = FakeProcess()
        fixture.process.terminate = terminate
        fixture.stop()
        # terminate() has been called during shutdown.
        self.assertEqual(0, fixture.process.returncode)

    def test_stop_failure(self):

        def terminate():
            # Simulate a failure.
            fixture.process.returncode = 34

        fixture = make_SauceConnectFixture()
        fixture.process = FakeProcess()
        fixture.process.terminate = terminate
        fixture.command = object()
        error = self.assertRaises(subprocess.CalledProcessError, fixture.stop)
        self.assertEqual(34, error.returncode)
        self.assertEqual(fixture.command, error.cmd)
        self.assertEqual([], fixture.process.events)

    def test_stop_timeout(self):
        fixture = make_SauceConnectFixture()
        fixture.process = FakeProcess()
        fixture.command = object()
        self.patch(saucelabs, "retries", one_retry)
        self.assertRaises(TimeoutException, fixture.stop)
        # terminate() and kill() were both called to ensure shutdown.
        self.assertEqual(["terminate", "kill"], fixture.process.events)


class TestSauceOnDemandFixture(TestCase):

    def test_init(self):
        # Default capabilities are added into the given ones.
        url = "http://het:field@localhost/lars/"
        fixture = SauceOnDemandFixture({1: 2}, url)
        capabilities_default = SauceOnDemandFixture.capabilities
        capabilities_expected = capabilities_default.copy()
        capabilities_expected[1] = 2
        self.assertEqual(capabilities_expected, fixture.capabilities)
        self.assertEqual(url, fixture.control_url)

    def test_init_override_capabilities(self):
        # Capabilities passed in override the defaults.
        capabilities_override = {
            name: factory.getRandomString()
            for name in SauceOnDemandFixture.capabilities
            }
        fixture = SauceOnDemandFixture(
            capabilities_override, factory.getRandomString())
        self.assertEqual(capabilities_override, fixture.capabilities)

    def test_setUp_and_cleanUp(self):
        calls = []
        capabilities = webdriver.DesiredCapabilities.FIREFOX.copy()
        url = "http://het:field@127.0.0.1/lars"
        fixture = SauceOnDemandFixture(capabilities, url)

        def start_session(driver, desired_capabilities, browser_profile=None):
            self.assertEqual(fixture.capabilities, desired_capabilities)
            calls.append("start_session")

        def quit(driver):
            calls.append("quit")

        def execute(driver, driver_command, params=None):
            pass  # Don't make any HTTP calls.

        self.patch(webdriver.Remote, "start_session", start_session)
        self.patch(webdriver.Remote, "quit", quit)
        self.patch(webdriver.Remote, "execute", execute)

        with fixture:
            self.assertIsInstance(fixture.browser, webdriver.Remote)
            self.assertEqual(url, fixture.browser.command_executor._url)
            self.assertEqual(["start_session"], calls)
        self.assertEqual(["start_session", "quit"], calls)
