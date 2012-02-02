# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.remote`."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from provisioningserver.remote import Provisioning
from testtools import TestCase
from testtools.deferredruntest import AsynchronousDeferredRunTest


class TestProvisioning(TestCase):

    run_tests_with = AsynchronousDeferredRunTest

    def test_hello(self):
        prov = Provisioning()
        self.assertEqual("I'm here.", prov.xmlrpc_hello())
