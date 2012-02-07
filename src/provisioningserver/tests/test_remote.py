# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.remote`."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from provisioningserver.cobblerclient import CobblerSession
from provisioningserver.remote import ProvisioningAPI
from provisioningserver.testing.fakecobbler import (
    FakeCobbler,
    FakeTwistedProxy,
    )
from testtools import TestCase
from testtools.deferredruntest import AsynchronousDeferredRunTest
from twisted.internet.defer import inlineCallbacks


class TestProvisioningAPI(TestCase):
    """Tests for `provisioningserver.remote.ProvisioningAPI`."""

    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=5)

    def get_cobbler_session(self):
        cobbler_session = CobblerSession(
            "http://localhost/does/not/exist", "user", "password")
        cobbler_fake = FakeCobbler({"user": "password"})
        cobbler_proxy = FakeTwistedProxy(cobbler_fake)
        cobbler_session.proxy = cobbler_proxy
        return cobbler_session

    @inlineCallbacks
    def test_add_distro(self):
        cobbler_session = self.get_cobbler_session()
        # Create a distro via the Provisioning API.
        prov = ProvisioningAPI(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        self.assertEqual("distro", distro)

    @inlineCallbacks
    def test_delete_distro(self):
        cobbler_session = self.get_cobbler_session()
        # Create a distro via the Provisioning API.
        prov = ProvisioningAPI(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        # Delete it again via the Provisioning API.
        yield prov.xmlrpc_delete_distro(distro)
        # It has gone, checked via the Cobbler session.
        distros = yield prov.xmlrpc_get_distros()
        self.assertEqual({}, distros)

    @inlineCallbacks
    def test_get_distros(self):
        cobbler_session = self.get_cobbler_session()
        prov = ProvisioningAPI(cobbler_session)
        distros = yield prov.xmlrpc_get_distros()
        self.assertEqual({}, distros)
        # Create some distros via the Provisioning API.
        expected = {}
        for num in xrange(3):
            initrd = self.getUniqueString()
            kernel = self.getUniqueString()
            name = self.getUniqueString()
            yield prov.xmlrpc_add_distro(name, initrd, kernel)
            expected[name] = {
                "initrd": initrd,
                "kernel": kernel,
                "name": name,
                }
        distros = yield prov.xmlrpc_get_distros()
        self.assertEqual(expected, distros)

    @inlineCallbacks
    def test_get_distros_by_name(self):
        cobbler_session = self.get_cobbler_session()
        prov = ProvisioningAPI(cobbler_session)
        distros = yield prov.xmlrpc_get_distros_by_name([])
        self.assertEqual({}, distros)
        # Create a distro via the Provisioning API.
        yield prov.xmlrpc_add_distro("alice", "initrd", "kernel")
        distros = yield prov.xmlrpc_get_distros_by_name(["alice", "bob"])
        # The response contains keys for all distributions found.
        self.assertSequenceEqual(["alice"], sorted(distros))

    @inlineCallbacks
    def test_add_profile(self):
        cobbler_session = self.get_cobbler_session()
        # Create a profile via the Provisioning API.
        prov = ProvisioningAPI(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        profile = yield prov.xmlrpc_add_profile("profile", distro)
        self.assertEqual("profile", profile)

    @inlineCallbacks
    def test_delete_profile(self):
        cobbler_session = self.get_cobbler_session()
        # Create a profile via the Provisioning API.
        prov = ProvisioningAPI(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        profile = yield prov.xmlrpc_add_profile("profile", distro)
        # Delete it again via the Provisioning API.
        yield prov.xmlrpc_delete_profile(profile)
        # It has gone, checked via the Cobbler session.
        profiles = yield prov.xmlrpc_get_profiles()
        self.assertEqual({}, profiles)

    @inlineCallbacks
    def test_get_profiles(self):
        cobbler_session = self.get_cobbler_session()
        prov = ProvisioningAPI(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        profiles = yield prov.xmlrpc_get_profiles()
        self.assertEqual({}, profiles)
        # Create some profiles via the Provisioning API.
        expected = {}
        for num in xrange(3):
            name = self.getUniqueString()
            yield prov.xmlrpc_add_profile(name, distro)
            expected[name] = {u'distro': u'distro', u'name': name}
        profiles = yield prov.xmlrpc_get_profiles()
        self.assertEqual(expected, profiles)

    @inlineCallbacks
    def test_get_profiles_by_name(self):
        cobbler_session = self.get_cobbler_session()
        prov = ProvisioningAPI(cobbler_session)
        profiles = yield prov.xmlrpc_get_profiles_by_name([])
        self.assertEqual({}, profiles)
        # Create a profile via the Provisioning API.
        distro = yield prov.xmlrpc_add_distro("distro", "initrd", "kernel")
        yield prov.xmlrpc_add_profile("alice", distro)
        profiles = yield prov.xmlrpc_get_profiles_by_name(["alice", "bob"])
        # The response contains keys for all profiles found.
        self.assertSequenceEqual(["alice"], sorted(profiles))

    @inlineCallbacks
    def test_add_node(self):
        cobbler_session = self.get_cobbler_session()
        # Create a system/node via the Provisioning API.
        prov = ProvisioningAPI(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        profile = yield prov.xmlrpc_add_profile("profile", distro)
        node = yield prov.xmlrpc_add_node("node", profile)
        self.assertEqual("node", node)

    @inlineCallbacks
    def test_delete_node(self):
        cobbler_session = self.get_cobbler_session()
        # Create a node via the Provisioning API.
        prov = ProvisioningAPI(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        profile = yield prov.xmlrpc_add_profile("profile", distro)
        node = yield prov.xmlrpc_add_node("node", profile)
        # Delete it again via the Provisioning API.
        yield prov.xmlrpc_delete_node(node)
        # It has gone, checked via the Cobbler session.
        nodes = yield prov.xmlrpc_get_nodes()
        self.assertEqual({}, nodes)

    @inlineCallbacks
    def test_get_nodes(self):
        cobbler_session = self.get_cobbler_session()
        prov = ProvisioningAPI(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        profile = yield prov.xmlrpc_add_profile("profile", distro)
        nodes = yield prov.xmlrpc_get_nodes()
        self.assertEqual({}, nodes)
        # Create some nodes via the Provisioning API.
        expected = {}
        for num in xrange(3):
            name = self.getUniqueString()
            yield prov.xmlrpc_add_node(name, profile)
            expected[name] = {'name': name, 'profile': 'profile'}
        nodes = yield prov.xmlrpc_get_nodes()
        self.assertEqual(expected, nodes)

    @inlineCallbacks
    def test_get_nodes_by_name(self):
        cobbler_session = self.get_cobbler_session()
        prov = ProvisioningAPI(cobbler_session)
        nodes = yield prov.xmlrpc_get_nodes_by_name([])
        self.assertEqual({}, nodes)
        # Create a node via the Provisioning API.
        distro = yield prov.xmlrpc_add_distro("distro", "initrd", "kernel")
        profile = yield prov.xmlrpc_add_profile("profile", distro)
        yield prov.xmlrpc_add_node("alice", profile)
        nodes = yield prov.xmlrpc_get_nodes_by_name(["alice", "bob"])
        # The response contains keys for all systems found.
        self.assertSequenceEqual(["alice"], sorted(nodes))
