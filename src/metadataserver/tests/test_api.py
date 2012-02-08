# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the metadata API."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maastesting import TestCase
from metadataserver.api import (
    check_version,
    make_list_response,
    make_text_response,
    meta_data,
    metadata_index,
    UnknownMetadataVersion,
    user_data,
    version_index,
    )


class TestHelpers(TestCase):
    """Tests for the API helper functions."""

    def make_text_response_presents_text_as_text_plain(self):
        input_text = "Hello."
        response = make_text_response(input_text)
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(input_text, response.content)

    def make_list_response_presents_list_as_newline_separated_text(self):
        response = make_list_response(['aaa', 'bbb'])
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual("aaa\nbbb", response.content)

    def check_version_accepts_latest(self):
        check_version('latest')
        # The test is that we get here without exception.
        pass

    def check_version_raises_UnknownMetadataVersion_for_unknown_version(self):
        self.assertRaises(UnknownMetadataVersion, check_version, '1.0')


class TestViews(TestCase):
    """Tests for the API views."""

    def fake_request(self):
        """Fake a request."""
        # This may have to become more realistic later.  For now, it's
        # just clearer to say "self.fake_request()" than to say "None."
        return None

    def test_metadata_index_shows_latest(self):
        contents = metadata_index(self.fake_request()).content
        self.assertIn('latest', contents)

    def test_metadata_index_shows_only_known_versions(self):
        contents = metadata_index(self.fake_request()).content
        for item in contents.splitlines():
            check_version(item)
        # The test is that we get here without exception.
        pass

    def test_version_index_shows_meta_data_and_user_data(self):
        contents = version_index(self.fake_request(), 'latest').content
        items = contents.splitlines()
        self.assertIn('meta-data', items)
        self.assertIn('user-data', items)

    def test_meta_data_view_returns_text_response(self):
        self.assertEqual(
            'text/plain',
            meta_data(self.fake_request(), 'latest')['Content-Type'])

    def test_user_data_view_returns_text_response(self):
        self.assertEqual(
            'text/plain',
            user_data(self.fake_request(), 'latest')['Content-Type'])
