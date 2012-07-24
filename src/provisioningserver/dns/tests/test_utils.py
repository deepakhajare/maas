# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for miscellaneous helpers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import socket
import struct

from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.dns.utils import (
    dotted_quad_to_int,
    generated_hostname,
    int_to_dotted_quad,
    ip_range,
    )


dottedquad_int = [
    ('255.255.255.255', 4294967295),
    ('192.168.0.1',     3232235521),
    ('0.0.0.12',        12),
    ('0.0.0.0',         0),
]


class TestUtilities(TestCase):

    def test_dotted_quad_to_int(self):
        inputs = [item[0] for item in dottedquad_int]
        expected = [item[1] for item in dottedquad_int]
        self.assertSequenceEqual(
            expected, list(map(dotted_quad_to_int, inputs)))

    def test_dotted_quad_to_int_raises_exception_if_invalid_input(self):
        self.assertRaises(
            socket.error, dotted_quad_to_int, '1.1.1.345')

    def test_int_to_dotted_quad(self):
        inputs = [item[1] for item in dottedquad_int]
        expected = [item[0] for item in dottedquad_int]
        self.assertEqual(
            expected, list(map(int_to_dotted_quad, inputs)))

    def test_int_to_dotted_quad_raises_exception_if_invalid_input(self):
        self.assertRaises(
            struct.error, int_to_dotted_quad, 4294967300)

    def test_ip_range(self):
        self.assertEqual(
            ['192.168.0.1', '192.168.0.2', '192.168.0.3'],
            list(ip_range('192.168.0.1', '192.168.0.3')))

    def test_generated_hostname_returns_hostname(self):
        self.assertEqual(
            '192-168-0-1', generated_hostname('192.168.0.1'))

    def test_generated_hostname_returns_hostname_plus_domain(self):
        domain = factory.getRandomString()
        self.assertEqual(
            '192-168-0-1.%s' % domain,
            generated_hostname('192.168.0.1', domain))
