# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Custom commissioning scripts, and their database backing."""


from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'CommissioningScript',
    ]


from django.db.models import (
    Manager,
    Model,
    )
from metadataserver import DefaultMeta


class CommissioningScriptManager(Manager):
    """Manager for `CommissioningScript`.

    Don't import or instantiate this directly; access as
    `CommissioningScript.objects`.
    """


class CommissioningScript(Model):

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    objects = CommissioningScriptManager()
