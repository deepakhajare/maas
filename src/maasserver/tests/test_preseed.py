# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `maasserver.preseed` and related bits and bobs."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import collections
from os import path

from django.conf import settings
from maasserver.preseed import (
    get_preseed_filenames,
    get_preseed_template,
    split_subarch,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase


class TestPreseedFilenameUtilities(TestCase):

    def test_split_subarch_returns_list(self):
        self.assertEqual(['amd64'], split_subarch('amd64'))

    def test_split_subarch_splits_sub_architecture(self):
        self.assertEqual(['amd64', 'test'], split_subarch('amd64/test'))

    def test_get_preseed_filenames_returns_filenames(self):
        hostname = factory.getRandomString()
        type = factory.getRandomString()
        release = factory.getRandomString()
        node = factory.make_node(hostname=hostname)
        self.assertSequenceEqual(
            [
                '%s_%s_%s_%s' % (type, node.architecture, release, hostname),
                '%s_%s_%s' % (type, node.architecture, release),
                '%s_%s' % (type, node.architecture),
                '%s' % type,
                'generic',
            ],
            list(get_preseed_filenames(node, type, release)))

    def test_get_preseed_filenames_returns_filenames_with_subarch(self):
        arch = factory.getRandomString()
        subarch = factory.getRandomString()
        fake_arch = '%s/%s' % (arch, subarch)
        hostname = factory.getRandomString()
        type = factory.getRandomString()
        release = factory.getRandomString()
        node = factory.make_node(hostname=hostname)
        # Set an architecture of the form '%s/%s' i.e. with a
        # sub-architecture.
        node.architecture = fake_arch
        self.assertSequenceEqual(
            [
                '%s_%s_%s_%s_%s' % (type, arch, subarch, release, hostname),
                '%s_%s_%s_%s' % (type, arch, subarch, release),
                '%s_%s_%s' % (type, arch, subarch),
                '%s_%s' % (type, arch),
                '%s' % type,
                'generic',
            ],
            list(get_preseed_filenames(node, type, release)))


class TestConfiguration(TestCase):
    """Test for correct configuration of the preseed component."""

    def test_setting_defined(self):
        self.assertIsInstance(
            settings.PRESEED_TEMPLATE_LOCATIONS,
            collections.Sequence)


class TestGetPreseedTemplate(TestCase):
    """Tests for `get_preseed_template`."""

    def test_returns_None_when_no_template_locations(self):
        # get_preseed_template() returns None when no template locations are
        # defined.
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [])
        self.assertIsNone(get_preseed_template(("fred", "bob")))

    def test_returns_None_when_no_filenames(self):
        # get_preseed_template() returns None when no filenames are passed in.
        location = self.make_dir()
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [location])
        self.assertIsNone(get_preseed_template(()))

    def test_find_template_in_first_location(self):
        template_content = factory.getRandomString()
        template_path = self.make_file(contents=template_content)
        template_filename = path.basename(template_path)
        locations = [
            path.dirname(template_path),
            self.make_dir(),
            ]
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", locations)
        self.assertEqual(
            (template_path, template_content),  # TODO: expect a template.
            get_preseed_template([template_filename]))

    def test_find_template_in_last_location(self):
        template_content = factory.getRandomString()
        template_path = self.make_file(contents=template_content)
        template_filename = path.basename(template_path)
        locations = [
            self.make_dir(),
            path.dirname(template_path),
            ]
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", locations)
        self.assertEqual(
            (template_path, template_content),  # TODO: expect a template.
            get_preseed_template([template_filename]))
