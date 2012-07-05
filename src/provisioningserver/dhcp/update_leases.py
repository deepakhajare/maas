# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Send lease updates to the server.

This code runs inside node-group workers.  It watches for changes to DHCP
leases, and notifies the MAAS server so that it can rewrite DNS zone files
as appropriate.

Leases in this module are represented as dicts, mapping each leased IP
address to the MAC address that it belongs to.

The modification time and leases of the last-uploaded leases are cached,
so as to suppress unwanted redundant updates.  This cache is updated
*before* the actual upload, so as to prevent thundering-herd problems:
if an upload takes too long for whatever reason, subsequent updates
should not be uploaded until the first upload is done.  Some uploads may
be lost due to concurrency or failures, but the situation will right
itself eventually.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'upload_leases',
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


def upload_leases():
    """Unconditionally send the current DHCP leases to the server."""
    pass


def update_leases():
    """Check for DHCP lease updates, and send them to the server if needed.
    """
    pass
