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
from maastesting import TestCase
from provisioningserver.testing.fakeapi import FakeSynchronousProvisioningAPI


class TestProvisioning(TestCase):

    def patch_in_fake_papi(self):
        papi_fake = FakeSynchronousProvisioningAPI()
        patch = MonkeyPatch(
            "maasserver.provisioning.get_provisioning_api_proxy",
            lambda: papi_fake)
        self.useFixture(patch)
        return papi_fake

    def test_patch_in_fake_papi(self):
        papi = provisioning.get_provisioning_api_proxy()
        papi_fake = self.patch_in_fake_papi()
        self.assertIsNot(provisioning.get_provisioning_api_proxy(), papi)
        self.assertIs(provisioning.get_provisioning_api_proxy(), papi_fake)
