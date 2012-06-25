# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the factory where appropriate.  Don't overdo this."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from datetime import datetime
import os.path
from random import randint

from maastesting.factory import factory
from maastesting.testcase import TestCase
from testtools.matchers import (
    Contains,
    FileContains,
    FileExists,
    MatchesAll,
    Not,
    StartsWith,
    )


class TestFactory(TestCase):

    def test_getRandomString_respects_size(self):
        sizes = [1, 10, 100]
        random_strings = [factory.getRandomString(size) for size in sizes]
        self.assertEqual(sizes, [len(string) for string in random_strings])

    def test_getRandomBoolean_returns_bool(self):
        self.assertIsInstance(factory.getRandomBoolean(), bool)

    def test_getRandomPort_returns_int(self):
        self.assertIsInstance(factory.getRandomPort(), int)

    def test_getRandomDate_returns_datetime(self):
        self.assertIsInstance(factory.getRandomDate(), datetime)

    def test_getRandomMACAddress(self):
        mac_address = factory.getRandomMACAddress()
        self.assertIsInstance(mac_address, str)
        self.assertEqual(17, len(mac_address))
        for hex_octet in mac_address.split(":"):
            self.assertTrue(0 <= int(hex_octet, 16) <= 255)

    def test_make_file_creates_file(self):
        self.assertThat(factory.make_file(self.make_dir()), FileExists())

    def test_make_file_writes_contents(self):
        contents = factory.getRandomString().encode('ascii')
        self.assertThat(
            factory.make_file(self.make_dir(), contents=contents),
            FileContains(contents))

    def test_make_file_makes_up_contents_if_none_given(self):
        with open(factory.make_file(self.make_dir())) as temp_file:
            contents = temp_file.read()
        self.assertNotEqual('', contents)

    def test_make_file_uses_given_name(self):
        name = factory.getRandomString()
        self.assertEqual(
            name,
            os.path.basename(factory.make_file(self.make_dir(), name=name)))

    def test_make_file_uses_given_dir(self):
        directory = self.make_dir()
        name = factory.getRandomString()
        self.assertEqual(
            (directory, name),
            os.path.split(factory.make_file(directory, name=name)))

    def test_make_name_returns_unicode(self):
        self.assertIsInstance(factory.make_name(), unicode)

    def test_make_name_combines_prefix_sep_and_random_text(self):
        self.assertThat(factory.make_name('abc'), StartsWith('abc-'))

    def test_make_name_includes_random_text_of_requested_length(self):
        size = randint(1, 99)
        self.assertEqual(
            len('prefix') + len('-') + size,
            len(factory.make_name('prefix', size=size)))

    def test_make_name_uses_configurable_separator(self):
        sep = ':%s:' % factory.getRandomString(3)
        prefix = factory.getRandomString(3)
        self.assertThat(
            factory.make_name(prefix, sep=sep),
            StartsWith(prefix + sep))

    def test_make_name_does_not_require_prefix(self):
        size = randint(1, 99)
        unprefixed_name = factory.make_name(sep='-', size=size)
        self.assertEqual(size, len(unprefixed_name))
        self.assertThat(unprefixed_name, Not(StartsWith('-')))

    def test_make_name_does_not_include_weird_characters(self):
        self.assertThat(
            factory.make_name(size=100),
            MatchesAll(*[Not(Contains(char)) for char in '/ \t\n\r\\']))
