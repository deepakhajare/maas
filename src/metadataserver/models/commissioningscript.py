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
        """Store a commissioning script.

        :param name: Name for this commissioning script.  By convention, the
            name should start with a two-digit number.  The prefix "00-maas-"
            is reserved for MAAS-internal scripts.
        :type name: :class:`unicode`
        :param content: Binary script content.
        :type content: :class:`metadataserver.fields.Bin`
        :return: :class:`CommissioningScript` object.  If a script of the
            given `name` already existed, it will be updated with the given
            `content`.  Otherwise, it will be newly created.
        """
        script, created = self.get_or_create(
            name=name, defaults={'content': content})
        if not created:
            script.content = content
            script.save()
        return script

    def get_scripts(self):
        """Return all :class:`CommissioningScript` objects, sorted by name.

        The ordering is used to ensure a predictable execution order.
        """
        return self.order_by('name')

    def drop_script(self, name):
        """Delete the named :class:`CommissioningScript`, if it existed."""
        self.filter(name=name).delete()


class CommissioningScript(Model):

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    objects = CommissioningScriptManager()

    name = CharField(max_length=255, null=False, editable=False, unique=True)
    content = BinaryField(null=False)
