# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Celery tasks."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from testresources import FixtureResource

from maastesting.celery import CeleryFixture
from maastesting.testcase import TestCase
from provisioningserver.tasks import power_on_ether_wake


class TestPowerTasks(TestCase):

    resources = (
        ("celery", FixtureResource(CeleryFixture())),
        )

    def test_ether_wake_power_on_with_not_enough_template_args(self):
        power_on_ether_wake.delay()
        # TODO: assert something

    def test_ether_wake_power_on(self):
        mac = "AA:BB:CC:DD:EE:FF"
        power_on_ether_wake.delay(mac=mac)
        # TODO: assert something
