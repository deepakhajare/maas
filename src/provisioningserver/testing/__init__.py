# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""..."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "skip",
    ]

from functools import wraps
from unittest.case import SkipTest


def skip(reason):
    """Skip a test.

    :param reason: The reason why this test is being skipped.
    :type reason: String.
    """
    def decorator(test):
        @wraps(test)
        def skip_test(self=None):
            raise SkipTest(reason)
        return skip_test
    return decorator
