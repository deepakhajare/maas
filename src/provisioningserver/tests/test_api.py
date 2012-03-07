# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.api`.

Also tests `provisioningserver.testing.fakeapi`.
"""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from abc import (
    ABCMeta,
    abstractmethod,
    )
from itertools import (
    count,
    islice,
    )
from os import (
    environ,
    path,
    )
from random import randint
from time import time
from unittest import skipIf
from urlparse import urlparse

from fixtures import TempDir
from provisioningserver.api import (
    cobbler_to_papi_distro,
    cobbler_to_papi_node,
    cobbler_to_papi_profile,
    mac_addresses_to_cobbler_deltas,
    postprocess_mapping,
    ProvisioningAPI,
    )
from provisioningserver.cobblerclient import (
    CobblerSession,
    CobblerSystem,
    )
from provisioningserver.interfaces import IProvisioningAPI
from provisioningserver.testing.fakeapi import FakeAsynchronousProvisioningAPI
from provisioningserver.testing.fakecobbler import make_fake_cobbler_session
from testtools import TestCase
from testtools.deferredruntest import AsynchronousDeferredRunTest
from twisted.internet.defer import (
    inlineCallbacks,
    returnValue,
    )
from twisted.web.xmlrpc import Fault
from zope.interface.verify import verifyObject


def touch(filename, content=b""):
    """Create `filename` with `content`."""
    with open(filename, "ab") as stream:
        stream.write(content)
    return filename


random_octet = lambda: randint(0, 255)
random_octets = iter(random_octet, None)


def fake_mac_address():
    """Return a random MAC address."""
    octets = islice(random_octets, 6)
    return ":".join(format(octet, "02x") for octet in octets)


class TestFunctions(TestCase):
    """Tests for the free functions in `provisioningserver.api`."""

    def test_postprocess_mapping(self):
        data = {
            "sad": "wings",
            "of": "destiny",
            }
        expected = {
            "sad": "Wings",
            "of": "Destiny",
            }
        observed = postprocess_mapping(data, unicode.capitalize)
        self.assertEqual(expected, observed)

    def test_cobbler_to_papi_node(self):
        data = {
            "name": "iced",
            "profile": "earth",
            "interfaces": {
                "eth0": {"mac_address": "12:34:56:78:9a:bc"},
                },
            "ju": "nk",
            }
        expected = {
            "name": "iced",
            "profile": "earth",
            "mac_addresses": ["12:34:56:78:9a:bc"],
            }
        observed = cobbler_to_papi_node(data)
        self.assertEqual(expected, observed)

    def test_cobbler_to_papi_node_without_interfaces(self):
        data = {
            "name": "iced",
            "profile": "earth",
            "ju": "nk",
            }
        expected = {
            "name": "iced",
            "profile": "earth",
            "mac_addresses": [],
            }
        observed = cobbler_to_papi_node(data)
        self.assertEqual(expected, observed)

    def test_cobbler_to_papi_profile(self):
        data = {
            "name": "paradise",
            "distro": "lost",
            "draconian": "times",
            }
        expected = {
            "name": "paradise",
            "distro": "lost",
            }
        observed = cobbler_to_papi_profile(data)
        self.assertEqual(expected, observed)

    def test_cobbler_to_papi_distro(self):
        data = {
            "name": "strapping",
            "initrd": "young",
            "kernel": "lad",
            "alien": "city",
            }
        expected = {
            "name": "strapping",
            "initrd": "young",
            "kernel": "lad",
            }
        observed = cobbler_to_papi_distro(data)
        self.assertEqual(expected, observed)


class TestInterfaceDeltas(TestCase):

    def test_mac_addresses_to_cobbler_deltas_set_1(self):
        current_interfaces = {
            "eth0": {
                "mac_address": "",
                },
            }
        mac_addresses_desired = ["12:34:56:78:90:12"]
        expected = [
            {"interface": "eth0",
             "mac_address": "12:34:56:78:90:12"},
            ]
        observed = list(
            mac_addresses_to_cobbler_deltas(
                current_interfaces, mac_addresses_desired))
        self.assertEqual(expected, observed)

    def test_mac_addresses_to_cobbler_deltas_set_2(self):
        current_interfaces = {
            "eth0": {
                "mac_address": "",
                },
            }
        mac_addresses_desired = [
            "11:11:11:11:11:11", "22:22:22:22:22:22"]
        expected = [
            {"interface": "eth0",
             "mac_address": "11:11:11:11:11:11"},
            {"interface": "eth1",
             "mac_address": "22:22:22:22:22:22"},
            ]
        observed = list(
            mac_addresses_to_cobbler_deltas(
                current_interfaces, mac_addresses_desired))
        self.assertEqual(expected, observed)

    def test_mac_addresses_to_cobbler_deltas_remove_1(self):
        current_interfaces = {
            "eth0": {
                "mac_address": "11:11:11:11:11:11",
                },
            "eth1": {
                "mac_address": "22:22:22:22:22:22",
                },
            }
        mac_addresses_desired = ["22:22:22:22:22:22"]
        expected = [
            {"interface": "eth0",
             "delete_interface": True},
            ]
        observed = list(
            mac_addresses_to_cobbler_deltas(
                current_interfaces, mac_addresses_desired))
        self.assertEqual(expected, observed)

    def test_mac_addresses_to_cobbler_deltas_set_1_remove_1(self):
        current_interfaces = {
            "eth0": {
                "mac_address": "11:11:11:11:11:11",
                },
            "eth1": {
                "mac_address": "22:22:22:22:22:22",
                },
            }
        mac_addresses_desired = [
            "22:22:22:22:22:22", "33:33:33:33:33:33"]
        expected = [
            {"interface": "eth0",
             "delete_interface": True},
            {"interface": "eth0",
             "mac_address": "33:33:33:33:33:33"},
            ]
        observed = list(
            mac_addresses_to_cobbler_deltas(
                current_interfaces, mac_addresses_desired))
        self.assertEqual(expected, observed)


class ProvisioningAPITestScenario:
    """Tests for `provisioningserver.api.ProvisioningAPI`.

    Abstract base class.  To exercise these tests, derive a test case from
    this class as well as from TestCase.  Provide it with a
    get_provisioning_api method that returns a ProvisioningAPI implementation
    that you want to test against.
    """

    __metaclass__ = ABCMeta

    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=5)

    @abstractmethod
    def get_provisioning_api(self):
        """Create a real, or faked, ProvisoningAPI to run tests against.

        Override this in the test case that exercises this scenario.
        """

    # TODO: Move this to module scope.
    def fake_metadata(self):
        """Produce fake metadata parameters for adding a node."""
        return {
            'maas-metadata-url': 'http://localhost:8000/metadata/',
            'maas-metadata-credentials': 'Fake metadata credentials',
        }

    names = ("test-%d" % num for num in count(int(time())))

    @inlineCallbacks
    def add_distro(self, papi):
        """Creates a new distro object via `papi`.

        Arranges for it to be deleted during test clean-up.
        """
        tempdir = self.useFixture(TempDir()).path
        initrd = path.join(tempdir, "initrd")
        touch(initrd, b"An example initrd for the benefit of Cobbler.")
        kernel = path.join(tempdir, "kernel")
        touch(kernel, b"An example kernel for the benefit of Cobbler.")
        distro_name = yield papi.add_distro(next(self.names), initrd, kernel)

        def cleanup():
            d = papi.delete_distros_by_name([distro_name])
            d.addErrback(lambda failure: failure.trap(Fault))
            return d

        self.addCleanup(cleanup)
        returnValue(distro_name)

    @inlineCallbacks
    def add_profile(self, papi, distro_name=None):
        """Creates a new profile object via `papi`.

        Arranges for it to be deleted during test clean-up. If `distro_name`
        is not specified, one will be obtained by calling `add_distro`.
        """
        if distro_name is None:
            distro_name = yield self.add_distro(papi)
        profile_name = yield papi.add_profile(next(self.names), distro_name)

        def cleanup():
            d = papi.delete_profiles_by_name([profile_name])
            d.addErrback(lambda failure: failure.trap(Fault))
            return d

        self.addCleanup(cleanup)
        returnValue(profile_name)

    @inlineCallbacks
    def add_node(self, papi, profile_name=None, metadata=None):
        """Creates a new node object via `papi`.

        Arranges for it to be deleted during test clean-up. If `profile_name`
        is not specified, one will be obtained by calling `add_profile`. If
        `metadata` is not specified, it will be obtained by calling
        `fake_metadata`.
        """
        if profile_name is None:
            profile_name = yield self.add_profile(papi)
        if metadata is None:
            metadata = self.fake_metadata()
        node_name = yield papi.add_node(
            next(self.names), profile_name, metadata)

        def cleanup():
            d = papi.delete_nodes_by_name([node_name])
            d.addErrback(lambda failure: failure.trap(Fault))
            return d

        self.addCleanup(cleanup)
        returnValue(node_name)

    def test_ProvisioningAPI_interfaces(self):
        papi = self.get_provisioning_api()
        verifyObject(IProvisioningAPI, papi)

    @inlineCallbacks
    def test_add_distro(self):
        # Create a distro via the Provisioning API.
        papi = self.get_provisioning_api()
        distro_name = yield self.add_distro(papi)
        distros = yield papi.get_distros_by_name([distro_name])
        self.assertEqual([distro_name], sorted(distros))

    @inlineCallbacks
    def test_add_profile(self):
        # Create a profile via the Provisioning API.
        papi = self.get_provisioning_api()
        profile_name = yield self.add_profile(papi)
        profiles = yield papi.get_profiles_by_name([profile_name])
        self.assertEqual([profile_name], sorted(profiles))

    @inlineCallbacks
    def test_add_node(self):
        # Create a system/node via the Provisioning API.
        papi = self.get_provisioning_api()
        node_name = yield self.add_node(papi)
        nodes = yield papi.get_nodes_by_name([node_name])
        self.assertEqual([node_name], sorted(nodes))

    @inlineCallbacks
    def test_modify_distros(self):
        papi = self.get_provisioning_api()
        distro_name = yield self.add_distro(papi)
        tempdir = self.useFixture(TempDir()).path
        initrd_new = path.join(tempdir, "initrd")
        kernel_new = path.join(tempdir, "initrd")
        yield papi.modify_distros(
            {distro_name: {
                    "initrd": touch(initrd_new),
                    "kernel": touch(kernel_new),
                    }})
        values = yield papi.get_distros_by_name([distro_name])
        self.assertEqual(initrd_new, values[distro_name]["initrd"])
        self.assertEqual(kernel_new, values[distro_name]["kernel"])

    @inlineCallbacks
    def test_modify_profiles(self):
        papi = self.get_provisioning_api()
        distro1_name = yield self.add_distro(papi)
        distro2_name = yield self.add_distro(papi)
        profile_name = yield self.add_profile(papi, distro1_name)
        yield papi.modify_profiles({profile_name: {"distro": distro2_name}})
        values = yield papi.get_profiles_by_name([profile_name])
        self.assertEqual(distro2_name, values[profile_name]["distro"])

    @inlineCallbacks
    def test_modify_nodes(self):
        papi = self.get_provisioning_api()
        distro_name = yield self.add_distro(papi)
        profile1_name = yield self.add_profile(papi, distro_name)
        profile2_name = yield self.add_profile(papi, distro_name)
        node_name = yield self.add_node(papi, profile1_name)
        yield papi.modify_nodes({node_name: {"profile": profile2_name}})
        values = yield papi.get_nodes_by_name([node_name])
        self.assertEqual(profile2_name, values[node_name]["profile"])

    @inlineCallbacks
    def test_modify_nodes_set_mac_addresses(self):
        papi = self.get_provisioning_api()
        node_name = yield self.add_node(papi)
        mac_address = fake_mac_address()
        yield papi.modify_nodes(
            {node_name: {"mac_addresses": [mac_address]}})
        values = yield papi.get_nodes_by_name([node_name])
        self.assertEqual(
            [mac_address], values[node_name]["mac_addresses"])

    @inlineCallbacks
    def test_modify_nodes_remove_mac_addresses(self):
        papi = self.get_provisioning_api()
        node_name = yield self.add_node(papi)
        mac_address1 = fake_mac_address()
        mac_address2 = fake_mac_address()
        mac_addresses_from = [mac_address1, mac_address2]
        mac_addresses_to = [mac_address2]
        yield papi.modify_nodes(
            {node_name: {"mac_addresses": mac_addresses_from}})
        yield papi.modify_nodes(
            {node_name: {"mac_addresses": mac_addresses_to}})
        values = yield papi.get_nodes_by_name([node_name])
        self.assertEqual(
            [mac_address2], values[node_name]["mac_addresses"])

    @inlineCallbacks
    def test_delete_distros_by_name(self):
        # Create a distro via the Provisioning API.
        papi = self.get_provisioning_api()
        distro_name = yield self.add_distro(papi)
        # Delete it again via the Provisioning API.
        yield papi.delete_distros_by_name([distro_name])
        # It has gone, checked via the Cobbler session.
        distros = yield papi.get_distros_by_name([distro_name])
        self.assertEqual({}, distros)

    @inlineCallbacks
    def test_delete_profiles_by_name(self):
        # Create a profile via the Provisioning API.
        papi = self.get_provisioning_api()
        profile = yield self.add_profile(papi)
        # Delete it again via the Provisioning API.
        yield papi.delete_profiles_by_name([profile])
        # It has gone, checked via the Cobbler session.
        profiles = yield papi.get_profiles_by_name([profile])
        self.assertEqual({}, profiles)

    @inlineCallbacks
    def test_delete_nodes_by_name(self):
        # Create a node via the Provisioning API.
        papi = self.get_provisioning_api()
        node = yield self.add_node(papi)
        # Delete it again via the Provisioning API.
        yield papi.delete_nodes_by_name([node])
        # It has gone, checked via the Cobbler session.
        nodes = yield papi.get_nodes_by_name([node])
        self.assertEqual({}, nodes)

    @inlineCallbacks
    def test_get_distros(self):
        papi = self.get_provisioning_api()
        distros_before = yield papi.get_distros()
        # Create some distros via the Provisioning API.
        distros_expected = set()
        for num in range(3):
            distro_name = yield self.add_distro(papi)
            distros_expected.add(distro_name)
        distros_after = yield papi.get_distros()
        distros_created = set(distros_after) - set(distros_before)
        self.assertSetEqual(distros_expected, distros_created)

    @inlineCallbacks
    def test_get_profiles(self):
        papi = self.get_provisioning_api()
        distro_name = yield self.add_distro(papi)
        profiles_before = yield papi.get_profiles()
        # Create some profiles via the Provisioning API.
        profiles_expected = set()
        for num in range(3):
            profile_name = yield self.add_profile(papi, distro_name)
            profiles_expected.add(profile_name)
        profiles_after = yield papi.get_profiles()
        profiles_created = set(profiles_after) - set(profiles_before)
        self.assertSetEqual(profiles_expected, profiles_created)

    @inlineCallbacks
    def test_get_nodes_returns_all_nodes(self):
        papi = self.get_provisioning_api()
        profile_name = yield self.add_profile(papi)
        node_names = set()
        for num in range(3):
            node_name = yield self.add_node(papi, profile_name)
            node_names.add(node_name)
        nodes = yield papi.get_nodes()
        self.assertSetEqual(node_names, node_names.intersection(nodes))

    @inlineCallbacks
    def test_get_nodes_includes_node_attributes(self):
        papi = self.get_provisioning_api()
        node_name = yield self.add_node(papi)
        nodes = yield papi.get_nodes()
        self.assertIn(node_name, nodes)
        self.assertIn('name', nodes[node_name])
        self.assertIn('profile', nodes[node_name])
        self.assertIn('mac_addresses', nodes[node_name])

    @inlineCallbacks
    def test_get_nodes_by_name(self):
        papi = self.get_provisioning_api()
        nodes = yield papi.get_nodes_by_name([])
        self.assertEqual({}, nodes)
        # Create a node via the Provisioning API.
        node_name = yield self.add_node(papi)
        nodes = yield papi.get_nodes_by_name([node_name])
        # The response contains keys for all systems found.
        self.assertSequenceEqual([node_name], sorted(nodes))

    @inlineCallbacks
    def test_get_distros_by_name(self):
        papi = self.get_provisioning_api()
        distros = yield papi.get_distros_by_name([])
        self.assertEqual({}, distros)
        # Create a distro via the Provisioning API.
        distro_name = yield self.add_distro(papi)
        distros = yield papi.get_distros_by_name([distro_name])
        # The response contains keys for all distributions found.
        self.assertSequenceEqual([distro_name], sorted(distros))

    @inlineCallbacks
    def test_get_profiles_by_name(self):
        papi = self.get_provisioning_api()
        profiles = yield papi.get_profiles_by_name([])
        self.assertEqual({}, profiles)
        # Create a profile via the Provisioning API.
        profile_name = yield self.add_profile(papi)
        profiles = yield papi.get_profiles_by_name([profile_name])
        # The response contains keys for all profiles found.
        self.assertSequenceEqual([profile_name], sorted(profiles))

    @inlineCallbacks
    def test_stop_nodes(self):
        papi = self.get_provisioning_api()
        node_name = yield self.add_node(papi)
        yield papi.stop_nodes([node_name])
        # The test is that we get here without error.
        pass

    @inlineCallbacks
    def test_start_nodes(self):
        papi = self.get_provisioning_api()
        node_name = yield self.add_node(papi)
        yield papi.start_nodes([node_name])
        # The test is that we get here without error.
        pass


class TestProvisioningAPI(ProvisioningAPITestScenario, TestCase):
    """Test :class:`ProvisioningAPI`.

    Includes by inheritance all the tests in ProvisioningAPITestScenario.
    """

    def get_provisioning_api(self):
        """Return a real ProvisioningAPI, but using a fake Cobbler session."""
        return ProvisioningAPI(make_fake_cobbler_session())

    @inlineCallbacks
    def test_add_node_preseeds_metadata(self):
        papi = self.get_provisioning_api()
        metadata = self.fake_metadata()
        node_name = yield self.add_node(papi, metadata=metadata)

        attrs = yield CobblerSystem(papi.session, node_name).get_values()
        preseed = attrs['ks_meta']['MAAS_PRESEED']
        self.assertIn(metadata['maas-metadata-url'], preseed)
        self.assertIn(metadata['maas-metadata-credentials'], preseed)


class TestFakeProvisioningAPI(ProvisioningAPITestScenario, TestCase):
    """Test :class:`FakeAsynchronousProvisioningAPI`.

    Includes by inheritance all the tests in ProvisioningAPITestScenario.
    """

    def get_provisioning_api(self):
        """Return a fake ProvisioningAPI."""
        return FakeAsynchronousProvisioningAPI()


TEST_COBBLER_URL = environ.get("TEST_COBBLER_URL")


class TestProvisioningAPILocal(ProvisioningAPITestScenario, TestCase):
    """Test :class:`ProvisioningAPI` with a local Cobbler instance.

    Includes by inheritance all the tests in ProvisioningAPITestScenario.
    """

    def setUp(self):
        super(TestProvisioningAPILocal, self).setUp()

    @skipIf(
        TEST_COBBLER_URL is None,
        "Set TEST_COBBLER_URL to the URL for a Cobbler "
        "instance to test against, e.g. http://username"
        ":test@localhost/cobbler_api. Warning: this "
        "will modify your Cobbler database.")
    def get_provisioning_api(self):
        """Return a real ProvisioningAPI connected to the local Cobbler.

        It assumes that the user/pass is `$LOGNAME/test`.
        """
        urlparts = urlparse(TEST_COBBLER_URL)
        cobbler_session = CobblerSession(
            urlparts.geturl(), urlparts.username, urlparts.password)
        return ProvisioningAPI(cobbler_session)
