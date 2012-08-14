# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""API credentials for node-group workers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'cache',
    ]


from multiprocessing import Manager


_manager = Manager()


class Cache(object):

    def __init__(self):
        self.clear()

    def set(self, key, value):
        self.cache_backend[key] = value

    def get(self, key):
        return self.cache_backend.get(key, None)

    def clear(self):
        self.cache_backend = _manager.dict()


# Initialize the process-safe cache object from this module.
cache = Cache()
