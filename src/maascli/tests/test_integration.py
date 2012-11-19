# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Integration-test the `maascli` command."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os.path
from subprocess import (
    CalledProcessError,
    check_call,
    )

from maastesting.testcase import TestCase
from testtools.matchers import FileContains


def locate_dev_root():
    """Root of development tree that this test is in."""
    return os.path.join(
        os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)


def locate_maascli():
    return os.path.join(locate_dev_root(), 'bin', 'maascli')


class TestMAASCli(TestCase):

    output_file = '/dev/null'

    def run_command(self, *args):
        with open(self.output_file, 'ab') as output:
            check_call(
                [locate_maascli()] + list(args),
                stdout=output, stderr=output)

    def test_run_without_args_fails(self):
        self.assertRaises(CalledProcessError, self.run_command)

    def test_run_without_args_shows_help_reminder(self):
        self.output_file = self.make_file('output')
        try:
            self.run_command()
        except CalledProcessError:
            pass
        self.assertThat(
            self.output_file,
            FileContains(
                "Run %s --help for usage details." % locate_maascli()))

    def test_help_option_succeeds(self):
        self.run_command('-h')
        # The test is that we get here without error.
        pass

    def test_list_command_succeeds(self):
        self.run_command('list')
        # The test is that we get here without error.
        pass
