# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Registration of available boot images."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'BootImage',
    ]


from django.db.models import (
    CharField,
    Manager,
    Model,
    )
from maasserver import DefaultMeta


class BootImageManager(Manager):
    """Manager for model class.

    Don't import or instantiate this directly; access as `BootImage.objects`.
    """

    def get_by_natural_key(self, architecture, subarchitecture, release,
                           purpose):
        """Look up a specific image."""
        return self.get(
            architecture=architecture, subarchitecture=subarchitecture,
            release=release, purpose=purpose)

    def register_image(self, architecture, subarchitecture, release, purpose):
        """Register an image if it wasn't already registered."""
        self.get_or_create(
            architecture=architecture, subarchitecture=subarchitecture,
            release=release, purpose=purpose)

    def have_image(self, architecture, subarchitecture, release, purpose):
        """Is an image for the given kind of boot available?"""
        try:
            self.get_by_natural_key(
                architecture=architecture, subarchitecture=subarchitecture,
                release=release, purpose=purpose)
            return True
        except BootImage.DoesNotExist:
            return False


class BootImage(Model):

    class Meta(DefaultMeta):
        unique_together = (
            ('architecture', 'subarchitecture', 'release', 'purpose'),
            )

    objects = BootImageManager()

    architecture = CharField(max_length=255, blank=False)
    subarchitecture = CharField(max_length=255, blank=False)
    release = CharField(max_length=255, blank=False)
    purpose = CharField(max_length=255, blank=False)
