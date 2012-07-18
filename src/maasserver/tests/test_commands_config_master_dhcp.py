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

from django.core.management import call_command
from maasserver.models import NodeGroup
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from testtools.matchers import MatchesStructure


def make_master_constants():
    """Return the standard, unchanging config for the master nodegroup."""
    return {
        'name': 'master',
        'worker_ip': '127.0.0.1',
    }


def make_dhcp_settings():
    """Return an arbitrary dict of DHCP settings."""
    return {
        'subnet_mask': '255.255.0.0',
        'broadcast_ip': '10.111.255.255',
        'router_ip': factory.getRandomIPAddress(),
        'ip_range_low': '10.111.123.9',
        'ip_range_high': '10.111.244.18',
    }


class TestConfigMasterDHCP(TestCase):

    def test_configures_dhcp_for_master_nodegroup(self):
        settings = make_dhcp_settings()
        call_command('config_master_dhcp', **settings)
        master = NodeGroup.objects.get(name='master')
        self.assertThat(
            master,
            MatchesStructure.fromExample(make_master_constants()))
        self.assertThat(master, MatchesStructure.fromExample(settings))

    def test_clears_dhcp_settings(self):
        master = NodeGroup.objects.ensure_master()
        for attribute, value in make_dhcp_settings():
            setattr(master, attribute, value)
        master.save()
        call_command('config_master_dhcp', disable=True)
        self.assertThat(
            master,
            MatchesStructure.fromExample(make_master_constants()))
        self.assertThat(master, MatchesStructure.fromExample({
            setting: None
            for setting in make_dhcp_settings().keys()}))

    def test_does_not_accept_partial_dhcp_settings(self):
        settings = make_dhcp_settings()
        del settings['subnet_mask']
        self.assertRaises(
            Exception,
            call_command, 'config_master_dhcp', **settings)
