# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the install_pxe_image command."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os

from django.core.management import call_command
from maasserver.management.commands.install_pxe_image import (
    make_destination,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maastesting.utils import (
    age_file,
    get_write_time,
    )
from testtools.matchers import DirExists, FileContains


class TestInstallPXEImage(TestCase):

    def test_installs_new_image(self):
        download_dir = self.make_dir()
        source_dir = factory.getRandomString()
        source_path = os.path.join(download_dir, source_dir)
        os.makedirs(source_path)
        dest = self.make_dir()
        contents = factory.getRandomString()
        testfile = factory.make_file(source_path, contents=contents)
        call_command(
            'install_pxe_image',
            source=source_path, dest=dest)
        self.assertThat(
            os.path.join(dest, source_dir, testfile), FileContains(contents))

    def test_updates_changed_image(self):
        download_dir = self.make_dir()
        source_dir = factory.getRandomString()
        source_path = os.path.join(download_dir, source_dir)
        os.makedirs(source_path)
        dest = self.make_dir()
        dest_path = os.path.join(dest, source_dir)
        contents = "New content"
        testfile = factory.make_file(source_path, contents=contents)
        os.makedirs(dest_path)
        factory.make_file(
            os.path.join(dest_path, testfile), contents="Old content")
        call_command('install_pxe_image', source=source_path, dest=dest)
        self.assertThat(
            os.path.join(dest_path, testfile), FileContains(contents))

    def test_leaves_unchanged_image_untouched(self):
        download_dir = self.make_dir()
        source_dir = factory.getRandomString()
        full_source_path = os.path.join(download_dir, source_dir)
        os.makedirs(full_source_path)
        dest = self.make_dir()
        full_dest_path = os.path.join(dest, source_dir)
        contents = factory.getRandomString()
        testfile = factory.make_file(full_source_path, contents=contents)
        target_testfile = os.path.join(full_dest_path, testfile)
        os.makedirs(full_dest_path)
        factory.make_file(target_testfile, contents=contents)
        age_file(target_testfile, 1)
        target_mtime = get_write_time(target_testfile)

        call_command('install_pxe_image', source=full_source_path, dest=dest)

        self.assertThat(target_testfile, FileContains(contents))
        self.assertFalse(os.path.isdir(full_source_path))
        self.assertEqual(target_mtime, get_write_time(target_testfile))

    def test_make_destination_follows_pxe_path_conventions(self):
        # The directory that make_destination returns follows the PXE
        # directory hierarchy specified for MAAS:
        # /var/lib/tftproot/maas/<arch>/<subarch>/<release>
        # (Where the /var/lib/tftproot/maas/ part is configurable, so we
        # can test this without overwriting system files).
        pxe_target_dir = self.make_dir()
        arch = 'arch-%s' % factory.getRandomString()
        subarch = 'subarch-%s' % factory.getRandomString()
        release = 'release-%s' % factory.getRandomString()
        self.assertEqual(
            os.path.join(pxe_target_dir, arch, subarch, release),
            make_destination(pxe_target_dir, arch, subarch, release))

    def test_make_destination_assumes_maas_dir_included_in_target_dir(self):
        # make_destination does not add a "maas" part to the path, as in
        # the default /var/lib/tftpboot/maas/; that is assumed to be
        # included already in the pxe-target-dir setting.
        pxe_target_dir = self.make_dir()
        self.assertNotIn(
            '/maas/',
            make_destination(pxe_target_dir, 'arch', 'sub', 'release'))

    def test_make_destination_creates_directory_if_not_present(self):
        pxe_target_dir = self.make_dir()
        expected_destination = os.path.join(
            pxe_target_dir, 'arch', 'sub', 'release')
        make_destination(pxe_target_dir, 'arch', 'sub', 'release')
        self.assertThat(expected_destination, DirExists())

    def test_make_destination_returns_existing_directory(self):
        pxe_target_dir = self.make_dir()
        expected_dest = os.path.join(
            pxe_target_dir, 'arch', 'sub', 'release')
        os.makedirs(expected_dest)
        contents = factory.getRandomString()
        testfile = factory.getRandomString()
        factory.make_file(expected_dest, contents=contents, name=testfile)
        dest = make_destination(pxe_target_dir, 'arch', 'sub', 'release')
        self.assertThat(os.path.join(dest, testfile), FileContains(contents))
