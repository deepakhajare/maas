# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Django command: generate a PXE configuration file for node enlistment.

Produces the "default" PXE configuration that we provide to nodes that
MAAS is not yet aware of.  A node that netboots using this configuration
will then register itself with the MAAS.
"""

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
    """Print out enlistment PXE config."""

    option_list = BaseCommand.option_list + (
        make_option(
            '--arch', dest='arch', default=None,
            help="Main system architecture to generate config for."),
        make_option(
            '--subarch', dest='arch', default='generic',
            help="Sub-architecture of the main architecture."),
        make_option(
            '--release', dest='release', default=None,
            help="Ubuntu release to run when enlisting nodes."),
        make_option(
            '--tftpdir', dest='tftproot', default='/var/lib/tftpboot/maas',
            help="TFTP directory to store the PXE configuration file in."),
        )

    def handle(self, arch=None, subarch=None, release=None, tftpdir=None,
               **kwargs):
# TODO: Implement!
        pass
