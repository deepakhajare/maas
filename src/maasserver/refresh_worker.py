# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Refresh node-group worker's knowledge."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'refresh_worker',
    ]

from provisioningserver.tasks import refresh_secrets


def refresh_worker(nodegroup):
    """Send worker for `nodegroup` a refresh message with credentials etc."""
    # TODO: Route this to the right worker, once we have multiple.
    knowledge = {
        'nodegroup_name': nodegroup.name,
    }
    if nodegroup.dhcp_key is not None and len(nodegroup.dhcp_key) > 0:
        knowledge['omapi_shared_key'] = nodegroup.dhcp_key
    refresh_secrets.delay(**knowledge)
