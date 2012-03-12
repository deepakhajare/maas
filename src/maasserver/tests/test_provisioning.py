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

from maasserver import provisioning
from maasserver.models import (
    Config,
    Node,
    NODE_AFTER_COMMISSIONING_ACTION,
    NODE_STATUS,
    )
from maasserver.provisioning import (
    compose_metadata,
    get_metadata_server_url,
    select_profile_for_node,
    )
from maasserver.testing import TestCase
from maasserver.testing.factory import factory
from metadataserver.models import NodeKey


class ProvisioningTests:
    """Tests for the Provisioning API as maasserver sees it."""

    # Must be defined in concrete subclasses.
    papi = None

    def make_node_without_saving(self, arch='i386'):
        """Create a Node, but don't save it to the database."""
        system_id = "node-%s" % factory.getRandomString()
        return Node(
            system_id=system_id, hostname=factory.getRandomString(),
            status=NODE_STATUS.DEFAULT_STATUS, owner=factory.make_user(),
            after_commissioning_action=(
                NODE_AFTER_COMMISSIONING_ACTION.DEFAULT),
            architecture=arch)

    def make_papi_profile(self):
        """Create a new profile on the provisioning API."""
        # Kernel and initrd are irrelevant here, but must be real files
        # for Cobbler's benefit.  Cobbler may not be running locally, so
        # just feed it some filenames that it's sure to have (and won't
        # be allowed accidentally to overwrite).
        shared_name = factory.getRandomString()
        distro_name = 'distro-%s' % shared_name
        fake_initrd = '/etc/cobbler/settings'
        fake_kernel = '/etc/cobbler/version'
        distro = self.papi.add_distro(distro_name, fake_initrd, fake_kernel)
        profile_name = 'profile-%s' % shared_name
        return self.papi.add_profile(profile_name, distro)

    def test_select_profile_for_node_selects_previously_chosen_profile(self):
        node = factory.make_node()
        # Set a different profile for the node.
        profile = self.make_papi_profile()
        metadata = compose_metadata(node)
        self.papi.add_node(node.system_id, profile, metadata)
        self.assertEqual(profile, select_profile_for_node(node, self.papi))

    def test_select_profile_for_node_selects_Precise_and_right_arch(self):
        nodes = {
            arch: self.make_node_without_saving(arch=arch)
            for arch in ['i386', 'amd64']}
        self.assertItemsEqual(
            ['precise-%s' % arch for arch in nodes.keys()],
            [
                select_profile_for_node(node, self.papi)
                for node in nodes.values()])

    def test_provision_post_save_Node_create(self):
        # The handler for Node's post-save signal registers the node in
        # its current state with the provisioning server.
        node = self.make_node_without_saving(arch='i386')
        node.id = factory.make_node().id
        provisioning.provision_post_save_Node(
            sender=Node, instance=node, created=True)
        system_id = node.system_id
        pserv_node = self.papi.get_nodes_by_name([system_id])[system_id]
        self.assertEqual("precise-i386", pserv_node["profile"])

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
