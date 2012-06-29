# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the install_pxe_bootloader command."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maasserver.management.commands.install_pxe_bootloader import (
    install_bootloader,
    make_destination,
    )
from maastesting.testcase import TestCase


class TestInstallPXEBootloader(TestCase):

    def test_integration(self):
        self.fail("TEST THIS")

    def test_make_destination_creates_directory_if_not_present(self):
        self.fail("TEST THIS")

    def test_make_destination_returns_existing_directory(self):
        self.fail("TEST THIS")

    def test_install_bootloader_installs_new_bootloader(self):
        self.fail("TEST THIS")

    def test_install_bootloader_replaces_bootloader_if_changed(self):
        self.fail("TEST THIS")

    def test_install_bootloader_skips_if_unchanged(self):
        self.fail("TEST THIS")

    def test_install_bootloader_sweeps_aside_dot_new_if_any(self):
        self.fail("TEST THIS")
