# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the generate-enlistment-pxe command."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django.core.management import call_command
from maasserver.enum import ARCHITECTURE_CHOICES
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase


class TestGenerateEnlistmentPXE(TestCase):

    def test_generates_default_pxe_config(self):
        arch = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        output = call_command('generate_enlistment_pxe', arch=arch)
        self.assertIn('/'.join([arch, 'generic']), output)
