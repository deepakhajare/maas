# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generate kernel command-line options for inclusion in PXE configs."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'compose_kernel_command_line',
    ]

from maasserver.utils import absolute_reverse


def compose_enlistment_preseed_url():
    """Compose enlistment preseed URL."""
    # Always uses the latest version of the metadata API.
    version = 'latest'
    return absolute_reverse(
        'metadata-enlist-preseed', args=[version],
        query={'op': 'get_enlist_preseed'})


def compose_preseed_url(node):
    """Compose a metadata URL for `node`'s preseed data."""
    # Always uses the latest version of the metadata API.
    version = 'latest'
    return absolute_reverse(
        'metadata-node-by-id', args=[version, node.system_id],
        query={'op': 'get_preseed'})


def compose_preseed_opt(node):
    """Compose a kernel option for preseed URL for given `node`.

    :param mac_address: A `Node`, or `None`.
    """
    if node is None:
        preseed_url = compose_enlistment_preseed_url()
    else:
        preseed_url = compose_preseed_url(node)
    return "auto url=%s" % preseed_url


def compose_kernel_command_line(node, arch, subarch, purpose):
    """Generate a line of kernel options for booting `node`.

    Include these options in the PXE config file's APPEND argument.

    The node may be None, in which case it will boot into enlistment.
    """
    options = [
        compose_preseed_opt(node),
        ]
    return ' '.join(options)
