# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Server fixture for Bind."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'BindServer',
    'set_up_named',
    ]

import os
from shutil import copy
import subprocess
import time

import fixtures
from provisioningserver.utils import atomic_write
from provisioningserver.dns.config import generate_rndc
from rabbitfixture.server import (
    allocate_ports,
    preexec_fn,
    )
import tempita
from testtools.content import Content
from testtools.content_type import UTF8_TEXT


def get_named_path():
    """Return the full path where the 'named' executable can be
    found.

    Note that it will be copied over to a temporary
    location in order to by-pass the limitations imposed by
    apparmor if the executable is in its default location
    (/usr/sbin/named).
    """
    return os.environ.get(
        'MAAS_NAMED_PATH', '/usr/sbin/named')


# Where the executable 'rndc' can be found (belongs to the package
# 'bind9utils').
RNDCBIN = "/usr/sbin/rndc"

# The configuration template for the Bind server.  The goal here
# is to override the defaults (default configuration files location,
# default port) to avoid clashing with the system's bind (if
# running).
NAMED_CONF_TEMPLATE = tempita.Template("""
options {
  directory "{{homedir}}";
  listen-on port {{port}} {127.0.0.1;};
  pid-file "{{homedir}}/named.pid";
  session-keyfile "{{homedir}}/session.key";
};

logging{
  channel simple_log {
    file "{{log_file}}";
    severity info;
    print-severity yes;
  };
  category default{
    simple_log;
  };
};
""")


def set_up_named(homedir, port, rndc_port, log_file, named_file,
                conf_file, rndcconf_file):
    """Setup an environment to run 'named'.

    - Create the default configuration for 'named' and setup rndc.
    - Copies the 'named' executable inside homedir (to by-pass the
    restrictions that apparmor imposes

    :param homedir: Home directory where the executable should be
        copied.
    :param port: Port that will be used by 'named'.
    :param rndc_port: rndc port that will be used by 'named'.
    :param log_file: Full path of the main logging file.
    :param named_file: Full path of where 'named' should be copied.
    :param conf_file: Full path of the main configuration file.
    :param rndcconf_file: Full path of the rndc configuration file.
    """
    # Generate rndc configuration (rndc config and named snippet).
    rndcconf, namedrndcconf = generate_rndc(
        rndc_port, 'dnsfixture-rndc-key')
    # Write main bind config file.
    named_conf = (
        NAMED_CONF_TEMPLATE.substitute(
            homedir=homedir, port=port, log_file=log_file)
        + namedrndcconf)
    atomic_write(named_conf, conf_file)
   # Write rndc config file.
    atomic_write(rndcconf, rndcconf_file)

    # Copy named executable to home dir.  This is done to avoid
    # the limitations imposed by apparmor if the executable
    # is in /usr/sbin/named.
    named_path = get_named_path()
    assert os.path.exists(named_path), (
        "'%s' executable not found.  Install the package "
        "'bind9' or define an environment variable named "
        "MAAS_NAMED_PATH with the path where the 'named' "
        "executable can be found." % named_path)
    copy(named_path, named_file)


class BindServerResources(fixtures.Fixture):
    """Allocate the resources a Bind server needs.

    :ivar port: A port that was free at the time setUp() was
        called.
    :ivar rndc_port: A port that was free at the time setUp() was
        called (used for rndc communication).
    :ivar homedir: A directory where to put all the files the
        Bind server needs (configuration files and executable).
    :ivar log_file: The log_file allocated for the server.
    """

    def __init__(self, port=None, rndc_port=None, homedir=None,
                 log_file=None):
        super(BindServerResources, self).__init__()
        self._defaults = dict(
            port=port,
            rndc_port=rndc_port,
            homedir=homedir,
            log_file=log_file,
            )

    def setUp(self):
        super(BindServerResources, self).setUp()
        self.__dict__.update(self._defaults)
        self.set_up_config()
        set_up_named(
            self.homedir, self.port, self.rndc_port, self.log_file,
            self.named_file, self.conf_file, self.rndcconf_file)

    def set_up_config(self):
        if self.port is None:
            [self.port] = allocate_ports(1)
        if self.rndc_port is None:
            [self.rndc_port] = allocate_ports(1)
        if self.homedir is None:
            self.homedir = self.useFixture(fixtures.TempDir()).path
        if self.log_file is None:
            self.log_file = os.path.join(self.homedir, 'named.log')
        self.named_file = os.path.join(
            self.homedir, os.path.basename(get_named_path()))
        self.conf_file = os.path.join(self.homedir, 'named.conf')
        self.rndcconf_file = os.path.join(self.homedir, 'rndc.conf')

    def tearDown(self):
        super(BindServerResources, self).tearDown()
        # Restore defaults, setting dynamic values back to None for
        # reallocation in setUp.
        self.__dict__.update(self._defaults)


