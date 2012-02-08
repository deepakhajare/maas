# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maasserver.provisioning`."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maastesting import TestCase
from zope.interface import implementer
from zope.interface.verify import verifyObject
from provisioningserver.interfaces import IProvisioningAPI


@implementer(IProvisioningAPI)
class FakeProvisioningAPI:

    def add_distro(self, name, initrd, kernel):
        """ """

    def add_profile(self, name, distro):
        """ """

    def add_node(self, name, profile):
        """ """

    def get_distros_by_name(self, names):
        """ """

    def get_profiles_by_name(self, names):
        """ """

    def get_nodes_by_name(self, names):
        """ """

    def delete_distros_by_name(self, names):
        """ """

    def delete_profiles_by_name(self, names):
        """ """

    def delete_nodes_by_name(self, names):
        """ """

    def get_distros(self):
        """ """

    def get_profiles(self):
        """ """

    def get_nodes(self):
        """ """


class TestFakeProvisioningAPI(TestCase):

    def test_interface(self):
        fake = FakeProvisioningAPI()
        verifyObject(IProvisioningAPI, fake)


class TestSomething(TestCase):

    #resources = [...]

    def test_something(self):
        self.assertTrue(1)
