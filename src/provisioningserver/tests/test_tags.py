# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for tag updating."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from apiclient.maas_client import MAASClient
import httplib
from maastesting.factory import factory
from mock import MagicMock
from provisioningserver.auth import (
    get_recorded_nodegroup_uuid,
    )
from provisioningserver.testing.testcase import PservTestCase
from provisioningserver import tags


class FakeResponse:

    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content


class TestTagUpdating(PservTestCase):

    def test_get_cached_knowledge_knows_nothing(self):
        # If we haven't given it any secrets, we should get back nothing
        self.assertEqual((None, None), tags.get_cached_knowledge())

    def test_get_cached_knowledge_with_only_url(self):
        self.set_maas_url()
        self.assertEqual((None, None), tags.get_cached_knowledge())

    def test_get_cached_knowledge_with_only_url_creds(self):
        self.set_maas_url()
        self.set_api_credentials()
        self.assertEqual((None, None), tags.get_cached_knowledge())

    def test_get_cached_knowledge_with_all_info(self):
        self.set_maas_url()
        self.set_api_credentials()
        self.set_node_group_uuid()
        client, uuid = tags.get_cached_knowledge()
        self.assertIsNot(None, client)
        self.assertIsInstance(client, MAASClient)
        self.assertIsNot(None, uuid)
        self.assertEqual(get_recorded_nodegroup_uuid(), uuid)

    def fake_client(self):
        return MAASClient(None, None, self.make_maas_url())

    def fake_cached_knowledge(self):
        nodegroup_uuid = factory.make_name('nodegroupuuid')
        return self.fake_client(), nodegroup_uuid

    def test_get_nodes_calls_correct_api_and_parses_result(self):
        client, uuid = self.fake_cached_knowledge()
        response = FakeResponse(httplib.OK, '["system-id1", "system-id2"]')
        mock = MagicMock(return_value=response)
        self.patch(client, 'get', mock)
        result = tags.get_nodes_for_node_group(client, uuid)
        self.assertEqual(['system-id1', 'system-id2'], result)
        url = 'api/1.0/nodegroup/%s/' % (uuid,)
        mock.assert_called_once_with(url, op='list_nodes')

    def test_get_hardware_details_calls_correct_api_and_parses_result(self):
        client, uuid = self.fake_cached_knowledge()
        xml_data = "<test><data /></test>"
        content = '[["system-id1", "%s"]]' % (xml_data,)
        response = FakeResponse(httplib.OK, content)
        mock = MagicMock(return_value=response)
        self.patch(client, 'get', mock)
        result = tags.get_hardware_details_for_nodes(
            client, uuid, ['system-id1', 'system-id2'])
        self.assertEqual([['system-id1', xml_data]], result)
        url = 'api/1.0/nodegroup/%s/' % (uuid,)
        mock.assert_called_once_with(
            url, op='node_hardware_details',
            system_ids=["system-id1", "system-id2"])

    def test_update_node_tags_calls_correct_api_and_parses_result(self):
        client, uuid = self.fake_cached_knowledge()
        content = '{"added": 1, "removed": 2}'
        response = FakeResponse(httplib.OK, content)
        mock = MagicMock(return_value=response)
        self.patch(client, 'post', mock)
        name = factory.make_name('tag')
        result = tags.update_node_tags(client, name, uuid,
            ['add-system-id'], ['remove-1', 'remove-2'])
        self.assertEqual({'added': 1, 'removed': 2}, result)
        url = 'api/1.0/tags/%s/' % (name,)
        mock.assert_called_once_with(
            url, op='update_nodes',
            add=['add-system-id'], remove=['remove-1', 'remove-2'])
