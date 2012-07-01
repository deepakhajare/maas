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
from maastesting.utils import (
    age_file,
    get_write_time,
    )
from provisioningserver.pxe.tftppath import (
    compose_bootloader_path,
    locate_tftp_path,
    )
from testtools.matchers import (
    DirExists,
    FileContains,
    FileExists,
    Not,
    )


class TestInstallPXEBootloader(TestCase):

    def test_integration(self):
        loader = self.make_file()
        tftproot = self.make_dir()
        arch = factory.make_name('arch')
        subarch = factory.make_name('subarch')

        call_command(
            'install_pxe_bootloader', arch=arch, subarch=subarch,
            loader=loader, tftproot=tftproot)

        self.assertThat(
            locate_tftp_path(
                compose_bootloader_path(arch, subarch), tftproot=tftproot),
            FileExists())
        self.assertThat(loader, Not(FileExists()))

    def test_make_destination_creates_directory_if_not_present(self):
        tftproot = self.make_dir()
        arch = factory.make_name('arch')
        subarch = factory.make_name('subarch')
        dest = make_destination(tftproot, arch, subarch)
        self.assertThat(os.path.dirname(dest), DirExists())

    def test_make_destination_returns_existing_directory(self):
        tftproot = self.make_dir()
        arch = factory.make_name('arch')
        subarch = factory.make_name('subarch')
        make_destination(tftproot, arch, subarch)
        dest = make_destination(tftproot, arch, subarch)
        self.assertThat(os.path.dirname(dest), DirExists())

    def test_install_bootloader_installs_new_bootloader(self):
        contents = factory.getRandomString()
        loader = self.make_file(contents=contents)
        install_dir = self.make_dir()
        dest = os.path.join(install_dir, factory.make_name('loader'))
        install_bootloader(loader, dest)
        self.assertThat(dest, FileContains(contents))

    def test_install_bootloader_replaces_bootloader_if_changed(self):
        contents = factory.getRandomString()
        loader = self.make_file(contents=contents)
        dest = self.make_file(contents="Old contents")
        install_bootloader(loader, dest)
        self.assertThat(dest, FileContains(contents))

    def test_install_bootloader_skips_if_unchanged(self):
        contents = factory.getRandomString()
        dest = self.make_file(contents=contents)
        age_file(dest, 100)
        original_write_time = get_write_time(dest)
        loader = self.make_file(contents=contents)
        install_bootloader(loader, dest)
        self.assertThat(dest, FileContains(contents))
        self.assertEqual(original_write_time, get_write_time(dest))

    def test_install_bootloader_sweeps_aside_dot_new_if_any(self):
        contents = factory.getRandomString()
        loader = self.make_file(contents=contents)
        dest = self.make_file(contents="Old contents")
        temp_file = '%s.new' % dest
        factory.make_file(
            os.path.dirname(temp_file), name=os.path.basename(temp_file))
        install_bootloader(loader, dest)
        self.assertThat(dest, FileContains(contents))