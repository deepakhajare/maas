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

from filecmp import cmpfiles
from optparse import make_option
import os.path
from shutil import (
    copytree,
    rmtree,
    )

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
    dest = os.path.join(pxe_target_dir, arch, subarch, release)
    if not os.path.isdir(dest):
        os.makedirs(dest)
    return dest


def are_identical_dirs(old, new):
    """Do directories `old` and `new` contain identical files?

    It's OK for `old` not to exist; that is considered a difference rather
    than an error.  But `new` is assumed to exist - if it doesn't, you
    shouldn't have come far enough to call this function.
    """
    assert os.path.isdir(new)
    if os.path.isdir(old):
        files = set(os.listdir(old) + os.listdir(new))
        # The shallow=False is needed to make cmpfiles() compare file
        # contents.  Otherwise it only compares os.stat() results,
        match, mismatch, errors = cmpfiles(old, new, files, shallow=False)
        return len(match) == len(files)
    else:
        return False


def install_dir(new, old):
    """Install directory `new`, replacing directory `old` if it exists.

    This works as atomically as possible, but isn't entirely.  Moreover,
    any TFTP downloads that are reading from the old directory during
    the move may receive inconsistent data, with some of the files (or
    parts of files!) coming from the old directory and some from the
    new.

    Some temporary paths will be used that are identical to `old`, but with
    suffixes ".old" or ".new".  If either of these directories already
    exists, it will be mercilessly deleted.

    This function makes no promises about whether it moves or copies
    `new` into place.  The caller should make an attempt to clean it up,
    but be prepared for it not being there.
    """
    # Get rid of any leftover temporary directories from potential
    # interrupted previous runs.
    rmtree('%s.old' % old, ignore_errors=True)
    rmtree('%s.new' % old, ignore_errors=True)

    # We have to move the existing directory out of the way and the new
    # one into place.  Between those steps, there is a window where
    # neither is in place.  To minimize that window, move the new one
    # into the same location (ensuring that it no longer needs copying
    # from one partition to another) and then swizzle the two as quickly
    # as possible.
    # This could be a simple "remove" if the downloaded image is on the
    # same filesystem as the destination, but because that isn't
    # certain, copy instead.  It's not particularly fast, but the extra
    # work happens outside the critical window so it shouldn't matter
    # much.
    copytree(new, '%s.new' % old)

    # Start of critical window.
    if os.path.isdir(old):
        os.rename(old, '%s.old' % old)
    os.rename('%s.new' % old, old)
    # End of critical window.

    # Now delete the old image directory at leisure.
    rmtree('%s.old' % old, ignore_errors=True)


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
        if not are_identical_dirs(os.path.join(dest, purpose), image):
            # Image has changed.  Move the new version into place.
            install_dir(image, os.path.join(dest, purpose))
        rmtree(image, ignore_errors=True)