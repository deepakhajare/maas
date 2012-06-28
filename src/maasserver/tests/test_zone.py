# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `Zone` class."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


import random

from maasserver.models.zone import (
    MAX_SERIAL,
    Zone,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase


class ZoneTest(TestCase):
    """Testing of the :class:`Zone` model."""

    def test_serial_defaults_to_zero(self):
        node_group = factory.make_node_group()
        zone = Zone(node_group=node_group)
        self.assertEqual(
            (0, '0' * len(str(MAX_SERIAL))),
            (zone.serial_number, zone.serial))

    def test_increment_serial_number(self):
        node_group = factory.make_node_group()
        zone = Zone(node_group=node_group)
        zone.increment_serial_number()
        self.assertEqual(zone.serial_number, 1)

    def test_serial_number_wraps_at_MAX_SERIAL(self):
        node_group = factory.make_node_group()
        zone = Zone(node_group=node_group)
        zone.serial_number = MAX_SERIAL
        zone.increment_serial_number()
        self.assertEqual(zone.serial_number, 0)

    def test_serial_display(self):
        node_group = factory.make_node_group()
        zone = Zone(node_group=node_group)
        zone.serial_number = random.randint(0, MAX_SERIAL)
        self.assertEqual(len(str(MAX_SERIAL)), len(zone.serial))
