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
from provisioningserver.auth import (
    get_recorded_nodegroup_uuid,
    )
from provisioningserver.testing.testcase import PservTestCase
from provisioningserver import tags


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
