# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provisioning API interfaces."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "IProvisioningAPI",
    "IProvisioningAPI_XMLRPC",
    ]

from inspect import getmembers
from types import MethodType

from zope.interface import Interface
from zope.interface.interface import InterfaceClass


class IProvisioningAPI_Template:
    """A template for building interfaces for the Provisioning API.

    This class is a placeholder for defining attributes and functions that we
    can enumerate when building interfaces.

    The primary use-case is that `IProvisioningAPI_XMLRPC` is related to
    `IProvisioningAPI` by a simple transformation: every method in the latter
    must appear identically in the former, but with `xmlrpc_` prefixed to the
    name.

    Zope's interfaces throw away the original functions, so defining a
    mechanically derived interface in code is not possible (as far as I know).
    The approach taken here allows for mechanically derived interfaces to be
    defined without duplication.
    """

    def add_distro(name, initrd, kernel):
        """ """

    def add_profile(name, distro):
        """ """

    def add_node(name, profile):
        """ """

    def get_distros_by_name(names):
        """ """

    def get_profiles_by_name(names):
        """ """

    def get_nodes_by_name(names):
        """ """

    def delete_distros_by_name(names):
        """ """

    def delete_profiles_by_name(names):
        """ """

    def delete_nodes_by_name(names):
        """ """

    def get_distros():
        """ """

    def get_profiles():
        """ """

    def get_nodes():
        """ """


PAPI_FUNCTIONS = {
    name: value.im_func
    for name, value in getmembers(IProvisioningAPI_Template)
    if not name.startswith("_") and isinstance(value, MethodType)
    }

IProvisioningAPI = InterfaceClass(
    b"IProvisioningAPI", (Interface,), PAPI_FUNCTIONS)


PAPI_XMLRPC_FUNCTIONS = {
    "xmlrpc_%s" % name: value
    for name, value in PAPI_FUNCTIONS.iteritems()
    }

IProvisioningAPI_XMLRPC = InterfaceClass(
    b"IProvisioningAPI_XMLRPC", (Interface,), PAPI_XMLRPC_FUNCTIONS)
