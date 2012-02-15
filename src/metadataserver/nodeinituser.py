# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""User management for nodes' access to the metadata service."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'NodeInitUser',
    ]

from django.contrib.auth.models import User
from maasserver.models import create_auth_token
from metadataserver.models import NodeKey


class NodeInitUser:
    """Wrapper for the maas-node-init user.

    This is the "user" that makes metadata requests on behalf of the nodes.
    Each node logs in as this user, but each using its own token.

    All instances of `NodeInitUser` share the same `User` identity.   There
    is no mutable state in this class.

    :ivar user_name: The reserved user name for this special user.
    :ivar user: The User object, once it has been loaded or created.
    """
    user_name = 'maas-node-init'
    user = None

    def __init__(self):
        """Do not instantiate these yourself; rely on `get` instead."""
        existing_user = list(
            User.objects.filter(username=NodeInitUser.user_name))
        if existing_user:
            # Special user already existed in the database.
            [self.user] = existing_user
        else:
            # Create special user.
            # Django won't let us create a user without email address,
            # so unfortunately we _have_ to make one up.
            self.user = User.objects.create_user(
                username=self.user_name, email='sample@example.com')

    def create_token(self, node):
        """Create an OAuth token for a given node.

        The node will be able to use this information for accessing the
        metadata service.  It will see its own, custom metadata.

        :param node: The system that is to be allowed access to the metadata
            service under the node init user's identity.
        :type node: Node
        :return: Consumer and Token for the node to use.  If passed the
            token's key, `self.get_node_for_key` will return `node`.
        :rtype: tuple
        """
        consumer, token = create_auth_token(self.user)
        NodeKey.objects.create(node=node, key=token.key).save()
        return consumer, token

    @staticmethod
    def get_node_for_key(key):
        """Find the `Node` that `key` was created for.

        :raise NodeKey.DoesNotExist: if `key` is not associated with any node.
        """
        return NodeKey.objects.get(key=key).node
