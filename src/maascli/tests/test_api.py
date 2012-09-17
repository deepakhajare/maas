# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maascli.api`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maascli import api
from maastesting.testcase import TestCase
from mock import sentinel


class TestFunctions(TestCase):
    """Test for miscellaneous functions in `maascli.api`."""

    def test_try_getpass(self):
        getpass = self.patch(api, "getpass")
        getpass.return_value = sentinel.password
        self.assertIs(sentinel.password, api.try_getpass(sentinel.prompt))
        getpass.assert_called_once_with(sentinel.prompt)

    def test_try_getpass_eof(self):
        getpass = self.patch(api, "getpass")
        getpass.side_effect = EOFError
        self.assertIsNone(api.try_getpass(sentinel.prompt))
        getpass.assert_called_once_with(sentinel.prompt)
