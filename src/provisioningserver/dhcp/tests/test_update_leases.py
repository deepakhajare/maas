# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the report_leases task."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from datetime import (
    datetime,
    timedelta,
    )

from maastesting.factory import factory
from maastesting.fakemethod import FakeMethod
from maastesting.testcase import TestCase
from maastesting.utils import (
    age_file,
    get_write_time,
    )
from provisioningserver import update_leases


class TestUpdateLeases(TestCase):

    def fake_leases_file(self, leases=None, age=None):
        """Create a fake leases file.

        :param leases: Dict of leases (mapping IP addresses to MACs).
        :param age: Number of seconds since last modification to leases file.
        :return: Path/name of temporary file.
        """
        if leases is None:
            leases = {}
        lease_file = self.make_file()
        if age is not None:
            age_file(lease_file, age)
        self.patch(update_leases, 'LEASES_FILE', lease_file)
        # TODO: We don't have a lease-file parser yet.  For now, just
        # fake up a "parser" that returns the given data.
        self.patch(update_leases, 'parse_leases', lambda: leases)
        return lease_file

    def test_check_lease_changes_returns_True_if_no_state_cached(self):
        update_leases.record_lease_state()
        self.fake_leases_file()
        self.assertTrue(update_leases.check_lease_changes())

    def test_check_lease_changes_returns_True_if_lease_changed(self):
        ip = factory.getRandomIPAddress()
        update_leases.record_lease_state(
            datetime.utcnow() - timedelta(seconds=10),
            {ip: factory.getRandomMACAddress()})
        self.fake_leases_file({ip: factory.getRandomMACAddress()})
        self.assertTrue(update_leases.check_lease_changes())

    def test_check_lease_changes_does_not_parse_unchanged_leases_file(self):
        parser = FakeMethod()
        self.patch(update_leases, 'parse_leases', parser)
        leases_file = self.fake_leases_file()
        update_leases.record_lease_state(get_write_time(leases_file), {})
        update_leases.update_leases()
        self.assertSequenceEqual([], parser.calls)

    def test_check_lease_changes_returns_True_if_lease_added(self):
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        update_leases.record_lease_state(
            datetime.utcnow() - timedelta(seconds=10), leases)
        leases[factory.getRandomIPAddress()] = factory.getRandomMACAddress()
        self.fake_leases_file(leases)
        self.assertTrue(update_leases.check_lease_changes())

    def test_check_lease_changes_returns_True_if_leases_dropped(self):
        update_leases.record_lease_state(
            datetime.utcnow() - timedelta(seconds=10),
            {factory.getRandomIPAddress(): factory.getRandomMACAddress()})
        self.fake_leases_file()
        self.assertTrue(update_leases.check_lease_changes())

    def test_check_lease_changes_returns_False_if_no_change(self):
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        leases_file = self.fake_leases_file(leases)
        update_leases.record_lease_state(get_write_time(leases_file), leases)
        self.assertFalse(update_leases.check_lease_changes())

    def test_check_lease_changes_ignores_irrelevant_changes(self):
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        self.fake_leases_file(leases, age=10)
        update_leases.record_lease_state(datetime.utcnow(), leases)
        self.assertFalse(update_leases.check_lease_changes())

    def test_update_leases_sends_leases_if_changed(self):
        send_leases = FakeMethod()
        self.patch(update_leases, 'send_leases', send_leases)
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        update_leases.record_lease_state(leases)
        update_leases.update_leases()
        self.assertSequenceEqual([leases], send_leases.extract_args())

    def test_update_leases_does_nothing_without_lease_changes(self):
        send_leases = FakeMethod()
        self.patch(update_leases, 'send_leases', send_leases)
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        leases_file = self.fake_leases_file(leases)
        update_leases.record_lease_state(get_write_time(leases_file), leases)
        self.assertSequenceEqual([], send_leases.calls)
