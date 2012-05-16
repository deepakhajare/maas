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

from provisioningserver.power,poweraction import PowerAction


class TestPowerAction(TestCase):
    """Tests for PowerAction."""

    def test_init_raises_for_unknown_action(self):
        pass

