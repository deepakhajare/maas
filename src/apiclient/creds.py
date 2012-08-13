# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Handling of MAAS API credentials."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'convert_string_to_tuple',
    'convert_tuple_to_string',
    ]


def convert_tuple_to_string(creds_tuple):
    """Represent a MAAS API credentials tuple as a colon-separated string."""
    return ':'.join(creds_tuple)


def convert_string_to_tuple(creds_string):
    """Recreate a MAAS API credentials tuple from a colon-separated string."""
    return tuple(creds_string.split(':'))
