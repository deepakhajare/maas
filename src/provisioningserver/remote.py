# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provisioning API for use by the MaaS API server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from provisioningserver.cobblerclient import CobblerSystem
from twisted.internet.defer import (
    inlineCallbacks,
    returnValue,
    )
from twisted.web.xmlrpc import XMLRPC


class Provisioning(XMLRPC):

    # TODO: make session mandatory.
    def __init__(self, session=None):
        XMLRPC.__init__(self, allowNone=True, useDateTime=True)
        self.session = session

    def xmlrpc_hello(self):
        return "I'm here."

    @inlineCallbacks
    def xmlrpc_add_node(self, name, profile):
        assert isinstance(name, basestring)
        assert isinstance(profile, basestring)
        system = yield CobblerSystem.new(
            self.session, name, {"profile": profile})
        returnValue(system)
