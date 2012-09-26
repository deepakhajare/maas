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

from maasserver.api import operation
from maasserver.testing.factory import factory
from maastesting.testcase import TestCase


class TestOperationDecorator(TestCase):
    """Testing for the `operation` decorator."""

    def test_valid_decoration(self):
        value = "value" + factory.getRandomString()
        decorate = operation(idempotent=False)
        decorated = decorate(lambda: value)
        self.assertEqual(value, decorated())

    def test_can_pass_exported_as(self):
        # Test that passing the optional "exported_as" works as expected.
        random_exported_name = factory.make_name("exportedas", sep='')
        decorate = operation(
            idempotent=False, exported_as=random_exported_name)
        decorated = decorate(lambda: None)
        self.assertEqual(
            [random_exported_name],
            decorated._api_exported.values())

    def test_exported_as_is_optional(self):
        # If exported_as is not passed then we expect the function to be
        # exported in the API using the actual function name itself.

        def exported_function():
            pass

        decorate = operation(idempotent=True)
        decorated = decorate(exported_function)

        self.assertEqual(
            ["exported_function"],
            decorated._api_exported.values())
