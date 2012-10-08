# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Fake `ProfileConfig` for testing."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maastesting.factory import factory


class FakeConfig(dict):
    """Fake `ProfileConfig`.  A dict that's also a context manager."""
    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        pass


def make_configs(number_of_configs=1):
    """Create a dict mapping config names to `FakeConfig`."""
    result = {}
    while len(result) < number_of_configs:
        profile = factory.make_name('profile')
        result[profile] = {
            'name': profile,
            'url': 'http://%s.example.com/' % profile,
            'description': {
                'handlers': [{
                    'name': factory.make_name('handler'),
                    'doc': "Short\n\nLong",
                    'params': [],
                    'actions': [{
                        'name': factory.make_name('action'),
                        'doc': "Doc\n\nstring",
                    }],
                }],
            },
        }
    return FakeConfig(result)
