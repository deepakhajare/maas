# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utility script to write out a dhcp server config from cmd line params."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


import argparse

from provisioningserver.dhcp import config


class DHCPConfigWriter:

    def __init__(self):
        self.set_up_args()

    def set_up_args(self):
        """Initialise an ArgumentParser's options."""
        self.argument_parser = argparse.ArgumentParser(description=__doc__)
        self.argument_parser.add_argument(
            "--subnet", action="store", type=str, required=True, help=(
                "Base subnet declaration, e.g. 192.168.1.0"))
        self.argument_parser.add_argument(
            "--subnet-mask", action="store", type=str, required=True, help=(
                "The mask for the subnet, e.g. 255.255.255.0"))
        self.argument_parser.add_argument(
            "--next-server", action="store", type=str, required=True, help=(
                "The address of the TFTP server"))
        self.argument_parser.add_argument(
            "--broadcast-address", action="store", type=str, required=True,
            help=(
                "The broadcast IP address for the subnet,"
                "e.g. 192.168.1.255"))
        self.argument_parser.add_argument(
            "--dns-servers", action="store", type=str, required=True, help=(
                "One or more IP addresses of the DNS server for the subnet"))
        self.argument_parser.add_argument(
            "--gateway", action="store", type=str, required=True, help=(
                "The router/gateway IP address for the subnet"))
        self.argument_parser.add_argument(
            "--low-range", action="store", type=str, required=True, help=(
                "The first IP address in the range of IP addresses to"
                "allocate"))
        self.argument_parser.add_argument(
            "--high-range", action="store", type=str, required=True, help=(
                "The last IP address in the range of IP addresses to"
                "allocate"))
        self.argument_parser.add_argument(
            "--out-file", action="store", type=str, required=False, help=(
                "The file to write the config.  If not set will write "
                "to stdout"))

    def parse_args(self, argv=None):
        """Parse provided argv or default to sys.argv."""
        self.args = self.argument_parser.parse_args(argv)

    def generate(self):
        """Generate the config."""
        params = self.args.__dict__
        output = config.get_config(**params)
        return output

    def run(self, argv=None):
        """Generate the config and write to stdout or a file as required."""
        self.parse_args(argv)
        output = self.generate()
        try:
            outfile = getattr(self.args, 'out_file')
            with open(outfile, "w") as f:
                f.write(output)
        except AttributeError:
            print(output)
        


def run():
    writer = DHCPConfigWriter()
    writer.run()
