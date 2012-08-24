# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Fixture to simulate the cache that worker processes normally share."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'WorkerCacheFixture',
    ]

from fixtures import Fixture
from provisioningserver import cache


class WorkerCacheFixture(Fixture):
    """Fake the cache that worker processes share."""

    def setUp(self):
        super(WorkerCacheFixture, self).setUp()
        self.old_initialized = cache.initialized
        self.old_cache = cache.cache
        cache.cache = cache.Cache({})
        cache.initalized = True

    def cleanUp(self):
        cache.cache = self.old_cache
        cache.initialized = self.old_initialized
        super(WorkerCacheFixture, self).cleanUp()
