# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Install a PXE pre-boot loader for TFTP download."""

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

from celeryconfig import TFTPROOT
from django.core.management.base import BaseCommand
from provisioningserver.pxe.tftppath import (
    compose_bootloader_path,
    locate_tftp_path,
    )


def make_destination(tftproot, arch, subarch):
    """Locate a loader's destination.  Create containing directory if needed.

    :param tftproot: The root directory served up by the TFTP server,
        e.g. /var/lib/tftpboot/.
    :param arch: Main architecture to locate the destination for.
    :param subarch: Sub-architecture of the main architecture.
    :return: Full path describing the filename that the installed loader
        should end up having.  For example, the loader for i386 (with
        sub-architecture "generic") should install at
        /maas/i386/generic/pxelinux.0.
    """
# TODO: Implement


def install_bootloader(loader, destination):
    """Install bootloader file at path `loader` as `destination`."""
# TODO: Implement


class Command(BaseCommand):
    """Install a PXE pre-boot loader into the TFTP directory structure."""

    option_list = BaseCommand.option_list + (
        make_option(
            '--arch', dest='arch', default=None,
            help="Main system architecture that the bootloader is for."),
        make_option(
            '--subarch', dest='subarch', default='generic',
            help="Sub-architecture of the main architecture."),
        make_option(
            '--loader', dest='loader', default=None,
            help="PXE pre-boot loader to install."),
        make_option(
            '--tftproot', dest='tftproot', default=TFTPROOT,
            help="Store to this TFTP directory tree instead of the default."),
        )

    def handle(self, arch=None, subarch='generic', loader=None, tftproot=None,
               **kwargs):
        if tftproot is None:
            tftproot = TFTPROOT

# TODO: Implement
