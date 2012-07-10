# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the :class:`DHCPLease` model."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maasserver.models.dhcplease import DHCPLease
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maasserver.utils import ignore_unused


def get_leases(nodegroup):
    """Return DHCPLease records for `nodegroup`."""
    return DHCPLease.objects.filter(nodegroup=nodegroup)


def map_leases(nodegroup):
    """Return IP/MAC mappings dict for leases in `nodegroup`."""
    return {lease.ip: lease.mac for lease in get_leases(nodegroup)}


class TestDHCPLease(TestCase):
    """Tests for :class:`DHCPLease`."""

    def test_init(self):
        nodegroup = factory.make_node_group()
        ip = factory.getRandomIPAddress()
        mac = factory.getRandomMACAddress()

        lease = DHCPLease(nodegroup=nodegroup, ip=ip, mac=mac)
        lease.save()

        self.assertItemsEqual([lease], get_leases(nodegroup))
        self.assertEqual(nodegroup, lease.nodegroup)
        self.assertEqual(ip, lease.ip)
        self.assertEqual(mac, lease.mac)


class TestDHCPLeaseManager(TestCase):
    """Tests for :class:`DHCPLeaseManager`."""

    def test_update_accepts_empty_leases(self):
        nodegroup = factory.make_node_group()
        DHCPLease.objects.update(nodegroup, {})
        self.assertItemsEqual([], get_leases(nodegroup))

    def test_update_creates_new_lease(self):
        nodegroup = factory.make_node_group()
        ip = factory.getRandomIPAddress()
        mac = factory.getRandomMACAddress()
        DHCPLease.objects.update(nodegroup, {ip: mac})
        self.assertEqual({ip: mac}, map_leases(nodegroup))

    def test_update_deletes_obsolete_lease(self):
        nodegroup = factory.make_node_group()
        factory.make_dhcp_lease(nodegroup=nodegroup)
        DHCPLease.objects.update(nodegroup, {})
        self.assertEqual({}, map_leases(nodegroup))

    def test_update_replaces_reassigned_ip(self):
        nodegroup = factory.make_node_group()
        ip = factory.getRandomIPAddress()
        factory.make_dhcp_lease(nodegroup=nodegroup, ip=ip)
        new_mac = factory.getRandomMACAddress()
        DHCPLease.objects.update(nodegroup, {ip: new_mac})
        self.assertEqual({ip: new_mac}, map_leases(nodegroup))

    def test_update_keeps_unchanged_mappings(self):
        lease = factory.make_dhcp_lease()
        lease_id = lease.id
        nodegroup = lease.nodegroup
        DHCPLease.objects.update(nodegroup, {lease.ip: lease.mac})
        self.assertEqual(
            [lease_id],
            [lease.id for lease in map_leases(nodegroup)])

    def test_update_adds_new_ip_to_mac(self):
        nodegroup = factory.make_node_group()
        mac = factory.getRandomMACAddress()
        ip1 = factory.getRandomIPAddress()
        ip2 = factory.getRandomIPAddress()
        factory.make_dhcp_lease(nodegroup=nodegroup, mac=mac, ip=ip1)
        DHCPLease.objects.update(nodegroup, {ip2: mac})
        self.assertEqual({ip1: mac, ip2: mac}, map_leases(nodegroup))

    def test_update_deletes_only_obsolete_ips(self):
        nodegroup = factory.make_node_group()
        mac = factory.getRandomMACAddress()
        obsolete_ip = factory.getRandomIPAddress()
        current_ip = factory.getRandomIPAddress()
        factory.make_dhcp_lease(nodegroup=nodegroup, mac=mac, ip=obsolete_ip)
        factory.make_dhcp_lease(nodegroup=nodegroup, mac=mac, ip=current_ip)
        DHCPLease.objects.update(nodegroup, {current_ip: mac})
        self.assertEqual({current_ip: mac}, map_leases(nodegroup))

    def test_update_leaves_other_nodegroups_alone(self):
        innocent_nodegroup = factory.make_node_group()
        innocent_lease = factory.make_dhcp_lease(nodegroup=innocent_nodegroup)
        DHCPLease.objects.update(
            factory.make_node_group(),
            {factory.getRandomIPAddress(): factory.getRandomMACAddress()})
        self.assertItemsEqual(
            [innocent_lease], get_leases(innocent_nodegroup))

    def test_update_combines_additions_deletions_and_replacements(self):
        nodegroup = factory.make_node_group()
        mac1 = factory.getRandomMACAddress()
        mac2 = factory.getRandomMACAddress()
        obsolete_lease = factory.make_dhcp_lease(
            nodegroup=nodegroup, mac=mac1)
        # The obsolete lease won't be in the update, so it'll disappear.
        ignore_unused(obsolete_lease)
        unchanged_lease = factory.make_dhcp_lease(
            nodegroup=nodegroup, mac=mac1)
        reassigned_lease = factory.make_dhcp_lease(
            nodegroup=nodegroup, mac=mac1)
        new_ip = factory.getRandomIPAddress()
        DHCPLease.objects.update(nodegroup, {
            reassigned_lease.ip: mac2,
            unchanged_lease.ip: mac1,
            new_ip: mac1,
        })
        self.assertEqual(
            {
                reassigned_lease.ip: mac2,
                unchanged_lease.ip: mac1,
                new_ip: mac1,
            },
            map_leases(nodegroup))
