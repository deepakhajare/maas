# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model for the metadata server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'NodeInitUser',
    ]

from django.contrib.auth.models import User


class NodeInitUser:
    """Wrapper for the maas-node-init user.

    This is the "user" that makes metadata requests on behalf of the nodes.

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

    @classmethod
    def get(cls):
        """Return the singleton `NodeInitUser`."""
        return cls()
