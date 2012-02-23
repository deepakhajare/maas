# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Custom field types for the metadata server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'BinaryField',
    ]

from base64 import (
    b64decode,
    b64encode,
    )

from django.db.models import (
    Field,
    SubfieldBase,
    )


class BinaryField(Field):
    """A field that stores binary data.

    The data is base64-encoded internally.
    """

    __metaclass__ = SubfieldBase

    def to_python(self, value):
        """Convert database value to python-side value."""
        if value is None:
            return None
        else:
            return b64decode(value)

    def get_db_prep_value(self, value):
        """Convert python-side value to database value."""
        if value is None:
            return None
        else:
            return b64encode(value)

    def get_internal_type(self):
        return 'TextField'
