# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ORM utilities."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django.core.exceptions import MultipleObjectsReturned
from maastesting.testcase import TestCase
from maasserver.utils.orm import get_one


class TestGetOne(TestCase):

    def test_get_one_returns_None_for_empty_result(self):
        self.fail("TEST THIS")

    def test_get_one_returns_single_result(self):
        self.fail("TEST THIS")

    def test_get_one_raises_django_error_if_query_result_is_too_big(self):
        self.fail("TEST THIS")

    def test_get_one_raises_assertion_error_if_other_sequence_is_too_big(self):
        self.fail("TEST THIS")
