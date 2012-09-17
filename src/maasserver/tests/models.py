# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test related classes and functions for maas and its applications."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'JSONFieldModel',
    'FieldChangeTestModel',
    ]

from django.db.models import (
    CharField,
    Model,
    )
from maasserver.fields import (
    JSONObjectField,
    XmlField,
    )
from maasserver.models.timestampedmodel import TimestampedModel


class JSONFieldModel(Model):
    name = CharField(max_length=255, unique=False)
    value = JSONObjectField(null=True)


class XmlFieldModel(Model):

    class Meta:
        db_table = "docs"

    name = CharField(max_length=255, unique=False)
    value = XmlField(null=True)


class MessagesTestModel(Model):
    name = CharField(max_length=255, unique=False)


class TimestampedModelTestModel(TimestampedModel):
    # This model inherits from TimestampedModel so it will have a 'created'
    # field and an 'updated' field.
    pass


class FieldChangeTestModel(Model):
    name1 = CharField(max_length=255, unique=False)
    name2 = CharField(max_length=255, unique=False)
