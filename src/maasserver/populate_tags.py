# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Populate what nodes are associated with a tag."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'populate_tags',
    ]

from maasserver.models import NodeGroup
from provisioningserver.tasks import update_node_tags


def populate_tags(tag):
    """Send worker for all nodegroups an update_node_tags request.
    """
    items = {
        'tag_name': tag.name,
        'tag_definition': tag.definition,
    }
    # NodeGroup.objects.refresh_workers()
    for nodegroup in NodeGroup.objects.all():
        update_node_tags.apply_async(queue=nodegroup.work_queue, kwargs=items)

