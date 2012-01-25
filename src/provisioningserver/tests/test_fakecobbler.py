# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import (
    print_function,
    unicode_literals,
    )

"""Tests for `FakeCobbler`."""

__metaclass__ = type
__all__ = []

from testtools.deferredruntest import AsynchronousDeferredRunTest
from unittest import TestCase
from provisioningserver import FakeCobbler, FakeTwistedProxy


def fake_cobbler():
    return FakeTwistedProxy(FakeCobbler())


class TestFakeCobbler(TestCase):

    run_tests_with = AsynchronousDeferredRunTest.make_factory()

    def test_something(self):
        self.assertTrue(1)
