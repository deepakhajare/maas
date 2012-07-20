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

import argparse

from provisioningserver.config import (
    get_config_filename,
    set_config_filename,
    )
import provisioningserver.dhcp.writer
import provisioningserver.pxe.install_bootloader
import provisioningserver.pxe.install_image
from provisioningserver.utils import ActionScript


class SetConfigFileAction(argparse.Action):
    """Set the configuration file for use in this process."""

    def __call__(self, parser, namespace, values, option_string=None):
        set_config_filename(values)


main = ActionScript(__doc__)
main.parser.add_argument(
    "-c", "--config-file", default=get_config_filename(),
    metavar="FILENAME", action=SetConfigFileAction,
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
