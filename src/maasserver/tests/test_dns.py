# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test DNS module."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django.db import connection
from maasserver.dns import (
    next_zone_serial,
    zone_serial,
    )
from maasserver.testing.testcase import TestCase


class TestDNSUtilities(TestCase):

    def query_seq(self, name):
        cursor = connection.cursor()
        cursor.execute(
            "SELECT nextval(%s)", [name])
        return cursor.fetchone()[0]

    def test_zone_serial_wraps_around_int32_max(self):
        query = "ALTER SEQUENCE %s" % zone_serial.sequence_name
        cursor = connection.cursor()
        cursor.execute(query + " RESTART WITH %s", [2 ** 32 - 1])
        zone_serial.nextval()
        val = zone_serial.nextval()
        self.assertEqual(1, val)

    def test_next_zone_serial_returns_sequence(self):
        self.assertSequenceEqual(
            ['%0.10d' % i for i in range(1, 11)],
            [next_zone_serial() for i in range(10)])
