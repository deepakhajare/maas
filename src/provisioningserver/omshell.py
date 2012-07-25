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

from subprocess import (
    CalledProcessError,
    PIPE,
    Popen,
    )
from textwrap import dedent


class Omshell:
    """Wrap up the omshell utility in Python."""

    def __init__(self, server_address, shared_key):
        self.server_address = server_address
        self.shared_key = shared_key

    def _run(self, stdin):
        command = ["omshell"]
        proc = Popen(command, stdin=PIPE, stdout=PIPE)
        stdout, stderr = proc.communicate(stdin)
        if proc.poll() != 0:
            raise CalledProcessError(proc.returncode, command, stdout)
        return proc.returncode, stdout

    def create(self, ip_address, mac_address):
        stdin = dedent("""\
            server %(server)s
            key omapi_key %(key)s
            connect
            new host
            set ip-address = %(ip_address)s
            set hardware-address = %(mac_address)s
            set name = %(ip_address)s
            create
            """)
        stdin = stdin % dict(
            server=self.server_address,
            key=self.shared_key,
            ip_address=ip_address,
            mac_address=mac_address)

        returncode, output = self._run(stdin)
        # If the call to omshell doesn't result in output containing the
        # magic string 'hardware-type' then we can be reasonably sure
        # that the 'create' command failed.  Unfortunately there's no
        # other output like "successful" to check so this is the best we
        # can do.
        if "hardware-type" not in output:
            raise CalledProcessError(returncode, "omshell", output)

    def remove(self, ip_address):
        stdin = dedent("""\
            server %(server)s
            key omapi_key %(key)s
            connect
            new host
            set name = %(ip_address)s
            open
            remove
            """)
        stdin = stdin % dict(
            server=self.server_address,
            key=self.shared_key,
            ip_address=ip_address)

        returncode, output = self._run(stdin)

        # If the omshell worked, the last line should reference a null
        # object.
        lines = output.splitlines()
        try:
            last_line = lines[-1]
        except IndexError:
            last_line = ""
        if last_line != "obj: <null>":
            raise CalledProcessError(returncode, "omshell", output)
