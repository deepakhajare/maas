# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the maas-import-pxe-files script."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os
from subprocess import check_call

from maastesting.factory import factory
from maastesting.testcase import TestCase
from maastesting.utils import (
    age_file,
    get_write_time,
    )
from provisioningserver.pxe import tftppath
from provisioningserver.testing.config import ConfigFixture
from testtools.matchers import FileContains


def read_file(path, name):
    """Return the contents of the file at `path/name`."""
    with open(os.path.join(path, name)) as infile:
        return infile.read()


def backdate(path):
    """Set the last modification time for the file at `path` to the past."""
    age_file(path, 9999999)


def compose_download_dir(archive, arch, release):
    """Locate a bootloader, initrd, and kernel in an archive.

    :param archive: Archive directory (corresponding to the script's ARCHIVE
        setting, except here it's a filesystem path not a URL).
    :param arch: Architecture.
    :param release: Ubuntu release name.
    :return: Full absolute path to the directory holding the requisite files
        for this archive, arch, and release.
    """
    if arch[0] in {'amd64', 'i386'}:
        return os.path.join(
            archive, 'dists', release, 'main', 'installer-%s' % arch[0],
            'current', 'images', 'netboot', 'ubuntu-installer', arch[0])
    elif arch[0] == 'armhf':
        return os.path.join(
            archive, 'dists', '%s-updates' % release, 'main',
            'installer-%s' % arch[0], 'current', 'images', arch[1], 'netboot')
    else:
        raise NotImplementedError('Unknown architecture: %r' % arch)


def compose_download_kernel_name(arch, release):
    """Name the kernel file expected to be found in a netboot archive.

    :param archive: Archive directory (corresponding to the script's ARCHIVE
        setting, except here it's a filesystem path not a URL).
    :param arch: Architecture.
    :return: the kernel name string, eg. "vmlinuz" or "linux" as appropriate
    """
    if arch[0] in {'amd64', 'i386'}:
        return 'linux'
    elif arch[0] == 'armhf':
        return 'vmlinuz'
    else:
        raise NotImplementedError('Unknown architecture: %r' % arch)


def compose_download_filenames(arch, release):
    """Name files expected to be found in the directory of a netboot archive.

    :param archive: Archive directory (corresponding to the script's ARCHIVE
        setting, except here it's a filesystem path not a URL).
    :param arch: Architecture.
    :return: list of names to be found in the netboot directory for this
        particular arch and release. Eg: ['vmlinuz', 'initrd.gz'] or
        ['linux', 'initrd.gz'] as appropriate.
    """
    return [compose_download_kernel_name(arch, release), 'initrd.gz']


def compose_tftp_bootloader_path(tftproot):
    """Compose path for MAAS TFTP bootloader."""
    return tftppath.locate_tftp_path(
        tftppath.compose_bootloader_path(), tftproot)


def compose_tftp_path(tftproot, arch, release, purpose, *path):
    """Compose path for MAAS TFTP files for given architecture.

    After the TFTP root directory and the architecture, just append any path
    components you want to drill deeper, e.g. the release name to get to the
    files for a specific release.
    """
    return os.path.join(
        tftppath.locate_tftp_path(
            tftppath.compose_image_path(arch[0], arch[1], release, purpose),
            tftproot),
        *path)


