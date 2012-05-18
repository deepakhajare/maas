# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.power`.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from fixtures import TempDir
import os
from testtools import TestCase
from textwrap import dedent

from django.conf import settings
from provisioningserver.enum import POWER_TYPE
from provisioningserver.power.poweraction import (
    PowerAction,
    UnknownPowerType,
    )


class TestPowerAction(TestCase):
    """Tests for PowerAction."""

    def test_init_raises_for_unknown_powertype(self):
        # If constructed with a power type that doesn't map to a
        # template file, UnknownPowerType should be raised.
        powertype = "weinerschnitzel"
        self.assertRaises(
            UnknownPowerType,
            PowerAction, powertype)

    def test_init_stores_ether_wake_type(self):
        # Using a power type that has a template file results in the
        # power type stored on the object.
        pa = PowerAction(POWER_TYPE.WAKE_ON_LAN)
        self.assertEqual(POWER_TYPE.WAKE_ON_LAN, pa.power_type)

    def test_init_stores_template_path(self):
        # Using a power type that has a template file results in the
        # path to the template file being stored on the object.
        power_type = POWER_TYPE.WAKE_ON_LAN
        basedir = settings.POWER_TEMPLATES_DIR
        path = os.path.join(basedir, power_type + ".template")
        pa = PowerAction(power_type)
        self.assertEqual(path, pa.path)

    def test_get_template(self):
        # get_template() should find and read the template file.
        pa = PowerAction(POWER_TYPE.WAKE_ON_LAN)
        with open(pa.path, "r") as f:
            template = f.read()
        self.assertEqual(template, pa.get_template())

    def test_render_template(self):
        # render_template() should take a template string and substitue
        # its variables.
        pa = PowerAction(POWER_TYPE.WAKE_ON_LAN)
        template = "template: %(mac)s"
        rendered = pa.render_template(template, mac="mymac")
        self.assertEqual(
            template % dict(mac="mymac"), rendered)

    def test_execute(self):
        # execute() should run the template through a shell.

        # Create a template in a temp dir.
        tempdir = self.useFixture(TempDir()).path
        output_file = os.path.join(tempdir, "output")
        template = dedent("""\
            echo working %(mac)s >""")
        template += output_file
        path = os.path.join(tempdir, "testscript.sh")
        with open(path, "w") as f:
            f.write(template)

        # Execute it.
        pa = PowerAction(POWER_TYPE.WAKE_ON_LAN)
        pa.path = path
        pa.execute(mac="test")

        # Check that it got executed by comparing the file it was
        # supposed to write out.
        with open(output_file, "r") as f:
            output = f.read()

        self.assertEqual("working test\n", output)
