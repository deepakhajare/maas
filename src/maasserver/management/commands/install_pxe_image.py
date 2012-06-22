# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Install a netboot image directory for TFTP download."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'Command',
    ]

from optparse import make_option
import os.path
from shutil import rmtree

from celeryconfig import PXE_TARGET_DIR
from django.core.management.base import BaseCommand


def make_destination(pxe_target_dir, arch, subarch, release):
    """Locate the destination directory, creating it if necessary.

    :param pxe_target_dir: The TFTP directory containing the MAAS portion
        of the PXE directory tree, e.g. /var/lib/tftpboot/maas/.
    :param arch: Main architecture to locate the destination for.
    :param subarch: Sub-architecture of the main architecture.
    :param release: OS release name, e.g. "precise".
    :return: Path of the destination directory that the image directory
        should be stored in.
    """


def identical_dirs(old, new):
    """Do directories `old` and `new` contain identical files?

    It's OK for `old` not to exist; that is considered a difference rather
    than an error.  But `new` is assumed to exist - if it doesn't, you
    shouldn't have come far enough to call this function.
    """


def install_dir(new, old):
    """Install directory `new`, replacing directory `old` if it exists.

    This works as atomically as possible, but isn't entirely.

    Some temporary paths will be used that are identical to `old`, but with
    suffixes ".old" or ".new".  If either of these directories already
    exists, it will be mercilessly deleted.
    """


class Command(BaseCommand):
    """Move a netboot image into the TFTP directory structure.

    The image is a directory containing a kernel and an initrd.  If the
    destination location already has an image of the same name and
    containing identical files, the new image is deleted and the old one
    is left untouched.
    """

    option_list = BaseCommand.option_list + (
        make_option(
            '--arch', dest='arch', default=None,
            help="Main system architecture that the image is for."),
        make_option(
            '--subarch', dest='subarch', default='generic',
            help="Sub-architecture of the main architecture."),
        make_option(
            '--release', dest='release', default=None,
            help="Ubuntu release that the image is for."),
        make_option(
            '--purpose', dest='purpose', default=None,
            help="Purpose of the image (e.g. 'install' or 'commissioning')."),
        make_option(
            '--image', dest='image', default=None,
            help="Netboot image directory, containing kernel & initrd."),
        make_option(
            '--pxe-target-dir', dest='pxe_target_dir', default=PXE_TARGET_DIR,
            help="Store to this TFTP directory tree instead of the default."),
        )

    def handle(self, arch=None, subarch='generic', release=None, purpose=None,
               image=None, pxe_target_dir=None, **kwargs):
        if pxe_target_dir is None:
            pxe_target_dir = PXE_TARGET_DIR

        dest = make_destination(pxe_target_dir, arch, subarch, release)
        if identical_dirs(image, os.path.join(dest, purpose)):
            # Nothing new in this image.  Delete it.
            rmtree(image)
        else:
            # Image has changed.  Move the new version into place.
            install_dir(image, os.path.join(dest, purpose))
