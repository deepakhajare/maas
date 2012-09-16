# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maascli.api`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maascli import utils
from maastesting.testcase import TestCase


class TestDocstringParsing(TestCase):
    """Tests for docstring parsing in `maascli.utils`."""

    def test_basic(self):
        self.assertEqual(
            ("Title", "Body"),
            utils.parse_docstring("Title\n\nBody"))
        self.assertEqual(
            ("A longer title", "A longer body"),
            utils.parse_docstring(
                "A longer title\n\nA longer body"))

    def test_no_body(self):
        # parse_docstring returns an empty string when there's no body.
        self.assertEqual(
            ("Title", ""),
            utils.parse_docstring("Title\n\n"))
        self.assertEqual(
            ("Title", ""),
            utils.parse_docstring("Title"))

    def test_unwrapping(self):
        # parse_docstring dedents and unwraps the title and body paragraphs.
        self.assertEqual(
            ("Title over two lines",
             "Paragraph over two lines\n\n"
             "Another paragraph over two lines"),
            utils.parse_docstring("""
                Title over
                two lines

                Paragraph over
                two lines

                Another paragraph
                over two lines
                """))

    def test_no_unwrapping_for_indented_paragraphs(self):
        # parse_docstring dedents body paragraphs, but does not unwrap those
        # with indentation beyond the rest.
        self.assertEqual(
            ("Title over two lines",
             "Paragraph over two lines\n\n"
             "  An indented paragraph\n  which will remain wrapped\n\n"
             "Another paragraph over two lines"),
            utils.parse_docstring("""
                Title over
                two lines

                Paragraph over
                two lines

                  An indented paragraph
                  which will remain wrapped

                Another paragraph
                over two lines
                """))

    def test_gets_docstring_from_function(self):
        # parse_docstring can extract the docstring when the argument passed
        # is not a string type.
        def example():
            """Title.

            Body.
            """
        self.assertEqual(
            ("Title.", "Body."),
            utils.parse_docstring(example))

    def test_normalises_whitespace(self):
        # parse_docstring can parse CRLF/CR/LF text, but always emits LF (\n,
        # new-line) separated text.
        self.assertEqual(
            ("long title", ""),
            utils.parse_docstring("long\r\ntitle"))
        self.assertEqual(
            ("title", "body1\n\nbody2"),
            utils.parse_docstring("title\n\nbody1\r\rbody2"))
