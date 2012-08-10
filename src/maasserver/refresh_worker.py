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


def refresh_worker(nodegroup):
    """Send worker for `nodegroup` a refresh message with credentials etc."""
