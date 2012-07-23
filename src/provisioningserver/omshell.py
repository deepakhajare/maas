# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Python wrapper around the `omshell` utility which amends objects
inside the DHCP server.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


class Omshell:
    """Wrap up the omshell utility in Python."""

    def __init__(self, server_address, shared_key):
        pass

    def create(self, ip_address, mac_address):
        pass

    def remove(self, ip_address):
        pass
