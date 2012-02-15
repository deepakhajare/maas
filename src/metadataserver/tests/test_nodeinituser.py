# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model tests for metadata server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django.contrib.auth.models import User
from maasserver.models import UserProfile
from maasserver.testing.factory import factory
from maastesting import TestCase
from metadataserver.models import NodeKey
from metadataserver.nodeinituser import NodeInitUser


class TestNodeInitUser(TestCase):
    """Test the special "user" that makes metadata requests from nodes."""

    def test_always_wraps_same_user(self):
        node_init_user = NodeInitUser()
        self.assertEqual(node_init_user.user.id, NodeInitUser().user.id)

    def test_reloads_if_already_created(self):
        user = NodeInitUser().user
        self.assertEqual(user.id, NodeInitUser().user.id)

    def test_holds_node_init_user(self):
        user = NodeInitUser().user
        self.assertIsInstance(user, User)
        self.assertEqual(NodeInitUser.user_name, user.username)
        self.assertItemsEqual([], UserProfile.objects.filter(user=user))

    def test_create_key_registers_node_key(self):
        node = factory.make_node()
        consumer, token = NodeInitUser().create_token(node)
        nodekey = NodeKey.objects.get(node=node, key=token.key)
        self.assertNotEqual(None, nodekey)

    def test_get_node_for_key_finds_node(self):
        node = factory.make_node()
        consumer, token = NodeInitUser().create_token(node)
        self.assertEqual(node, NodeInitUser.get_node_for_key(token.key))

    def test_get_node_for_key_raises_DoesNotExist_if_key_not_found(self):
        non_key = factory.getRandomString()
        self.assertRaises(
            NodeKey.DoesNotExist, NodeInitUser.get_node_for_key, non_key)
