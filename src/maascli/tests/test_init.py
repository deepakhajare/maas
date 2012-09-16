# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maascli`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maascli import ArgumentParser
from maastesting.testcase import TestCase


class TestArgumentParser(TestCase):

    def test_add_subparsers_disabled(self):
        parser = ArgumentParser()
        self.assertRaises(NotImplementedError, parser.add_subparsers)

    def test_subparsers_property(self):
        parser = ArgumentParser()
        # argparse.ArgumentParser.add_subparsers populates a _subparsers
        # attribute when called. Its contents are not the same as the return
        # value from add_subparsers, so we just use it an indicator here.
        self.assertIsNone(parser._subparsers)
        # Reference the subparsers property.
        subparsers = parser.subparsers
        # _subparsers is populated, meaning add_subparsers has been called on
        # the superclass.
        self.assertIsNotNone(parser._subparsers)
        # The subparsers property, once populated, always returns the same
        # object.
        self.assertIs(subparsers, parser.subparsers)
