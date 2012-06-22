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
    are_identical_dirs,
    make_destination,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maastesting.utils import (
    age_file,
    get_write_time,
    )
from testtools.matchers import (
    DirExists,
    FileContains,
    )


def make_random_string(prefix):
    """Return an arbitrary string starting with the given prefix."""
    return '-'.join([prefix, factory.getRandomString(5)])


def make_arch_subarch_release():
    """Create arbitrary architecture/subarchitecture/release names.

    :return: A triplet of three identifiers for these respective items.
    """
    return (
        make_random_string('arch'),
        make_random_string('subarch'),
        make_random_string('release'),
        )


class TestInstallPXEImage(TestCase):

    def make_download(self, download_dir, contents=None):
        """Fake a downloaded image directory in `download_dir`.

        :param download_dir: A directory (make sure it gets cleaned up
            after your test!) where the fake image directory will be
            created.  A sample file will be created inside the image
            directory.
        :param contents: Optional contents for the sample file in the image
            directory.  If none is given, it will have arbitrary contents.
        :return: A tuple: (image directory, image file, image file contents).
            For example, if this returns ('foo', 'bar', 'splat') then your
            `download_dir` now contains a directory `foo`, which contains a
            file `bar`, which contains the text "splat".
        """
        if contents is None:
            contents = factory.getRandomString()
        source_dir = factory.getRandomString()
        source_path = os.path.join(download_dir, source_dir)
        os.makedirs(source_path)
        testfile = factory.make_file(source_path, contents=contents)
        return source_dir, testfile, contents

    def test_installs_new_image(self):
        pxe_target_dir = self.make_dir()
        arch, subarch, release = make_arch_subarch_release()
        purpose = make_random_string('purpose')
        download_dir = self.make_dir()
        source_dir, source_file, contents = self.make_download(download_dir)

        call_command(
            'install_pxe_image', pxe_target_dir=pxe_target_dir, arch=arch,
            subarch=subarch, release=release, purpose=purpose,
            image=os.path.join(download_dir, source_dir))

        self.assertThat(
            os.path.join(
                make_destination(pxe_target_dir, arch, subarch, release),
                purpose, os.path.basename(source_file)),
            FileContains(contents))

    def test_updates_changed_image(self):
        pxe_target_dir = self.make_dir()
        arch, subarch, release = make_arch_subarch_release()
        purpose = make_random_string('purpose')
        download_dir = self.make_dir()
        source_dir, source_file, contents = self.make_download(
            download_dir, contents="Old contents")
        source_path = os.path.join(download_dir, source_dir, source_file)
        pxe_target_dir = self.make_dir()
        target_path = os.path.join(
            pxe_target_dir, arch, subarch, release, purpose, source_file)

        call_command(
            'install_pxe_image', pxe_target_dir=pxe_target_dir, arch=arch,
            subarch=subarch, release=release, purpose=purpose,
            image=source_path)

        with open(source_path, 'w') as outfile:
            outfile.write("New contents")

        call_command(
            'install_pxe_image', pxe_target_dir=pxe_target_dir, arch=arch,
            subarch=subarch, release=release, purpose=purpose,
            image=source_path)

        self.assertThat(target_path, FileContains("New contents"))

    def test_leaves_unchanged_image_untouched(self):
        pxe_target_dir = self.make_dir()
        arch, subarch, release = make_arch_subarch_release()
        purpose = make_random_string('purpose')
        download_dir = self.make_dir()
        source_dir, source_file, contents = self.make_download(download_dir)
        source_path = os.path.join(download_dir, source_dir)
        pxe_target_dir = self.make_dir()
        target_path = os.path.join(
            pxe_target_dir, arch, subarch, release, purpose, source_file)

        call_command(
            'install_pxe_image', pxe_target_dir=pxe_target_dir, arch=arch,
            subarch=subarch, release=release, purpose=purpose,
            image=source_path)

        age_file(target_path, 1)
        target_mtime = get_write_time(target_path)

        call_command(
            'install_pxe_image', pxe_target_dir=pxe_target_dir, arch=arch,
            subarch=subarch, release=release, purpose=purpose,
            image=source_path)

        self.assertThat(target_path, FileContains(contents))
        self.assertFalse(os.path.isdir(source_path))
        self.assertEqual(target_mtime, get_write_time(target_path))

    def test_make_destination_follows_pxe_path_conventions(self):
        # The directory that make_destination returns follows the PXE
        # directory hierarchy specified for MAAS:
        # /var/lib/tftproot/maas/<arch>/<subarch>/<release>
        # (Where the /var/lib/tftproot/maas/ part is configurable, so we
        # can test this without overwriting system files).
        pxe_target_dir = self.make_dir()
        arch, subarch, release = make_arch_subarch_release()
        self.assertEqual(
            os.path.join(pxe_target_dir, arch, subarch, release),
            make_destination(pxe_target_dir, arch, subarch, release))

    def test_make_destination_assumes_maas_dir_included_in_target_dir(self):
        # make_destination does not add a "maas" part to the path, as in
        # the default /var/lib/tftpboot/maas/; that is assumed to be
        # included already in the pxe-target-dir setting.
        pxe_target_dir = self.make_dir()
        arch, subarch, release = make_arch_subarch_release()
        self.assertNotIn(
            '/maas/',
            make_destination(pxe_target_dir, arch, subarch, release))

    def test_make_destination_creates_directory_if_not_present(self):
        pxe_target_dir = self.make_dir()
        arch, subarch, release = make_arch_subarch_release()
        expected_destination = os.path.join(
            pxe_target_dir, arch, subarch, release)
        make_destination(pxe_target_dir, arch, subarch, release)
        self.assertThat(expected_destination, DirExists())

    def test_make_destination_returns_existing_directory(self):
        pxe_target_dir = self.make_dir()
        arch, subarch, release = make_arch_subarch_release()
        expected_dest = os.path.join(pxe_target_dir, arch, subarch, release)
        os.makedirs(expected_dest)
        contents = factory.getRandomString()
        testfile = factory.getRandomString()
        factory.make_file(expected_dest, contents=contents, name=testfile)
        dest = make_destination(pxe_target_dir, arch, subarch, release)
        self.assertThat(os.path.join(dest, testfile), FileContains(contents))

    def test_are_identical_dirs_sees_missing_old_dir_as_different(self):
        self.assertFalse(
            are_identical_dirs(
                os.path.join(self.make_dir(), factory.getRandomString()),
                os.path.dirname(self.make_file())))

    def test_are_identical_dirs_returns_true_if_identical(self):
        name = factory.getRandomString()
        contents = factory.getRandomString()
        self.assertTrue(are_identical_dirs(
            os.path.dirname(self.make_file(name=name, contents=contents)),
            os.path.dirname(self.make_file(name=name, contents=contents))))

    def test_are_identical_dirs_returns_false_if_file_has_changed(self):
        name = factory.getRandomString()
        old = os.path.dirname(self.make_file(name=name))
        new = os.path.dirname(self.make_file(name=name))
        self.assertFalse(are_identical_dirs(old, new))

    def test_are_identical_dirs_returns_false_if_file_was_added(self):
        shared_file = factory.getRandomString()
        contents = factory.getRandomString()
        old = os.path.dirname(
            self.make_file(name=shared_file, contents=contents))
        new = os.path.dirname(
            self.make_file(name=shared_file, contents=contents))
        factory.make_file(new)
        self.assertFalse(are_identical_dirs(old, new))

    def test_are_identical_dirs_returns_false_if_file_was_removed(self):
        shared_file = factory.getRandomString()
        contents = factory.getRandomString()
        old = os.path.dirname(
            self.make_file(name=shared_file, contents=contents))
        new = os.path.dirname(
            self.make_file(name=shared_file, contents=contents))
        factory.make_file(old)
        self.assertFalse(are_identical_dirs(old, new))
