# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Sanity checks for database migrations.

These tests need to be included in each of the MAAS applications that has
South-managed database migrations.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maastesting.db_migrations import (
    detect_sequence_clashes,
    locate_migrations,
    )
from maastesting.testcase import TestCase


class TestMigrations(TestCase):

    def test_migrations_have_unique_numbers(self):
        migrations_dir = locate_migrations(__file__)
        self.assertEqual([], detect_sequence_clashes(migrations_dir))
