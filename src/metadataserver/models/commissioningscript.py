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
    CharField,
    Manager,
    Model,
    )
from metadataserver import DefaultMeta
from metadataserver.fields import BinaryField


class CommissioningScriptManager(Manager):
    """Manager for `CommissioningScript`.

    Don't import or instantiate this directly; access as
    `CommissioningScript.objects`.
    """

    def store_script(self, name, content):
        return # TODO: Watch tests fail first.
        script, created = self.get_or_create(name, {'content': content})
        if not created:
            script.content = content
            content.save()

    def get_scripts(self):
        return [] # TODO: Watch tests fail first.

    def drop_script(self, name):
        return # TODO: Watch tests fail first.


class CommissioningScript(Model):

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    objects = CommissioningScriptManager()

    name = CharField(max_length=255, null=False, editable=False, unique=True)
    content = BinaryField(null=False)
