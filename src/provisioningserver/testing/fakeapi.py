# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Fake Provisioning API."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "FakeProvisioningAPI",
    ]

from maastesting import TestCase
from zope.interface import implementer
from zope.interface.verify import verifyObject
from provisioningserver.interfaces import IProvisioningAPI


class FakeProvisioningDatabase(dict):

    def __missing__(self, key):
        self[key] = {"name": key}
        return self[key]

    def select(self, keys):
        """Select a subset of this mapping."""
        keys = frozenset(keys)
        return {
            key: value
            for key, value in self.iteritems()
            if key in keys
            }

    def delete(self, keys):
        """Delete a subset of this mapping."""
        for key in keys:
            if key in self:
                del self[key]

    def duplicate(self):
        """Duplicate this mapping.

        Keys are assumed to be immutable, and values are assumed to have a
        `copy` method, like a `dict` for example.
        """
        return {
            key: value.copy()
            for key, value in self.iteritems()
            }


@implementer(IProvisioningAPI)
class FakeProvisioningAPI:

    def __init__(self):
        super(FakeProvisioningAPI, self).__init__()
        self.distros = FakeProvisioningDatabase()
        self.profiles = FakeProvisioningDatabase()
        self.nodes = FakeProvisioningDatabase()

    def add_distro(self, name, initrd, kernel):
        self.distros[name]["initrd"] = initrd
        self.distros[name]["kernel"] = kernel

    def add_profile(self, name, distro):
        self.profiles[name]["distro"] = distro

    def add_node(self, name, profile):
        self.nodes[name]["profile"] = profile

    def get_distros_by_name(self, names):
        return self.distros.select(names)

    def get_profiles_by_name(self, names):
        return self.profiles.select(names)

    def get_nodes_by_name(self, names):
        return self.nodes.select(names)

    def delete_distros_by_name(self, names):
        return self.distros.delete(names)

    def delete_profiles_by_name(self, names):
        return self.profiles.delete(names)

    def delete_nodes_by_name(self, names):
        return self.nodes.delete(names)

    def get_distros(self):
        return self.distros.duplicate()

    def get_profiles(self):
        return self.profiles.duplicate()

    def get_nodes(self):
        return self.nodes.duplicate()


class TestFakeProvisioningAPI(TestCase):

    def test_interface(self):
        fake = FakeProvisioningAPI()
        verifyObject(IProvisioningAPI, fake)
