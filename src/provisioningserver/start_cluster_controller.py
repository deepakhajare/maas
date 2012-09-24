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


class ClusterControllerRejected(Exception):
    """Request to become a cluster controller has been rejected."""


def add_arguments(parser):
    """This command takes no arguments."""


def request_accreditation():
    """Request Rabbit connection details from the domain controller.

    Offers this machine to the region controller as a potential cluster
    controller.

    :return: A dict of connection details if this cluster controller has been
        accepted, or `None` if accreditation is still pending.
    :raise ClusterControllerRejected: if this system has been rejected as a
        cluster controller.
    """


def start_up(connection_details):
    """We've been accepted as a cluster controller; start doing the job."""


def run(args):
    """Start the cluster controller.

    If this system is still awaiting approval as a cluster controller, this
    command will keep looping until it gets a definite answer.
    """
