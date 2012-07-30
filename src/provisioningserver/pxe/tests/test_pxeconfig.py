# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.pxe.config`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import re

from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.pxe import pxeconfig
from testtools.matchers import (
    MatchesRegex,
    StartsWith,
    )


class TestRenderPXEConfig(TestCase):
    """Tests for `provisioningserver.pxe.config.render_pxe_config`."""

    def test_template(self):
        # Given the right configuration options, the PXE configuration is
        # correctly rendered.
        options = {
            "menu_title": factory.make_name("menu_title"),
            "kernel": factory.make_name("kernel"),
            "initrd": factory.make_name("initrd"),
            "append": factory.make_name("append"),
            }
        config = pxeconfig.template.substitute(options)
        # The template has rendered without error. PXELINUX configurations
        # typically start with a DEFAULT line.
        self.assertThat(config, StartsWith("DEFAULT "))

    def test_missing_config_parameter(self):
        # If not enough arguments are supplied to fill in template
        # variables then a PXEConfigFail is raised.
        exception = self.assertRaises(
            pxeconfig.PXEConfigFail, pxeconfig.render_pxe_config, "i386")
        self.assertThat(
            exception.message, MatchesRegex(
                "name 'menu_title' is not defined at line \d+ column \d+ "
                "in file %s" % re.escape(pxeconfig.template_filename)))
