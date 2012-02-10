# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maasserver.provisioning`."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from fixtures import MonkeyPatch
from maasserver import provisioning
from maasserver.models import Node
from maastesting import TestCase
from provisioningserver.testing.fakeapi import FakeSynchronousProvisioningAPI


class ProvisioningTests:
    """Tests for the Provisioning API as maasserver sees it."""

    # Must be defined in concrete subclasses.
    papi = None

    def test_provision_post_save_Node_create(self):
        # Creating and saving a node automatically creates a dummy distro and
        # profile too, and associates it with the new node.
        node_model = Node(system_id="frank")
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
        node_model = Node(system_id="frank")
        node_model.save()
        node_model.add_mac_address("12:34:56:78:90:12")
        node = self.papi.get_nodes_by_name(["frank"])["frank"]
        self.assertEqual(
            {"mac_address": "12:34:56:78:90:12"},
            node["interfaces"])

    def test_provision_post_save_Node_update(self):
        # Saving an existing node does not change the profile or distro
        # associated with it.
        node_model = Node(system_id="frank")
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
        node_model = Node(system_id="frank")
        node_model.save()
        mac_model = node_model.add_mac_address("12:34:56:78:90:12")
        mac_model.mac_address = "11:22:33:44:55:66"
        mac_model.save()
        node = self.papi.get_nodes_by_name(["frank"])["frank"]
        self.assertEqual(
            {"mac_address": "11:22:33:44:55:66"},
            node["interfaces"])

    def test_provision_post_delete_Node(self):
        node_model = Node(system_id="frank")
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
        node_model = Node(system_id="frank")
        node_model.save()
        node_model.add_mac_address("12:34:56:78:90:12")
        node_model.remove_mac_address("12:34:56:78:90:12")
        node = self.papi.get_nodes_by_name(["frank"])["frank"]
        self.assertEqual({}, node["interfaces"])


def patch_in_fake_papi(test):
    """Patch in a fake Provisioning API for the duration of the test."""
    papi_fake = FakeSynchronousProvisioningAPI()
    patch = MonkeyPatch(
        "maasserver.provisioning.get_provisioning_api_proxy",
        lambda: papi_fake)
    test.useFixture(patch)
    return papi_fake


class TestProvisioningFake(TestCase):
    """Tests for `patch_in_fake_papi`."""

    def test_patch_in_fake_papi(self):
        # patch_in_fake_papi() patches in a fake provisioning API so that we
        # can observe what the signal handlers are doing.
        papi = provisioning.get_provisioning_api_proxy()
        papi_fake = patch_in_fake_papi(self)
        self.assertIsNot(provisioning.get_provisioning_api_proxy(), papi)
        self.assertIs(provisioning.get_provisioning_api_proxy(), papi_fake)
        # The fake is pristine; it does not contain sample data.
        self.assertEqual({}, papi_fake.distros)
        self.assertEqual({}, papi_fake.profiles)
        self.assertEqual({}, papi_fake.nodes)


class TestProvisioningWithFake(ProvisioningTests, TestCase):
    """Tests for the Provisioning API using a fake."""

    def setUp(self):
        super(TestProvisioningWithFake, self).setUp()
        self.papi = patch_in_fake_papi(self)
