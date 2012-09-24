# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Command: start the cluster controller."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'add_arguments',
    'run',
    ]

import httplib
import json
from time import sleep
from urllib2 import HTTPError

from apiclient.maas_client import (
    MAASClient,
    MAASDispatcher,
    NoAuth,
    )


class ClusterControllerRejected(Exception):
    """Request to become a cluster controller has been rejected."""


def add_arguments(parser):
    """For use by :class:`MainScript`."""
    parser.add_argument(
        'server_url', metavar='URL', help="URL to the MAAS region controller.")


def register(server_url):
    """Request Rabbit connection details from the domain controller.

    Offers this machine to the region controller as a potential cluster
    controller.

    :return: A dict of connection details if this cluster controller has been
        accepted, or `None` if accreditation is still pending.
    :raise ClusterControllerRejected: if this system has been rejected as a
        cluster controller.
    """
    known_responses = [httplib.OK, httplib.FORBIDDEN, httplib.ACCEPTED]
    client = MAASClient(NoAuth(), MAASDispatcher(), server_url)
    try:
        response = client.post('api/1.0/nodegroups', 'register')
    except HTTPError as e:
        status_code = e.code
        if e.code not in known_responses:
            raise
    else:
        status_code = response.getcode()

    if status_code == httplib.OK:
        return json.loads(response.read())
    elif status_code == httplib.FORBIDDEN:
        raise ClusterControllerRejected(
            "This system has been rejected as a cluster controller.")
    elif status_code == httplib.ACCEPTED:
        return None
    else:
        raise AssertionError("Unexpected return code: %r" % status_code)


def start_up(connection_details):
    """We've been accepted as a cluster controller; start doing the job."""


def run(args):
    """Start the cluster controller.

    If this system is still awaiting approval as a cluster controller, this
    command will keep looping until it gets a definite answer.
    """
    connection_details = register(args.server_url)
    while connection_details is None:
        sleep(60)
        connection_details = register(args.server_url)
    start_up(connection_details)
