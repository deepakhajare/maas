# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""DNS management module: connect DNS tasks with signals."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    ]


from django.db.models.signals import (
    post_delete,
    post_save,
    )
from django.dispatch import receiver
from maasserver.models import (
    Node,
    NodeGroup,
    NodeGroupInterface,
    )
from maasserver.signals import connect_to_field_change


@receiver(post_save, sender=NodeGroup)
def dns_post_save_NodeGroup(sender, instance, created, **kwargs):
    """Create or update DNS zones related to the saved nodegroup."""
    from maasserver.dns import write_full_dns_config, add_zone
    if created:
        add_zone(instance)
    else:
        write_full_dns_config()


# XXX rvb 2012-09-12: This is only needed because we use that
# information to pre-populate the zone file.  Once we stop doing that,
# this can be removed.
@receiver(post_save, sender=NodeGroupInterface)
def dns_post_save_NodeGroupInterface(sender, instance, created, **kwargs):
    """Create or update DNS zones related to the saved nodegroupinterface."""
    from maasserver.dns import write_full_dns_config, add_zone
    if created:
        add_zone(instance.nodegroup)
    else:
        write_full_dns_config()


@receiver(post_delete, sender=NodeGroup)
def dns_post_delete_NodeGroup(sender, instance, **kwargs):
    """Delete DNS zones related to the nodegroup."""
    from maasserver.dns import write_full_dns_config
    write_full_dns_config()


@receiver(post_delete, sender=Node)
def dns_post_delete_Node(sender, instance, **kwargs):
    """When a Node is deleted, update the Node's zone file."""
    from maasserver.dns import change_dns_zones
    change_dns_zones(instance.nodegroup)


def dns_post_edit_hostname_Node(instance, old_field):
    """When a Node has been flagged, update the related zone."""
    from maasserver.dns import change_dns_zones
    change_dns_zones(instance.nodegroup)


connect_to_field_change(dns_post_edit_hostname_Node, Node, 'hostname')
