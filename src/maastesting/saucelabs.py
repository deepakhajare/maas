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
    "SauceConnectFixture",
    "SauceOnDemandFixture",
    "SSTOnDemandFixture",
    "TimeoutException",
    ]

from contextlib import closing
from io import BytesIO
from itertools import (
    chain,
    islice,
    repeat,
    )
from os import path
import subprocess
from urllib2 import urlopen
from zipfile import ZipFile

from fixtures import (
    Fixture,
    TempDir,
    )
from maastesting.utils import (
    content_from_file,
    extract_word_list,
    preexec_fn,
    retries,
    )
from selenium import webdriver
from testtools.monkey import MonkeyPatcher


sauce_connect_url = "https://saucelabs.com/downloads/Sauce-Connect-latest.zip"
sauce_connect_dir = path.expanduser("~/.saucelabs/connect")


def get_or_download_sauce_connect(url=sauce_connect_url):
    """Find or download ``Sauce-Connect.jar`` to a shared location."""
    sauce_connect_jarfile = path.join(
        sauce_connect_dir, "Sauce-Connect.jar")
    if not path.exists(sauce_connect_jarfile):
        with closing(urlopen(url)) as fin:
            buf = BytesIO(fin.read())
        with ZipFile(buf) as zipfile:
            zipfile.extractall(sauce_connect_dir)
    return sauce_connect_jarfile


def get_credentials():
    """Load credentials for the SauceLabs Connect service.

    @return: A ``(username, api_key)`` tuple.
    """
    sauce_connect_credentials_file = path.join(
        sauce_connect_dir, "credentials")
    with open(sauce_connect_credentials_file, "rb") as fd:
        creds = extract_word_list(fd.read())
    return tuple(islice(chain(creds, repeat(b"")), 2))


class TimeoutException(Exception):
    """An operation has timed-out."""


class SauceConnectFixture(Fixture):
    """Start up a Sauce Connect server.

    See `Test Internal Sites`_.

    .. _Test Internal Sites:
      http://saucelabs.com/docs/ondemand/connect

    """

    def __init__(self, jarfile=None, credentials=None, control_port=4445):
        """
        @param jarfile: The path to the ``Sauce-Connect.jar`` file.
        @param credentials: Credentials for the SauceLabs service, typically a
            2-tuple of (username, api_key).
        @param control_port: The port on which to accept Selenium commands.
        """
        super(SauceConnectFixture, self).__init__()
        if jarfile is None:
            jarfile = get_or_download_sauce_connect()
        if credentials is None:
            credentials = get_credentials()
        self.jarfile = path.abspath(jarfile)
        self.username, self.api_key = credentials
        self.control_port = control_port

    def setUp(self):
        super(SauceConnectFixture, self).setUp()
        self.workdir = self.useFixture(TempDir()).path
        self.logfile = path.join(self.workdir, "connect.log")
        self.readyfile = path.join(self.workdir, "ready")
        self.command = (
            "java", "-jar", self.jarfile,
            self.username, self.api_key,
            "--se-port", "%d" % self.control_port,
            "--readyfile", self.readyfile)
        self.start()
        self.addCleanup(self.stop)

    def start(self):
        with open(path.devnull, "rb") as devnull:
            with open(self.logfile, "wb", 1) as log:
                self.addDetail(
                    path.basename(self.logfile),
                    content_from_file(self.logfile))
                self.process = subprocess.Popen(
                    self.command, stdin=devnull, stdout=log, stderr=log,
                    cwd=self.workdir, preexec_fn=preexec_fn)
        # Wait for start-up to complete.
        for elapsed, remaining in retries(120):
            if self.process.poll() is None:
                if path.isfile(self.readyfile):
                    break
            else:
                raise subprocess.CalledProcessError(
                    self.process.returncode, self.command)
        else:
            # Things are taking too long; stop and bail out.
            self.stop()
            raise TimeoutException(
                "%s took too long to start (more than %d seconds)" % (
                    path.relpath(self.jarfile), elapsed))

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            # Wait for shutdown to complete.
            for elapsed, remaining in retries(60):
                returncode = self.process.poll()
                # Sauce-Connect.jar appears to exit cleanly with code 143.
                if returncode in (0, 143):
                    break
                if returncode is not None:
                    raise subprocess.CalledProcessError(
                        self.process.returncode, self.command)
            else:
                # Things are taking too long; kill.
                self.process.kill()
                raise TimeoutException(
                    "%s took too long to stop (more than %d seconds)" % (
                        path.relpath(self.jarfile), elapsed))

    @property
    def control_url(self):
        """URL for Selenium to connect to so that commands are proxied.

        Possibly suitable for use with Selenium 2 only.
        """
        return "http://%s:%s@localhost:%d/wd/hub" % (
            self.username, self.api_key, self.control_port)


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
        @param control_url: The URL, including username and API key for the
            Sauce OnDemand service, or a Sauce Connect service.
        """
        super(SauceOnDemandFixture, self).__init__()
        self.capabilities = self.capabilities.copy()
        self.capabilities.update(capabilities)
        self.control_url = control_url

    def setUp(self):
        super(SauceOnDemandFixture, self).setUp()
        self.driver = webdriver.Remote(
            desired_capabilities=self.capabilities,
            command_executor=self.control_url.encode("ascii"))
        self.driver.implicitly_wait(30)  # TODO: Is this always needed?
        self.addCleanup(self.driver.quit)


class SSTOnDemandFixture(SauceOnDemandFixture):
    """Variant of `SauceOnDemandFixture` that also patches `sst`.

    When this fixture is active you can use `sst` with the allocated driver
    without calling `sst.actions.start` or `sst.actions.stop`.
    """

    noop = staticmethod(lambda *args, **kwargs: None)

    def setUp(self):
        from sst import actions
        super(SSTOnDemandFixture, self).setUp()
        patcher = MonkeyPatcher(
            (actions, "browser", self.driver),
            (actions, "browsermob_proxy", None),
            (actions, "start", self.noop),
            (actions, "stop", self.noop))
        self.addCleanup(patcher.restore)
        patcher.patch()
