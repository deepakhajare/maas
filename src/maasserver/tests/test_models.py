"""
Test maasserver models.
"""

from django.test import TestCase
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

    def make_MAC(self, address):
        """Create a MAC address."""
        node = Node()
        node.save()
        return MACAddress(mac_address=address, node=node)

    def test_invalid_address_raises_validation_error(self):
        mac = self.make_MAC('AA:BB:CCXDD:EE:FF')
        self.assertRaises(ValidationError, mac.full_clean)

    def test_valid_address_passes_validation(self):
        mac = self.make_MAC('AA:BB:CC:DD:EE:FF')
        mac.full_clean()  # No exception.

    def test_mac_address_is_stored_and_retrieved(self):
        stored_mac = self.make_MAC('001122334455')
        stored_mac.save()
        [loaded_mac] = MACAddress.objects.filter(id=stored_mac.id)
        self.assertEqual('00:11:22:33:44:55', loaded_mac.mac_address)
