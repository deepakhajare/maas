# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the NodeGroup model."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maasserver.models import NodeGroup
from maasserver.testing import reload_object
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maasserver.worker_user import get_worker_user
from testtools.matchers import MatchesStructure


def make_dhcp_settings():
    """Create a dict of arbitrary nodegroup configuration parameters."""
    return {
        'subnet_mask': '255.0.0.0',
        'broadcast_ip': '10.255.255.255',
        'router_ip': factory.getRandomIPAddress(),
        'ip_range_low': '10.0.0.1',
        'ip_range_high': '10.254.254.254',
    }


class TestNodeGroupManager(TestCase):

    def test_new_does_not_require_dhcp_settings(self):
        name = factory.make_name('nodegroup')
        ip = factory.getRandomIPAddress()
        nodegroup = NodeGroup.objects.new(name, ip)
        self.assertEqual(name, nodegroup.name)
        self.assertEqual(ip, nodegroup.worker_ip)
        self.assertIsNone(nodegroup.subnet_mask)
        self.assertIsNone(nodegroup.broadcast_ip)
        self.assertIsNone(nodegroup.router_ip)
        self.assertIsNone(nodegroup.ip_range_low)
        self.assertIsNone(nodegroup.ip_range_high)

    def test_new_creates_nodegroup_with_given_dhcp_settings(self):
        name = factory.make_name('nodegroup')
        ip = factory.getRandomIPAddress()
        dhcp_settings = make_dhcp_settings()
        nodegroup = NodeGroup.objects.new(name, ip, **dhcp_settings)
        nodegroup = reload_object(nodegroup)
        self.assertEqual(name, nodegroup.name)
        self.assertThat(
            nodegroup, MatchesStructure.fromExample(dhcp_settings))

    def test_new_assigns_token_and_key_for_worker_user(self):
        nodegroup = NodeGroup.objects.new(
            factory.make_name('nodegroup'), factory.getRandomIPAddress())
        self.assertIsNotNone(nodegroup.api_token)
        self.assertIsNotNone(nodegroup.api_key)
        self.assertEqual(get_worker_user(), nodegroup.api_token.user)
        self.assertEqual(nodegroup.api_key, nodegroup.api_token.key)
