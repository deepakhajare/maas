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
    def xmlrpc_get_distros(self):
        distros = yield CobblerDistro.find(self.session)
        returnValue(sorted(distro.name for distro in distros))

    @inlineCallbacks
    def xmlrpc_add_profile(self, name, distro):
        assert isinstance(name, basestring)
        assert isinstance(distro, basestring)
        profile = yield CobblerProfile.new(
            self.session, name, {"distro": distro})
        returnValue(profile.name)

    @inlineCallbacks
    def xmlrpc_get_profiles(self):
        profiles = yield CobblerProfile.find(self.session)
        returnValue(sorted(profile.name for profile in profiles))

    @inlineCallbacks
    def xmlrpc_add_node(self, name, profile):
        assert isinstance(name, basestring)
        assert isinstance(profile, basestring)
        system = yield CobblerSystem.new(
            self.session, name, {"profile": profile})
        returnValue(system.name)

    @inlineCallbacks
    def xmlrpc_get_nodes(self):
        systems = yield CobblerSystem.find(self.session)
        returnValue(sorted(system.name for system in systems))
