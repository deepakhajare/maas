# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for :class:`NodeGroupInterface`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maasserver.enum import (
    NODEGROUP_STATUS,
    NODEGROUPINTERFACE_MANAGEMENT,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from netaddr import IPNetwork


def make_interface():
    nodegroup = factory.make_node_group(
        status=NODEGROUP_STATUS.ACCEPTED,
        management=NODEGROUPINTERFACE_MANAGEMENT.DHCP_AND_DNS)
    return nodegroup.get_managed_interface()


class TestNodeGroupInterface(TestCase):

    def test_network_is_defined_when_broadcast_and_mask_are(self):
        interface = make_interface()
        self.assertIsInstance(interface.network, IPNetwork)

    def test_network_is_undefined_when_broadcast_is_None(self):
        interface = make_interface()
        interface.broadcast_ip = None
        self.assertIsNone(interface.network)

    def test_network_is_undefined_when_broadcast_is_empty(self):
        interface = make_interface()
        interface.broadcast_ip = ""
        self.assertIsNone(interface.network)

    def test_network_is_undefined_when_subnet_mask_is_None(self):
        interface = make_interface()
        interface.subnet_mask = None
        self.assertIsNone(interface.network)

    def test_network_is_undefined_subnet_mask_is_empty(self):
        interface = make_interface()
        interface.subnet_mask = ""
        self.assertIsNone(interface.network)