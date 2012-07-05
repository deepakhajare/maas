# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Send lease updates to the server.

This code runs inside node-group workers.  It watches for changes to DHCP
leases, and notifies the MAAS server so that it can rewrite DNS zone files
as appropriate.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'send_leases',
    'update_leases',
    ]


from celeryconfig import DHCP_LEASES_FILE


def check_lease_changes():
    """Has the DHCP leases file changed in any significant way?"""
    pass


def parse_leases():
    """Parse the DHCP leases file.

    :return: A dict mapping each leased IP address to the MAC address that
        it has been assigned to.
    """
    # TODO: Implement leases-file parser here.


def record_lease_state(last_change, leases):
    """Record a snapshot of the state of DHCP leases.

    :param last_change: Modification date on the leases file with the given
        leases.
    :param leases: A dict mapping each leased IP address to the MAC address
        that it has been assigned to.
    """
    pass


def send_leases(leases):
    """Send snapshot of current leases to the MAAS server."""
    # TODO: Implement API call for uploading leases.


def update_leases():
    """Check for DHCP lease updates, and send them to the server if needed.
    """
    pass
