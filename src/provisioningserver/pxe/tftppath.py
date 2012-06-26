# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Construct TFTP paths for PXE files."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'compose_config_path',
    'compose_image_path',
    'locate_tftp_path',
    ]

import os.path

from celeryconfig import TFTPROOT


def compose_config_path(arch, subarch, name):
    """Compose the TFTP path for a PXE configuration file.

    The path returned is relative to the TFTP root, as it would be
    identified by clients on the network.

    :param arch: Main machine architecture.
    :param subarch: Sub-architecture, or "generic" if there is none.
    :param name: Configuration file's name.
    :return: Path for the corresponding PXE config file as exposed over
        TFTP.
    """
    # Not using os.path.join: this is a TFTP path, not a native path.
    # Yes, in practice for us they're the same.
    return '/'.join(['/maas', arch, subarch, 'pxelinux.cfg', name])


def compose_image_path(arch, subarch, release, purpose):
    """Compose the TFTP path for a PXE kernel/initrd directory.

    The path returned is relative to the TFTP root, as it would be
    identified by clients on the network.

    :param arch: Main machine architecture.
    :param subarch: Sub-architecture, or "generic" if there is none.
    :param release: Operating system release, e.g. "precise".
    :param purpose: Purpose of the image, e.g. "install" or
        "commissioning".
    :return: Path for the corresponding image directory (containing a
        kernel and initrd) as exposed over TFTP.
    """
    return '/'.join(['/maas', arch, subarch, release, purpose])


def locate_tftp_path(tftp_path, tftproot=None):
    """Return the local filesystem path corresponding to `tftp_path`.

    The return value gives the filesystem path where you'd have to put
    a file if you wanted it made available over TFTP as `tftp_path`.

    :param tftp_path: Path as used in the TFTP protocol which you want
        the local filesystem equivalent for.
    :param tftproot: Optional TFTP root directory to override the
        configured default.
    """
    if tftproot is None:
        tftproot = TFTPROOT
    return os.path.join(tftproot, tftp_path)
