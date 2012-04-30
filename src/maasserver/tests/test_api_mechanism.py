# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing of the API infrastructure, as opposed to code that uses it to
export API methods.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maastesting.testcase import TestCase
from maasserver.testing.factory import factory

from maasserver.api import (
    api_exported,
    dispatch_methods,
    )


class TestApiExported(TestCase):
    """Testing for the api_exported decorator."""

    def test_invalid_method(self):
        # If the supplied HTPP method is not in the allowed set, it should
        # raise a ValueError.
        random_method = "method" + factory.getRandomString(4)
        decorated = api_exported(method=random_method)
        self.assertRaises(ValueError, decorated, lambda: None)

    def test_allowed_methods(self):
        # HTTP methods in dispatch_methods should not be allowed.
        for method in dispatch_methods:
            decorated = api_exported(method=dispatch_methods.get(method))
            self.assertRaises(ValueError, decorated, lambda: None)

    def test_valid_decoration(self):
        value = "value" + factory.getRandomString()
        decorated = api_exported()
        func = decorated(lambda: value)
        self.assertEqual(value, func())
