# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the install_pxe_bootloader command."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os.path

from django.core.management import call_command
from maasserver.management.commands.install_pxe_bootloader import (
    install_bootloader,
    make_destination,
    )
from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.pxe.tftppath import (
    compose_bootloader_path,
    locate_tftp_path,
    )
from testtools.matchers import FileContains


class TestInstallPXEBootloader(TestCase):

    def test_integration(self):
        contents = factory.getRandomString()
        loader = self.make_file(contents=contents)
        tftproot = self.make_dir()
        arch = factory.make_name('arch')
        subarch = factory.make_name('subarch')

        call_command(
            'install_pxe_bootloader', arch=arch, subarch=subarch,
            loader=loader, tftproot=tftproot)

        self.assertThat(
            locate_tftp_path(
                compose_bootloader_path(arch, subarch), tftproot=tftproot),
            FileContains(contents))

    def test_make_destination_creates_directory_if_not_present(self):
        self.fail("TEST THIS")

    def test_make_destination_returns_existing_directory(self):
        self.fail("TEST THIS")

    def test_install_bootloader_installs_new_bootloader(self):
        self.fail("TEST THIS")

    def test_install_bootloader_replaces_bootloader_if_changed(self):
        self.fail("TEST THIS")

    def test_install_bootloader_skips_if_unchanged(self):
        self.fail("TEST THIS")

    def test_install_bootloader_sweeps_aside_dot_new_if_any(self):
        self.fail("TEST THIS")
