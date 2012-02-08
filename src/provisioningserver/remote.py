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

from provisioningserver.api import ProvisioningAPI
from provisioningserver.interfaces import (
    IProvisioningAPI,
    IProvisioningAPI_XMLRPC,
    )
from twisted.web.xmlrpc import XMLRPC
from zope.interface import implements


class ProvisioningAPI_XMLRPC(XMLRPC, ProvisioningAPI):

    implements(IProvisioningAPI_XMLRPC)

    def __init__(self, session):
        XMLRPC.__init__(self, allowNone=True, useDateTime=True)
        ProvisioningAPI.__init__(self, session)

# Add an xmlrpc_* method for each function defined in IProvisioningAPI.
for name in IProvisioningAPI.names(all=True):
    method = getattr(ProvisioningAPI, name)
    setattr(ProvisioningAPI_XMLRPC, "xmlrpc_%s" % name, method)
