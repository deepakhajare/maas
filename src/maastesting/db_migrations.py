# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for testing South database migrations.

Each Django application in MAAS tests the basic sanity of its own South
database migrations.  To minimize repetition, this single module provides all
the code those tests need.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'detect_sequence_clashes',
    'locate_migrations',
    ]

from collections import Counter
import os
import re


def locate_migrations(test_module):
    """Find the migrations dir for the application that `test_module` is in.

    :param test_module: The `__file__` of a test that checks the migrations
        for a particular MAAS sub-application.
    :return: Path to the MAAS sub-application's South migrations.
    """
    test_dir = os.path.dirname(test_module)
    application_dir = os.path.dirname(test_dir)
    return os.path.join(application_dir, 'migrations')


def match_migration_name(filename):
    """Return a regex match on a migration filename; None if no match.

    The match, if any, has the migration's sequence number as its first group.
    """
    return re.match('([0-9]+)_[^.]+\\.py$', filename)


def extract_number(migration_name):
    """Extract the sequence number from a migration module name."""
    return int(match_migration_name(migration_name).groups()[0])


def get_duplicates(numbers):
    """Return set of those items that occur more than once."""
    return {
        numbers
        for numbers, count in Counter(numbers).items()
            if count > 1}


def list_migrations(migrations_dir):
    """List schema-migration files in `migrations_dir`."""
    return filter(
        lambda name: match_migration_name(name) is not None,
        os.listdir(migrations_dir))


def detect_sequence_clashes(migrations_dir):
    """List numbering clashes among database migrations in given directory.

    :param migrations_dir: Location of an application's migration modules.
    :return: A sorted `list` of tuples `(number, filename)` representing all
        migration modules in `migrations_dir`.  The `number` is as found in
        `filename`, but in `int` form.
    """
    migrations = list_migrations(migrations_dir)
    numbers_and_names = [(extract_number(name), name) for name in migrations]
    duplicates = get_duplicates(number for number, name in numbers_and_names)
    return sorted(
        (number, name)
        for number, name in numbers_and_names
            if number in duplicates)
