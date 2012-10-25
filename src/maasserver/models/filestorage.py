# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Storage for uploaded files."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'FileStorage',
    ]


from django.db.models import (
    CharField,
    Manager,
    Model,
    )
from maasserver import DefaultMeta
from maasserver.models.cleansave import CleanSave
from metadataserver.fields import (
    Bin,
    BinaryField,
    )


class FileStorageManager(Manager):
    """Manager for `FileStorage` objects.

    Store files by calling `save_file`.  No two `FileStorage` objects can
    have the same filename at the same time.  Writing new data to a file
    whose name is already in use, replaces its `FileStorage` with one
    pointing to the new data.

    Underneath, however, the storage layer will keep the old version of the
    file around indefinitely.  Thus, if the overwriting transaction rolls
    back, it may leave the new file as garbage on the filesystem; but the
    original file will not be affected.  Also, any ongoing reads from the
    old file will continue without iterruption.
    """

    def save_file(self, filename, file_object):
        """Save the file to the database.

        If a file of that name already existed, it will be replaced by the
        new contents.
        """
        # This probably ought to read in chunks but large files are
        # not expected.
        content = Bin(file_object.read())
        storage, created = self.get_or_create(
            filename=filename, defaults={'content': content})
        if not created:
            storage.content = content
            storage.save()
        return storage


class FileStorage(CleanSave, Model):
    """A simple file storage keyed on file name.

    :ivar filename: A unique file name to use for the data being stored.
    :ivar content: The file's actual data.
    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    filename = CharField(max_length=255, unique=True, editable=False)
    content = BinaryField(null=False)

    objects = FileStorageManager()

    def __unicode__(self):
        return self.filename
