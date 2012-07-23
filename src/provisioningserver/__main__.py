#!/usr/bin/env python2.7
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Command-line interface for the MAAS provisioning component."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type

from os import environ

import provisioningserver.dhcp.writer
import provisioningserver.pxe.install_bootloader
import provisioningserver.pxe.install_image
from provisioningserver.utils import ActionScript


main = ActionScript(__doc__)
main.parser.add_argument(
    "-c", "--config-file", metavar="FILENAME",
    default=environ.get("MAAS_PROVISION_SETTINGS", "/etc/maas/pserv.yaml"),
    help="Configuration file to load [%(default)s].")
main.register(
    "generate-dhcp-config",
    provisioningserver.dhcp.writer)
main.register(
    "install-pxe-bootloader",
    provisioningserver.pxe.install_bootloader)
main.register(
    "install-pxe-image",
    provisioningserver.pxe.install_image)
main()
