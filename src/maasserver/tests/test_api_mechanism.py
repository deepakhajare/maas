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
        decorate = api_exported(method=random_method)
        self.assertRaises(ValueError, decorate, lambda: None)

    def test_allowed_methods(self):
        # HTTP methods in dispatch_methods should not be allowed.
        for method in dispatch_methods:
            decorate = api_exported(method=dispatch_methods.get(method))
            self.assertRaises(ValueError, decorate, lambda: None)

    def test_valid_decoration(self):
        value = "value" + factory.getRandomString()
        decorate = api_exported()
        decorated = decorate(lambda: value)
        self.assertEqual(value, decorated())

    def test_can_pass_export_as(self):
        # Test that passing the optional "export_as" works as expected.

        def foo():
            pass

        random_exported_name = "exportedas" + factory.getRandomString()
        decorate = api_exported(
            exported_as=random_exported_name, method="POST")
        decorated = decorate(foo)

        self.assertEqual(
            random_exported_name, decorated._api_exported["POST"])

