# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.api`.

Also tests `provisioningserver.testing.fakeapi`.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from testtools import TestCase

from provisioningserver.enum import POWER_TYPE
from provisioningserver.power.poweraction import (
    PowerAction,
    UnknownPowerType,
    )


class TestPowerAction(TestCase):
    """Tests for PowerAction."""

    def test_init_raises_for_unknown_powertype(self):
        powertype = "schnitzel"
        self.assertRaises(
            UnknownPowerType,
            PowerAction, powertype)

    def test_init_works_for_ether_wake(self):
        pa = PowerAction(POWER_TYPE.WAKE_ON_LAN)
        self.assertEqual(POWER_TYPE.WAKE_ON_LAN, pa.power_type)
