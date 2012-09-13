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


class TestAPICommand(TestCase):

    def test_find_action_not_found(self):
        # find_action() looks through the actions list to find one with the
        # given name, and raises LookupError when one can't be found.
        handler = api.APICommand()
        handler.actions = []
        self.assertRaises(LookupError, handler.get_action, "bob")

    def test_find_action_checks_name_field(self):
        # find_action() looks through the actions list. Each action is a dict,
        # and it uses the "name" field for comparisons.
        handler = api.APICommand()
        handler.actions = [{"name": "alice"}, {"name": "bob"}]
        self.assertEqual({"name": "bob"}, handler.get_action("bob"))
