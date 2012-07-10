# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Node IP/MAC mappings as leased from the workers' DHCP servers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'DHCPLease',
    ]


from django.db.models import (
    ForeignKey,
    IPAddressField,
    Manager,
    Model,
    )
from maasserver import DefaultMeta
from maasserver.fields import MACAddressField
from maasserver.models.cleansave import CleanSave


class DHCPLeaseManager(Manager):
    """Utility for managing :class:`DHCPLease` objects.

    This will be a large and busy part of the database.  Try to perform
    operations in bulk, in this manager class, where at all possible.
    """

    def update(self, nodegroup, leases):
        """Refresh our knowledge of a node group's IP mappings.

        This deletes entries that are no longer current, adds new ones,
        and updates or replaces ones that have changed.

        :param nodegroup: The node group that these updates are for.
        :param leases: A dict describing all current IP/MAC mappings as
            managed by the node group's DHCP server.  Keys are IP
            addresses, values are MAC addresses.  Any :class:`DHCPLease`
            entries for `nodegroup` that are not in `leases` will be
            deleted.
        """


class DHCPLease(CleanSave, Model):
    """A known mapping of an IP address to a MAC address.

    These correspond to the latest-known DHCP leases handed out to nodes
    (or potential nodes -- they may not have been enlisted yet!) by the
    node group worker's DHCP server.
    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    objects = DHCPLeaseManager()

    nodegroup = ForeignKey('maasserver.NodeGroup', null=False, editable=False)
    ip = IPAddressField(null=False, editable=False, unique=True)
    mac = MACAddressField(null=False, editable=False, unique=False)

    def __unicode__(self):
        return "%s->%s" % (self.ip, self.mac)
