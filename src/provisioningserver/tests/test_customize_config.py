# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for customize_config."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from argparse import (
    ArgumentError,
    ArgumentParser,
    )
from io import BytesIO
import sys
from textwrap import dedent

from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver import customize_config
from provisioningserver.utils import maas_custom_config_markers


class TestCustomizeConfig(TestCase):

    def run_command(self, *args):
        parser = ArgumentParser()
        customize_config.add_arguments(parser)
        parsed_args = parser.parse_args(args)
        customize_config.run(parsed_args)

    def test_integration(self):
        header, footer = maas_custom_config_markers
        original_file = self.make_file("Original text here.")
        self.patch(
            sys, 'stdin', BytesIO("Custom section here.".encode('utf-8')))
        self.patch(sys, 'stdout', BytesIO())

        self.run_command('--file', original_file)

        sys.stdout.seek(0)
        expected = dedent("""\
            "Original text here.
            %s
            Custom section here.
            %s
            """) % (header, footer)
        self.assertEqual(expected, sys.stdout.read().decode('utf-8'))

    def test_requires_file_argument(self):
        self.assertRaises(ArgumentError, self.run_command)

    def test_does_not_modify_original(self):
        original_text = factory.getRandomString().encode('ascii')
        original_file = self.make_file(contents=original_text)

        self.run_command('--file', original_file)

        with open(original_file, 'rb') as reread_file:
            contents_after = reread_file.read()

        self.assertEqual(original_text, contents_after)
