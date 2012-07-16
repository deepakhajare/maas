# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for testing helpers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os
import random

from maastesting.factory import factory
from maastesting.testcase import TestCase
from maastesting.utils import (
    extract_word_list,
    increment_age,
    incremental_write,
    )


class TestFunctions(TestCase):

    def test_extract_word_list(self):
        expected = {
            "one 2": ["one", "2"],
            ", one ; 2": ["one", "2"],
            "one,2": ["one", "2"],
            "one;2": ["one", "2"],
            "\none\t 2;": ["one", "2"],
            "\none-two\t 3;": ["one-two", "3"],
            }
        observed = {
            string: extract_word_list(string)
            for string in expected
            }
        self.assertEqual(expected, observed)


class TestIncrementalWrite(TestCase):
    """Test `incremental_write`."""

    def test_incremental_write_increments_modification_time(self):
        content = factory.getRandomString()
        filename = self.make_file(contents=factory.getRandomString())
        # Pretend that this file is older than it is.  So that
        # incrementing its mtime won't put it in the future.
        old_mtime = os.stat(filename).st_mtime - 10
        os.utime(filename, (old_mtime, old_mtime))
        incremental_write(content, filename)
        self.assertAlmostEqual(
            os.stat(filename).st_mtime, old_mtime + 1, delta=0.01)


class TestIncrementAge(TestCase):
    """Test `increment_age`."""

    def setUp(self):
        super(TestIncrementAge, self).setUp()
        self.filename = self.make_file()
        self.now = os.stat(self.filename).st_mtime

    def test_increment_age_sets_mtime_in_the_past(self):
        delta = random.randint(100, 200)
        increment_age(self.filename, old_mtime=None, delta=delta)
        self.assertAlmostEqual(
            os.stat(self.filename).st_mtime,
            self.now - delta, delta=2)

    def test_increment_age_increments_mtime(self):
        old_mtime = self.now - 200
        increment_age(self.filename, old_mtime=old_mtime)
        self.assertAlmostEqual(
            os.stat(self.filename).st_mtime, old_mtime + 1, delta=0.01)

    def test_increment_age_does_not_increment_mtime_if_in_future(self):
        old_mtime = self.now + 200
        increment_age(self.filename, old_mtime=old_mtime)
        self.assertAlmostEqual(
            os.stat(self.filename).st_mtime, old_mtime, delta=0.01)
