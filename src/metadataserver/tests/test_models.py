# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model tests for metadata server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maasserver.models import UserProfile
from maastesting import TestCase
from metadataserver.models import (
    NodeInitUser,
    User,
    )


class TestNodeInitUser(TestCase):
    """Test the special "user" that makes metadata requests from nodes."""

    def test_always_wraps_same_user(self):
        node_init_user = NodeInitUser()
        self.assertEqual(node_init_user.user.id, NodeInitUser().user.id)

    def test_reloads_if_already_created(self):
        user = NodeInitUser().user
        self.assertEqual(user.id, NodeInitUser().user.id)

    def test_holds_node_init_user(self):
        user = NodeInitUser.get().user
        self.assertIsInstance(user, User)
        self.assertEqual(NodeInitUser.user_name, user.username)
        self.assertItemsEqual([], UserProfile.objects.filter(user=user))
