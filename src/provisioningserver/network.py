# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Discover networks."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'discover_networks',
    ]

from io import BytesIO
import os
from subprocess import check_call


class InterfaceInfo:

    def __init__(self, interface):
        self.interface = interface
        self.ip = None
        self.mask = None

    def may_be_subnet(self):
        return all([
            self.interface != 'lo',
            self.ip is not None,
            self.mask is not None,
            ])

    def as_dict(self):
        return {
            'interface': self.interface,
            'ip': self.ip,
            'mask': self.mask,
        }


def run_ifconfig():
    env = dict(os.environ, LC_ALL='C')
    stdout = BytesIO()
    check_call(['/sbin/ifconfig'], env=env, stdout=stdout)
    stdout.seek(0)
    return stdout.read().decode('ascii')


def parse_stanza(stanza):
    pass


def split_stanzas(output):
    stanzas = [stanza.strip() for stanza in output.strip().split('\n\n')]
    return [stanza for stanza in stanzas if len(stanza) > 0]


def parse_ifconfig(output):
    return [parse_stanza(stanza) for stanza in split_stanzas(output)]


def discover_networks():
    output = run_ifconfig()
    return [
        interface
        for interface in parse_ifconfig(output)
            if interface.may_be_subnet()]
