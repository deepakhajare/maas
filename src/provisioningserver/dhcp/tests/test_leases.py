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
from textwrap import dedent

from maastesting.factory import factory
from maastesting.fakemethod import FakeMethod
from maastesting.testcase import TestCase
from maastesting.utils import (
    age_file,
    get_write_time,
    )
from provisioningserver.dhcp import leases as leases_module
from provisioningserver.dhcp.leases import (
    check_lease_changes,
    parse_leases,
    record_lease_state,
    update_leases,
    upload_leases,
    )


class StopExecuting(BaseException):
    """Exception class to stop execution at a desired point.

    This is deliberately not just an :class:`Exception`.  We want to
    interrupt the code that's being tested, not just exercise its
    error-handling capabilities.
    """


class TestUpdateLeases(TestCase):

    def make_lease(self):
        """Create a leases dict with one, arbitrary lease in it."""
        return {factory.getRandomIPAddress(): factory.getRandomMACAddress()}

    def redirect_parser(self, path):
        """Make the leases parser read from a file at `path`."""
        self.patch(leases_module, 'DHCP_LEASES_FILE', path)

    def fake_leases_file(self, leases=None, age=None):
        """Fake the presence of a leases file.

        This does not go through the leases parser.  It patches out the
        leases parser with a fake that returns the lease data you pass in
        here.

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
        self.redirect_parser(leases_file)
        self.patch(leases_module, 'parse_leases', lambda: (timestamp, leases))
        return leases_file

    def write_leases_file(self, contents):
        """Create a leases file, and cause the parser to read from it.

        This patches out the leases parser to read from the new file.

        :param contents: Text contents for the leases file.
        """
        leases_file = self.make_file(
            contents=dedent(contents).encode('utf-8'))
        self.redirect_parser(leases_file)

    def test_check_lease_changes_returns_tuple_if_no_state_cached(self):
        record_lease_state(None, None)
        leases = self.make_lease()
        leases_file = self.fake_leases_file(leases)
        self.assertEqual(
            (get_write_time(leases_file), leases),
            check_lease_changes())

    def test_check_lease_changes_returns_tuple_if_lease_changed(self):
        ip = factory.getRandomIPAddress()
        leases = {ip: factory.getRandomMACAddress()}
        record_lease_state(
            datetime.utcnow() - timedelta(seconds=10), leases.copy())
        leases[ip] = factory.getRandomMACAddress()
        leases_file = self.fake_leases_file(leases)
        self.assertEqual(
            (get_write_time(leases_file), leases),
            check_lease_changes())

    def test_check_lease_changes_does_not_parse_unchanged_leases_file(self):
        parser = FakeMethod()
        leases_file = self.fake_leases_file()
        self.patch(leases_module, 'parse_leases', parser)
        record_lease_state(get_write_time(leases_file), {})
        update_leases()
        self.assertSequenceEqual([], parser.calls)

    def test_check_lease_changes_returns_tuple_if_lease_added(self):
        leases = self.make_lease()
        record_lease_state(
            datetime.utcnow() - timedelta(seconds=10), leases.copy())
        leases[factory.getRandomIPAddress()] = factory.getRandomMACAddress()
        leases_file = self.fake_leases_file(leases)
        self.assertEqual(
            (get_write_time(leases_file), leases),
            check_lease_changes())

    def test_check_lease_changes_returns_tuple_if_leases_dropped(self):
        record_lease_state(
            datetime.utcnow() - timedelta(seconds=10), self.make_lease())
        leases_file = self.fake_leases_file({})
        self.assertEqual(
            (get_write_time(leases_file), {}),
            check_lease_changes())

    def test_check_lease_changes_returns_None_if_no_change(self):
        leases = self.make_lease()
        leases_file = self.fake_leases_file(leases)
        record_lease_state(get_write_time(leases_file), leases.copy())
        self.assertIsNone(check_lease_changes())

    def test_check_lease_changes_ignores_irrelevant_changes(self):
        leases = self.make_lease()
        self.fake_leases_file(leases, age=10)
        record_lease_state(datetime.utcnow(), leases.copy())
        self.assertIsNone(check_lease_changes())

    def test_update_leases_sends_leases_if_changed(self):
        record_lease_state(None, None)
        send_leases = FakeMethod()
        self.patch(leases_module, 'send_leases', send_leases)
        leases = self.make_lease()
        self.fake_leases_file(leases)
        update_leases()
        self.assertSequenceEqual([(leases, )], send_leases.extract_args())

    def test_update_leases_does_nothing_without_lease_changes(self):
        send_leases = FakeMethod()
        self.patch(leases_module, 'send_leases', send_leases)
        leases = self.make_lease()
        leases_file = self.fake_leases_file(leases)
        record_lease_state(get_write_time(leases_file), leases.copy())
        self.assertSequenceEqual([], send_leases.calls)

    def test_update_leases_records_update(self):
        record_lease_state(None, None)
        self.fake_leases_file()
        self.patch(leases_module, 'send_leases', FakeMethod())
        update_leases()
        self.assertIsNone(check_lease_changes())

    def test_update_leases_records_state_before_sending(self):
        record_lease_state(None, None)
        self.fake_leases_file()
        self.patch(
            leases_module, 'send_leases', FakeMethod(failure=StopExecuting()))
        try:
            update_leases()
        except StopExecuting:
            pass
        self.assertIsNone(check_lease_changes())

    def test_upload_leases_sends_leases_unconditionally(self):
        send_leases = FakeMethod()
        leases = self.make_lease()
        leases_file = self.fake_leases_file(leases)
        record_lease_state(get_write_time(leases_file), leases.copy())
        self.patch(leases_module, 'send_leases', send_leases)
        upload_leases()
        self.assertSequenceEqual([(leases, )], send_leases.extract_args())

    def test_upload_leases_records_update(self):
        record_lease_state(None, None)
        self.fake_leases_file()
        self.patch(leases_module, 'send_leases', FakeMethod())
        upload_leases()
        self.assertIsNone(check_lease_changes())

    def test_upload_leases_records_state_before_sending(self):
        record_lease_state(None, None)
        self.fake_leases_file()
        self.patch(
            leases_module, 'send_leases', FakeMethod(failure=StopExecuting()))
        try:
            upload_leases()
        except StopExecuting:
            pass
        self.assertIsNone(check_lease_changes())

    def test_parse_leases_parses_lease(self):
        params = {
            'ip': factory.getRandomIPAddress(),
            'mac': factory.getRandomMACAddress(),
        }
        self.write_leases_file("""\
            lease %(ip)s {
                starts 5 2010/01/01 00:00:01;
                ends never;
                tstp 6 2010/01/02 05:00:00;
                tsfp 6 2010/01/02 05:00:00;
                binding state free;
                hardware ethernet %(mac)s;
            }
            """ % params)
        leases = parse_leases()
        self.assertEqual(1, len(leases))
        lease = leases[0]
        self.assertEqual(params['ip'], lease.ip)
        self.assertEqual(params['mac'], lease.mac)

    def test_parse_leases_ignores_incomplete_lease_at_end(self):
        params = {
            'ip': factory.getRandomIPAddress(),
            'mac': factory.getRandomMACAddress(),
            'incomplete_ip': factory.getRandomIPAddress(),
        }
        self.write_leases_file("""\
            lease %(ip)s {
                hardware ethernet %(mac)s;
            }
            lease %(incomplete_ip)s {
                starts 5 2010/01/01 00:00:05;
            """ % params)
        leases = parse_leases()
        self.assertEqual(1, len(leases))
        self.assertEqual(params['ip'], leases[0].ip)

    def test_parse_leases_ignores_comments(self):
        params = {
            'ip': factory.getRandomIPAddress(),
            'mac': factory.getRandomMACAddress(),
        }
        self.write_leases_file("""\
            # Top comment (ignored).
            lease %(ip)s { # End-of-line comment (ignored).
                # Comment in lease block (ignored).
                hardware ethernet %(mac)s;  # EOL comment in lease (ignored).
            } # Comment right after closing brace (ignored).
            # End comment (ignored).
            """ % params)
        leases = parse_leases()
        self.assertEqual(1, len(leases))
        self.assertEqual(params['ip'], leases[0].ip)

    def test_parse_leases_treats_never_as_eternity(self):
        params = {
            'ip': factory.getRandomIPAddress(),
            'mac': factory.getRandomMACAddress(),
        }
        self.write_leases_file("""\
            lease %(ip)s {
                hardware ethernet %(mac)s;
                ends never;
            }
            """ % params)
        self.assertIsNone(parse_leases()[0].end)

    def test_parse_leases_treats_missing_end_date_as_eternity(self):
        params = {
            'ip': factory.getRandomIPAddress(),
            'mac': factory.getRandomMACAddress(),
        }
        self.write_leases_file("""\
            lease %(ip)s {
                hardware ethernet %(mac)s;
            }
            """ % params)
        self.assertIsNone(parse_leases()[0].end)

    def test_parse_leases_ignores_expired_leases(self):
        params = {
            'ip': factory.getRandomIPAddress(),
            'mac': factory.getRandomMACAddress(),
        }
        self.write_leases_file("""\
            lease %(ip)s {
                hardware ethernet %(mac)s;
                ends 1 2001/01/01 00:00:00;
            }
            """ % params)
        self.assertSequenceEqual([], parse_leases())

    def test_parse_leases_takes_latest_lease_for_address(self):
        params = {
            'ip': factory.getRandomIPAddress(),
            'old_owner': factory.getRandomMACAddress(),
            'new_owner': factory.getRandomMACAddress(),
        }
        self.write_leases_file("""\
            lease %(ip)s {
                hardware ethernet %(old_owner)s;
            }
            lease %(ip)s {
                hardware ehternet %(new_owner)s;
            }
            """ % params)
        leases = parse_leases()
        self.assertEqual(1, len(leases))
        self.assertEqual(params['new_owner'], leases[0].mac)