class BindServerRunner(fixtures.Fixture):
    """Run a Bind server."""

    def __init__(self, config):
        """Create a `BindServerRunner` instance.

        :param config: An object exporting the variables
            `BindServerResources` exports.
        """
        super(BindServerRunner, self).__init__()
        self.config = config
        self.process = None

    def setUp(self):
        super(BindServerRunner, self).setUp()
        self._start()

    def is_running(self):
        """Is the Bind server process still running?"""
        if self.process is None:
            return False
        else:
            return self.process.poll() is None

    def _spawn(self):
        """Spawn the Bind server process."""
        env = dict(os.environ, HOME=self.config.homedir)
        with open(self.config.log_file, "wb") as log_file:
            with open(os.devnull, "rb") as devnull:
                self.process = subprocess.Popen(
                    [self.config.named_file, "-f", "-c",
                     self.config.conf_file],
                    stdin=devnull,
                    stdout=log_file, stderr=log_file,
                    close_fds=True, cwd=self.config.homedir,
                    env=env, preexec_fn=preexec_fn)
        # Keep the log_file open for reading so that we can still get the log
        # even if the log is deleted.
        open_log_file = open(self.config.log_file, "rb")
        self.addDetail(
            os.path.basename(self.config.log_file),
            Content(UTF8_TEXT, lambda: open_log_file))

    def rndc(self, command):
        """Executes a ``rndc`` command and returns status."""
        if isinstance(command, basestring):
            command = (command,)
        ctl = subprocess.Popen(
            (RNDCBIN, "-c", self.config.rndcconf_file) + command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            preexec_fn=preexec_fn)
        outstr, errstr = ctl.communicate()
        return outstr, errstr

    def is_server_running(self):
        """Checks that the Bind server is up and running."""
        outdata, errdata = self.rndc("status")
        return "server is up and running" in outdata

    def _start(self):
        """Start the Bind server."""
        self._spawn()
        # Wait for the server to come up: stop when the process is dead, or
        # the timeout expires, or the server responds.
        timeout = time.time() + 15
        while time.time() < timeout and self.is_running():
            if self.is_server_running():
                break
            time.sleep(0.3)
        else:
            raise Exception(
                "Timeout waiting for Bind server to start: log in %r." %
                (self.config.log_file,))
        self.addCleanup(self._stop)

    def _request_stop(self):
        outstr, errstr = self.rndc("stop")
        if outstr:
            self.addDetail('stop-out', Content(UTF8_TEXT, lambda: [outstr]))
        if errstr:
            self.addDetail('stop-err', Content(UTF8_TEXT, lambda: [errstr]))

    def _stop(self):
        """Stop the running server. Normally called by cleanups."""
        self._request_stop()
        # Wait for the server to go down...
        timeout = time.time() + 15
        while time.time() < timeout:
            if not self.is_server_running():
                break
            time.sleep(0.3)
        else:
            raise Exception(
                "Timeout waiting for Bind server to go down.")
        # Wait at least 5 more seconds for the process to end...
        timeout = max(timeout, time.time() + 5)
        while time.time() < timeout:
            if not self.is_running():
                break
            self.process.terminate()
            time.sleep(0.1)
        else:
            # Die!!!
            if self.is_running():
                self.process.kill()
                time.sleep(0.5)
            if self.is_running():
                raise Exception("Bind server just won't die.")


class BindServer(fixtures.Fixture):
    """A Bind server fixture.

    When setup a Bind instance will be running.

    :ivar config: The `BindServerResources` used to start the server.
    """

    def __init__(self, config=None):
        super(BindServer, self).__init__()
        self.config = config

    def setUp(self):
        super(BindServer, self).setUp()
        if self.config is None:
            self.config = BindServerResources()
        self.useFixture(self.config)
        self.runner = BindServerRunner(self.config)
        self.useFixture(self.runner)
