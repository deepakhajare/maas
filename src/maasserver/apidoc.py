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
    "describe_handler",
    "find_api_handlers",
    "generate_api_docs",
    ]

from inspect import (
    getargspec,
    getdoc,
    )
from itertools import (
    chain,
    izip,
    repeat,
    )
from types import MethodType as instancemethod
from urllib import quote

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
    """Generate serialisable descriptions of arguments."""
    # The end of the defaults list aligns with the end of the args list, hence
    # we pad it with undefined, in order that we can zip it with args later.
    undefined = object()
    if defaults is None:
        defaults = repeat(undefined)
    else:
        defaults = chain(
            repeat(undefined, len(args) - len(defaults)),
            defaults)
    for arg, default in izip(args, defaults):
        if default is undefined:
            yield {"name": arg}
        else:
            yield {"name": arg, "default": default}


def describe_function_args(func):
    """Generate serialisable descriptions of function arguments.

    When describing the API, we ignore varargs and keywords args.
    """
    args, _, _, defaults = getargspec(func)
    # Trim the first arg (self or cls) if it's uninteresting.
    if isinstance(func, (instancemethod, classmethod)):
        args = args[1:]
    return describe_args(args, defaults)


def describe_function(method, func):
    """Return a serialisable description of a handler function."""
    return {"doc": getdoc(func), "method": method}


def describe_operation(method, func, op):
    """Return a serialisable description of a handler operation."""
    description = describe_function(method, func)
    description["args"] = list(describe_function_args(func))
    description["op"] = op
    return description


def describe_handler(handler):
    """Return a serialisable description of a handler.

    :type handler: :class:`BaseHandler` instance that has been decorated by
        `api_operations`.
    """
    # Avoid circular imports.
    from maasserver.api import dispatch_methods

    uri_template = generate_doc(handler).resource_uri_template
    if uri_template is None:
        uri_template = ""

    uri_params = handler.resource_uri()
    assert len(uri_params) <= 2 or uri_params[2] == {}, (
        "Resource URIs with keyword parameters are not yet supported.")
    uri_params = uri_params[1] if len(uri_params) >= 2 else []

    actions = []
    for http_method in handler.allowed_methods:
        if http_method in handler._available_api_methods:
            # Default Piston CRUD method has been overridden; inspect
            # custom operations instead.
            operations = handler._available_api_methods[http_method]
            for op, func in operations.items():
                desc = describe_operation(http_method, func, op)
                desc["uri"] = "%s?op=%s" % (uri_template, quote(desc["op"]))
                desc["uri_params"] = uri_params
                actions.append(desc)
        else:
            # Default Piston CRUD method still stands.
            op = dispatch_methods[http_method]
            func = getattr(handler, op)
            desc = describe_function(http_method, func)
            desc["uri"] = uri_template
            desc["uri_params"] = uri_params
            actions.append(desc)

    return {
        "actions": actions,
        }
