# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provisioning API for use by the MaaS API server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from twisted.web.xmlrpc import XMLRPC


class Provisioning(XMLRPC):

    # TODO: make session mandatory.
    def __init__(self, session=None):
        XMLRPC.__init__(self)
        self.session = session

    def xmlrpc_hello(self):
        return "I'm here."

    def xmlrpc_add_node(self):
        return self.session.call(
            "new_system", self.session.token_placeholder)
