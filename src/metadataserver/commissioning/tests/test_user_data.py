# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test generation of commissioning user data."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os.path

from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maastesting.matchers import ContainsAll
from metadataserver.commissioning.user_data import (
    generate_user_data,
    is_snippet,
    list_snippets,
    read_snippet,
    strip_name,
    )


class TestUserData(TestCase):

    def test_read_snippet_reads_snippet_file(self):
        contents = factory.getRandomString()
        snippet = self.make_file(contents=contents)
        self.assertEqual(
            contents,
            read_snippet(os.path.dirname(snippet), os.path.basename(snippet)))

    def test_strip_name_leaves_simple_names_intact(self):
        simple_name = factory.getRandomString()
        self.assertEqual(simple_name, strip_name(simple_name))

    def test_strip_name_replaces_dots(self):
        self.assertEqual('_x_y_', strip_name('.x.y.'))

    def test_is_snippet(self):
        are_snippets = {
            'snippet': True,
            'with-dash': True,
            'module.py': True,
            '.backup': False,
            'backup~': False,
            'module.pyc': False,
            '__init__.pyc': False,
        }
        self.assertEqual(
            are_snippets,
            {name: is_snippet(name) for name in are_snippets})

    def test_list_snippets(self):
        snippets_dir = self.make_dir()
        factory.make_file(snippets_dir, 'snippet')
        factory.make_file(snippets_dir, '.backup.pyc')
        self.assertItemsEqual(['snippet'], list_snippets(snippets_dir))

    def test_generate_user_data_produces_commissioning_script(self):
        # generate_user_data produces a commissioning script which contains
        # both definitions and use of various commands in python.
        self.assertThat(
            generate_user_data(), ContainsAll({
                'maas-get',
                'maas-signal',
                'def authenticate_headers',
                'def encode_multipart_data',
            }))
