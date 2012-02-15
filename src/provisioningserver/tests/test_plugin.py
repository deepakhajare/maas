# Copyright 2005-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the psmaas TAP."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from functools import partial
import os
from unittest import skip

from fixtures import TempDir
from provisioningserver.plugin import (
    Config,
    Options,
    ProvisioningServiceMaker,
    )
from testtools import TestCase
from testtools.matchers import (
    MatchesException,
    Raises,
    )
from twisted.application.service import MultiService
from twisted.python.usage import UsageError


class TestConfig(TestCase):
    """Tests for `provisioningserver.plugin.Config`."""

    def test_defaults(self):
        expected = {
            'broker': {
                'host': 'localhost',
                'password': '',
                'port': 5673,
                'username': '',
                'vhost': u'/',
                },
            'logfile': '/some/where.log',
            'oops': {
                'directory': '',
                'reporter': '',
                },
            'port': 8001,
            }
        mandatory_arguments = {
            "logfile": "/some/where.log",
            }
        observed = Config.to_python(mandatory_arguments)
        self.assertEqual(expected, observed)

    def test_parse(self):
        # Configuration can be parsed from a snipped of YAML.
        observed = Config.parse(
            b'logfile: "/some/where.log"')
        self.assertEqual("/some/where.log", observed["logfile"])

    def test_load(self):
        # Configuration can be loaded and parsed from a file.
        filename = os.path.join(
            self.useFixture(TempDir()).path, "config.yaml")
        with open(filename, "wb") as stream:
            stream.write(b'logfile: "/some/where.log"')
        observed = Config.load(filename)
        self.assertEqual("/some/where.log", observed["logfile"])

    def test_load_example(self):
        # The example configuration can be loaded and validated.
        filename = os.path.join(
            os.path.dirname(__file__), "pserv.example.yaml")
        Config.load(filename)


class TestOptions(TestCase):
    """Tests for `provisioningserver.plugin.Options`."""

    @skip(
        "RabbitMQ is not yet a required component "
        "of a running MaaS installation. Re-enable "
        "when RabbitMQ is once again needed; remove "
        "the other similarly named test.")
    def test_defaults_SKIPPED(self):
        options = Options()
        expected = {
            "brokerhost": "127.0.0.1",
            "brokerpassword": None,
            "brokerport": 5672,
            "brokeruser": None,
            "brokervhost": "/",
            "logfile": "pserv.log",
            "oops-dir": None,
            "oops-reporter": "MAAS-PS",
            "port": 8001,
            }
        self.assertEqual(expected, options.defaults)

    def test_defaults(self):
        options = Options()
        expected = {
            "logfile": "pserv.log",
            "oops-dir": None,
            "oops-reporter": "MAAS-PS",
            "port": 8001,
            }
        self.assertEqual(expected, options.defaults)

    def check_exception(self, options, message, *arguments):
        # Check that a UsageError is raised when parsing options.
        self.assertThat(
            partial(options.parseOptions, arguments),
            Raises(MatchesException(UsageError, message)))

    @skip(
        "RabbitMQ is not yet a required component "
        "of a running MaaS installation.")
    def test_option_brokeruser_required(self):
        options = Options()
        self.check_exception(
            options,
            "--brokeruser must be specified")

    @skip(
        "RabbitMQ is not yet a required component "
        "of a running MaaS installation.")
    def test_option_brokerpassword_required(self):
        options = Options()
        self.check_exception(
            options,
            "--brokerpassword must be specified",
            "--brokeruser", "Bob")

    def test_parse_minimal_options(self):
        options = Options()
        # The minimal set of options that must be provided.
        arguments = []
        options.parseOptions(arguments)  # No error.

    @skip(
        "RabbitMQ is not yet a required component "
        "of a running MaaS installation. Re-enable "
        "when RabbitMQ is once again needed; remove "
        "the other similarly named test.")
    def test_parse_int_options_SKIPPED(self):
        # Some options are converted to ints.
        options = Options()
        arguments = [
            "--brokerpassword", "Hoskins",
            "--brokerport", "4321",
            "--brokeruser", "Bob",
            "--port", "3456",
            ]
        options.parseOptions(arguments)
        self.assertEqual(4321, options["brokerport"])
        self.assertEqual(3456, options["port"])

    def test_parse_int_options(self):
        # Some options are converted to ints.
        options = Options()
        arguments = [
            "--port", "3456",
            ]
        options.parseOptions(arguments)
        self.assertEqual(3456, options["port"])

    @skip(
        "RabbitMQ is not yet a required component "
        "of a running MaaS installation. Re-enable "
        "when RabbitMQ is once again needed; remove "
        "the other similarly named test.")
    def test_parse_broken_int_options_SKIPPED(self):
        # An error is raised if the integer options do not contain integers.
        options = Options()
        arguments = [
            "--brokerpassword", "Hoskins",
            "--brokerport", "Jr.",
            "--brokeruser", "Bob",
            ]
        self.assertRaises(
            UsageError, options.parseOptions, arguments)

    def test_parse_broken_int_options(self):
        # An error is raised if the integer options do not contain integers.
        options = Options()
        arguments = [
            "--port", "Metallica",
            ]
        self.assertRaises(
            UsageError, options.parseOptions, arguments)

    @skip(
        "RabbitMQ is not yet a required component "
        "of a running MaaS installation. Re-enable "
        "when RabbitMQ is once again needed; remove "
        "the other similarly named test.")
    def test_oops_dir_without_reporter_SKIPPED(self):
        # It is an error to omit the OOPS reporter if directory is specified.
        options = Options()
        arguments = [
            "--brokerpassword", "Hoskins",
            "--brokeruser", "Bob",
            "--oops-dir", "/some/where",
            "--oops-reporter", "",
            ]
        expected = MatchesException(
            UsageError, "A reporter must be supplied")
        self.assertThat(
            partial(options.parseOptions, arguments),
            Raises(expected))

    def test_oops_dir_without_reporter(self):
        # It is an error to omit the OOPS reporter if directory is specified.
        options = Options()
        arguments = [
            "--oops-dir", "/some/where",
            "--oops-reporter", "",
            ]
        expected = MatchesException(
            UsageError, "A reporter must be supplied")
        self.assertThat(
            partial(options.parseOptions, arguments),
            Raises(expected))


