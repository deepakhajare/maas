# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provisioning API for use by the MaaS API server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "ProvisioningAPI",
    "ProvisioningAPI_XMLRPC",
    ]

from provisioningserver.cobblerclient import (
    CobblerDistro,
    CobblerProfile,
    CobblerSystem,
    )
from provisioningserver.interfaces import (
    IProvisioningAPI,
    IProvisioningAPI_XMLRPC,
    )
from twisted.internet.defer import (
    inlineCallbacks,
    returnValue,
    )
from twisted.web.xmlrpc import XMLRPC
from zope.interface import implements


class ProvisioningAPI:

    implements(IProvisioningAPI)

    def __init__(self, session):
        super(ProvisioningAPI, self).__init__()
        self.session = session

    @inlineCallbacks
    def add_distro(self, name, initrd, kernel):
        assert isinstance(name, basestring)
        assert isinstance(initrd, basestring)
        assert isinstance(kernel, basestring)
        distro = yield CobblerDistro.new(
            self.session, name, {
                "initrd": initrd,
                "kernel": kernel,
                })
        returnValue(distro.name)

    @inlineCallbacks
    def add_profile(self, name, distro):
        assert isinstance(name, basestring)
        assert isinstance(distro, basestring)
        profile = yield CobblerProfile.new(
            self.session, name, {"distro": distro})
        returnValue(profile.name)

    @inlineCallbacks
    def add_node(self, name, profile):
        assert isinstance(name, basestring)
        assert isinstance(profile, basestring)
        system = yield CobblerSystem.new(
            self.session, name, {"profile": profile})
        returnValue(system.name)

    @inlineCallbacks
    def get_objects_by_name(self, object_type, names):
        """Get `object_type` objects by name.

        :param object_type: The type of object to look for.
        :type object_type: provisioningserver.objectclient.CobblerObjectType
        :param names: A list of names to search for.
        :type names: list
        """
        objects_by_name = {}
        for name in names:
            objects = yield object_type.find(self.session, name=name)
            for obj in objects:
                values = yield obj.get_values()
                objects_by_name[obj.name] = values
        returnValue(objects_by_name)

    def get_distros_by_name(self, names):
        return self.get_objects_by_name(CobblerDistro, names)

    def get_profiles_by_name(self, names):
        return self.get_objects_by_name(CobblerProfile, names)

    def get_nodes_by_name(self, names):
        return self.get_objects_by_name(CobblerSystem, names)

    @inlineCallbacks
    def delete_objects_by_name(self, object_type, names):
        """Delete `object_type` objects by name.

        :param object_type: The type of object to delete.
        :type object_type: provisioningserver.objectclient.CobblerObjectType
        :param names: A list of names to search for.
        :type names: list
        """
        for name in names:
            objects = yield object_type.find(self.session, name=name)
            for obj in objects:
                yield obj.delete()

    def delete_distros_by_name(self, names):
        return self.delete_objects_by_name(CobblerDistro, names)

    def delete_profiles_by_name(self, names):
        return self.delete_objects_by_name(CobblerProfile, names)

    def delete_nodes_by_name(self, names):
        return self.delete_objects_by_name(CobblerSystem, names)

    @inlineCallbacks
    def get_distros(self):
        # WARNING: This could return a *huge* number of results. Consider
        # adding filtering options to this function before using it in anger.
        distros = yield CobblerDistro.get_all_values(self.session)
        returnValue(distros)

    @inlineCallbacks
    def get_profiles(self):
        # WARNING: This could return a *huge* number of results. Consider
        # adding filtering options to this function before using it in anger.
        profiles = yield CobblerProfile.get_all_values(self.session)
        returnValue(profiles)

    @inlineCallbacks
    def get_nodes(self):
        # WARNING: This could return a *huge* number of results. Consider
        # adding filtering options to this function before using it in anger.
        systems = yield CobblerSystem.get_all_values(self.session)
        returnValue(systems)


class ProvisioningAPI_XMLRPC(XMLRPC):

    implements(IProvisioningAPI_XMLRPC)

    def __init__(self, papi):
        XMLRPC.__init__(self, allowNone=True, useDateTime=True)
        self.papi = papi

    def xmlrpc_add_distro(self, name, initrd, kernel):
        return self.papi.add_distro(name, initrd, kernel)

    def xmlrpc_add_profile(self, name, distro):
        return self.papi.add_profile(name, distro)

    def xmlrpc_add_node(self, name, profile):
        return self.papi.add_node(name, profile)

    def xmlrpc_get_distros_by_name(self, names):
        return self.papi.get_distros_by_name(names)

    def xmlrpc_get_profiles_by_name(self, names):
        return self.papi.get_profiles_by_name(names)

    def xmlrpc_get_nodes_by_name(self, names):
        return self.papi.get_nodes_by_name(names)

    def xmlrpc_delete_distros_by_name(self, names):
        return self.papi.delete_distros_by_name(names)

    def xmlrpc_delete_profiles_by_name(self, names):
        return self.papi.delete_profiles_by_name(names)

    def xmlrpc_delete_nodes_by_name(self, names):
        return self.papi.delete_nodes_by_name(names)

    def xmlrpc_get_distros(self):
        return self.papi.get_distros()

    def xmlrpc_get_profiles(self):
        return self.papi.get_profiles()

    def xmlrpc_get_nodes(self):
        return self.papi.get_nodes()
