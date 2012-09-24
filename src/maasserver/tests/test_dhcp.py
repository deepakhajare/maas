# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for DHCP management."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django.conf import settings
from maasserver import dhcp
from maasserver.dhcp import (
    configure_dhcp,
    is_dhcp_managed,
    )
from maasserver.dns import get_dns_server_address
from maasserver.enum import NODEGROUP_STATUS
from maasserver.server_address import get_maas_facing_server_address
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maastesting.celery import CeleryFixture
from provisioningserver import tasks
from testresources import FixtureResource


class TestDHCP(TestCase):

    resources = (
        ('celery', FixtureResource(CeleryFixture())),
        )

    def test_is_dhcp_managed_follows_nodegroup_status(self):
        expected_results = {
            NODEGROUP_STATUS.PENDING: False,
            NODEGROUP_STATUS.REJECTED: False,
            NODEGROUP_STATUS.ACCEPTED: True,
        }
        nodegroups = {
            factory.make_node_group(status=status): value
            for status, value in expected_results.items()
        }
        self.patch(settings, "DHCP_CONNECT", True)
        results = {
            nodegroup.status: is_dhcp_managed(nodegroup)
            for nodegroup, value in nodegroups.items()
        }
        self.assertEquals(expected_results, results)

    def test_configure_dhcp_writes_dhcp_config(self):
        mocked_task = self.patch(dhcp, 'write_dhcp_config')
        self.patch(
            settings, 'DEFAULT_MAAS_URL',
            'http://%s/' % factory.getRandomIPAddress())
        nodegroup = factory.make_node_group(
            status=NODEGROUP_STATUS.ACCEPTED,
            dhcp_key=factory.getRandomString(),
            ip_range_low='192.168.102.1', ip_range_high='192.168.103.254',
            subnet_mask='255.255.252.0', broadcast_ip='192.168.103.255')

        self.patch(settings, "DHCP_CONNECT", True)
        configure_dhcp(nodegroup)
        dhcp_params = [
            'subnet_mask', 'broadcast_ip', 'router_ip',
            'ip_range_low', 'ip_range_high']

        interface = nodegroup.get_managed_interface()
        expected_params = {
            param: getattr(interface, param)
            for param in dhcp_params}

        # Currently all nodes use the central TFTP server.  This will be
        # decentralized to use NodeGroup.worker_ip later.
        expected_params["next_server"] = get_maas_facing_server_address()

        expected_params["omapi_key"] = nodegroup.dhcp_key
        expected_params["dns_servers"] = get_dns_server_address()
        expected_params["subnet"] = '192.168.100.0'

        result_params = mocked_task.apply_async.call_args[1]['kwargs']
        # The check that the callback is correct is done in
        # test_configure_dhcp_restart_dhcp_server.
        del result_params['callback']

        self.assertEqual(expected_params, result_params)

    def test_configure_dhcp_restart_dhcp_server(self):
        self.patch(tasks, "sudo_write_file")
        mocked_check_call = self.patch(tasks, "check_call")
        self.patch(settings, "DHCP_CONNECT", True)
        nodegroup = factory.make_node_group(status=NODEGROUP_STATUS.ACCEPTED)
        configure_dhcp(nodegroup)
        self.assertEqual(
            mocked_check_call.call_args[0][0],
            ['sudo', '-n', 'service', 'isc-dhcp-server', 'restart'])

    def test_dhcp_config_gets_written_when_nodegroup_becomes_active(self):
        nodegroup = factory.make_node_group(status=NODEGROUP_STATUS.PENDING)
        self.patch(settings, "DHCP_CONNECT", True)
        self.patch(dhcp, 'write_dhcp_config')
        nodegroup.accept()
        self.assertEqual(1, dhcp.write_dhcp_config.apply_async.call_count)

    def test_write_dhcp_config_task_routed_to_nodegroup_worker(self):
        nodegroup = factory.make_node_group(status=NODEGROUP_STATUS.PENDING)
        self.patch(settings, "DHCP_CONNECT", True)
        self.patch(dhcp, 'write_dhcp_config')
        nodegroup.accept()
        self.assertEqual(
            nodegroup.uuid,
            dhcp.write_dhcp_config.apply_async.call_args[1]['queue'])

    def test_write_dhcp_config_restart_task_routed_to_nodegroup_worker(self):
        nodegroup = factory.make_node_group(status=NODEGROUP_STATUS.PENDING)
        self.patch(settings, "DHCP_CONNECT", True)
        self.patch(tasks, 'sudo_write_file')
        task = self.patch(dhcp, 'restart_dhcp_server')
        nodegroup.accept()
        self.assertEqual(
            nodegroup.uuid, task.subtask.call_args[1]['options']['queue'])

    def test_dhcp_config_gets_written_when_nodegroupinterface_changes(self):
        nodegroup = factory.make_node_group(status=NODEGROUP_STATUS.ACCEPTED)
        interface = nodegroup.get_managed_interface()
        self.patch(settings, "DHCP_CONNECT", True)
        self.patch(dhcp, 'write_dhcp_config')
        new_router_ip = factory.getRandomIPAddress()
        interface.router_ip = new_router_ip
        interface.save()
        async_mock = dhcp.write_dhcp_config.apply_async
        self.assertEqual(
            (1, new_router_ip),
            (
                dhcp.write_dhcp_config.apply_async.call_count,
                async_mock.call_args[1]['kwargs']['router_ip'],
            ))
