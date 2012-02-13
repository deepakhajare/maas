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
    "MaasAPIBadRequest",
    "MaasAPIException",
    "MaasAPINotFound",
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


class MaasAPIBadRequest(MaasAPIException):
    api_error = rc.BAD_REQUEST


class MaasAPINotFound(MaasAPIException):
    api_error = rc.NOT_FOUND


class PermissionDenied(MaasAPIException):
    api_error = rc.FORBIDDEN

