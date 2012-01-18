"""
Test maasserver models.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from maasserver.models import Node, MACAddress


class NodeTest(TestCase):

    def setUp(self):
        self.node = Node()
        self.node.save()

    def test_system_id(self):
        """
        The generated system_id looks good.

        """
        self.assertEqual(len(self.node.system_id), 41)
        self.assertTrue(self.node.system_id.startswith('node-'))

    def test_addMACAddress(self):
        self.node.addMACAddress('AA:BB:CC:DD:EE:FF')
        macs = MACAddress.objects.filter(
            node=self.node, mac_address='AA:BB:CC:DD:EE:FF').count()
        self.assertEqual(1, macs)

    def test_removeMACAddress(self):
        self.node.addMACAddress('AA:BB:CC:DD:EE:FF')
        self.node.removeMACAddress('AA:BB:CC:DD:EE:FF')
        macs = MACAddress.objects.filter(
            node=self.node, mac_address='AA:BB:CC:DD:EE:FF').count()
        self.assertEqual(0, macs)


class MACAddressTest(TestCase):

    def make_MAC(self, address):
        """Create a MAC address."""
        node = Node()
        node.save()
        return MACAddress(mac_address=address, node=node)

    def test_stores_to_database(self):
        mac = self.make_MAC('00:11:22:33:44:55')
        mac.save()
        self.assertEqual([mac], list(MACAddress.objects.all()))

    def test_invalid_address_raises_validation_error(self):
        mac = self.make_MAC('AA:BB:CCXDD:EE:FF')
        self.assertRaises(ValidationError, mac.full_clean)
