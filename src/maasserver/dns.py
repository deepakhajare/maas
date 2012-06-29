# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""DNS management module."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'zone_serial',
    ]


from maasserver.sequence import (
    INT_MAX,
    Sequence,
    )


ZONE_SERIAL_SEQ_NAME = 'zone_serial'


zone_serial = Sequence(ZONE_SERIAL_SEQ_NAME, minvalue=1, maxvalue=INT_MAX)


def next_zone_serial():
    return '%0.10d' % zone_serial.nextval()
