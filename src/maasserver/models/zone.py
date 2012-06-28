# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""DNS zone."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'MAX_SERIAL',
    'Zone',
    ]


from django.db.models import (
    IntegerField,
    OneToOneField,
    )
from maasserver import DefaultMeta
from maasserver.models.cleansave import CleanSave
from maasserver.models.nodegroup import NodeGroup
from maasserver.models.timestampedmodel import TimestampedModel


LIMIT_SERIAL = 2 ** 32

MAX_SERIAL = LIMIT_SERIAL - 1

LIMIT_SIGNED_INT = 2 ** 31


class Zone(CleanSave, TimestampedModel):
    """A DNS zone.

    :ivar node_group: The associated NodeGroup.
    :type node_group: class:`NodeGroup`
    :ivar serial_number: The serial number (32-bit auto-incremented integer).
    :type serial_number: int
    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    node_group = OneToOneField(NodeGroup, null=False, unique=True)
    _serial_number = IntegerField(default=-LIMIT_SIGNED_INT)

    def __unicode__(self):
        return "nodegroup: %s / serial: %s" % (
            self.node_group.id, self.serial)

    def increment_serial_number(self):
        self.serial_number = (self.serial_number + 1) % LIMIT_SERIAL
        self.save()

    def _get_serial_number(self):
        return self._serial_number + LIMIT_SIGNED_INT

    def _set_serial_number(self, new_serial_number):
        self._serial_number = new_serial_number - LIMIT_SIGNED_INT

    serial_number = property(_get_serial_number, _set_serial_number)

    @property
    def serial(self):
        return '%0.10d' % self.serial_number
