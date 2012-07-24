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
__all__ = [
    "Omshell",
    ]

from StringIO import StringIO
from subprocess import (
    CalledProcessError,
    PIPE,
    Popen,
    )


class Omshell:
    """Wrap up the omshell utility in Python."""

    def __init__(self, server_address, shared_key):
        self.server_address = server_address
        self.shared_key = shared_key
        self.proc = Popen("omshell", stdin=PIPE, stdout=PIPE)

    def _run(self, stdin):
        stdout, stderr = self.proc.communicate(stdin)
        return stdout

    def create(self, ip_address, mac_address):
        stdin = (
            "server %(server)s\n"
            "key omapi_key %(key)s\n"
            "connect\n"
            "new host\n"
            "set ip-address = %(ip)s\n"
            "set hardware-address = %(mac)s\n"
            "set name = %(ip)s\n"
            "create\n")
        stdin = stdin % dict(
            server=self.server_address,
            key=self.shared_key,
            ip=ip_address,
            mac=mac_address)

        output = self._run(stdin)
        if "hardware-type" not in output:
            raise CalledProcessError(output)

    def remove(self, ip_address):
        pass
