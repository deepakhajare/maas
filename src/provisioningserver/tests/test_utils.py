# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `provisioningserver.utils`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.utils import (
    Safe,
    ShellTemplate,
    )


class TestSafe(TestCase):
    """Test `Safe`."""

    def test_value(self):
        something = object()
        safe = Safe(something)
        self.assertIs(something, safe.value)

    def test_repr(self):
        string = factory.getRandomString()
        safe = Safe(string)
        self.assertEqual("<Safe %r>" % string, repr(safe))


class TestShellTemplate(TestCase):
    """Test `ShellTemplate`."""

    def test_substitute(self):
        # Substitutions will be shell-escaped, unless marked `safe`.
        template = ShellTemplate("{{a}} {{b|safe}} {{safe(c)}}")
        expected = "'1 2 3' a b c $ ! ()"
        observed = template.substitute(a="1 2 3", b="a b c", c="$ ! ()")
        self.assertEqual(expected, observed)
