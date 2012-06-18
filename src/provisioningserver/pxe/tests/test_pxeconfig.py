# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.pxe`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os
import re

from celeryconfig import (
    PXE_TARGET_DIR,
    PXE_TEMPLATES_DIR,
    )
from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.pxe.pxeconfig import PXEConfig


class TestPXEConfig(TestCase):
    """Tests for PXEConfig."""

    def test_init_sets_up_paths(self):
        pxeconfig = PXEConfig("armhf", "armadaxp")

        expected_template = os.path.join(PXE_TEMPLATES_DIR, "maas.template")
        expected_target = os.path.join(PXE_TARGET_DIR, "armhf", "armadaxp")
        self.assertEqual(expected_template, pxeconfig.template)
        self.assertEqual(expected_target, pxeconfig.target_dir)
