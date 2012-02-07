# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provisioning API for use by the MaaS API server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "ProvisioningAPI_XMLRPC",
    ]

from provisioningserver.interfaces import IProvisioningAPI_XMLRPC
from twisted.web.xmlrpc import XMLRPC
from zope.interface import implements


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
