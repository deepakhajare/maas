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

from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.pxe.tftppath import compose_config_path
from provisioningserver.tftp.plugin import TFTPBackend
from testtools.deferredruntest import AsynchronousDeferredRunTest


class TestTFTPBackend(TestCase):
    """Tests for `provisioningserver.tftp.plugin.TFTPBackend`."""

    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=5)

    def setUp(self):
        super(TestTFTPBackend, self).setUp()
        self.tempdir = self.make_dir()

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
