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
    "PermissionDenied",
    ]


from piston.utils import rc


class MaasException(Exception):
    """Base class for Maas' exceptions.

    :ivar api_error: The HTTP code that should be returned when this error
        is raised in the API (defaults to 500: "Internal Server Error").

    """
    api_error = rc.INTERNAL_ERROR


class PermissionDenied(MaasException):
    api_error = rc.FORBIDDEN
