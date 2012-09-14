# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the config_master_dhcp command."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from optparse import OptionValueError

from django.core.management import call_command
from maasserver.enum import DNS_DHCP_MANAGEMENT, NODEGROUPINTERFACE_MANAGEMENT
from maasserver.management.commands.config_master_dhcp import name_option
from maasserver.models import (
    Config,
    NodeGroup,
    )
from maasserver.testing import disable_dhcp_management
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from testtools.matchers import MatchesStructure


def make_master_constants():
    """Return the standard, unchanging config for the master nodegroup."""
    return {
        'name': 'master',
    }


def make_dhcp_settings():
    """Return an arbitrary dict of DHCP settings."""
    return {
        'ip': '10.111.123.10',
        'interface': factory.make_name('interface'),
        'subnet_mask': '255.255.0.0',
        'broadcast_ip': '10.111.255.255',
        'router_ip': factory.getRandomIPAddress(),
        'ip_range_low': '10.111.123.9',
        'ip_range_high': '10.111.244.18',
    }


def make_cleared_dhcp_settings():
    """Return dict of cleared DHCP settings."""
    return {
        setting: None
        for setting in make_dhcp_settings().keys()}


class TestConfigMasterDHCP(TestCase):

    def setUp(self):
        super(TestConfigMasterDHCP, self).setUp()
        # Make sure any attempts to write a dhcp config do nothing.
        self.patch(NodeGroup, 'set_up_dhcp')

    def test_configures_dhcp_for_master_nodegroup(self):
        settings = make_dhcp_settings()
        call_command('config_master_dhcp', **settings)
        master = NodeGroup.objects.get(name='master')
        interface = master.get_managed_interface()
        self.assertThat(
            master,
            MatchesStructure.fromExample(make_master_constants()))
        self.assertThat(interface, MatchesStructure.byEquality(**settings))
        self.assertEqual(
            NODEGROUPINTERFACE_MANAGEMENT.DHCP, interface.management)

    def test_re_configures_dhcp_for_master_nodegroup(self):
        management = NODEGROUPINTERFACE_MANAGEMENT.DHCP_AND_DNS
        master = factory.make_node_group(name='master', management=management)
        settings = make_dhcp_settings()
        call_command('config_master_dhcp', **settings)
        master = NodeGroup.objects.get(name='master')
        interface = master.get_managed_interface()
        self.assertThat(interface, MatchesStructure.byEquality(**settings))
        # master's management has been preserved.
        self.assertEqual(management, interface.management)

    def test_clears_dhcp_settings(self):
        master = NodeGroup.objects.ensure_master()
        for attribute, value in make_dhcp_settings().items():
            setattr(master, attribute, value)
        master.save()
        call_command('config_master_dhcp', clear=True)
        self.assertThat(
            master,
            MatchesStructure.byEquality(**make_master_constants()))
        self.assertIsNone(master.get_managed_interface())

    def test_does_not_accept_partial_dhcp_settings(self):
        settings = make_dhcp_settings()
        del settings['subnet_mask']
        self.assertRaises(
            OptionValueError,
            call_command, 'config_master_dhcp', **settings)

    def test_ignores_nonsense_settings_when_clear_is_passed(self):
        settings = make_dhcp_settings()
        call_command('config_master_dhcp', **settings)
        settings['subnet_mask'] = '@%$^&'
        settings['broadcast_ip'] = ''
        call_command('config_master_dhcp', clear=True, **settings)
        master = NodeGroup.objects.get(name='master')
        self.assertIsNone(master.get_managed_interface())

    def test_clear_conflicts_with_ensure(self):
        self.assertRaises(
            OptionValueError,
            call_command, 'config_master_dhcp', clear=True, ensure=True)

    def test_ensure_creates_master_nodegroup_without_dhcp_settings(self):
        call_command('config_master_dhcp', ensure=True)
        self.assertThat(
            NodeGroup.objects.get(name='master'),
            MatchesStructure.fromExample(make_cleared_dhcp_settings()))

    def test_ensure_leaves_cleared_settings_cleared(self):
        call_command('config_master_dhcp', clear=True)
        call_command('config_master_dhcp', ensure=True)
        master = NodeGroup.objects.get(name='master')
        self.assertIsNone(master.get_managed_interface())

    def test_ensure_leaves_dhcp_settings_intact(self):
        settings = make_dhcp_settings()
        call_command('config_master_dhcp', **settings)
        call_command('config_master_dhcp', ensure=True)
        self.assertThat(
            NodeGroup.objects.get(name='master'),
            MatchesStructure.fromExample(settings))

    def test_name_option_turns_dhcp_setting_name_into_option(self):
        self.assertEqual('--subnet-mask', name_option('subnet_mask'))

    def test_sets_up_dhcp_and_enables_it(self):
        master = NodeGroup.objects.ensure_master()
        settings = make_dhcp_settings()
        disable_dhcp_management()
        call_command('config_master_dhcp', **settings)
        self.assertEqual(1, master.set_up_dhcp.call_count)
        self.assertEqual(
            Config.objects.get_config('dns_dhcp_management'),
            DNS_DHCP_MANAGEMENT.DHCP_ONLY)

    def test_sets_up_dhcp_preserves_dns_dhcp_setting_if_dhcp_enabled(self):
        master = NodeGroup.objects.ensure_master()
        settings = make_dhcp_settings()
        dns_dhcp_config = DNS_DHCP_MANAGEMENT.DNS_AND_DHCP
        Config.objects.set_config('dns_dhcp_management', dns_dhcp_config)
        call_command('config_master_dhcp', **settings)
        self.assertEqual(1, master.set_up_dhcp.call_count)
        self.assertEqual(
            Config.objects.get_config('dns_dhcp_management'),
            dns_dhcp_config)
