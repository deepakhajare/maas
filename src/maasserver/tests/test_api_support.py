# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for MAAS Piston API support code."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django.http import QueryDict
from maasserver.api_utils import get_overrided_query_dict
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase


class TestGetOverridedQueryDict(TestCase):

    def test_get_overrided_query_dict_returns_QueryDict(self):
        defaults = {factory.getRandomString(): factory.getRandomString()}
        results = get_overrided_query_dict(defaults, QueryDict(''))
        expected_results = QueryDict('').copy()
        expected_results.update(defaults)
        self.assertEqual(expected_results, results)

    def test_get_overrided_query_dict_values_in_data_replaces_defaults(self):
        key = factory.getRandomString()
        defaults = {key: factory.getRandomString()}
        data_value = factory.getRandomString()
        data = {key: data_value}
        results = get_overrided_query_dict(defaults, data)
        self.assertEqual([data_value], results.getlist(key))
