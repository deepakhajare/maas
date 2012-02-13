# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Exceptions."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "MaasException",
    "MaasAPIException",
    "PermissionDenied",
    ]


from piston.utils import rc


class MaasException(Exception):
    """Base class for Maas' exceptions."""


class MaasAPIException(Exception):
    """Base class for Maas' API exceptions.

    :ivar api_error: The HTTP code that should be returned when this error
        is raised in the API (defaults to 500: "Internal Server Error").

    """
    api_error = rc.INTERNAL_ERROR


class PermissionDenied(MaasAPIException):
    api_error = rc.FORBIDDEN


class NodesNotAvailable(MaasAPIException):
    """Requested node(s) are not available to be acquired."""
    # Error code 409: Conflict.  Piston calls it "conflict/duplicate
    # entry" after its most likely cause, but really it can be any
    # resource state where the request can't be satisfied for the
    # moment (typically because of some third-party request).
    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.10
    api_error = rc.DUPLICATE_ENTRY
