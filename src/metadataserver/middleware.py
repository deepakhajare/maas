# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Middleware for the metadata service."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'AccessMiddleware',
    ]


from maasserver.exceptions import Unauthorized
from metadataserver.nodeinituser import get_node_init_user


class AccessMiddleware:
    """Require node authentication for access to metadata.

    The metadata service returns customized data for each node.  Thus a
    request must be authenticated.

    All requests authenticate under the node-init user, but using a token
    specific to the requesting node.
    """

    def process_request(self, request):
        if not request.path.startswith('/metadata/'):
            # This is not a metadata request.  Therefore it is of no
            # interest to this middleware class.
            return None
        node_init_user = get_node_init_user()
        if request.user != node_init_user:
            raise Unauthorized(
                "Must be logged in as %s to access node metadata."
                % node_init_user.username)
        return None
