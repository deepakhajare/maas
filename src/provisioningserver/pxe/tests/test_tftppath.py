# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the tftppath module."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os.path

from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.enum import ARP_HTYPE
from provisioningserver.pxe.tftppath import (
    compose_bootloader_path,
    compose_config_path,
    compose_image_path,
    list_boot_images,
    locate_tftp_path,
    )
from provisioningserver.testing.config import ConfigFixture
from testtools.matchers import (
    Not,
    StartsWith,
    )


class TestTFTPPath(TestCase):

    def setUp(self):
        super(TestTFTPPath, self).setUp()
        self.tftproot = self.make_dir()
        self.config = {"tftp": {"root": self.tftproot}}
        self.useFixture(ConfigFixture(self.config))

    def make_boot_image_params(self):
        """Create a dict of boot-image parameters, as in list_boot_images."""
        return {
            'architecture': factory.make_name('architecture'),
            'subarchitecture': factory.make_name('subarchitecture'),
            'release': factory.make_name('release'),
            'purpose': factory.make_name('purpose'),
        }

    def make_image_dir(self, image_params, tftproot):
        """Fake a boot image matching `image_params` under `tftproot`."""
        image_dir = locate_tftp_path(
            compose_image_path(
                arch=image_params['architecture'],
                subarch=image_params['subarchitecture'],
                release=image_params['release'],
                purpose=image_params['purpose']),
            tftproot)
        os.makedirs(image_dir)
        factory.make_file(image_dir, 'linux')
        factory.make_file(image_dir, 'initrd.gz')

    def test_compose_config_path_follows_maas_pxe_directory_layout(self):
        name = factory.make_name('config')
        self.assertEqual(
            'pxelinux.cfg/%02x-%s' % (ARP_HTYPE.ETHERNET, name),
            compose_config_path(name))

    def test_compose_config_path_does_not_include_tftp_root(self):
        name = factory.make_name('config')
        self.assertThat(
            compose_config_path(name),
            Not(StartsWith(self.tftproot)))

    def test_compose_image_path_follows_maas_pxe_directory_layout(self):
        arch = factory.make_name('arch')
        subarch = factory.make_name('subarch')
        release = factory.make_name('release')
        purpose = factory.make_name('purpose')
        self.assertEqual(
            '%s/%s/%s/%s' % (arch, subarch, release, purpose),
            compose_image_path(arch, subarch, release, purpose))

    def test_compose_image_path_does_not_include_tftp_root(self):
        arch = factory.make_name('arch')
        subarch = factory.make_name('subarch')
        release = factory.make_name('release')
        purpose = factory.make_name('purpose')
        self.assertThat(
            compose_image_path(arch, subarch, release, purpose),
            Not(StartsWith(self.tftproot)))

    def test_compose_bootloader_path_follows_maas_pxe_directory_layout(self):
        self.assertEqual('pxelinux.0', compose_bootloader_path())

    def test_compose_bootloader_path_does_not_include_tftp_root(self):
        self.assertThat(
            compose_bootloader_path(),
            Not(StartsWith(self.tftproot)))

    def test_locate_tftp_path_prefixes_tftp_root(self):
        pxefile = factory.make_name('pxefile')
        self.assertEqual(
            os.path.join(self.tftproot, pxefile),
            locate_tftp_path(pxefile, tftproot=self.tftproot))

    def test_locate_tftp_path_returns_root_when_path_is_None(self):
        self.assertEqual(
            self.tftproot, locate_tftp_path(None, tftproot=self.tftproot))

    def test_list_boot_images_copes_with_missing_directory(self):
        missing_dir = os.path.join(
            self.make_dir(), factory.make_name('missing-dir'))
        self.assertItemsEqual([], list_boot_images(missing_dir))

    def test_list_boot_images_copes_with_empty_directory(self):
        self.assertItemsEqual([], list_boot_images(self.tftproot))

    def test_list_boot_images_copes_with_unexpected_files(self):
        os.makedirs(os.path.join(self.tftproot, factory.make_name('empty')))
        factory.make_file(self.tftproot)
        self.assertItemsEqual([], list_boot_images(self.tftproot))

    def test_list_boot_images_finds_boot_image(self):
        image = self.make_boot_image_params()
        self.make_image_dir(image, self.tftproot)
        self.assertItemsEqual([image], list_boot_images(self.tftproot))

    def test_list_boot_images_enumerates_boot_images(self):
        images = [self.make_boot_image_params() for counter in range(3)]
        for image in images:
            self.make_image_dir(image, self.tftproot)
        self.assertItemsEqual(images, list_boot_images(self.tftproot))
