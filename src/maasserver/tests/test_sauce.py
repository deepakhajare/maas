# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SauceLabs' Sauce OnDemand fixtures."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "SauceOnDemandFixture",
    ]

from os import (
    environ,
    path,
    )
import subprocess
from time import (
    sleep,
    time,
    )

from fixtures import (
    Fixture,
    TempDir,
    TimeoutException,
    )
from maastesting.testcase import TestCase
from selenium import webdriver
from testtools.content import Content
from testtools.content_type import UTF8_TEXT

# TODO: Rename password to api_key, or access_key, or something.


def content_from_file(path):
    fd = open(path, "rb")
    def lines():
        fd.seek(0)
        return fd.readlines()
    return Content(UTF8_TEXT, lines)


def retries(timeout=30, delay=1):
    """Helper for retrying something, sleeping between attempts.

    Yields ``(elapsed, remaining)`` tuples, giving times in seconds.

    @param timeout: From now, how long to keep iterating, in seconds.
    @param delay: The sleep between each iteration, in seconds.
    """
    start = time()
    end = start + timeout + (delay / 2.0)
    for now in iter(time, None):
        if now < end:
            yield now - start, end - now
            sleep(min(delay, end - now))
        else:
            break


class SauceConnectFixture(Fixture):
    """Start up a Sauce Connect server.

    See `Test Internal Sites`_.

    .. _Test Internal Sites:
      http://saucelabs.com/docs/ondemand/connect

    """

    def __init__(self, jarfile, username, password):
        """
        @param jarfile: The path to the ``Sauce-Connect.jar`` file.
        @param username: The username to connect to SauceLabs with.
        @param password: The API key for the SauceLabs service.
        """
        super(SauceConnectFixture, self).__init__()
        self.jarfile = path.abspath(jarfile)
        self.username = username
        self.password = password

    def setUp(self):
        super(SauceConnectFixture, self).setUp()
        self.workdir = self.useFixture(TempDir()).path
        self.logfile = path.join(self.workdir, "connect.log")
        self.readyfile = path.join(self.workdir, "ready")
        self.command = (
            "java", "-jar", self.jarfile, self.username,
            self.password, "--readyfile", self.readyfile)
        self.start()
        self.addCleanup(self.stop)

    def start(self):
        with open(path.devnull, "rb") as devnull:
            with open(self.logfile, "wb", 1) as log:
                self.addDetail(
                    path.basename(self.logfile),
                    content_from_file(self.logfile))
                self.process = subprocess.Popen(
                    self.command, stdin=devnull, stdout=log,
                    stderr=log, cwd=self.workdir)
        for elapsed, remaining in retries(120):
            if self.process.poll() is None:
                if path.isfile(self.readyfile):
                    break
            else:
                raise subprocess.CalledProcessError(
                    self.process.returncode, self.command)
        else:
            self.stop()
            raise TimeoutException(
                "%s took too long to start (more than %d seconds)" % (
                    path.relpath(self.jarfile), elapsed))

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            for elapsed, remaining in retries(60):
                returncode = self.process.poll()
                # Sauce-Connect.jar appears to exit cleanly with code 143.
                if returncode in (0, 143):
                    break
                if returncode is not None:
                    raise subprocess.CalledProcessError(
                        self.process.returncode, self.command)
            else:
                self.process.kill()
                raise TimeoutException(
                    "%s took too long to stop (more than %d seconds)" % (
                        path.relpath(self.jarfile), elapsed))


if __name__ == "__main__":
    from sys import argv
    fixture = SauceConnectFixture(*argv[1:4])
    try:
        print("Setting up.")
        fixture.setUp()
        print("Ready.")
    finally:
        try:
            print("Shutting down.")
            details = fixture.getDetails()
            fixture.cleanUp()
        finally:
            print(details)


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
