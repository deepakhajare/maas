# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for helpers used to sanity-check South migrations."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os.path
from random import randint

from maastesting.db_migrations import (
    detect_sequence_clashes,
    extract_number,
    get_duplicates,
    list_migrations,
    locate_migrations,
    match_migration_name,
    )
from maastesting.factory import factory
from maastesting.testcase import TestCase


def make_migration_name(number=None, name=None):
    """Create a migration-file name."""
    if number is None:
        number = randint(0, 9999)
    if name is None:
        name = factory.getRandomString()
    return '{0:=04}_{1}.py'.format(number, name)


class TestDBMigrations(TestCase):

    def test_locate_migrations_finds_migrations_dir_from_test(self):
        app_dir = os.path.join(
            factory.make_name('branch'), 'src', factory.make_name('app'))
        test_name = 'test_%s.py' % factory.make_name()
        test = os.path.join(app_dir, 'tests', test_name)

        self.assertEqual(
            os.path.join(app_dir, 'migrations'),
            locate_migrations(test))

    def test_match_migration_name_matches_real_migration_name(self):
        self.assertIsNotNone(match_migration_name('0002_macaddress_unique.py'))

    def test_match_migration_name_matches_any_migration_name(self):
        self.assertIsNotNone(match_migration_name(make_migration_name()))

    def test_match_migration_name_ignores_other_files(self):
        self.assertIsNone(match_migration_name('__init__.py'))

    def test_match_migration_name_ignores_unnumbered_file(self):
        self.assertIsNone(match_migration_name('macaddress_unique.py'))

    def test_match_migration_name_ignores_non_python_file(self):
        self.assertIsNone(match_migration_name('0002_macaddress_unique'))

    def test_match_migration_name_ignores_dot_files(self):
        self.assertIsNone(match_migration_name('.' + make_migration_name()))

    def test_match_migration_name_ignores_suffixed_names(self):
        self.assertIsNone(match_migration_name(make_migration_name() + '~'))

    def test_extract_number_returns_sequence_number(self):
        number = randint(0, 999999)
        self.assertEqual(number, extract_number(make_migration_name(number)))

    def test_get_duplicates_finds_duplicates(self):
        item = factory.make_name('item')
        self.assertEqual({item}, get_duplicates([item, item]))

    def test_get_duplicates_finds_all_duplicates(self):
        dup1 = factory.make_name('dup1')
        dup2 = factory.make_name('dup2')
        self.assertEqual({dup1, dup2}, get_duplicates(2 * [dup1, dup2]))

    def test_get_duplicates_ignores_unique_items(self):
        self.assertEqual(set(), get_duplicates(range(5)))

    def test_get_duplicates_ignores_ordering(self):
        dup = factory.make_name('dup')
        unique = factory.make_name('unique')
        self.assertEqual({dup}, get_duplicates([dup, unique, dup]))

    def test_list_migrations_does_not_include_path(self):
        migration = make_migration_name()
        self.assertItemsEqual(
            [migration],
            list_migrations(os.path.dirname(self.make_file(migration))))

    def test_list_migrations_lists_all_migrations_and_only_migrations(self):
        migrations = [make_migration_name(number) for number in range(3)]
        location = self.make_dir()
        for migration in migrations:
            factory.make_file(location, migration)
        for other_file in ['__init__.py', '__init__.pyc', 'README.txt']:
            factory.make_file(location, other_file)
        self.assertItemsEqual(migrations, list_migrations(location))

    def test_detect_sequence_clashes_returns_list(self):
        self.assertEqual([], detect_sequence_clashes(self.make_dir()))

    def test_detect_sequence_clashes_finds_clashes(self):
        location = self.make_dir()
        number = randint(0, 999)
        names = [make_migration_name(number) for counter in range(2)]
        for name in names:
            factory.make_file(location, name)
        self.assertItemsEqual(
            [(number, name) for name in names],
            detect_sequence_clashes(location))

    def test_detect_sequence_clashes_ignores_unique_migrations(self):
        location = self.make_dir()
        for number in range(5):
            factory.make_file(location, make_migration_name(number))
        self.assertItemsEqual([], detect_sequence_clashes(location))
