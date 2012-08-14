# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests cache."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from multiprocessing.managers import DictProxy

from maastesting.factory import factory
from provisioningserver.cache import cache
from provisioningserver.testing.testcase import TestCase


class TestCache(TestCase):

    def test_cache_initializes_backend(self):
        self.assertIsInstance(cache.cache_backend, DictProxy)

    def test_cache_stores_key_value(self):
        key = factory.getRandomString()
        value = factory.getRandomString()
        cache.set(key, value)
        self.assertEqual(value, cache.get(key))

    def test_cache_clear(self):
        cache.set(factory.getRandomString(), factory.getRandomString())
        cache.clear()
        self.assertEqual(0, len(cache.cache_backend))
