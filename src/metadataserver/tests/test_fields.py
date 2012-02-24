# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test custom field types."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maasserver.testing import TestModelTestCase
from metadataserver.tests.models import BinaryFieldModel


class TestBinaryField(TestModelTestCase):

    app = 'metadataserver.tests'

    def test_stores_and_retrieves_None(self):
        binary_item = BinaryFieldModel()
        self.assertIsNone(binary_item.data)
        binary_item.save()
        self.assertIsNone(
            BinaryFieldModel.objects.get(id=binary_item.id).data)

    def test_stores_and_retrieves_empty_data(self):
        binary_item = BinaryFieldModel(data=b'')
        self.assertEqual(b'', binary_item.data)
        binary_item.save()
        self.assertEqual(
            b'', BinaryFieldModel.objects.get(id=binary_item.id).data)

    def test_stores_and_retrieves_data(self):
        data = b"\x01\x00\x99"
        binary_item = BinaryFieldModel(data=data)
        self.assertEqual(data, binary_item.data)
        binary_item.save()
        self.assertEqual(
            data, BinaryFieldModel.objects.get(id=binary_item.id).data)

    def test_returns_bytes_not_text(self):
        binary_item = BinaryFieldModel(data=b"Data")
        binary_item.save()
        retrieved_data = BinaryFieldModel.objects.get(id=binary_item.id).data
        self.assertIsInstance(retrieved_data, str)

    def test_looks_up_data(self):
        data = b"Binary item"
        binary_item = BinaryFieldModel(data=data)
        binary_item.save()
        self.assertEqual(binary_item, BinaryFieldModel.objects.get(data=data))
