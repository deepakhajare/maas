# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test custom commissioning scripts."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from io import BytesIO
import os.path
from random import randint
import tarfile

from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maastesting.utils import sample_binary_data
from metadataserver.fields import Bin
from metadataserver.models import CommissioningScript
from metadataserver.models.commissioningscript import ARCHIVE_PREFIX


def open_tarfile(content):
    """Open tar file from raw binary data."""
    return tarfile.open(fileobj=BytesIO(content))


def make_script_name(base_name=None, number=None):
    """Make up a name for a commissioning script."""
    if base_name is None:
        base_name = 'script'
    if number is None:
        number = randint(0, 99)
    return factory.make_name(
        '%0.2d-%s' % (number, factory.make_name(base_name)))


class TestCommissioningScriptManager(TestCase):

    def test_get_archive_wraps_scripts_in_tar(self):
        script = factory.make_commissioning_script()
        archive = open_tarfile(CommissioningScript.objects.get_archive())
        archived_script = archive.next()
        self.assertTrue(archived_script.isfile())
        self.assertEqual(
            os.path.join(ARCHIVE_PREFIX, script.name),
            archived_script.name)
        self.assertEqual(
            script.content,
            archive.extractfile(archived_script).read())

    def test_get_archive_wraps_all_scripts(self):
        scripts = {factory.make_commissioning_script() for counter in range(3)}
        archive = open_tarfile(CommissioningScript.objects.get_archive())
        self.assertItemsEqual(
            {os.path.join(ARCHIVE_PREFIX, script.name) for script in scripts},
            archive.getnames())

    def test_get_archive_supports_binary_scripts(self):
        script = factory.make_commissioning_script(content=sample_binary_data)
        archive = open_tarfile(CommissioningScript.objects.get_archive())
        archived_script = archive.next()
        self.assertEqual(
            script.content,
            archive.extractfile(archived_script).read())

    def test_get_archive_returns_empty_tarball_if_no_scripts(self):
        CommissioningScript.objects.all().delete()
        archive = open_tarfile(CommissioningScript.objects.get_archive())
        self.assertItemsEqual([], archive.getnames())


class TestCommissioningScript(TestCase):

    def test_scripts_may_be_binary(self):
        name = make_script_name()
        CommissioningScript.objects.create(
            name=name, content=Bin(sample_binary_data))
        stored_script = CommissioningScript.objects.get(name=name)
        self.assertEqual(sample_binary_data, stored_script.content)
