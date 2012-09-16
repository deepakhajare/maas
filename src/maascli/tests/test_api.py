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
import os.path
import sqlite3

from maascli import api
from maastesting.testcase import TestCase
from twisted.python.filepath import FilePath


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
        # ProfileConfig.open() returns a context manager that closes the
        # database on exit.
        config_file = os.path.join(self.make_dir(), "config")
        config = api.ProfileConfig.open(config_file)
        self.assertIsInstance(config, contextlib.GeneratorContextManager)
        with config as config:
            self.assertIsInstance(config, api.ProfileConfig)
            with config.cursor() as cursor:
                self.assertEqual(
                    (1,), cursor.execute("SELECT 1").fetchone())
        self.assertRaises(sqlite3.ProgrammingError, config.cursor)

    def test_open_permissions_new_database(self):
        # ProfileConfig.open() applies restrictive file permissions to newly
        # created configuration databases.
        config_file = os.path.join(self.make_dir(), "config")
        with api.ProfileConfig.open(config_file):
            perms = FilePath(config_file).getPermissions()
            self.assertEqual("rw-------", perms.shorthand())

    def test_open_permissions_existing_database(self):
        # ProfileConfig.open() leaves the file permissions of existing
        # configuration databases.
        config_file = os.path.join(self.make_dir(), "config")
        open(config_file, "wb").close()  # touch.
        os.chmod(config_file, 0644)  # u=rw,go=r
        with api.ProfileConfig.open(config_file):
            perms = FilePath(config_file).getPermissions()
            self.assertEqual("rw-r--r--", perms.shorthand())


class TestFunctions(TestCase):
    """Tests for miscellaneous functions in `maascli.api`."""

    maxDiff = TestCase.maxDiff * 2

    def test_safe_name(self):
        # safe_name attempts to discriminate parts of a vaguely camel-cased
        # string, and rejoins them using a hyphen.
        expected = {
            "NodeHandler": "Node-Handler",
            "SpadeDiggingHandler": "Spade-Digging-Handler",
            "SPADE_Digging_Handler": "SPADE-Digging-Handler",
            "SpadeHandlerForDigging": "Spade-Handler-For-Digging",
            "JamesBond007": "James-Bond007",
            "JamesBOND": "James-BOND",
            "James-BOND-007": "James-BOND-007",
            }
        observed = {
            name_in: api.safe_name(name_in)
            for name_in in expected
            }
        self.assertItemsEqual(
            expected.items(), observed.items())

    def test_safe_name_non_ASCII(self):
        # safe_name will not break if passed a string with non-ASCII
        # characters. However, those characters will not be present in the
        # returned name.
        self.assertEqual(
            "a-b-c", api.safe_name(u"a\u1234_b\u5432_c\u9876"))

    def test_handler_command_name(self):
        # handler_command_name attempts to discriminate parts of a vaguely
        # camel-cased string, removes any "handler" parts, joins again with
        # underscrores, and returns the whole lot in lower case.
        expected = {
            "NodeHandler": "node",
            "SpadeDiggingHandler": "spade_digging",
            "SPADE_Digging_Handler": "spade_digging",
            "SpadeHandlerForDigging": "spade_for_digging",
            "JamesBond007": "james_bond007",
            "JamesBOND": "james_bond",
            "James-BOND-007": "james_bond_007",
            }
        observed = {
            name_in: api.handler_command_name(name_in)
            for name_in in expected
            }
        self.assertItemsEqual(
            expected.items(), observed.items())
        # handler_command_name also ensures that all names are encoded into
        # byte strings.
        expected_types = {
            name_out: bytes
            for name_out in observed.values()
            }
        observed_types = {
            name_out: type(name_out)
            for name_out in observed.values()
            }
        self.assertItemsEqual(
            expected_types.items(), observed_types.items())

    def test_handler_command_name_non_ASCII(self):
        # handler_command_name will not break if passed a string with
        # non-ASCII characters. However, those characters will not be present
        # in the returned name.
        self.assertEqual(
            "a_b_c", api.handler_command_name(u"a\u1234_b\u5432_c\u9876"))

    def test_ensure_trailing_slash(self):
        # ensure_trailing_slash ensures that the given string - typically a
        # URL or path - has a trailing forward slash.
        self.assertEqual("fred/", api.ensure_trailing_slash("fred"))
        self.assertEqual("fred/", api.ensure_trailing_slash("fred/"))

    def test_ensure_trailing_slash_string_type(self):
        # Given a unicode string, ensure_trailing_slash will always return a
        # unicode string, and given a byte string it will always return a byte
        # string.
        self.assertIsInstance(api.ensure_trailing_slash(u"fred"), unicode)
        self.assertIsInstance(api.ensure_trailing_slash(b"fred"), bytes)
