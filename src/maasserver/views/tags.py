# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tag views."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'TagView',
    ]

from maasserver.models import Tag


class TagView:
    """Basic view of a tag.
    """

    context_object_name = 'tag'

    def get_object(self):
        system_id = self.kwargs.get('name', None)
        tag = Tag.objects.get_tag_or_404(
            name=name, user=self.request.user,
            to_edit=False)
        return tag


