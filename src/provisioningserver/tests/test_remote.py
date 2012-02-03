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
from provisioningserver.remote import Provisioning
from provisioningserver.testing.fakecobbler import (
    FakeCobbler,
    FakeTwistedProxy,
    )
from testtools import TestCase
from testtools.deferredruntest import AsynchronousDeferredRunTest
from twisted.internet.defer import inlineCallbacks


class TestProvisioning(TestCase):
    """Tests for `provisioningserver.remote.Provisioning`."""

    run_tests_with = AsynchronousDeferredRunTest

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
        prov = Provisioning(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        self.assertEqual("distro", distro)

    @inlineCallbacks
    def test_add_profile(self):
        cobbler_session = self.get_cobbler_session()
        # Create a profile via the Provisioning API.
        prov = Provisioning(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        profile = yield prov.xmlrpc_add_profile("profile", distro)
        self.assertEqual("profile", profile)

    @inlineCallbacks
    def test_add_node(self):
        cobbler_session = self.get_cobbler_session()
        # Create a system/node via the Provisioning API.
        prov = Provisioning(cobbler_session)
        distro = yield prov.xmlrpc_add_distro(
            "distro", "an_initrd", "a_kernel")
        profile = yield prov.xmlrpc_add_profile("profile", distro)
        node = yield prov.xmlrpc_add_node("node", profile)
        self.assertEqual("node", node)
