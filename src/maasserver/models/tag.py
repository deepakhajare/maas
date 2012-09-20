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
    )
from django.shortcuts import get_object_or_404
from maasserver import DefaultMeta
from maasserver.models.cleansave import CleanSave
from maasserver.models.timestampedmodel import TimestampedModel


# Permission model for tags. Everyone can see all tags, but only superusers can
# edit tags.
class TagManager(Manager):
    """A utility to manage the collection of Tags."""

    def get_tag_or_404(self, name):
        """Fetch a `Tag` by name.  Raise exceptions if no `Tag` with
        this name exist.

        :param name: The Tag.name.
        :type name: str
        :raises: django.http.Http404_,
            :class:`maasserver.exceptions.PermissionDenied`.

        .. _django.http.Http404: https://
           docs.djangoproject.com/en/dev/topics/http/views/
           #the-http404-exception
        """
        tag = get_object_or_404(Tag, name=name)
        return tag


class Tag(CleanSave, TimestampedModel):
    """A `Tag` is a label applied to a `Node`.

    :ivar name: The short-human-identifiable name for this tag.
    :ivar definition: The XPATH string identifying what nodes should match this
        tag.
    :ivar comment: A long-form description for humans about what this tag is
        trying to accomplish.
    :ivar objects: The :class:`TagManager`.
    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    name = CharField(max_length=256, unique=True, editable=True)
    definition = TextField()
    comment = TextField(blank=True)

    objects = TagManager()

    def __unicode__(self):
        return self.name

