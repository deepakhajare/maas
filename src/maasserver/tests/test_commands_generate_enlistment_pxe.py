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

import os.path

from django.core.management import call_command
from maasserver.enum import ARCHITECTURE_CHOICES
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from testtools.matchers import FileContains


class TestGenerateEnlistmentPXE(TestCase):

    def test_generates_default_pxe_config(self):
        arch = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        tftpdir = self.make_dir()
        call_command(
            'generate_enlistment_pxe', arch=arch, release='precise',
            tftpdir=tftpdir)
        # This produces a "default" PXE config file in the right place.
        # It refers to the kernel and initrd for the requested
        # architecture and release.
        self.assertThat(
            os.path.join(tftpdir, arch, 'pxelinux.cfg', 'default'),
            FileContains('/'.join([arch, 'generic', 'precise'])))
