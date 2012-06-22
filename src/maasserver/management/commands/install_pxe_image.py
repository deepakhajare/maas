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

from django.core.management.base import BaseCommand


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
            '--pxe-target-dir', dest='pxe_target_dir', default=None,
            help="Store to this TFTP directory tree instead of the default."),
        )

    def handle(self, arch=None, subarch='generic', release=None, purpose=None,
               image=None, pxe_target_dir=None, **kwargs):
        pass
