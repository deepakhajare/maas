# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ORM-related utilities."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'get_one',
    ]

from django.core.exceptions import MultipleObjectsReturned


def get_exception_class(items):
    """Return exception class to raise."""
    model = getattr(items, 'model', None)
    if model is None:
        return MultipleObjectsReturned
    else:
        return getattr(
            model, 'MultipleObjectsReturned', MultipleObjectsReturned)


def get_one(items):
    """Assume there's at most one item in `items`, and return it (or None).

    If `items` contains more than one item, raise an error.  If `items` looks
    like a Django ORM result set, the error will be of the same model-specific
    Django `MultipleObjectsReturned` type that `items.get()` would raise.
    Otherwise, a plain Django :class:`MultipleObjectsReturned` error.

    :param items: Any sequence.
    :return: The one item in that sequence, or None if it was empty.
    """
    retrieved_items = items[:2]
    length = len(retrieved_items)
    if length == 0:
        return None
    elif length == 1:
        return retrieved_items[0]
    else:
        raise get_exception_class(items)("Got more than one item.")
