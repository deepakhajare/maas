# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Network utilities."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'int_to_dotted_quad',
    'dotted_quad_to_int',
    'next_ip',
    ]

import socket
import struct


def int_to_dotted_quad(n):
    """Convert int to dotted quad string.

    >>> int_to_dotted_quad(3232235521)
    '192.168.0.1'
    """
    return socket.inet_ntoa(struct.pack(str('>L'), n))


def dotted_quad_to_int(ip):
    """Convert decimal dotted quad string to integer.

    >>> dotted_quad_to_int('192.168.0.1')
    3232235521L
    """
    return struct.unpack(str('>L'), socket.inet_aton(ip))[0]


def next_ip(ip):
    """Return the next IP Address.

    IP Addresses being essentially 32-bit integers, this returns
    the next IP Address conresponding to the next 32-bit integer.

    >>> next_ip('192.168.0.1')
    '192.168.0.2'
    """
    return int_to_dotted_quad(dotted_quad_to_int(ip) + 1)
