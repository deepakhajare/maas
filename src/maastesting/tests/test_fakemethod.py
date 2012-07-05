# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for :class:`FakeMethod`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maastesting.fakemethod import FakeMethod
from maastesting.testcase import TestCase


class TestFakeMethod(TestCase):

    def test_fakemethod_returns_None_by_default(self):
        self.assertEqual(None, FakeMethod()())

    def test_fakemethod_returns_given_value(self):
        self.assertEqual("Input value", FakeMethod("Input value")())

    def test_fakemethod_raises_given_failure(self):
        class ExpectedException(Exception):
            pass

        self.assertRaises(
            ExpectedException,
            FakeMethod(failure=ExpectedException()))

    def test_fakemethod_has_no_calls_initially(self):
        self.assertSequenceEqual([], FakeMethod().calls)

    def test_fakemethod_records_call(self):
        stub = FakeMethod()
        stub()
        self.assertSequenceEqual([((), {})], stub.calls)

    def test_fakemethod_records_args(self):
        stub = FakeMethod()
        stub(1, 2)
        self.assertSequenceEqual([((1, 2), {})], stub.calls)

    def test_fakemethod_records_kwargs(self):
        stub = FakeMethod()
        stub(x=10)
        self.assertSequenceEqual([((), {'x': 10})], stub.calls)
