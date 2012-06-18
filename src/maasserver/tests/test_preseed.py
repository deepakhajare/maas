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

import base64
import os

from django.conf import settings
from maasserver.preseed import (
    GENERIC_FILENAME,
    get_preseed_filenames,
    get_preseed_template,
    load_preseed_template,
    PreseedTemplate,
    split_subarch,
    TemplateNotFoundError,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from testtools.matchers import (
    AllMatch,
    IsInstance,
    )


class TestSplitSubArch(TestCase):
    """Tests for `split_subarch`."""

    def test_split_subarch_returns_list(self):
        self.assertEqual(['amd64'], split_subarch('amd64'))

    def test_split_subarch_splits_sub_architecture(self):
        self.assertEqual(['amd64', 'test'], split_subarch('amd64/test'))


class TestGetPreseedFilenames(TestCase):
    """Tests for `get_preseed_filenames`."""

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
            list(get_preseed_filenames(node, type, release, True)))

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
            list(get_preseed_filenames(node, type, release, True)))

    def test_get_preseed_filenames_returns_list_without_default(self):
        # If default=False is passed to get_preseed_filenames, the
        # returned list won't include the default template name as a
        # last resort template.
        hostname = factory.getRandomString()
        prefix = factory.getRandomString()
        release = factory.getRandomString()
        node = factory.make_node(hostname=hostname)
        self.assertSequenceEqual(
            'generic',
            list(get_preseed_filenames(node, prefix, release, True))[-1])

    def test_get_preseed_filenames_returns_list_with_default(self):
        # If default=True is passed to get_preseed_filenames, the
        # returned list will include the default template name as a
        # last resort template.
        hostname = factory.getRandomString()
        prefix = factory.getRandomString()
        release = factory.getRandomString()
        node = factory.make_node(hostname=hostname)
        self.assertSequenceEqual(
            prefix,
            list(get_preseed_filenames(node, prefix, release, False))[-1])


class TestConfiguration(TestCase):
    """Test for correct configuration of the preseed component."""

    def test_setting_defined(self):
        self.assertThat(
            settings.PRESEED_TEMPLATE_LOCATIONS,
            AllMatch(IsInstance(basestring)))


class TestPreseedTemplate(TestCase):
    """Tests for :class:`PreseedTemplate`."""

    def test_preseed_template_b64decode(self):
        content = factory.getRandomString()
        encoded_content = base64.b64encode(content)
        template = PreseedTemplate("{{b64decode('%s')}}" % encoded_content)
        self.assertEqual(content, template.substitute())

    def test_preseed_template_b64encode(self):
        content = factory.getRandomString()
        template = PreseedTemplate("{{b64encode('%s')}}" % content)
        self.assertEqual(base64.b64encode(content), template.substitute())


class TestGetPreseedTemplate(TestCase):
    """Tests for `get_preseed_template`."""

    def test_get_preseed_template_returns_None_if_no_template_locations(self):
        # get_preseed_template() returns None when no template locations are
        # defined.
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [])
        self.assertEqual(
            (None, None),
            get_preseed_template(
                (factory.getRandomString(), factory.getRandomString())))

    def test_get_preseed_template_returns_None_when_no_filenames(self):
        # get_preseed_template() returns None when no filenames are passed in.
        location = self.make_dir()
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [location])
        self.assertEqual((None, None), get_preseed_template(()))

    def test_get_preseed_template_find_template_in_first_location(self):
        template_content = factory.getRandomString()
        template_path = self.make_file(contents=template_content)
        template_filename = os.path.basename(template_path)
        locations = [
            os.path.dirname(template_path),
            self.make_dir(),
            ]
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", locations)
        self.assertEqual(
            (template_path, template_content),
            get_preseed_template([template_filename]))

    def test_get_preseed_template_find_template_in_last_location(self):
        template_content = factory.getRandomString()
        template_path = self.make_file(contents=template_content)
        template_filename = os.path.basename(template_path)
        locations = [
            self.make_dir(),
            os.path.dirname(template_path),
            ]
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", locations)
        self.assertEqual(
            (template_path, template_content),
            get_preseed_template([template_filename]))


