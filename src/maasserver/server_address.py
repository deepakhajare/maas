# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper to obtain the MAAS server's address."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'get_maas_facing_server_address',
    ]


from socket import gethostbyname
from urlparse import urlparse

from django.conf import settings


def get_maas_facing_server_address():
    """Return address where nodes and workers can reach the MAAS server.

    The address is derived from DEFAULT_MAAS_URL, which in turn is derived
    from the server's primary IP address by default, but can be overridden
    for multi-interface servers where this guess is wrong.

    Since DEFAULT_MAAS_URL is also used for locating the user interface,
    this won't work if NAT gives the server different IP addresses from the
    user's perspective and from inside the MAAS.  If we ever need to split
    the two perspectives, `get_maas_facing_server_address` is explicitly
    meant to guide connections from nodes and workers towards the server.

    :return: An IP address.  If the configured URL uses a hostname, this
        function will resolve that hostname.
    """
    host = urlparse(settings.DEFAULT_MAAS_URL).netloc.split(':')[0]
    return gethostbyname(host)
