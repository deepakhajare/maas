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
    "generate_omapi_key",
    "Omshell",
    ]

import os
import shutil
from subprocess import (
    CalledProcessError,
    check_output,
    PIPE,
    Popen,
    )
from tempfile import mkdtemp
from textwrap import dedent

from provisioningserver.utils import parse_config


def call_dnssec_keygen(tmpdir):
    return check_output(
        ['dnssec-keygen', '-r', '/dev/urandom', '-a', 'HMAC-MD5',
         '-b', '512', '-n', 'HOST', '-K', tmpdir, '-q', 'omapi_key'])


def generate_omapi_key():
    """Generate a HMAC-MD5 key by calling out to the dnssec-keygen tool.

    :return: The shared key suitable for OMAPI access.
    :type: string
    """
    # dnssec-keygen writes out files to a specified directory, so we
    # need to make a temp directory for that.

    # mkdtemp() says it will return a directory that is readable,
    # writable, and searchable only by the creating user ID.
    tmpdir = mkdtemp(prefix="%s." % os.path.basename(__file__))
    try:
        key_id = call_dnssec_keygen(tmpdir)

        # Locate the file that was written and strip out the Key: field in
        # it.
        if not key_id:
            raise AssertionError("dnssec-keygen didn't generate anything")
        key_id = key_id.strip()  # Remove trailing newline.
        key_file_name = os.path.join(tmpdir, key_id + '.private')
        config = parse_config(key_file_name)
        if 'Key' in config:
            return config['Key']
        else:
            raise AssertionError(
                "Key field not found in output from dnssec-keygen")
    finally:
        shutil.rmtree(tmpdir)


class Omshell:
    """Wrap up the omshell utility in Python.

    'omshell' is an external executable that communicates with a DHCP daemon
    and manipulates its objects.  This class wraps up the commands necessary
    to add and remove host maps (MAC to IP).

    :param server_address: The address for the DHCP server (ip or hostname)
    :param shared_key: An HMAC-MD5 key generated by dnssec-keygen like:
        $ dnssec-keygen -r /dev/urandom -a HMAC-MD5 -b 512 -n HOST omapi_key
        $ cat Komapi_key.+*.private |grep ^Key|cut -d ' ' -f2-
        It must match the key set in the DHCP server's config which looks
        like this:

        omapi-port 7911;
        key omapi_key {
            algorithm HMAC-MD5;
            secret "XXXXXXXXX"; #<-The output from the generated key above.
        };
        omapi-key omapi_key;
    """

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
            server {self.server_address}
            key omapi_key {self.shared_key}
            connect
            new host
            set ip-address = {ip_address}
            set hardware-address = {mac_address}
            set name = {ip_address}
            create
            """)
        stdin = stdin.format(
            self=self, ip_address=ip_address, mac_address=mac_address)

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
            server {self.server_address}
            key omapi_key {self.shared_key}
            connect
            new host
            set name = {ip_address}
            open
            remove
            """)
        stdin = stdin.format(
            self=self, ip_address=ip_address)

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
