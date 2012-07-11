# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the set_up_dns command."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from codecs import getwriter
from io import BytesIO

from django.core.management import call_command
from maasserver.testing.testcase import TestCase
from testtools.matchers import (
    Contains,
    FileContains,
    )


class TestGenerateEnlistmentPXE(TestCase):

    def test_set_up_dns_returns_snippet(self):
        out = BytesIO()
        stdout = getwriter("UTF-8")(out)
        call_command('set_up_dns', stdout=stdout)
        result = stdout.getvalue()
        # Just check that the returned snippet looks all right.
        self.assertIn('include "', result)

    def test_set_up_dns_appends_to_config_file(self):
        file_path = self.make_file()
        call_command(
            'set_up_dns', edit=True, config_path=file_path)
        self.assertThat(
            file_path,
            FileContains(
                matcher=Contains('include "')))
