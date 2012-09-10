# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""..."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "find_api_handlers",
    "generate_api_docs",
    ]

from piston.doc import generate_doc
from piston.handler import HandlerMetaClass


def find_api_handlers(module):
    """Find the API handlers defined in `module`.

    Handlers are of type :class:`HandlerMetaClass`.

    :rtype: Generator, yielding handlers.
    """
    try:
        names = module.__all__
    except AttributeError:
        names = sorted(
            name for name in dir(module)
            if not name.startswith("_"))
    for name in names:
        candidate = getattr(module, name)
        if isinstance(candidate, HandlerMetaClass):
            yield candidate


def generate_api_docs(handlers):
    """Generate ReST documentation objects for the ReST API.

    Yields Piston Documentation objects describing the current registered
    handlers.

    This also ensures that handlers define 'resource_uri' methods. This is
    easily forgotten and essential in order to generate proper documentation.

    :rtype: :class:`...`
    """
    sentinel = object()
    for handler in handlers:
        if getattr(handler, "resource_uri", sentinel) is sentinel:
            raise AssertionError(
                "Missing resource_uri in %s" % handler.__name__)
        yield generate_doc(handler)
