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
from provisioningserver.dhcp import update_leases


class StopExecuting(BaseException):
    """Exception class to stop execution at a desired point.

    This is deliberately not just an :class:`Exception`.  We want to
    interrupt the code that's being tested, not just exercise its
    error-handling capabilities.
    """


class TestUpdateLeases(TestCase):

    def fake_leases_file(self, leases=None, age=None):
        """Create a fake leases file.

        :param leases: Dict of leases (mapping IP addresses to MACs).
        :param age: Number of seconds since last modification to leases file.
        :return: Path/name of temporary file.
        """
        if leases is None:
            leases = {}
        leases = leases.copy()
        leases_file = self.make_file()
        if age is not None:
            age_file(leases_file, age)
        timestamp = get_write_time(leases_file)
        self.patch(update_leases, 'DHCP_LEASES_FILE', leases_file)
        # TODO: We don't have a lease-file parser yet.  For now, just
        # fake up a "parser" that returns the given data.
        self.patch(
            update_leases, 'parse_leases', lambda: (timestamp, leases))
        return leases_file

    def test_check_lease_changes_returns_True_if_no_state_cached(self):
        update_leases.record_lease_state(None, None)
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
        leases_file = self.fake_leases_file()
        self.patch(update_leases, 'parse_leases', parser)
        update_leases.record_lease_state(get_write_time(leases_file), {})
        update_leases.update_leases()
        self.assertSequenceEqual([], parser.calls)

    def test_check_lease_changes_returns_True_if_lease_added(self):
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        update_leases.record_lease_state(
            datetime.utcnow() - timedelta(seconds=10), leases.copy())
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
        update_leases.record_lease_state(None, None)
        send_leases = FakeMethod()
        self.patch(update_leases, 'send_leases', send_leases)
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        self.fake_leases_file(leases)
        update_leases.update_leases()
        self.assertSequenceEqual([(leases, )], send_leases.extract_args())

    def test_update_leases_does_nothing_without_lease_changes(self):
        send_leases = FakeMethod()
        self.patch(update_leases, 'send_leases', send_leases)
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        leases_file = self.fake_leases_file(leases)
        update_leases.record_lease_state(get_write_time(leases_file), leases)
        self.assertSequenceEqual([], send_leases.calls)

    def test_update_leases_records_update(self):
        update_leases.record_lease_state(None, None)
        self.fake_leases_file()
        self.patch(update_leases, 'send_leases', FakeMethod())
        update_leases.update_leases()
        self.assertFalse(update_leases.check_lease_changes())

    def test_update_leases_records_state_before_sending(self):
        update_leases.record_lease_state(None, None)
        self.fake_leases_file()
        self.patch(
            update_leases, 'send_leases', FakeMethod(failure=StopExecuting()))
        try:
            update_leases.update_leases()
        except StopExecuting:
            pass
        self.assertFalse(update_leases.check_lease_changes())

    def test_upload_leases_sends_leases_unconditionally(self):
        send_leases = FakeMethod()
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        leases_file = self.fake_leases_file(leases)
        update_leases.record_lease_state(get_write_time(leases_file), leases)
        self.patch(update_leases, 'send_leases', send_leases)
        update_leases.upload_leases()
        self.assertSequenceEqual([(leases, )], send_leases.extract_args())

    def test_upload_leases_records_update(self):
        update_leases.record_lease_state(None, None)
        self.fake_leases_file()
        self.patch(update_leases, 'send_leases', FakeMethod())
        update_leases.upload_leases()
        self.assertFalse(update_leases.check_lease_changes())

    def test_upload_leases_records_state_before_sending(self):
        update_leases.record_lease_state(None, None)
        self.fake_leases_file()
        self.patch(
            update_leases, 'send_leases', FakeMethod(failure=StopExecuting()))
        try:
            update_leases.upload_leases()
        except StopExecuting:
            pass
        self.assertFalse(update_leases.check_lease_changes())
