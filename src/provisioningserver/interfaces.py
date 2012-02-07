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


class ProvisioningAPIBase:
    # TODO: Flesh this out.

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
    for name, value in getmembers(ProvisioningAPIBase)
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
