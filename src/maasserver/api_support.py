# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Supporting infrastructure for Piston-based APIs in MAAS."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'AnonymousOperationsHandler',
    'get_list_from_dict_or_multidict',
    'get_mandatory_param',
    'get_optional_list',
    'get_overrided_query_dict',
    'operation',
    'OperationsHandler',
    ]

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    )
from django.http import (
    HttpResponseBadRequest,
    QueryDict,
    )
from formencode.validators import Invalid
from piston.handler import (
    AnonymousBaseHandler,
    BaseHandler,
    HandlerMetaClass,
    )
from piston.resource import Resource


class OperationsResource(Resource):
    """A resource supporting operation dispatch.

    All requests are passed onto the handler's `dispatch` method. See
    :class:`OperationsHandler`.
    """

    crudmap = Resource.callmap
    callmap = dict.fromkeys(crudmap, "dispatch")


class RestrictedResource(OperationsResource):
    """A resource that's restricted to active users."""

    def authenticate(self, request, rm):
        actor, anonymous = super(
            RestrictedResource, self).authenticate(request, rm)
        if not anonymous and not request.user.is_active:
            raise PermissionDenied("User is not allowed access to this API.")
        else:
            return actor, anonymous


class AdminRestrictedResource(RestrictedResource):
    """A resource that's restricted to administrators."""

    def authenticate(self, request, rm):
        actor, anonymous = super(
            AdminRestrictedResource, self).authenticate(request, rm)
        if anonymous or not request.user.is_superuser:
            raise PermissionDenied("User is not allowed access to this API.")
        else:
            return actor, anonymous


def operation(idempotent, exported_as=None):
    """Decorator to make a method available on the API.

    :param idempotent: If this operation is idempotent. Idempotent operations
        are made available via HTTP GET, non-idempotent operations via HTTP
        POST.
    :param exported_as: Optional operation name; defaults to the name of the
        exported method.
    """
    method = "GET" if idempotent else "POST"

    def _decorator(func):
        if exported_as is None:
            func.export = method, func.__name__
        else:
            func.export = method, exported_as
        return func

    return _decorator


class OperationsHandlerType(HandlerMetaClass):
    """Type for handlers that dispatch operations.

    Collects all the exported operations, CRUD and custom, into the class's
    `exports` attribute. This is a signature:function mapping, where signature
    is an (http-method, operation-name) tuple. If operation-name is None, it's
    a CRUD method.

    The `allowed_methods` attribute is calculated as the union of all HTTP
    methods required for the exported CRUD and custom operations.
    """

    def __new__(metaclass, name, bases, namespace):
        cls = super(OperationsHandlerType, metaclass).__new__(
            metaclass, name, bases, namespace)

        # Create a signature:function mapping for CRUD operations.
        crud = {
            (http_method, None): getattr(cls, method)
            for http_method, method in OperationsResource.crudmap.items()
            if getattr(cls, method, None) is not None
            }

        # Create a signature:function mapping for non-CRUD operations.
        operations = {
            attribute.export: attribute
            for attribute in vars(cls).values()
            if getattr(attribute, "export", None) is not None
            }

        # Create the exports mapping.
        exports = {}
        exports.update(crud)
        exports.update(operations)

        # Update the class.
        cls.exports = exports
        cls.allowed_methods = frozenset(
            http_method for http_method, name in exports)

        return cls


class OperationsHandlerMixin:
    """Handler mixin for operations dispatch.

    This enabled dispatch to custom functions that piggyback on HTTP methods
    that ordinarily, in Piston, are used for CRUD operations.

    This must be used in cooperation with :class:`OperationsResource` and
    :class:`OperationsHandlerType`.
    """

    def dispatch(self, request, *args, **kwargs):
        signature = request.method.upper(), request.REQUEST.get("op")
        function = self.exports.get(signature)
        if function is None:
            return HttpResponseBadRequest(
                "Unrecognised signature: %s %s" % signature)
        else:
            return function(self, request, *args, **kwargs)


class OperationsHandler(
    OperationsHandlerMixin, BaseHandler):
    """Base handler that supports operation dispatch."""

    __metaclass__ = OperationsHandlerType


class AnonymousOperationsHandler(
    OperationsHandlerMixin, AnonymousBaseHandler):
    """Anonymous base handler that supports operation dispatch."""

    __metaclass__ = OperationsHandlerType


def get_mandatory_param(data, key, validator=None):
    """Get the parameter from the provided data dict or raise a ValidationError
    if this parameter is not present.

    :param data: The data dict (usually request.data or request.GET where
        request is a django.http.HttpRequest).
    :param data: dict
    :param key: The parameter's key.
    :type key: basestring
    :param validator: An optional validator that will be used to validate the
         retrieved value.
    :type validator: formencode.validators.Validator
    :return: The value of the parameter.
    :raises: ValidationError
    """
    value = data.get(key, None)
    if value is None:
        raise ValidationError("No provided %s!" % key)
    if validator is not None:
        try:
            return validator.to_python(value)
        except Invalid, e:
            raise ValidationError("Invalid %s: %s" % (key, e.msg))
    else:
        return value


def get_optional_list(data, key, default=None):
    """Get the list from the provided data dict or return a default value.
    """
    value = data.getlist(key)
    if value == []:
        return default
    else:
        return value


def get_list_from_dict_or_multidict(data, key, default=None):
    """Get a list from 'data'.

    If data is a MultiDict, then we use 'getlist' if the data is a plain dict,
    then we just use __getitem__.

    The rationale is that data POSTed as multipart/form-data gets parsed into a
    MultiDict, but data POSTed as application/json gets parsed into a plain
    dict(key:list).
    """
    getlist = getattr(data, 'getlist', None)
    if getlist is not None:
        return getlist(key, default)
    return data.get(key, default)


def get_overrided_query_dict(defaults, data):
    """Returns a QueryDict with the values of 'defaults' overridden by the
    values in 'data'.

    :param defaults: The dictionary containing the default values.
    :type defaults: dict
    :param data: The data used to override the defaults.
    :type data: :class:`django.http.QueryDict`
    :return: The updated QueryDict.
    :raises: :class:`django.http.QueryDict`
    """
    # Create a writable query dict.
    new_data = QueryDict('').copy()
    # Missing fields will be taken from the node's current values.  This
    # is to circumvent Django's ModelForm (form created from a model)
    # default behaviour that requires all the fields to be defined.
    new_data.update(defaults)
    # We can't use update here because data is a QueryDict and 'update'
    # does not replaces the old values with the new as one would expect.
    for k, v in data.items():
        new_data[k] = v
    return new_data
