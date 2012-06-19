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
import tempita

from celeryconfig import (
    PXE_TARGET_DIR,
    PXE_TEMPLATES_DIR,
    )
from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.pxe.pxeconfig import (
    PXEConfig,
    PXEConfigFail,
    )
from testtools.matchers import (
    MatchesRegex,
    )


class TestPXEConfig(TestCase):
    """Tests for PXEConfig."""

    def test_init_sets_up_paths(self):
        pxeconfig = PXEConfig("armhf", "armadaxp")

        expected_template = os.path.join(PXE_TEMPLATES_DIR, "maas.template")
        expected_target = os.path.join(PXE_TARGET_DIR, "armhf", "armadaxp")
        self.assertEqual(expected_template, pxeconfig.template)
        self.assertEqual(expected_target, pxeconfig.target_dir)

    def test_init_with_no_subarch_makes_path_with_generic(self):
        pxeconfig = PXEConfig("i386")
        expected_target = os.path.join(PXE_TARGET_DIR, "i386", "generic")
        self.assertEqual(expected_target, pxeconfig.target_dir)

    def test_get_template(self):
        pxeconfig = PXEConfig("i386")
        template = pxeconfig.get_template()
        with open(pxeconfig.template, "rb") as f:
            expected = f.read()
        self.assertIsInstance(template, tempita.Template)
        self.assertEqual(expected, template.content)

    def test_render_template(self):
        pxeconfig = PXEConfig("i386")
        template = tempita.Template("template: {{kernelimage}}")
        rendered = pxeconfig.render_template(template, kernelimage="myimage")
        self.assertEqual("template: myimage", rendered)

    def test_render_template_raises_PXEConfigFail(self):
        # If not enough arguments are supplied to fill in template
        # variables then a PXEConfigFail is raised.
        pxeconfig = PXEConfig("i386")
        template_name = factory.getRandomString()
        template = tempita.Template(
            "template: {{kernelimage}}", name=template_name)
        exception = self.assertRaises(
            PXEConfigFail, pxeconfig.render_template, template)
        self.assertThat(
            exception.message, MatchesRegex(
                "name 'kernelimage' is not defined at line \d+ column \d+ "
                "in file %s" % re.escape(template_name)))
