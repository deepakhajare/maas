# Copyright 2005-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for provisioning configuration."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from functools import partial
from getpass import getuser
import os
from textwrap import dedent

from fixtures import EnvironmentVariableFixture
import formencode
from maastesting.factory import factory
from maastesting.testcase import TestCase
from mocker import Mocker
import provisioningserver.config
from provisioningserver.config import (
    Config,
    get_config_filename,
    set_config_filename,
    )
from provisioningserver.testing.config import ConfigFixture
from testtools.matchers import (
    MatchesException,
    Raises,
    )


class TestConfigFixture(TestCase):
    """Tests for `provisioningserver.testing.config.ConfigFixture`."""

    def test_use_minimal(self):
        # With no arguments, ConfigFixture can arrange a minimal global
        # configuration.
        dummy_cached_config = object()
        dummy_cached_config_filename = object()
        self.patch(provisioningserver.config, "config", dummy_cached_config)
        self.patch(
            provisioningserver.config, "config_filename",
            dummy_cached_config_filename)
        self.assertIs(dummy_cached_config, provisioningserver.config.get())
        self.assertIs(
            dummy_cached_config_filename,
            provisioningserver.config.config_filename)
        with ConfigFixture():
            config = provisioningserver.config.get()
            config_filename = provisioningserver.config.config_filename
            self.assertIsNot(dummy_cached_config, config)
            self.assertIsNot(dummy_cached_config_filename, config_filename)
            self.assertIsInstance(config, dict)
        self.assertIs(dummy_cached_config, provisioningserver.config.get())
        self.assertIs(
            dummy_cached_config_filename,
            provisioningserver.config.config_filename)

    def test_use_with_config(self):
        # Given a configuration, ConfigFixture can arrange a minimal global
        # configuration with the additional options merged in.
        dummy_cached_config = object()
        dummy_logfile = factory.make_name("logfile")
        self.patch(provisioningserver.config, "config", dummy_cached_config)
        self.assertIs(dummy_cached_config, provisioningserver.config.get())
        with ConfigFixture({"logfile": dummy_logfile}):
            config = provisioningserver.config.get()
            self.assertIsNot(dummy_cached_config, config)
            self.assertIsInstance(config, dict)
            self.assertEqual(dummy_logfile, config["logfile"])
        self.assertIs(dummy_cached_config, provisioningserver.config.get())


class TestGetConfigFilename(TestCase):
    """Tests for `provisioningserver.config.get_config_filename`."""

    def setUp(self):
        super(TestGetConfigFilename, self).setUp()
        # Clear config_filename to ensure a consistent starting point.
        self.patch(provisioningserver.config, "config_filename", None)

    def test_call_with_environment(self):
        # get_config_filename() returns the value of MAAS_PROVISION_SETTINGS
        # when it's defined in the environment.
        dummy_config_filename = factory.make_name("config")
        self.useFixture(
            EnvironmentVariableFixture(
                "MAAS_PROVISION_SETTINGS", dummy_config_filename))
        self.assertEquals(dummy_config_filename, get_config_filename())

    def test_call_without_environment(self):
        # get_config_filename() returns a hard-coded path when
        # MAAS_PROVISION_SETTINGS is not defined in the environment.
        self.useFixture(
            EnvironmentVariableFixture("MAAS_PROVISION_SETTINGS", None))
        self.assertEquals("/etc/maas/pserv.yaml", get_config_filename())

    def test_call_when_set(self):
        # get_config_filename() returns the value of config_filename when it
        # has already been defined.
        dummy_config_filename = factory.make_name("config")
        self.patch(
            provisioningserver.config, "config_filename",
            dummy_config_filename)
        self.assertEquals(dummy_config_filename, get_config_filename())


class TestSetConfigFilename(TestCase):
    """Tests for `provisioningserver.config.set_config_filename`."""

    def setUp(self):
        super(TestSetConfigFilename, self).setUp()
        # Clear config_filename to ensure a consistent starting point.
        self.patch(provisioningserver.config, "config_filename", None)

    def test_call_with_no_prior_setting(self):
        # set_config_filename() sets config_filename when it has not
        # previously been defined.
        dummy_config_filename = factory.make_name("config")
        set_config_filename(dummy_config_filename)
        self.assertEquals(
            dummy_config_filename,
            provisioningserver.config.config_filename)

    def test_call_with_prior_setting(self):
        # set_config_filename() raises ValueError when config_filename has
        # already been set.
        self.patch(
            provisioningserver.config, "config_filename",
            factory.make_name("existing-config"))
        self.assertRaises(
            ValueError, set_config_filename,
            factory.make_name("updated-config"))

    def test_call_with_config_already_set(self):
        # set_config_filename() raises ValueError when config has already been
        # set.
        self.patch(provisioningserver.config, "config", object())
        self.assertRaises(
            ValueError, set_config_filename,
            factory.make_name("updated-config"))

    def test_call_with_same_filename(self):
        # set_config_filename() ignores calls to set the filename when it's
        # identical to an already set filename.
        dummy_config_filename = factory.make_name("config")
        set_config_filename(dummy_config_filename)
        set_config_filename(dummy_config_filename)


