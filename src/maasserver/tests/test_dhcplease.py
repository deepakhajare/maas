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

from maasserver.models.dhcplease import (
    DHCPLease,
    DHCPLeaseManager,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase


class TestDHCPLease(TestCase):
    """Tests for :class:`DHCPLease`."""

    def test_init(self):
        nodegroup = factory.make_node_group()
        ip = factory.getRandomIPAddress()
        mac = factory.getRandomMACAddress()

        lease = DHCPLease(nodegroup=nodegroup, ip=ip, mac=mac)
        lease.save()

        self.assertEqual(nodegroup, lease.nodegroup)
        self.assertEqual(ip, lease.ip)
        self.assertEqual(mac, lease.mac)


class TestDHCPLeaseManager(TestCase):
    """Tests for :class:`DHCPLeaseManager`."""

    def test_update_accepts_empty_leases(self):
        self.fail("TEST THIS")

    def test_update_creates_new_lease(self):
        self.fail("TEST THIS")

    def test_update_deletes_obsolete_lease(self):
        self.fail("TEST THIS")

    def test_update_replaces_reassigned_ip(self):
        self.fail("TEST THIS")

    def test_update_replaces_changed_mac(self):
        self.fail("TEST THIS")
