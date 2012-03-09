# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maasserver.provisioning`."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from urlparse import parse_qs

from django.conf import settings
from maasserver import provisioning
from maasserver.models import (
    Config,
    Node,
    )
from maasserver.provisioning import (
    compose_metadata,
    get_metadata_server_url,
    )
from maasserver.testing import TestCase
from maasserver.testing.factory import factory
from metadataserver.models import NodeKey


class ProvisioningTests:
    """Tests for the Provisioning API as maasserver sees it."""

    # Must be defined in concrete subclasses.
    papi = None

    def test_transactionmiddleware(self):
        # The TransactionMiddleware is enabled.
        self.assertIn(
            'django.middleware.transaction.TransactionMiddleware',
            settings.MIDDLEWARE_CLASSES)

    def test_provision_post_save_Node_create(self):
        # Creating and saving a node automatically creates a dummy distro and
        # profile too, and associates it with the new node.
        node_model = factory.make_node(system_id="frank")
        provisioning.provision_post_save_Node(
            sender=Node, instance=node_model, created=True)
        nodes = self.papi.get_nodes_by_name(["frank"])
        self.assertEqual(["frank"], sorted(nodes))
        node = nodes["frank"]
        profile_name = node["profile"]
        profiles = self.papi.get_profiles_by_name([profile_name])
        self.assertEqual([profile_name], sorted(profiles))
        profile = profiles[profile_name]
        distro_name = profile["distro"]
        distros = self.papi.get_distros_by_name([distro_name])
        self.assertEqual([distro_name], sorted(distros))

    def test_provision_post_save_MACAddress_create(self):
        # Creating and saving a MACAddress updates the Node with which it's
        # associated.
        node_model = factory.make_node(system_id="frank")
        node_model.add_mac_address("12:34:56:78:90:12")
        node = self.papi.get_nodes_by_name(["frank"])["frank"]
        self.assertEqual(["12:34:56:78:90:12"], node["mac_addresses"])

    def test_provision_post_save_Node_update(self):
        # Saving an existing node does not change the profile or distro
        # associated with it.
        node_model = factory.make_node(system_id="frank")
        provisioning.provision_post_save_Node(
            sender=Node, instance=node_model, created=True)
        # Record the current profile name.
        node = self.papi.get_nodes_by_name(["frank"])["frank"]
        profile_name1 = node["profile"]
        # Update the model node.
        provisioning.provision_post_save_Node(
            sender=Node, instance=node_model, created=False)
        # The profile name is unchanged.
        node = self.papi.get_nodes_by_name(["frank"])["frank"]
        profile_name2 = node["profile"]
        self.assertEqual(profile_name1, profile_name2)

    def test_provision_post_save_MACAddress_update(self):
        # Saving an existing MACAddress updates the Node with which it's
        # associated.
        node_model = factory.make_node(system_id="frank")
        mac_model = node_model.add_mac_address("12:34:56:78:90:12")
        mac_model.mac_address = "11:22:33:44:55:66"
        mac_model.save()
        node = self.papi.get_nodes_by_name(["frank"])["frank"]
        self.assertEqual(["11:22:33:44:55:66"], node["mac_addresses"])

    def test_provision_post_delete_Node(self):
        node_model = factory.make_node(system_id="frank")
        provisioning.provision_post_save_Node(
            sender=Node, instance=node_model, created=True)
        provisioning.provision_post_delete_Node(
            sender=Node, instance=node_model)
        # The node is deleted, but the profile and distro remain.
        self.assertNotEqual({}, self.papi.get_distros())
        self.assertNotEqual({}, self.papi.get_profiles())
        self.assertEqual({}, self.papi.get_nodes_by_name(["frank"]))

    def test_provision_post_delete_MACAddress(self):
        # Deleting a MACAddress updates the Node with which it's associated.
        node_model = factory.make_node(system_id="frank")
        node_model.add_mac_address("12:34:56:78:90:12")
        node_model.remove_mac_address("12:34:56:78:90:12")
        node = self.papi.get_nodes_by_name(["frank"])["frank"]
        self.assertEqual([], node["mac_addresses"])

    def test_metadata_server_url_refers_to_own_metadata_service(self):
        self.assertEqual(
            "http://%s/metadata/"
            % Config.objects.get_config('metadata-host'),
            get_metadata_server_url())

    def test_compose_metadata_includes_metadata_url(self):
        node = factory.make_node()
        self.assertEqual(
            get_metadata_server_url(),
            compose_metadata(node)['maas-metadata-url'])

    def test_compose_metadata_includes_node_oauth_token(self):
        node = factory.make_node()
        metadata = compose_metadata(node)
        token = NodeKey.objects.get_token_for_node(node)
        self.assertEqual({
            'oauth_consumer_key': [token.consumer.key],
            'oauth_token_key': [token.key],
            'oauth_token_secret': [token.secret],
            },
            parse_qs(metadata['maas-metadata-credentials']))


class TestProvisioningWithFake(ProvisioningTests, TestCase):
    """Tests for the Provisioning API using a fake."""

    def setUp(self):
        super(TestProvisioningWithFake, self).setUp()
        self.papi = provisioning.get_provisioning_api_proxy()