class TestProvisioningServiceMaker(TestCase):
    """Tests for `provisioningserver.plugin.ProvisioningServiceMaker`."""

    def get_log_file(self):
        return os.path.join(
            self.useFixture(TempDir()).path, "pserv.log")

    def test_init(self):
        service_maker = ProvisioningServiceMaker("Harry", "Hill")
        self.assertEqual("Harry", service_maker.tapname)
        self.assertEqual("Hill", service_maker.description)

    def test_makeService(self):
        """
        Only the site service is created when no options are given.
        """
        options = Options()
        options["logfile"] = self.get_log_file()
        service_maker = ProvisioningServiceMaker("Harry", "Hill")
        service = service_maker.makeService(options, _set_proc_title=False)
        self.assertIsInstance(service, MultiService)
        self.assertSequenceEqual(
            ["log", "oops", "site"],
            sorted(service.namedServices))
        self.assertEqual(
            len(service.namedServices), len(service.services),
            "Not all services are named.")
        site_service = service.getServiceNamed("site")
        self.assertEqual(options["port"], site_service.args[0])

    @skip(
        "RabbitMQ is not yet a required component "
        "of a running MaaS installation.")
    def test_makeService_with_broker(self):
        """
        The log, oops, site, and amqp services are created when the broker
        user and password options are given.
        """
        options = Options()
        options["brokerpassword"] = "Hoskins"
        options["brokeruser"] = "Bob"
        options["logfile"] = self.get_log_file()
        service_maker = ProvisioningServiceMaker("Harry", "Hill")
        service = service_maker.makeService(options, _set_proc_title=False)
        self.assertIsInstance(service, MultiService)
        self.assertSequenceEqual(
            ["amqp", "log", "oops", "site"],
            sorted(service.namedServices))
        self.assertEqual(
            len(service.namedServices), len(service.services),
            "Not all services are named.")
        amqp_client_service = service.getServiceNamed("amqp")
        self.assertEqual(options["brokerhost"], amqp_client_service.args[0])
        self.assertEqual(options["brokerport"], amqp_client_service.args[1])
        site_service = service.getServiceNamed("site")
        self.assertEqual(options["port"], site_service.args[0])