class TestImportPXEFiles(TestCase):

    scenarios = (
        ("i386/generic", dict(arch=("i386", "generic"))),
        ("amd64/generic", dict(arch=("amd64", "generic"))),
        ("armhf/highbank", dict(arch=("armhf", "highbank"))),
        )

    def setUp(self):
        super(TestImportPXEFiles, self).setUp()
        self.tftproot = self.make_dir()
        self.config = {"tftp": {"root": self.tftproot}}
        self.config_fixture = ConfigFixture(self.config)
        self.useFixture(self.config_fixture)

    def make_downloads(self, release=None, arch=None):
        """Set up a directory with an image for "download" by the script.

        Returns an "ARCHIVE" URL for the download.
        """
        if release is None:
            release = factory.make_name('release')
        archive = self.make_dir()
        download = compose_download_dir(archive, arch, release)
        os.makedirs(download)
        for filename in compose_download_filenames(arch, release):
            factory.make_file(download, filename)
        return archive

    def call_script(self, archive_dir, tftproot, arch=None, release=None):
        """Call the maas-import-pxe-files script with given settings.

        The ARCHIVE URL and TFTPROOT path must be set, or the script will try
        to download from the Ubuntu server and store into the system's real
        TFTP root directory, respectively.  Both bad ideas.
        """
        # TODO: Use path.py <http://pypi.python.org/pypi/path.py> instead, or
        # something similar; this is tedious stuff.
        here = os.path.dirname(__file__)
        root = os.path.join(here, os.pardir, os.pardir, os.pardir)
        script = os.path.join(root, "scripts", "maas-import-pxe-files")

        path = [os.path.join(root, "bin"), os.path.join(root, "scripts")]
        path.extend(os.environ.get("PATH", "").split(os.pathsep))
        env = {
            'ARCHIVE': 'file://%s' % archive_dir,
            # Substitute curl for wget; it accepts file:// URLs.
            'DOWNLOAD': 'curl -O --silent',
            'PATH': os.pathsep.join(path),
            # Suppress running of maas-import-ephemerals.  It gets too
            # intimate with the system to test here.
            'IMPORT_EPHEMERALS': '0',
        }
        env.update(self.config_fixture.environ)
        if arch is not None:
            env['ARCHES'] = '/'.join(arch)
        if release is not None:
            env['RELEASES'] = release

        with open(os.devnull, 'wb') as dev_null:
            check_call(script, env=env, stdout=dev_null)

    def test_procures_pre_boot_loader(self):
        release = 'precise'
        archive = self.make_downloads(arch=self.arch, release=release)
        self.call_script(
            archive, self.tftproot, arch=self.arch, release=release)
        tftp_path = compose_tftp_bootloader_path(self.tftproot)
        expected_contents = read_file('/usr/lib/syslinux', 'pxelinux.0')
        self.assertThat(tftp_path, FileContains(expected_contents))

    def test_updates_pre_boot_loader(self):
        release = 'precise'
        tftp_path = compose_tftp_bootloader_path(self.tftproot)
        with open(tftp_path, 'w') as existing_file:
            existing_file.write(factory.getRandomString())
        archive = self.make_downloads(arch=self.arch, release=release)
        self.call_script(
            archive, self.tftproot, arch=self.arch, release=release)
        expected_contents = read_file('/usr/lib/syslinux', 'pxelinux.0')
        self.assertThat(tftp_path, FileContains(expected_contents))

    def test_procures_install_image(self):
        release = 'precise'
        archive = self.make_downloads(arch=self.arch, release=release)
        self.call_script(
            archive, self.tftproot, arch=self.arch, release=release)
        tftp_path = compose_tftp_path(
            self.tftproot, self.arch, release, 'install', 'linux')
        download_path = compose_download_dir(archive, self.arch, release)
        expected_contents = read_file(download_path,
            compose_download_kernel_name(self.arch, release))
        self.assertThat(tftp_path, FileContains(expected_contents))

    def test_updates_install_image(self):
        release = 'precise'
        tftp_path = compose_tftp_path(
            self.tftproot, self.arch, release, 'install', 'linux')
        os.makedirs(os.path.dirname(tftp_path))
        with open(tftp_path, 'w') as existing_file:
            existing_file.write(factory.getRandomString())
        archive = self.make_downloads(arch=self.arch, release=release)
        self.call_script(
            archive, self.tftproot, arch=self.arch, release=release)
        download_path = compose_download_dir(archive, self.arch, release)
        expected_contents = read_file(download_path,
            compose_download_kernel_name(self.arch, release))
        self.assertThat(tftp_path, FileContains(expected_contents))

    def test_leaves_install_image_untouched_if_unchanged(self):
        release = 'precise'
        archive = self.make_downloads(arch=self.arch, release=release)
        self.call_script(
            archive, self.tftproot, arch=self.arch, release=release)
        tftp_path = compose_tftp_path(
            self.tftproot, self.arch, release, 'install', 'linux')
        backdate(tftp_path)
        original_timestamp = get_write_time(tftp_path)
        self.call_script(
            archive, self.tftproot, arch=self.arch, release=release)
        self.assertEqual(original_timestamp, get_write_time(tftp_path))
