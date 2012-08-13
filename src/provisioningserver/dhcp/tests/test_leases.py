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

from apiclient.maas_client import MAASClient
from maastesting.factory import factory
from maastesting.fakemethod import FakeMethod
from maastesting.utils import (
    age_file,
    get_write_time,
    )
from provisioningserver import auth
from provisioningserver.dhcp import leases as leases_module
from provisioningserver.dhcp.leases import (
    check_lease_changes,
    identify_new_leases,
    parse_leases_file,
    process_leases,
    record_lease_state,
    record_omapi_shared_key,
    register_new_leases,
    send_leases,
    update_leases,
    upload_leases,
    )
from provisioningserver.omshell import Omshell
from provisioningserver.testing.testcase import TestCase
from testtools.testcase import ExpectedException


class TestHelpers(TestCase):

    def test_record_omapi_shared_key_records_shared_key(self):
        self.patch(leases_module, 'recorded_omapi_shared_key', None)
        key = factory.getRandomString()
        record_omapi_shared_key(key)
        self.assertEqual(key, leases_module.recorded_omapi_shared_key)

    def test_record_lease_state_records_time_and_leases(self):
        time = datetime.utcnow()
        leases = {factory.getRandomIPAddress(): factory.getRandomMACAddress()}
        self.patch(leases_module, 'recorded_leases_time', None)
        self.patch(leases_module, 'recorded_leases', None)
        record_lease_state(time, leases)
        self.assertEqual(
            (time, leases), (
                leases_module.recorded_leases_time,
                leases_module.recorded_leases,
                ))


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
        self.patch(
            leases_module, 'parse_leases_file', lambda: (timestamp, leases))
        return leases_file

    def write_leases_file(self, contents):
        """Create a leases file, and cause the parser to read from it.

        This patches out the leases parser to read from the new file.

        :param contents: Text contents for the leases file.
        :return: Path of temporary leases file.
        """
        leases_file = self.make_file(
            contents=dedent(contents).encode('utf-8'))
        self.redirect_parser(leases_file)
        return leases_file

    def set_omapi_key(self, key=None):
        """Set a recorded omapi key for the duration of this test."""
        if key is None:
            key = factory.getRandomString()
        self.patch(leases_module, 'recorded_omapi_shared_key', key)

    def clear_omapi_key(self):
        """Clear the recorded omapi key for the duration of this test."""
        self.patch(leases_module, 'omapi_shared_key', None)

    def set_nodegroup_name(self):
        """Set the recorded nodegroup name for the duration of this test."""
        name = factory.make_name('nodegroup')
        auth.record_nodegroup_name(name)
        return name

    def set_api_credentials(self):
        """Set recorded API credentials for the duration of this test."""
        creds_string = ':'.join(
            factory.getRandomString() for counter in range(3))
        auth.record_api_credentials(creds_string)

    def set_lease_state(self, time=None, leases=None):
        """Set the recorded state of DHCP leases.

        This is similar to record_lease_state, except it will patch() the
        state so that it gets reset at the end of the test.  Using this will
        prevent recorded lease state from leaking into other tests.
        """
        self.patch(leases_module, 'recorded_leases_time', time)
        self.patch(leases_module, 'recorded_leases', leases)

    def test_record_lease_state_sets_leases_and_timestamp(self):
        time = datetime.utcnow()
        leases = {factory.getRandomIPAddress(): factory.getRandomMACAddress()}
        self.set_lease_state()
        record_lease_state(time, leases)
        self.assertEqual(
            (time, leases), (
                leases_module.recorded_leases_time,
                leases_module.recorded_leases,
                ))

    def test_check_lease_changes_returns_tuple_if_no_state_cached(self):
        self.set_lease_state()
        leases = self.make_lease()
        leases_file = self.fake_leases_file(leases)
        self.assertEqual(
            (get_write_time(leases_file), leases),
            check_lease_changes())

    def test_check_lease_changes_returns_tuple_if_lease_changed(self):
        ip = factory.getRandomIPAddress()
        leases = {ip: factory.getRandomMACAddress()}
        self.set_lease_state(
            datetime.utcnow() - timedelta(seconds=10), leases.copy())
        leases[ip] = factory.getRandomMACAddress()
        leases_file = self.fake_leases_file(leases)
        self.assertEqual(
            (get_write_time(leases_file), leases),
            check_lease_changes())

    def test_check_lease_changes_does_not_parse_unchanged_leases_file(self):
        parser = FakeMethod()
        leases_file = self.fake_leases_file()
        self.patch(leases_module, 'parse_leases_file', parser)
        self.set_lease_state(get_write_time(leases_file), {})
        update_leases()
        self.assertSequenceEqual([], parser.calls)

    def test_check_lease_changes_returns_tuple_if_lease_added(self):
        leases = self.make_lease()
        self.set_lease_state(
            datetime.utcnow() - timedelta(seconds=10), leases.copy())
        leases[factory.getRandomIPAddress()] = factory.getRandomMACAddress()
        leases_file = self.fake_leases_file(leases)
        self.assertEqual(
            (get_write_time(leases_file), leases),
            check_lease_changes())

    def test_check_lease_changes_returns_tuple_if_leases_dropped(self):
        self.set_lease_state(
            datetime.utcnow() - timedelta(seconds=10), self.make_lease())
        leases_file = self.fake_leases_file({})
        self.assertEqual(
            (get_write_time(leases_file), {}),
            check_lease_changes())

    def test_check_lease_changes_returns_None_if_no_change(self):
        leases = self.make_lease()
        leases_file = self.fake_leases_file(leases)
        self.set_lease_state(get_write_time(leases_file), leases.copy())
        self.assertIsNone(check_lease_changes())

    def test_check_lease_changes_ignores_irrelevant_changes(self):
        leases = self.make_lease()
        self.fake_leases_file(leases, age=10)
        self.set_lease_state(datetime.utcnow(), leases.copy())
        self.assertIsNone(check_lease_changes())

    def test_update_leases_processes_leases_if_changed(self):
        self.set_lease_state()
        self.patch(leases_module, 'send_leases', FakeMethod())
        leases = self.make_lease()
        self.fake_leases_file(leases)
        self.patch(Omshell, 'create', FakeMethod())
        update_leases()
        self.assertEqual(
            [(leases, )],
            leases_module.send_leases.extract_args())

    def test_update_leases_does_nothing_without_lease_changes(self):
        fake_send_leases = FakeMethod()
        self.patch(leases_module, 'send_leases', fake_send_leases)
        leases = self.make_lease()
        leases_file = self.fake_leases_file(leases)
        self.set_lease_state(get_write_time(leases_file), leases.copy())
        self.assertEqual([], leases_module.send_leases.calls)

    def test_process_leases_records_update(self):
        self.set_lease_state()
        self.clear_omapi_key()
        self.patch(leases_module, 'send_leases', FakeMethod())
        new_leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        self.fake_leases_file(new_leases)
        process_leases(datetime.utcnow(), new_leases)
        self.assertIsNone(check_lease_changes())

    def test_process_leases_records_state_before_sending(self):
        self.set_lease_state()
        self.patch(Omshell, 'create', FakeMethod())
        self.fake_leases_file({})
        self.patch(
            leases_module, 'send_leases', FakeMethod(failure=StopExecuting()))
        new_leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        try:
            process_leases(datetime.utcnow(), new_leases)
        except StopExecuting:
            pass
        self.fake_leases_file(new_leases)
        self.assertIsNone(check_lease_changes())

    def test_process_leases_registers_new_leases(self):
        self.set_lease_state()
        self.set_omapi_key()
        self.patch(Omshell, 'create', FakeMethod())
        ip = factory.getRandomIPAddress()
        mac = factory.getRandomMACAddress()
        process_leases(datetime.utcnow(), {ip: mac})
        self.assertEqual([(ip, mac)], Omshell.create.extract_args())

    def test_process_leases_retries_failed_registrations(self):

        class OmshellFailure(Exception):
            pass

        self.set_lease_state()
        self.set_omapi_key()
        self.patch(Omshell, 'create', FakeMethod(failure=OmshellFailure()))
        ip = factory.getRandomIPAddress()
        mac = factory.getRandomMACAddress()
        with ExpectedException(OmshellFailure):
            process_leases(datetime.utcnow(), {ip: mac})
        # At this point {ip: mac} has not been successfully registered.
        # But if we re-run process_leases later, it will retry.
        self.patch(Omshell, 'create', FakeMethod())
        process_leases(datetime.utcnow(), {ip: mac})
        self.assertEqual([(ip, mac)], Omshell.create.extract_args())

    def test_upload_leases_processes_leases_unconditionally(self):
        leases = self.make_lease()
        leases_file = self.fake_leases_file(leases)
        self.set_lease_state(get_write_time(leases_file), leases.copy())
        self.patch(leases_module, 'send_leases', FakeMethod())
        upload_leases()
        self.assertEqual(
            [(leases, )],
            leases_module.send_leases.extract_args())

    def test_parse_leases_file_parses_leases(self):
        params = {
            'ip': factory.getRandomIPAddress(),
            'mac': factory.getRandomMACAddress(),
        }
        leases_file = self.write_leases_file("""\
            lease %(ip)s {
                starts 5 2010/01/01 00:00:01;
                ends never;
                tstp 6 2010/01/02 05:00:00;
                tsfp 6 2010/01/02 05:00:00;
                binding state free;
                hardware ethernet %(mac)s;
            }
            """ % params)
        self.assertEqual(
            (get_write_time(leases_file), {params['ip']: params['mac']}),
            parse_leases_file())

    def test_identify_new_leases_identifies_everything_first_time(self):
        self.patch(leases_module, 'recorded_leases', None)
        current_leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        self.assertEqual(current_leases, identify_new_leases(current_leases))

    def test_identify_new_leases_identifies_previously_unknown_leases(self):
        self.patch(leases_module, 'recorded_leases', {})
        current_leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        self.assertEqual(current_leases, identify_new_leases(current_leases))

    def test_identify_new_leases_leaves_out_previously_known_leases(self):
        old_leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        self.patch(leases_module, 'recorded_leases', old_leases)
        new_leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        current_leases = old_leases.copy()
        current_leases.update(new_leases)
        self.assertEqual(new_leases, identify_new_leases(current_leases))

    def test_register_new_leases_registers_new_leases(self):
        self.patch(Omshell, 'create', FakeMethod())
        self.set_lease_state()
        self.set_omapi_key()
        ip = factory.getRandomIPAddress()
        mac = factory.getRandomMACAddress()
        register_new_leases({ip: mac})
        [create_args] = Omshell.create.extract_args()
        self.assertEqual((ip, mac), create_args)

    def test_register_new_leases_ignores_known_leases(self):
        self.patch(Omshell, 'create', FakeMethod())
        self.set_omapi_key()
        self.set_nodegroup_name()
        old_leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        self.set_lease_state(None, old_leases)
        register_new_leases(old_leases)
        self.assertEqual([], Omshell.create.calls)

    def test_register_new_leases_does_nothing_without_omapi_key(self):
        self.patch(Omshell, 'create', FakeMethod())
        self.set_lease_state()
        self.clear_omapi_key()
        self.set_nodegroup_name()
        new_leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        register_new_leases(new_leases)
        self.assertEqual([], Omshell.create.calls)

    def test_register_new_leases_does_nothing_without_nodegroup_name(self):
        self.patch(Omshell, 'create', FakeMethod())
        self.set_lease_state()
        self.clear_omapi_key()
        new_leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        register_new_leases(new_leases)
        self.assertEqual([], Omshell.create.calls)

    def test_send_leases_posts_to_API(self):
        self.patch(Omshell, 'create', FakeMethod())
        self.set_api_credentials()
        nodegroup_name = self.set_nodegroup_name()
        self.patch(MAASClient, 'post', FakeMethod())
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        send_leases(leases)
        self.assertEqual([(
                ('nodegroups/%s/' % nodegroup_name, 'update_leases'),
                {'leases': leases},
                )],
            MAASClient.post.calls)

    def test_send_leases_does_nothing_without_credentials(self):
        self.patch(MAASClient, 'post', FakeMethod())
        leases = {
            factory.getRandomIPAddress(): factory.getRandomMACAddress(),
        }
        send_leases(leases)
        self.assertEqual([], MAASClient.post.calls)
