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
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maastesting.utils import (
    age_file,
    get_write_time,
    )
from testtools.matchers import FileContains


class TestInstallPXEImage(TestCase):

    def test_installs_new_image(self):
        download_dir = self.make_dir()
        source_dir = factory.getRandomString()
        os.makedirs(source_dir)
        dest = self.make_dir()
        contents = factory.getRandomString()
        testfile = factory.make_file(source_dir, contents=contents)
        call_command(
            'install_pxe_image',
            source=os.path.join(download_dir, source_dir), dest=dest)
        self.assertThat(
            os.path.join(dest, source_dir, testfile), FileContains(contents))

    def test_updates_changed_image(self):
        download_dir = self.make_dir()
        source_dir = factory.getRandomString()
        os.makedirs(source_dir)
        dest = self.make_dir()
        contents = "New content"
        testfile = factory.make_file(source_dir, contents=contents)
        os.makedirs(os.path.join(dest, source_dir))
        factory.make_file(
            os.path.join(dest, source_dir, testfile), contents="Old content")
        call_command(
            'install_pxe_image',
            source=os.path.join(download_dir, source_dir), dest=dest)
        self.assertThat(
            os.path.join(dest, source_dir, testfile), FileContains(contents))

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
