# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the fake Provisioning API."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from testtools import TestCase
from zope.interface.verify import verifyObject
from provisioningserver.interfaces import IProvisioningAPI
from provisioningserver.testing.fakeapi import FakeProvisioningAPI


class TestFakeProvisioningAPI(TestCase):
    """Test :class:`FakeProvisioningAPI`."""

    def test_interface(self):
        fake = FakeProvisioningAPI()
        verifyObject(IProvisioningAPI, fake)
