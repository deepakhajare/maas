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
    "describe_api",
    "describe_handler",
    "describe_method",
    "find_api_handlers",
    "generate_api_docs",
    ]

from inspect import getargspec
from itertools import (
    chain,
    izip,
    repeat,
    )
from types import MethodType as instancemethod

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


def describe_args(args, defaults):
    """Generate serialisable descriptions of a method's regular arguments.

    When describing the API, we ignore varargs and keywords args.
    """
    # The end of the defaults list aligns with the end of the args list, hence
    # we pad it with undefined, in order that we can zip it with args later.
    undefined = object()
    defaults = chain(
        repeat(undefined, len(args) - len(defaults)),
        defaults)
    for arg, default in izip(args, defaults):
        if default is undefined:
            yield {"name": arg}
        else:
            yield {"name": arg, "default": default}


def describe_method(method_doc):
    """Return a serialisable description of a handler method.

    :type method_doc: :class:`HandlerMethod`
    """
    argspec = getargspec(method_doc.method)
    # Trim the first (self or cls) argument from the argument list if it's an
    # instance method or class method.
    if isinstance(method_doc.method, (instancemethod, classmethod)):
        argspec = argspec._replace(args=argspec.args[1:])
    arguments = describe_args(argspec.args, argspec.defaults)
    return {
        "arguments": list(arguments),
        "documentation": method_doc.doc,
        "name": method_doc.name,
        "signature": method_doc.signature,
        }


def describe_handler(handler_doc):
    """Return a serialisable description of a handler.

    :type handler_doc: :class:`HandlerDocumentation`
    """


def describe_api(docs):
    """Return a serialisable description of an API.

    :type docs: Iterable of :class:`HandlerDocumentation`
    """
