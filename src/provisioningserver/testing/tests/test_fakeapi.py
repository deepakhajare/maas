# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the fake Provisioning API."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from provisioningserver.testing.fakeapi import FakeAsynchronousProvisioningAPI
from provisioningserver.tests.test_api import TestProvisioningAPI


class TestFakeProvisioningAPI(TestProvisioningAPI):
    """Test :class:`FakeProvisioningAPI`."""

    def get_provisioning_api(self):
        return FakeAsynchronousProvisioningAPI()
