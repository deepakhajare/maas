# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the NodeGroupInterface model."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maasserver.testing import (
    disable_dhcp_management,
    enable_dhcp_management,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maastesting.celery import CeleryFixture
from testresources import FixtureResource


class TestNodeGroupInterface(TestCase):

    resources = (
        ('celery', FixtureResource(CeleryFixture())),
        )

    def test_is_dhcp_enabled_returns_True_if_fully_set_up(self):
        enable_dhcp_management()
        self.assertTrue(factory.make_node_group().is_dhcp_enabled())

    def test_is_dhcp_enabled_returns_False_if_disabled(self):
        disable_dhcp_management()
        self.assertFalse(factory.make_node_group().is_dhcp_enabled())

    def test_is_dhcp_enabled_returns_False_if_config_is_missing(self):
        enable_dhcp_management()
        required_fields = [
            'subnet_mask', 'broadcast_ip', 'ip_range_low', 'ip_range_high']
        # Map each required field's name to a nodegroupinterface that
        # has just that field set to None.
        nodegroupinterfaces = {
            field: factory.make_node_group().get_managed_interface()
            for field in required_fields}
        for field, nodegroupinterface in nodegroupinterfaces.items():
            setattr(nodegroupinterface, field, None)
            nodegroupinterface.save()
        # List any nodegroups from this mapping that have DHCP
        # management enabled.  There should not be any.
        self.assertEqual([], [
            field
            for field, nodegroupinterface in nodegroupinterfaces.items()
                if nodegroupinterface.is_dhcp_enabled()])
