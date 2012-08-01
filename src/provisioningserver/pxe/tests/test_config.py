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
from provisioningserver.pxe.config import render_pxe_config
from provisioningserver.pxe.tftppath import compose_image_path
from testtools.matchers import (
    IsInstance,
    MatchesAll,
    MatchesRegex,
    StartsWith,
    )


class TestRenderPXEConfig(TestCase):
    """Tests for `provisioningserver.pxe.config.render_pxe_config`."""

    def test_render(self):
        # Given the right configuration options, the PXE configuration is
        # correctly rendered.
        options = {
            "title": factory.make_name("title"),
            "arch": factory.make_name("arch"),
            "subarch": factory.make_name("subarch"),
            "release": factory.make_name("release"),
            "purpose": factory.make_name("purpose"),
            "append": factory.make_name("append"),
            }
        output = render_pxe_config(**options)
        # The output is always a Unicode string.
        self.assertThat(output, IsInstance(unicode))
        # The template has rendered without error. PXELINUX configurations
        # typically start with a DEFAULT line.
        self.assertThat(output, StartsWith("DEFAULT "))
        # The PXE parameters are all set according to the options.
        image_dir = compose_image_path(
            arch=options["arch"], subarch=options["subarch"],
            release=options["release"], purpose=options["purpose"])
        self.assertThat(
            output, MatchesAll(
                MatchesRegex(
                    r'.*^MENU TITLE %s$' % re.escape(options["title"]),
                    re.MULTILINE | re.DOTALL),
                MatchesRegex(
                    r'.*^\s+KERNEL %s/kernel$' % re.escape(image_dir),
                    re.MULTILINE | re.DOTALL),
                MatchesRegex(
                    r'.*^\s+INITRD %s/initrd[.]gz$' % re.escape(image_dir),
                    re.MULTILINE | re.DOTALL),
                MatchesRegex(
                    r'.*^\s+APPEND %s$' % re.escape(options["append"]),
                    re.MULTILINE | re.DOTALL)))

    def test_render_with_extra_arguments(self):
        # render_pxe_config() allows any keyword arguments as a safety valve.
        options = {
            "title": factory.make_name("title"),
            "arch": factory.make_name("arch"),
            "subarch": factory.make_name("subarch"),
            "release": factory.make_name("release"),
            "purpose": factory.make_name("purpose"),
            "append": factory.make_name("append"),
            }
        # Capture the output before sprinking in some random options.
        output_before = render_pxe_config(**options)
        # Sprinkle some magic in.
        options.update(
            (factory.make_name("name"), factory.make_name("value"))
            for _ in range(10))
        # Capture the output after sprinking in some random options.
        output_after = render_pxe_config(**options)
        # The generated template is the same.
        self.assertEqual(output_before, output_after)
