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


class TestProvisioning(TestCase):
    """Tests for `provisioningserver.remote.Provisioning`."""

    run_tests_with = AsynchronousDeferredRunTest

    def test_hello(self):
        prov = Provisioning()
        self.assertEqual("I'm here.", prov.xmlrpc_hello())

    def test_add_node(self):
        cobbler_session = CobblerSession(
            "http://localhost/does/not/exist", "user", "password")
        cobbler_fake = FakeCobbler({"user": "password"})
        cobbler_proxy = FakeTwistedProxy(cobbler_fake)
        cobbler_session.proxy = cobbler_proxy
        prov = Provisioning(cobbler_session)
        return prov.xmlrpc_add_node()
