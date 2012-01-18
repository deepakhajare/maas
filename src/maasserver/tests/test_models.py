# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver models."""

from __future__ import print_function

__metaclass__ = type
__all__ = []

from maas.testing import TestCase
from maasserver.models import Node, MACAddress
from django.core.exceptions import ValidationError


class NodeTest(TestCase):

    def test_system_id(self):
        """
        The generated system_id looks good.

        """
        node = Node()
        self.assertEqual(len(node.system_id), 41)
        self.assertTrue(node.system_id.startswith('node-'))


class MACAddressTest(TestCase):

    def test_mac_address_invalid(self):
        """
        An invalid MAC address does not pass the model validation phase.

        """
        node = Node()
        node.save()
        mac = MACAddress(mac_address='AA:BB:CCXDD:EE:FF', node=node)
        self.assertRaises(ValidationError, mac.full_clean)

    def test_mac_address_valid(self):
        """
        A valid MAC address passes the model validation phase.

        """
        node = Node()
        node.save()
        mac = MACAddress(mac_address='AA:BB:CC:DD:EE:FF', node=node)
        mac.full_clean()  # No exception.
