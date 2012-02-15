# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model for the metadata server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'NodeKey',
    ]

from django.db.models import (
    CharField,
    ForeignKey,
    Model,
    )
from maasserver.models import Node
from piston.models import KEY_SIZE


class NodeKey(Model):
    """Associate a Node with its OAuth (token) key."""
    node = ForeignKey(Node, null=False, editable=False)
    key = CharField(max_length=KEY_SIZE, null=False, editable=False)
