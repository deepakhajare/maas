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

from operator import itemgetter
import socket
import struct

from maasserver.utils.network import (
    dotted_quad_to_int,
    int_to_dotted_quad,
    next_ip,
    )
from maastesting.testcase import TestCase


dottedquad_int = [
    ('255.255.255.255', 4294967295),
    ('192.168.0.1',     3232235521),
    ('0.0.0.12',        12),
    ('0.0.0.0',         0),
]


class TestUtilities(TestCase):

    def test_dotted_quad_to_int(self):
        inputs = map(itemgetter(0), dottedquad_int)
        expected = map(itemgetter(1), dottedquad_int)
        self.assertEqual(
            expected, map(dotted_quad_to_int, inputs))

    def test_dotted_quad_to_int_raises_exception_if_invalid_input(self):
        self.assertRaises(
            socket.error, dotted_quad_to_int, '1.1.1.345')

    def test_int_to_dotted_quad(self):
        inputs = map(itemgetter(1), dottedquad_int)
        expected = map(itemgetter(0), dottedquad_int)
        self.assertEqual(
            expected, map(int_to_dotted_quad, inputs))

    def test_int_to_dotted_quad_raises_exception_if_invalid_input(self):
        self.assertRaises(
            struct.error, int_to_dotted_quad, 4294967300)

    def test_next_ip_returns_next_ip(self):
        ip_nextip = [
            ('192.168.0.255', '192.168.1.0'),
            ('192.168.0.1',   '192.168.0.2'),
            ('0.0.0.0',       '0.0.0.1'),
        ]
        inputs = map(itemgetter(0), ip_nextip)
        expected = map(itemgetter(1), ip_nextip)
        self.assertEqual(
            expected, map(next_ip, inputs))

    def test_next_ip_raises_exception_at_end_of_spectrum(self):
        self.assertRaises(struct.error, next_ip, '255.255.255.255')
