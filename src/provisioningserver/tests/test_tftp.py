# Copyright 2005-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the maastftp Twisted plugin."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from os import path
from urllib import urlencode
from urlparse import (
    parse_qsl,
    urlparse,
    )

from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.pxe.tftppath import compose_config_path
from provisioningserver.tftp import (
    BytesReader,
    TFTPBackend,
    )
from testtools.deferredruntest import AsynchronousDeferredRunTest
from tftp.backend import IReader
from twisted.internet.defer import (
    inlineCallbacks,
    succeed,
    )
from zope.interface.verify import verifyObject


class TestBytesReader(TestCase):
    """Tests for `provisioningserver.tftp.BytesReader`."""

    def test_interfaces(self):
        reader = BytesReader(b"")
        self.addCleanup(reader.finish)
        verifyObject(IReader, reader)

    def test_read(self):
        data = factory.getRandomString(size=10).encode("ascii")
        reader = BytesReader(data)
        self.addCleanup(reader.finish)
        self.assertEqual(data[:7], reader.read(7))
        self.assertEqual(data[7:], reader.read(7))
        self.assertEqual(b"", reader.read(7))

    def test_finish(self):
        reader = BytesReader(b"1234")
        reader.finish()
        self.assertRaises(ValueError, reader.read, 1)


class TestTFTPBackend(TestCase):
    """Tests for `provisioningserver.tftp.TFTPBackend`."""

    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=5)

    def test_re_config_file(self):
        # The regular expression for extracting components of the file path is
        # compatible with the PXE config path generator.
        regex = TFTPBackend.re_config_file
        for iteration in range(10):
            args = {
                "arch": factory.getRandomString(),
                "subarch": factory.getRandomString(),
                "name": factory.getRandomString(),
                }
            config_path = compose_config_path(**args)
            # Remove leading slash from config path; the TFTP server does not
            # include them in paths.
            config_path = config_path.lstrip("/")
            match = regex.match(config_path)
            self.assertIsNotNone(match, config_path)
            self.assertEqual(args, match.groupdict())

    def test_init(self):
        temp_dir = self.make_dir()
        generator_url = "http://%s.example.com/%s" % (
            factory.getRandomString(), factory.getRandomString())
        backend = TFTPBackend(temp_dir, generator_url)
        self.assertEqual((True, False), (backend.can_read, backend.can_write))
        self.assertEqual(temp_dir, backend.base.path)
        self.assertEqual(generator_url, backend.generator_url.geturl())

    def test_get_reader_regular_file(self):
        # TFTPBackend.get_reader() returns a regular FilesystemReader for
        # paths not matching re_config_file.
        data = factory.getRandomString().encode("ascii")
        temp_dir = self.make_dir()
        temp_file = path.join(temp_dir, "example")
        with open(temp_file, "wb") as stream:
            stream.write(data)
        backend = TFTPBackend(temp_dir, "http://nowhere.example.com/")
        reader = backend.get_reader("example")
        self.addCleanup(reader.finish)
        self.assertEqual(len(data), reader.size)
        self.assertEqual(data, reader.read(len(data)))
        self.assertEqual(b"", reader.read(1))

    @inlineCallbacks
    def test_get_reader_config_file(self):
        # TFTPBackend.get_reader() returns a BytesReader for paths matching
        # re_config_file.
        arch = factory.getRandomString().encode("ascii")
        subarch = factory.getRandomString().encode("ascii")
        name = factory.getRandomString().encode("ascii")
        kernelimage = factory.getRandomString().encode("ascii")
        menutitle = factory.getRandomString().encode("ascii")
        append = factory.getRandomString().encode("ascii")
        backend_url = "http://example.com/?" + urlencode(
            {b"kernelimage": kernelimage, b"menutitle": menutitle,
             b"append": append})
        config_path = compose_config_path(arch, subarch, name)
        backend = TFTPBackend(self.make_dir(), backend_url)
        backend.get_page = succeed  # Return the URL, via a Deferred.
        reader = yield backend.get_reader(config_path.lstrip("/"))
        self.addCleanup(reader.finish)
        self.assertIsInstance(reader, BytesReader)
        url = reader.read(1000)
        query = parse_qsl(urlparse(url).query)
        query_expected = [
            ("append", append),
            ("kernelimage", kernelimage),
            ("arch", arch),
            ("subarch", subarch),
            ("menutitle", menutitle),
            ("name", name),
            ]
        self.assertItemsEqual(query_expected, sorted(query))
