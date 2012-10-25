# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the FileStorage model."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import codecs
from io import BytesIO

from maasserver.models import FileStorage
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase


class FileStorageTest(TestCase):
    """Testing of the :class:`FileStorage` model."""

    def make_data(self, including_text='data'):
        """Return arbitrary data.

        :param including_text: Text to include in the data.  Leave something
            here to make failure messages more recognizable.
        :type including_text: basestring
        :return: A string of bytes, including `including_text`.
        :rtype: bytes
        """
        # Note that this won't automatically insert any non-ASCII bytes.
        # Proper handling of real binary data is tested separately.
        text = "%s %s" % (including_text, factory.getRandomString())
        return text.encode('ascii')

    def test_save_file_creates_storage(self):
        filename = factory.getRandomString()
        content = self.make_data()
        storage = FileStorage.objects.save_file(filename, BytesIO(content))
        self.assertEqual(
            (filename, content),
            (storage.filename, storage.content))

    def test_storage_can_be_retrieved(self):
        filename = factory.getRandomString()
        content = self.make_data()
        factory.make_file_storage(filename=filename, content=content)
        storage = FileStorage.objects.get(filename=filename)
        self.assertEqual(
            (filename, content),
            (storage.filename, storage.content))

    def test_stores_binary_data(self):
        # This horrible binary data could never, ever, under any
        # encoding known to man be interpreted as text(1).  Switch the
        # bytes of the byte-order mark around and by design you get an
        # invalid codepoint; put a byte with the high bit set between bytes
        # that have it cleared, and you have a guaranteed non-UTF-8
        # sequence.
        #
        # (1) Provided, of course, that man know only about ASCII and
        # UTF.
        binary_data = codecs.BOM64_LE + codecs.BOM64_BE + b'\x00\xff\x00'

        # And yet, because FileStorage supports binary data, it comes
        # out intact.
        storage = factory.make_file_storage(filename="x", content=binary_data)
        self.assertEqual(binary_data, storage.content)

    def test_overwrites_file(self):
        # If a file of the same name has already been stored, the
        # reference to the old data gets overwritten with one to the new
        # data.
        filename = factory.make_name('filename')
        old_storage = factory.make_file_storage(
            filename=filename, content=self.make_data('old data'))
        new_data = self.make_data('new-data')
        new_storage = factory.make_file_storage(
            filename=filename, content=new_data)
        self.assertEqual(old_storage.filename, new_storage.filename)
        self.assertEqual(
            new_data, FileStorage.objects.get(filename=filename).content)
