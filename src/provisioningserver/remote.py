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
from provisioningserver.interfaces import IProvisioningAPI
from provisioningserver.interfaces import IProvisioningAPI_XMLRPC
from twisted.web.xmlrpc import XMLRPC
from zope.interface import classImplements


class ProvisioningAPI_XMLRPC_Base(XMLRPC, ProvisioningAPI):

    def __init__(self, session):
        XMLRPC.__init__(self, allowNone=True, useDateTime=True)
        ProvisioningAPI.__init__(self, session)


ProvisioningAPI_XMLRPC = type(
    b"ProvisioningAPI_XMLRPC", (ProvisioningAPI_XMLRPC_Base,), {
        "xmlrpc_%s" % name: getattr(ProvisioningAPI, name)
        for name in IProvisioningAPI.names(all=True)
        })

classImplements(ProvisioningAPI, IProvisioningAPI_XMLRPC)
