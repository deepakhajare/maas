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
