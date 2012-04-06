# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""MAAS components management."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "discard_persistent_error",
    "get_persistent_errors",
    "PERSISTENT_COMPONENTS_ERRORS",
    "persistent_error_sensor",
    "register_persistent_error",
    ]

from collections import Sequence
import threading


PERSISTENT_COMPONENTS_ERRORS = {
    'provisioning_server_error': """
        The provisioning server is failing.
        """,
    'cobbler_server_error': """
        Cobbler is failing.
        """,
    'maas-import-isos_error': """
        The maas-import-isos script appears not to have been run.
        """,
}

# Persistent errors are global to a MAAS instance.
_PERSISTENT_ERRORS = set()


_PERSISTENT_ERRORS_LOCK = threading.Lock()


def register_persistent_error(error_code):
    with _PERSISTENT_ERRORS_LOCK:
        global _PERSISTENT_ERRORS
        _PERSISTENT_ERRORS.add(error_code)


def discard_persistent_error(error_code):
    with _PERSISTENT_ERRORS_LOCK:
        global _PERSISTENT_ERRORS
        _PERSISTENT_ERRORS.discard(error_code)


def get_persistent_errors():
    for error_code in _PERSISTENT_ERRORS:
        yield PERSISTENT_COMPONENTS_ERRORS[error_code]


def persistent_error_sensor(exceptions, error_code):
    """A method decorator used to report if the decorated method ran
    successfully or raised an exception.  In case of success,
    the permanent error corresponding to error_code will be discarded if it
    was previously registered; if one of the exceptions in 'exceptions' is
    raised, the permanent error corresponding to error_code will be
    registered.
    """
    if not isinstance(exceptions, Sequence):
        exceptions = (exceptions, )

    def wrapper(func):
        def _wrapper(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
                discard_persistent_error(error_code)
                return res
            except exceptions:
                register_persistent_error(error_code)
                raise
        return _wrapper
    return wrapper
