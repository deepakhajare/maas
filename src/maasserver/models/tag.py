# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Node objects."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "Tag",
    ]

from django.db.models import (
    CharField,
    TextField,
    Manager,
    ManyToManyField,
    )
from maasserver import DefaultMeta
from maasserver.models.cleansave import CleanSave
from maasserver.models.timestampedmodel import TimestampedModel
from maasserver.models.node import Node


class TagManager(Manager):
    """A utility to manage the collection of Tags."""
    pass


class Tag(CleanSave, TimestampedModel):
    """A `Tag` is a label applied to a `Node`.

    :ivar name: The short-human-identifiable name for this tag.
    :ivar definition: The XPATH string identifying what nodes should match this
        tag.
    :ivar comment: A long-form description for humans about what this tag is
        trying to accomplish.
    :ivar nodes: A list of the Nodes that are labled by this particular tag.
    :ivar objects: The :class:`TagManager`.
    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    name = CharField(max_length=256, unique=True, editable=True)
    definition = TextField()
    comment = TextField(blank=True)

    nodes = ManyToManyField(Node)
    objects = TagManager()

    def __unicode__(self):
        return self.name
