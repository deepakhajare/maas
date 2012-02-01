# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.testing`."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from unittest.case import SkipTest

from provisioningserver.testing import skip
from testtools import TestCase
from testtools.testcase import ExpectedException


class TestSkipDecorator(TestCase):
    """Tests for `skip`."""

    def test_skip_function_test(self):
        function = lambda: 0 / 0
        skip_decorator = skip("Example reason")
        skip_decorated = skip_decorator(function)
        with ExpectedException(SkipTest, "Example reason"):
            skip_decorated()

    def test_skip_method_test(self):
        method = lambda self: 0 / 0
        skip_decorator = skip("Example reason")
        skip_decorated = skip_decorator(method)
        with ExpectedException(SkipTest, "Example reason"):
            skip_decorated(self)
