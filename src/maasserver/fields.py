# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Custom model fields."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "MACAddressField",
    "MACAddressFormField",
    ]

from copy import deepcopy
from json import (
    dumps,
    loads,
    )
import re

from django.core.validators import RegexValidator
from django.db.models import (
    Field,
    SubfieldBase,
    )
from django.forms import RegexField
import psycopg2.extensions
from south.modelsinspector import add_introspection_rules


mac_re = re.compile(r'^\s*([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\s*$')


mac_error_msg = "Enter a valid MAC address (e.g. AA:BB:CC:DD:EE:FF)."


validate_mac = RegexValidator(regex=mac_re, message=mac_error_msg)


# The MACAddressField, JSONObjectField and XMLField don't introduce any new
# parameters compared to their parent's constructors so South will handle
# them just fine.
# See http://south.aeracode.org/docs/customfields.html#extending-introspection
# for details.
add_introspection_rules(
    [], [
        "^maasserver\.fields\.MACAddressField",
        "^maasserver\.fields\.JSONObjectField",
        "^maasserver\.fields\.XMLField",
    ])


class MACAddressFormField(RegexField):

    def __init__(self, *args, **kwargs):
        super(MACAddressFormField, self).__init__(
            regex=mac_re, error_message=mac_error_msg, *args, **kwargs)


class MACAddressField(Field):
    """Model field type: MAC address."""

    description = "MAC address"

    default_validators = [validate_mac]

    def db_type(self, *args, **kwargs):
        return "macaddr"


class MACAddressAdapter:
    """Adapt a `MACAddressField` for database storage using psycopg2.

    PostgreSQL supports MAC addresses as a native type.
    """

    def __init__(self, value):
        self._wrapped = value

    def getquoted(self):
        """Render this object in SQL."""
        if self._wrapped is None:
            return 'NULL'
        else:
            return "'%s'::macaddr" % self._wrapped


psycopg2.extensions.register_adapter(MACAddressField, MACAddressAdapter)


class JSONObjectField(Field):
    """A field that will store any jsonizable python object."""

    __metaclass__ = SubfieldBase

    def to_python(self, value):
        """db -> python: json load."""
        if value is not None:
            if isinstance(value, basestring):
                try:
                    return loads(value)
                except ValueError:
                    pass
            return value
        else:
            return None

    def get_db_prep_value(self, value, connection=None, prepared=False):
        """python -> db: json dump."""
        if value is not None:
            return dumps(deepcopy(value))
        else:
            return None

    def get_internal_type(self):
        return 'TextField'

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type not in ['exact', 'isnull']:
            raise TypeError("Lookup type %s is not supported." % lookup_type)
        return super(JSONObjectField, self).get_prep_lookup(
            lookup_type, value)


class XMLField(Field):
    """A field for storing xml natively.

    This is not like the removed Django XMLField which just added basic python
    level checking on top of a text column.

    Really inserts should be wrapped like `XMLPARSE(DOCUMENT value)` but it's
    hard to do from django so rely on postgres supporting casting from char.
    """

    description = "XML document or fragment"

    def db_type(self, connection):
        return "xml"

    def get_db_prep_lookup(self, lookup_type, value):
        """Limit lookup types to those that work on xml.

        Unlike character fields the xml type is non-comparible, see:
        <http://www.postgresql.org/docs/devel/static/datatype-xml.html>
        """
        if lookup_type != 'isnull':
            raise TypeError("Lookup type %s is not supported." % lookup_type)
        return super(XMLField, self).get_db_prep_lookup(lookup_type, value)
