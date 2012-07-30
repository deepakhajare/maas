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
import provisioningserver.pxe.config
from provisioningserver.pxe.config import (
    render_pxe_config,
    PXEConfigFail,
    )
from testtools.matchers import (
    Contains,
    MatchesRegex,
    StartsWith,
    )


class TestRenderPXEConfig(TestCase):
    """Tests for `provisioningserver.pxe.config.render_pxe_config`."""

    def test_render(self):
        # Given the right configuration options, the PXE configuration is
        # correctly rendered.
        options = {
            "menu_title": factory.make_name("menu_title"),
            "kernel": factory.make_name("kernel"),
            "initrd": factory.make_name("initrd"),
            "append": factory.make_name("append"),
            }
        output = render_pxe_config(**options)
        # The template has rendered without error. PXELINUX configurations
        # typically start with a DEFAULT line.
        self.assertThat(output, StartsWith("DEFAULT "))
        for value in options.values():
            self.assertThat(output, Contains(value))

    def test_missing_config_parameter(self):
        # If not enough arguments are supplied to fill in template
        # variables then a PXEConfigFail is raised.
        exception = self.assertRaises(PXEConfigFail, render_pxe_config)
        self.assertThat(
            exception.message, MatchesRegex(
                "name 'menu_title' is not defined at line \d+ column \d+ "
                "in file %s" % re.escape(
                    provisioningserver.pxe.config.template_filename)))