class TestGet(TestCase):
    """Tests for `provisioningserver.config.get`."""

    def test_get(self):
        # When the configuration has not yet been loaded, get() loads the
        # configuration file returned from get_config_filename().
        dummy_config = object()
        dummy_config_filename = factory.make_name("config")

        # Create a mock Config object that expects a load() call.
        mocker = Mocker()
        mock_Config = mocker.mock()
        mock_Config.load(dummy_config_filename)
        mocker.result(dummy_config)

        # Clear cached config, and patch in the mock Config class.
        self.patch(provisioningserver.config, "config", None)
        self.patch(
            provisioningserver.config, "config_filename",
            dummy_config_filename)
        self.patch(provisioningserver.config, "Config", mock_Config)

        with mocker:
            config = provisioningserver.config.get()

        self.assertIs(dummy_config, config)

    def test_get_config_already_cached(self):
        # When the configuration has already been loaded it is returned
        # without reloading the configuration.
        dummy_config = object()

        # Create a mock Config object that expects that it will not be used.
        mocker = Mocker()
        mock_Config = mocker.mock()

        # Set the cached config, and patch in the mock Config class.
        self.patch(provisioningserver.config, "config", dummy_config)
        self.patch(provisioningserver.config, "Config", mock_Config)

        with mocker:
            config = provisioningserver.config.get()

        self.assertIs(dummy_config, config)


class TestConfig(TestCase):
    """Tests for `provisioningserver.config.Config`."""

    def test_defaults(self):
        mandatory = {
            'password': 'killing_joke',
            }
        expected = {
            'broker': {
                'host': 'localhost',
                'port': 5673,
                'username': getuser(),
                'password': 'test',
                'vhost': '/',
                },
            'cobbler': {
                'url': 'http://localhost/cobbler_api',
                'username': getuser(),
                'password': 'test',
                },
            'logfile': 'pserv.log',
            'oops': {
                'directory': '',
                'reporter': '',
                },
            'tftp': {
                'generator': 'http://localhost:5243/api/1.0/pxeconfig',
                'port': 5244,
                'root': "/var/lib/tftpboot",
                },
            'interface': '127.0.0.1',
            'port': 5241,
            'username': getuser(),
            }
        expected.update(mandatory)
        observed = Config.to_python(mandatory)
        self.assertEqual(expected, observed)

    def test_parse(self):
        # Configuration can be parsed from a snippet of YAML.
        observed = Config.parse(
            b'logfile: "/some/where.log"\n'
            b'password: "black_sabbath"\n'
            )
        self.assertEqual("/some/where.log", observed["logfile"])

    def test_load(self):
        # Configuration can be loaded and parsed from a file.
        config = dedent("""
            logfile: "/some/where.log"
            password: "megadeth"
            """)
        filename = self.make_file(name="config.yaml", contents=config)
        observed = Config.load(filename)
        self.assertEqual("/some/where.log", observed["logfile"])

    def test_load_example(self):
        # The example configuration can be loaded and validated.
        filename = os.path.join(
            os.path.dirname(__file__), os.pardir,
            os.pardir, os.pardir, "etc", "pserv.yaml")
        Config.load(filename)

    def test_oops_directory_without_reporter(self):
        # It is an error to omit the OOPS reporter if directory is specified.
        config = (
            'oops:\n'
            '  directory: /tmp/oops\n'
            )
        expected = MatchesException(
            formencode.Invalid, "oops: You must give a value for reporter")
        self.assertThat(
            partial(Config.parse, config),
            Raises(expected))

    def test_field(self):
        self.assertIs(Config, Config.field())
        self.assertIs(Config.fields["tftp"], Config.field("tftp"))
        self.assertIs(
            Config.fields["tftp"].fields["root"],
            Config.field("tftp", "root"))
