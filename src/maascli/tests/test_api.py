# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maascli.api`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import contextlib
import sqlite3

from maascli import api
from maastesting.testcase import TestCase


class TestProfileConfig(TestCase):
    """Tests for `ProfileConfig`."""

    def test_init(self):
        database = sqlite3.connect(":memory:")
        config = api.ProfileConfig(database)
        with config.cursor() as cursor:
            # The profiles table has been created.
            self.assertEqual(
                cursor.execute(
                    "SELECT COUNT(*) FROM sqlite_master"
                    " WHERE type = 'table'"
                    "   AND name = 'profiles'").fetchone(),
                (1,))

    def test_profiles_pristine(self):
        # A pristine configuration has no profiles.
        database = sqlite3.connect(":memory:")
        config = api.ProfileConfig(database)
        self.assertSetEqual(set(), set(config))

    def test_adding_profile(self):
        database = sqlite3.connect(":memory:")
        config = api.ProfileConfig(database)
        config["alice"] = {"abc": 123}
        self.assertEqual({"alice"}, set(config))
        self.assertEqual({"abc": 123}, config["alice"])

    def test_getting_profile(self):
        database = sqlite3.connect(":memory:")
        config = api.ProfileConfig(database)
        config["alice"] = {"abc": 123}
        self.assertEqual({"abc": 123}, config["alice"])

    def test_removing_profile(self):
        database = sqlite3.connect(":memory:")
        config = api.ProfileConfig(database)
        config["alice"] = {"abc": 123}
        del config["alice"]
        self.assertEqual(set(), set(config))

    def test_open_and_close(self):
        # open() returns a context manager that closes the database on exit.
        config = api.ProfileConfig.open(":memory:")
        self.assertIsInstance(config, contextlib.GeneratorContextManager)
        with config as config:
            self.assertIsInstance(config, api.ProfileConfig)
            with config.cursor() as cursor:
                self.assertEqual(
                    (1,), cursor.execute("SELECT 1").fetchone())
        self.assertRaises(sqlite3.ProgrammingError, config.cursor)
