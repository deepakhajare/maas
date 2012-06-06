# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for write-dhcp-config.py"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from testtools import TestCase
from testtools.matchers import MatchesStructure

from provisioningserver.dhcp.write_dhcp_config import DHCPConfigWriter


class TestModule(TestCase):
    """Test the write-dhcp-config module."""

    def test_arg_setup(self):
        writer = DHCPConfigWriter()
        test_args = [
            '--subnet', 'subnet',
            '--subnet-mask', 'subnet-mask',
            '--next-server', 'next-server',
            '--broadcast-address', 'broadcast-address',
            '--dns-servers', 'dns-servers',
            '--gateway', 'gateway',
            '--low-range', 'low-range',
            '--high-range', 'high-range',
            '--out-file', 'out-file',
            ]
        writer.parse_args(test_args)

        self.assertThat(
            writer.args, MatchesStructure.byEquality(
                subnet='subnet',
                subnet_mask='subnet-mask',
                next_server='next-server',
                broadcast_address='broadcast-address',
                dns_servers='dns-servers',
                gateway='gateway',
                low_range='low-range',
                high_range='high-range',
                out_file='out-file'))