class TestLoadPreseedTemplate(TestCase):
    """Tests for `load_preseed_template`."""

    def create_template(self, location, name, content=None):
        # Create a tempita template in the given `location` with the
        # given `name`.  If content is not provided, a random content
        # will be put inside the template.
        path = os.path.join(location, name)
        rendered_content = None
        if content is None:
            rendered_content = factory.getRandomString()
            content = b'{{def stuff}}%s{{enddef}}{{stuff}}' % rendered_content
        with open(path, "wb") as outf:
            outf.write(content)
        return rendered_content

    def test_load_preseed_template_returns_PreseedTemplate(self):
        location = self.make_dir()
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [location])
        name = factory.getRandomString()
        self.create_template(location, name)
        node = factory.make_node()
        template = load_preseed_template(node, name)
        self.assertIsInstance(template, PreseedTemplate)

    def test_load_preseed_template_raises_if_no_template(self):
        location = self.make_dir()
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [location])
        node = factory.make_node()
        unknown_template_name = factory.getRandomString()
        self.assertRaises(
            TemplateNotFoundError, load_preseed_template, node,
            unknown_template_name)

    def test_load_preseed_template_generic_lookup(self):
        # The template lookup method ends up picking up a template named
        # 'generic' if no more specific template exist.
        location = self.make_dir()
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [location])
        content = self.create_template(location, GENERIC_FILENAME)
        node = factory.make_node(hostname=factory.getRandomString())
        template = load_preseed_template(node, factory.getRandomString())
        self.assertEqual(content, template.substitute())

    def test_load_preseed_template_prefix_lookup(self):
        # 2nd last in the hierarchy is a template named 'prefix'.
        location = self.make_dir()
        prefix = factory.getRandomString()
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [location])
        # Create the generic template.  This one will be ignored due to the
        # presence of a more specific template.
        self.create_template(location, GENERIC_FILENAME)
        # Create the 'prefix' template.  This is the one which will be
        # picked up.
        content = self.create_template(location, prefix)
        node = factory.make_node(hostname=factory.getRandomString())
        template = load_preseed_template(node, prefix)
        self.assertEqual(content, template.substitute())

    def test_load_preseed_template_node_specific_lookup(self):
        # At the top of the lookup hierarchy is a template specific to this
        # node.  It will be used first if it's present.
        location = self.make_dir()
        prefix = factory.getRandomString()
        release = factory.getRandomString()
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [location])
        # Create the generic and 'prefix' templates.  They will be ignored
        # due to the presence of a more specific template.
        self.create_template(location, GENERIC_FILENAME)
        self.create_template(location, prefix)
        node = factory.make_node(hostname=factory.getRandomString())
        node_template_name = "%s_%s_%s_%s" % (
            prefix, node.architecture, release, node.hostname)
        # Create the node-specific template.
        content = self.create_template(location, node_template_name)
        template = load_preseed_template(node, prefix, release)
        self.assertEqual(content, template.substitute())

    def test_load_preseed_template_with_inherits(self):
        # A preseed file can "inherit" from another file.
        location = self.make_dir()
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [location])
        prefix = factory.getRandomString()
        # Create preseed template.
        master_template_name = factory.getRandomString()
        preseed_content = '{{inherit "%s"}}' % master_template_name
        self.create_template(location, prefix, preseed_content)
        master_content = self.create_template(location, master_template_name)
        node = factory.make_node()
        template = load_preseed_template(node, prefix)
        self.assertEqual(master_content, template.substitute())

    def test_load_preseed_template_parent_lookup_doesnt_include_default(self):
        # The lookup for parent templates does not include the default
        # 'generic' file.
        location = self.make_dir()
        self.patch(settings, "PRESEED_TEMPLATE_LOCATIONS", [location])
        prefix = factory.getRandomString()
        # Create 'generic' template.  It won't be used because the
        # lookup for parent templates does not use the 'generic' template.
        self.create_template(location, GENERIC_FILENAME)
        unknown_master_template_name = factory.getRandomString()
        # Create preseed template.
        preseed_content = '{{inherit "%s"}}' % unknown_master_template_name
        self.create_template(location, prefix, preseed_content)
        node = factory.make_node()
        template = load_preseed_template(node, prefix)
        self.assertRaises(
            TemplateNotFoundError, template.substitute)
