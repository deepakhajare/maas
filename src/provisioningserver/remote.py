# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provisioning API over XML-RPC."""

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
from zope.interface.interface import Method


def export_via_xmlrpc(iface):
    """Class decorator to alias methods of a class with an "xmlrpc_" prefix.

    For each method defined in the given interface, the concrete method in the
    decorated class is copied to a new name of "xmlrpc_%(original_name)s". In
    combination with :class:`XMLRPC`, and the rest of the Twisted stack, this
    has the effect of exposing the method via XML-RPC.

    The decorated class must implement `iface`.
    """
    def decorate(cls):
        assert iface.implementedBy(cls), (
            "%s does not implement %s" % (cls.__name__, iface.__name__))
        for name in iface:
            element = iface[name]
            if isinstance(element, Method):
                method = getattr(cls, name)
                setattr(cls, "xmlrpc_%s" % name, method)
        return cls
    return decorate


@export_via_xmlrpc(IProvisioningAPI)
class ProvisioningAPI_XMLRPC(XMLRPC, ProvisioningAPI):

    implements(IProvisioningAPI_XMLRPC)

    def __init__(self, session):
        XMLRPC.__init__(self, allowNone=True, useDateTime=True)
        ProvisioningAPI.__init__(self, session)
