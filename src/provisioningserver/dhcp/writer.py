# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generate a DHCP server configuration."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "add_arguments",
    "run",
    ]

from argparse import ArgumentParser
import sys

from provisioningserver.dhcp import config


def add_arguments(parser):
    """Initialise options for generating DHCP configuration.

    :param parser: An instance of :class:`ArgumentParser`.
    """
    parser.add_argument(
        "--subnet", action="store", required=True, help=(
            "Base subnet declaration, e.g. 192.168.1.0"))
    parser.add_argument(
        "--subnet-mask", action="store", required=True, help=(
            "The mask for the subnet, e.g. 255.255.255.0"))
    parser.add_argument(
        "--next-server", action="store", required=True, help=(
            "The address of the TFTP server"))
    parser.add_argument(
        "--broadcast-address", action="store", required=True, help=(
            "The broadcast IP address for the subnet, e.g. 192.168.1.255"))
    parser.add_argument(
        "--dns-servers", action="store", required=True, help=(
            "One or more IP addresses of the DNS server for the subnet "
            "separated by spaces."))
    parser.add_argument(
        "--gateway", action="store", required=True, help=(
            "The router/gateway IP address for the subnet"))
    parser.add_argument(
        "--low-range", action="store", required=True, help=(
            "The first IP address in the range of IP addresses to "
            "allocate"))
    parser.add_argument(
        "--high-range", action="store", required=True, help=(
            "The last IP address in the range of IP addresses to "
            "allocate"))


def run(args):
    params = vars(args)
    output = config.get_config(**params)
    sys.stdout.write(output)


def main(argv=None):
    """Generate the config and write to stdout or a file as required."""
    parser = ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args(argv)
    run(args)


# TODO: Get rid of this.
if __name__ == "__main__":
    main()
