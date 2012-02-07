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
    ]

from provisioningserver.cobblerclient import (
    CobblerDistro,
    CobblerProfile,
    CobblerSystem,
    )
from twisted.internet.defer import (
    inlineCallbacks,
    returnValue,
    )
from twisted.web.xmlrpc import XMLRPC


class ProvisioningAPI(XMLRPC):

    def __init__(self, session):
        XMLRPC.__init__(self, allowNone=True, useDateTime=True)
        self.session = session

    @inlineCallbacks
    def xmlrpc_add_distro(self, name, initrd, kernel):
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
    def xmlrpc_delete_distro(self, name):
        assert isinstance(name, basestring)
        distros = yield CobblerDistro.find(self.session, name=name)
        for distro in distros:
            yield distro.delete()

    @inlineCallbacks
    def xmlrpc_get_distros(self):
        # WARNING: This could return a *huge* number of results. Consider
        # adding filtering options to this function before using it in anger.
        distros = yield CobblerDistro.get_all_values(self.session)
        returnValue(distros)

    @inlineCallbacks
    def xmlrpc_get_distros_by_name(self, names):
        distros_by_name = {name: None for name in names}
        for name in names:
            distros = yield CobblerDistro.find(self.session, name=name)
            for distro in distros:
                values = yield distro.get_values()
                distros_by_name[distro.name] = values
        returnValue(distros_by_name)

    @inlineCallbacks
    def xmlrpc_add_profile(self, name, distro):
        assert isinstance(name, basestring)
        assert isinstance(distro, basestring)
        profile = yield CobblerProfile.new(
            self.session, name, {"distro": distro})
        returnValue(profile.name)

    @inlineCallbacks
    def xmlrpc_delete_profile(self, name):
        assert isinstance(name, basestring)
        profiles = yield CobblerProfile.find(self.session, name=name)
        for profile in profiles:
            yield profile.delete()

    @inlineCallbacks
    def xmlrpc_get_profiles(self):
        # WARNING: This could return a *huge* number of results. Consider
        # adding filtering options to this function before using it in anger.
        profiles = yield CobblerProfile.get_all_values(self.session)
        returnValue(profiles)

    @inlineCallbacks
    def xmlrpc_add_node(self, name, profile):
        assert isinstance(name, basestring)
        assert isinstance(profile, basestring)
        system = yield CobblerSystem.new(
            self.session, name, {"profile": profile})
        returnValue(system.name)

    @inlineCallbacks
    def xmlrpc_delete_node(self, name):
        assert isinstance(name, basestring)
        systems = yield CobblerSystem.find(self.session, name=name)
        for system in systems:
            yield system.delete()

    @inlineCallbacks
    def xmlrpc_get_nodes(self):
        # WARNING: This could return a *huge* number of results. Consider
        # adding filtering options to this function before using it in anger.
        systems = yield CobblerSystem.get_all_values(self.session)
        returnValue(systems)
