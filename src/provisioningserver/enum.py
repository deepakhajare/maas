# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enumerations meaningful to the provisioning server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'POWER_TYPE',
    'POWER_TYPE_CHOICES',
    ]


class POWER_TYPE:
    """Choice of mechanism to control a node's power."""

    # Use virsh (for virtual machines).
    VIRSH = 'virsh'

    # Network wake-up.
    WAKE_ON_LAN = 'ether_wake'


POWER_TYPE_CHOICES = (
    (POWER_TYPE.VIRSH, "virsh (virtual systems)"),
    (POWER_TYPE.WAKE_ON_LAN, "Wake-on-LAN"),
    )
