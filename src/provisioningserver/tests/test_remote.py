# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.remote`."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from provisioningserver.cobblerclient import (
    CobblerSession,
    CobblerSystem,
    )
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

    def test_hello(self):
        prov = Provisioning()
        self.assertEqual("I'm here.", prov.xmlrpc_hello())

    def get_cobbler_session(self):
        cobbler_session = CobblerSession(
            "http://localhost/does/not/exist", "user", "password")
        cobbler_fake = FakeCobbler({"user": "password"})
        cobbler_proxy = FakeTwistedProxy(cobbler_fake)
        cobbler_session.proxy = cobbler_proxy
        return cobbler_session

    @inlineCallbacks
    def test_add_node(self):
        cobbler_session = self.get_cobbler_session()
        prov = Provisioning(cobbler_session)
        node = yield prov.xmlrpc_add_node("system")
        self.assertIsInstance(node, CobblerSystem)
        self.assertEqual("system", node.name)
        self.assertIs(cobbler_session, node.session)
