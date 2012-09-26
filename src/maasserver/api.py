# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Restful MAAS API.

This is the documentation for the API that lets you control and query MAAS.
The API is "Restful", which means that you access it through normal HTTP
requests.


API versions
------------

At any given time, MAAS may support multiple versions of its API.  The version
number is included in the API's URL, e.g. /api/1.0/

For now, 1.0 is the only supported version.


HTTP methods and parameter-passing
----------------------------------

The following HTTP methods are available for accessing the API:
 * GET (for information retrieval and queries),
 * POST (for asking the system to do things),
 * PUT (for updating objects), and
 * DELETE (for deleting objects).

All methods except DELETE may take parameters, but they are not all passed in
the same way.  GET parameters are passed in the URL, as is normal with a GET:
"/item/?foo=bar" passes parameter "foo" with value "bar".

POST and PUT are different.  Your request should have MIME type
"multipart/form-data"; each part represents one parameter (for POST) or
attribute (for PUT).  Each part is named after the parameter or attribute it
contains, and its contents are the conveyed value.

All parameters are in text form.  If you need to submit binary data to the
API, don't send it as any MIME binary format; instead, send it as a plain text
part containing base64-encoded data.

Most resources offer a choice of GET or POST operations.  In those cases these
methods will take one special parameter, called `op`, to indicate what it is
you want to do.

For example, to list all nodes, you might GET "/api/1.0/nodes/?op=list".
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "AccountHandler",
    "AnonNodeGroupsHandler",
    "AnonNodesHandler",
    "AnonymousOperationsHandler",
    "api_doc",
    "api_doc_title",
    "BootImagesHandler",
    "FilesHandler",
    "get_oauth_token",
    "NodeGroupsHandler",
    "NodeGroupInterfaceHandler",
    "NodeGroupInterfacesHandler",
    "NodeHandler",
    "NodeMacHandler",
    "NodeMacsHandler",
    "NodesHandler",
    "OperationsHandler",
    "TagHandler",
    "TagsHandler",
    "pxeconfig",
    "render_api_docs",
    ]

from base64 import b64decode
from cStringIO import StringIO
from datetime import (
    datetime,
    timedelta,
    )
from functools import partial
import httplib
from inspect import getdoc
import json
import sys
from textwrap import dedent

from celery.app import app_or_default
from django.conf import settings
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    )
from django.db.utils import DatabaseError
from django.forms.models import model_to_dict
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    QueryDict,
    )
from django.shortcuts import (
    get_object_or_404,
    render_to_response,
    )
from django.template import RequestContext
from docutils import core
from formencode import validators
from formencode.validators import Invalid
from maasserver.apidoc import (
    describe_handler,
    find_api_handlers,
    generate_api_docs,
    )
from maasserver.components import (
    COMPONENT,
    discard_persistent_error,
    register_persistent_error,
    )
from maasserver.enum import (
    ARCHITECTURE,
    NODE_PERMISSION,
    NODE_STATUS,
    NODEGROUP_STATUS,
    )
from maasserver.exceptions import (
    MAASAPIBadRequest,
    MAASAPINotFound,
    NodesNotAvailable,
    NodeStateViolation,
    Unauthorized,
    )
from maasserver.fields import validate_mac
from maasserver.forms import (
    get_node_create_form,
    get_node_edit_form,
    NodeGroupInterfaceForm,
    NodeGroupWithInterfacesForm,
    TagForm,
    )
from maasserver.models import (
    BootImage,
    Config,
    DHCPLease,
    FileStorage,
    MACAddress,
    Node,
    NodeGroup,
    NodeGroupInterface,
    Tag,
    )
from maasserver.preseed import (
    compose_enlistment_preseed_url,
    compose_preseed_url,
    )
from maasserver.server_address import get_maas_facing_server_address
from maasserver.utils.orm import get_one
from piston.handler import (
    AnonymousBaseHandler,
    BaseHandler,
    HandlerMetaClass,
    )
from piston.models import Token
from piston.resource import Resource
from piston.utils import rc
from provisioningserver.kernel_opts import KernelParameters


class OperationsResource(Resource):
    """A resource supporting operation dispatch.

    All requests are passed onto the handler's `dispatch` method. See
    :class:`OperationsHandler`.
    """

    crudmap = Resource.callmap
    callmap = dict.fromkeys(crudmap, "dispatch")


class RestrictedResource(OperationsResource):

    def authenticate(self, request, rm):
        actor, anonymous = super(
            RestrictedResource, self).authenticate(request, rm)
        if not anonymous and not request.user.is_active:
            raise PermissionDenied("User is not allowed access to this API.")
        else:
            return actor, anonymous


class AdminRestrictedResource(RestrictedResource):

    def authenticate(self, request, rm):
        actor, anonymous = super(
            AdminRestrictedResource, self).authenticate(request, rm)
        if anonymous or not request.user.is_superuser:
            raise PermissionDenied("User is not allowed access to this API.")
        else:
            return actor, anonymous


def api_exported(method='POST', exported_as=None):
    """Decorator to make a method available on the API.

    :param method: The HTTP method over which to export the operation.
    :param exported_as: Optional operation name; defaults to the name of the
        exported method.

    """
    def _decorator(func):
        if method not in OperationsResource.callmap:
            raise ValueError("Invalid method: '%s'" % method)
        if exported_as is None:
            func._api_exported = {method: func.__name__}
        else:
            func._api_exported = {method: exported_as}
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

        # Create an http-method:function mapping for CRUD operations.
        crud = {
            http_method: getattr(cls, method)
            for http_method, method in OperationsResource.crudmap.items()
            if getattr(cls, method, None) is not None
            }

        # Create a operation-name:function mapping for non-CRUD operations.
        # These functions contain an _api_exported attribute that will be
        # used later on.
        operations = {
            name: attribute for name, attribute in vars(cls).items()
            if getattr(attribute, "_api_exported", None) is not None
            }

        # Create the exports mapping.
        exports = {}
        exports.update(
            ((http_method, None), function)
            for http_method, function in crud.items())
        exports.update(
            (signature, function)
            for name, function in operations.items()
            for signature in function._api_exported.items())

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


def extract_oauth_key_from_auth_header(auth_data):
    """Extract the oauth key from auth data in HTTP header.

    :param auth_data: {string} The HTTP Authorization header.

    :return: The oauth key from the header, or None.
    """
    for entry in auth_data.split():
        key_value = entry.split('=', 1)
        if len(key_value) == 2:
            key, value = key_value
            if key == 'oauth_token':
                return value.rstrip(',').strip('"')
    return None


def extract_oauth_key(request):
    """Extract the oauth key from a request's headers.

    Raises :class:`Unauthorized` if no key is found.
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if auth_header is None:
        raise Unauthorized("No authorization header received.")
    key = extract_oauth_key_from_auth_header(auth_header)
    if key is None:
        raise Unauthorized("Did not find request's oauth token.")
    return key


def get_oauth_token(request):
    """Get the OAuth :class:`piston.models.Token` used for `request`.

    Raises :class:`Unauthorized` if no key is found, or if the token is
    unknown.
    """
    try:
        return Token.objects.get(key=extract_oauth_key(request))
    except Token.DoesNotExist:
        raise Unauthorized("Unknown OAuth token.")


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


# Node's fields exposed on the API.
DISPLAYED_NODE_FIELDS = (
    'system_id',
    'hostname',
    ('macaddress_set', ('mac_address',)),
    'architecture',
    'status',
    'netboot',
    'power_type',
    'power_parameters',
    'tag_names',
    )


class NodeHandler(OperationsHandler):
    """Manage individual Nodes."""
    create = None  # Disable create.
    model = Node
    fields = DISPLAYED_NODE_FIELDS

    def read(self, request, system_id):
        """Read a specific Node."""
        return Node.objects.get_node_or_404(
            system_id=system_id, user=request.user, perm=NODE_PERMISSION.VIEW)

    def update(self, request, system_id):
        """Update a specific Node.

        :param hostname: The new hostname for this node.
        :type hostname: basestring
        :param architecture: The new architecture for this node (see
            vocabulary `ARCHITECTURE`).
        :type architecture: basestring
        :param power_type: The new power type for this node (see
            vocabulary `POWER_TYPE`).  Note that if you set power_type to
            use the default value, power_parameters will be set to the empty
            string.  Available to admin users.
        :type power_type: basestring
        :param power_parameters_{param1}: The new value for the 'param1'
            power parameter.  Note that this is dynamic as the available
            parameters depend on the selected value of the Node's power_type.
            For instance, if the power_type is 'ether_wake', the only valid
            parameter is 'power_address' so one would want to pass 'myaddress'
            as the value of the 'power_parameters_power_address' parameter.
            Available to admin users.
        :type power_parameters_{param1}: basestring
        :param power_parameters_skip_check: Whether or not the new power
            parameters for this node should be checked against the expected
            power parameters for the node's power type ('true' or 'false').
            The default is 'false'.
        :type power_parameters_skip_validation: basestring
        """

        node = Node.objects.get_node_or_404(
            system_id=system_id, user=request.user, perm=NODE_PERMISSION.EDIT)
        data = get_overrided_query_dict(model_to_dict(node), request.data)
        Form = get_node_edit_form(request.user)
        form = Form(data, instance=node)
        if form.is_valid():
            return form.save()
        else:
            raise ValidationError(form.errors)

    def delete(self, request, system_id):
        """Delete a specific Node."""
        node = Node.objects.get_node_or_404(
            system_id=system_id, user=request.user,
            perm=NODE_PERMISSION.ADMIN)
        node.delete()
        return rc.DELETED

    @classmethod
    def resource_uri(cls, node=None):
        # This method is called by piston in two different contexts:
        # - when generating an uri template to be used in the documentation
        # (in this case, it is called with node=None).
        # - when populating the 'resource_uri' field of an object
        # returned by the API (in this case, node is a Node object).
        node_system_id = "system_id"
        if node is not None:
            node_system_id = node.system_id
        return ('node_handler', (node_system_id, ))

    @api_exported('POST')
    def stop(self, request, system_id):
        """Shut down a node."""
        nodes = Node.objects.stop_nodes([system_id], request.user)
        if len(nodes) == 0:
            raise PermissionDenied(
                "You are not allowed to shut down this node.")
        return nodes[0]

    @api_exported('POST')
    def start(self, request, system_id):
        """Power up a node.

        :param user_data: If present, this blob of user-data to be made
            available to the nodes through the metadata service.
        :type user_data: base64-encoded basestring
        :param distro_series: If present, this parameter specifies the
            Ubuntu Release the node will use.
        :type distro_series: basestring

        Ideally we'd have MIME multipart and content-transfer-encoding etc.
        deal with the encapsulation of binary data, but couldn't make it work
        with the framework in reasonable time so went for a dumb, manual
        encoding instead.
        """
        user_data = request.POST.get('user_data', None)
        series = request.POST.get('distro_series', None)
        if user_data is not None:
            user_data = b64decode(user_data)
        if series is not None:
            node = Node.objects.get_node_or_404(
                system_id=system_id, user=request.user,
                perm=NODE_PERMISSION.EDIT)
            node.set_distro_series(series=series)
        nodes = Node.objects.start_nodes(
            [system_id], request.user, user_data=user_data)
        if len(nodes) == 0:
            raise PermissionDenied(
                "You are not allowed to start up this node.")
        return nodes[0]

    @api_exported('POST')
    def release(self, request, system_id):
        """Release a node.  Opposite of `NodesHandler.acquire`."""
        node = Node.objects.get_node_or_404(
            system_id=system_id, user=request.user, perm=NODE_PERMISSION.EDIT)
        node.set_distro_series(series='')
        if node.status == NODE_STATUS.READY:
            # Nothing to do.  This may be a redundant retry, and the
            # postcondition is achieved, so call this success.
            pass
        elif node.status in [NODE_STATUS.ALLOCATED, NODE_STATUS.RESERVED]:
            node.release()
        else:
            raise NodeStateViolation(
                "Node cannot be released in its current state ('%s')."
                % node.display_status())
        return node


def create_node(request):
    """Service an http request to create a node.

    The node will be in the Declared state.

    :param request: The http request for this node to be created.
    :return: A `Node`.
    :rtype: :class:`maasserver.models.Node`.
    :raises: ValidationError
    """
    Form = get_node_create_form(request.user)
    form = Form(request.data)
    if form.is_valid():
        return form.save()
    else:
        raise ValidationError(form.errors)


class AnonNodesHandler(AnonymousOperationsHandler):
    """Create Nodes."""
    create = read = update = delete = None
    fields = DISPLAYED_NODE_FIELDS

    @api_exported('POST')
    def new(self, request):
        """Create a new Node.

        Adding a server to a MAAS puts it on a path that will wipe its disks
        and re-install its operating system.  In anonymous enlistment and when
        the enlistment is done by a non-admin, the node is held in the
        "Declared" state for approval by a MAAS admin.
        """
        return create_node(request)

    @api_exported('GET')
    def is_registered(self, request):
        """Returns whether or not the given MAC address is registered within
        this MAAS (and attached to a non-retired node).

        :param mac_address: The mac address to be checked.
        :type mac_address: basestring
        :return: 'true' or 'false'.
        :rtype: basestring
        """
        mac_address = get_mandatory_param(request.GET, 'mac_address')
        return MACAddress.objects.filter(
            mac_address=mac_address).exclude(
                node__status=NODE_STATUS.RETIRED).exists()

    @api_exported('POST')
    def accept(self, request):
        """Accept a node's enlistment: not allowed to anonymous users."""
        raise Unauthorized("You must be logged in to accept nodes.")

    @api_exported("POST")
    def check_commissioning(self, request):
        """Check all commissioning nodes to see if they are taking too long.

        Anything that has been commissioning for longer than
        settings.COMMISSIONING_TIMEOUT is moved into the FAILED_TESTS status.
        """
        interval = timedelta(minutes=settings.COMMISSIONING_TIMEOUT)
        cutoff = datetime.now() - interval
        query = Node.objects.filter(
            status=NODE_STATUS.COMMISSIONING, updated__lte=cutoff)
        query.update(status=NODE_STATUS.FAILED_TESTS)
        # Note that Django doesn't call save() on updated nodes here,
        # but I don't think anything requires its effects anyway.

    @classmethod
    def resource_uri(cls, *args, **kwargs):
        return ('nodes_handler', [])


def extract_constraints(request_params):
    """Extract a dict of node allocation constraints from http parameters.

    :param request_params: Parameters submitted with the allocation request.
    :type request_params: :class:`django.http.QueryDict`
    :return: A mapping of applicable constraint names to their values.
    :rtype: :class:`dict`
    """
    supported_constraints = ('name', 'arch')
    return {constraint: request_params[constraint]
        for constraint in supported_constraints
            if constraint in request_params}


class NodesHandler(OperationsHandler):
    """Manage collection of Nodes."""
    create = read = update = delete = None
    anonymous = AnonNodesHandler

    @api_exported('POST')
    def new(self, request):
        """Create a new Node.

        When a node has been added to MAAS by an admin MAAS user, it is
        ready for allocation to services running on the MAAS.
        """
        node = create_node(request)
        if request.user.is_superuser:
            node.accept_enlistment(request.user)
        return node

    @api_exported('POST')
    def accept(self, request):
        """Accept declared nodes into the MAAS.

        Nodes can be enlisted in the MAAS anonymously or by non-admin users,
        as opposed to by an admin.  These nodes are held in the Declared
        state; a MAAS admin must first verify the authenticity of these
        enlistments, and accept them.

        Enlistments can be accepted en masse, by passing multiple nodes to
        this call.  Accepting an already accepted node is not an error, but
        accepting one that is already allocated, broken, etc. is.

        :param nodes: system_ids of the nodes whose enlistment is to be
            accepted.  (An empty list is acceptable).
        :return: The system_ids of any nodes that have their status changed
            by this call.  Thus, nodes that were already accepted are
            excluded from the result.
        """
        system_ids = set(request.POST.getlist('nodes'))
        # Check the existence of these nodes first.
        existing_ids = set(Node.objects.filter().values_list(
            'system_id', flat=True))
        if len(existing_ids) < len(system_ids):
            raise MAASAPIBadRequest(
                "Unknown node(s): %s." % ', '.join(system_ids - existing_ids))
        # Make sure that the user has the required permission.
        nodes = Node.objects.get_nodes(
            request.user, perm=NODE_PERMISSION.ADMIN, ids=system_ids)
        ids = set(node.system_id for node in nodes)
        if len(nodes) < len(system_ids):
            raise PermissionDenied(
                "You don't have the required permission to accept the "
                "following node(s): %s." % (
                    ', '.join(system_ids - ids)))
        return filter(
            None, [node.accept_enlistment(request.user) for node in nodes])

    @api_exported('POST')
    def accept_all(self, request):
        """Accept all declared nodes into the MAAS.

        Nodes can be enlisted in the MAAS anonymously or by non-admin users,
        as opposed to by an admin.  These nodes are held in the Declared
        state; a MAAS admin must first verify the authenticity of these
        enlistments, and accept them.

        :return: Representations of any nodes that have their status changed
            by this call.  Thus, nodes that were already accepted are excluded
            from the result.
        """
        nodes = Node.objects.get_nodes(
            request.user, perm=NODE_PERMISSION.ADMIN)
        nodes = nodes.filter(status=NODE_STATUS.DECLARED)
        nodes = [node.accept_enlistment(request.user) for node in nodes]
        return filter(None, nodes)

    @api_exported('GET')
    def list(self, request):
        """List Nodes visible to the user, optionally filtered by criteria.

        :param mac_address: An optional list of MAC addresses.  Only
            nodes with matching MAC addresses will be returned.
        :type mac_address: iterable
        :param id: An optional list of system ids.  Only nodes with
            matching system ids will be returned.
        :type id: iterable
        """
        # Get filters from request.
        match_ids = get_optional_list(request.GET, 'id')
        match_macs = get_optional_list(request.GET, 'mac_address')
        # Fetch nodes and apply filters.
        nodes = Node.objects.get_nodes(
            request.user, NODE_PERMISSION.VIEW, ids=match_ids)
        if match_macs is not None:
            nodes = nodes.filter(macaddress__mac_address__in=match_macs)
        return nodes.order_by('id')

    @api_exported('GET')
    def list_allocated(self, request):
        """Fetch Nodes that were allocated to the User/oauth token."""
        token = get_oauth_token(request)
        match_ids = get_optional_list(request.GET, 'id')
        nodes = Node.objects.get_allocated_visible_nodes(token, match_ids)
        return nodes.order_by('id')

    @api_exported('POST')
    def acquire(self, request):
        """Acquire an available node for deployment."""
        node = Node.objects.get_available_node_for_acquisition(
            request.user, constraints=extract_constraints(request.data))
        if node is None:
            raise NodesNotAvailable("No matching node is available.")
        node.acquire(request.user, get_oauth_token(request))
        return node

    @classmethod
    def resource_uri(cls, *args, **kwargs):
        return ('nodes_handler', [])


class NodeMacsHandler(OperationsHandler):
    """
    Manage all the MAC addresses linked to a Node / Create a new MAC address
    for a Node.

    """
    update = delete = None

    def read(self, request, system_id):
        """Read all MAC addresses related to a Node."""
        node = Node.objects.get_node_or_404(
            user=request.user, system_id=system_id, perm=NODE_PERMISSION.VIEW)

        return MACAddress.objects.filter(node=node).order_by('id')

    def create(self, request, system_id):
        """Create a MAC address for a specified Node."""
        node = Node.objects.get_node_or_404(
            user=request.user, system_id=system_id, perm=NODE_PERMISSION.EDIT)
        mac = node.add_mac_address(request.data.get('mac_address', None))
        return mac

    @classmethod
    def resource_uri(cls, *args, **kwargs):
        return ('node_macs_handler', ['system_id'])


class NodeMacHandler(OperationsHandler):
    """Manage a MAC address linked to a Node."""
    create = update = None
    fields = ('mac_address',)
    model = MACAddress

    def read(self, request, system_id, mac_address):
        """Read a MAC address related to a Node."""
        node = Node.objects.get_node_or_404(
            user=request.user, system_id=system_id, perm=NODE_PERMISSION.VIEW)

        validate_mac(mac_address)
        return get_object_or_404(
            MACAddress, node=node, mac_address=mac_address)

    def delete(self, request, system_id, mac_address):
        """Delete a specific MAC address for the specified Node."""
        validate_mac(mac_address)
        node = Node.objects.get_node_or_404(
            user=request.user, system_id=system_id, perm=NODE_PERMISSION.EDIT)

        mac = get_object_or_404(MACAddress, node=node, mac_address=mac_address)
        mac.delete()
        return rc.DELETED

    @classmethod
    def resource_uri(cls, mac=None):
        node_system_id = "system_id"
        mac_address = "mac_address"
        if mac is not None:
            node_system_id = mac.node.system_id
            mac_address = mac.mac_address
        return ('node_mac_handler', [node_system_id, mac_address])


def get_file(handler, request):
    """Get a named file from the file storage.

    :param filename: The exact name of the file you want to get.
    :type filename: string
    :return: The file is returned in the response content.
    """
    filename = request.GET.get("filename", None)
    if not filename:
        raise MAASAPIBadRequest("Filename not supplied")
    try:
        db_file = FileStorage.objects.get(filename=filename)
    except FileStorage.DoesNotExist:
        raise MAASAPINotFound("File not found")
    return HttpResponse(db_file.data.read(), status=httplib.OK)


class AnonFilesHandler(AnonymousOperationsHandler):
    """Anonymous file operations.

    This is needed for Juju. The story goes something like this:

    - The Juju provider will upload a file using an "unguessable" name.

    - The name of this file (or its URL) will be shared with all the agents in
      the environment. They cannot modify the file, but they can access it
      without credentials.

    """
    create = read = update = delete = None

    get = api_exported('GET', exported_as='get')(get_file)


class FilesHandler(OperationsHandler):
    """File management operations."""
    create = read = update = delete = None
    anonymous = AnonFilesHandler

    get = api_exported('GET', exported_as='get')(get_file)

    @api_exported('POST')
    def add(self, request):
        """Add a new file to the file storage.

        :param filename: The file name to use in the storage.
        :type filename: string
        :param file: Actual file data with content type
            application/octet-stream
        """
        filename = request.data.get("filename", None)
        if not filename:
            raise MAASAPIBadRequest("Filename not supplied")
        files = request.FILES
        if not files:
            raise MAASAPIBadRequest("File not supplied")
        if len(files) != 1:
            raise MAASAPIBadRequest("Exactly one file must be supplied")
        uploaded_file = files['file']

        # As per the comment in FileStorage, this ought to deal in
        # chunks instead of reading the file into memory, but large
        # files are not expected.
        FileStorage.objects.save_file(filename, uploaded_file)
        return HttpResponse('', status=httplib.CREATED)

    @classmethod
    def resource_uri(cls, *args, **kwargs):
        return ('files_handler', [])


DISPLAYED_NODEGROUP_FIELDS = ('uuid', 'status', 'name')


class AnonNodeGroupsHandler(AnonymousOperationsHandler):
    """Anon Node-groups API."""
    create = read = update = delete = None
    fields = DISPLAYED_NODEGROUP_FIELDS

    @api_exported('GET')
    def list(self, request):
        """List of node groups."""
        return NodeGroup.objects.all()

    @classmethod
    def resource_uri(cls):
        return ('nodegroups_handler', [])

    @api_exported('POST')
    def refresh_workers(self, request):
        """Request an update of all node groups' configurations.

        This sends each node-group worker an update of its API credentials,
        OMAPI key, node-group name, and so on.

        Anyone can request this (for example, a bootstrapping worker that
        does not know its node-group name or API credentials yet) but the
        information will be sent only to the known workers.
        """
        NodeGroup.objects.refresh_workers()
        return HttpResponse("Sending worker refresh.", status=httplib.OK)

    @api_exported('POST')
    def register(self, request):
        """Register a new `NodeGroup`.

        This method will use HTTP return codes to indicate the success of the
        call:

        - 200 (OK): the nodegroup has been accepted, the response will
          contain the RabbitMQ credentials in JSON format: e.g.:
          '{"BROKER_URL" = "amqp://guest:guest@localhost:5672//"}'
        - 202 (Accepted): the registration of the nodegroup has been accepted,
          it now needs to be validated by an administrator.  Please issue
          the same request later.
        - 403 (Forbidden): this nodegroup has been rejected.

        :param uuid: The UUID of the nodegroup.
        :type name: basestring
        :param name: The name of the nodegroup.
        :type name: basestring
        :param interfaces: The list of the interfaces' data.
        :type interface: json string containing a list of dictionaries with
            the data to initialize the interfaces.
            e.g.: '[{"ip_range_high": "192.168.168.254",
            "ip_range_low": "192.168.168.1", "broadcast_ip":
            "192.168.168.255", "ip": "192.168.168.18", "subnet_mask":
            "255.255.255.0", "router_ip": "192.168.168.1", "interface":
            "eth0"}]'
        """
        uuid = get_mandatory_param(request.data, 'uuid')
        existing_nodegroup = get_one(NodeGroup.objects.filter(uuid=uuid))
        if existing_nodegroup is None:
            # This nodegroup (identified by its uuid), does not exist yet,
            # create it if the data validates.
            form = NodeGroupWithInterfacesForm(request.data)
            if form.is_valid():
                form.save()
                return HttpResponse(
                    "Cluster registered.  Awaiting admin approval.",
                    status=httplib.ACCEPTED)
            else:
                raise ValidationError(form.errors)
        else:
            if existing_nodegroup.status == NODEGROUP_STATUS.ACCEPTED:
                # The nodegroup exists and is validated, return the RabbitMQ
                # credentials as JSON.
                celery_conf = app_or_default().conf
                return {
                    'BROKER_URL': celery_conf.BROKER_URL,
                }
            elif existing_nodegroup.status == NODEGROUP_STATUS.REJECTED:
                raise PermissionDenied('Rejected cluster.')
            elif existing_nodegroup.status == NODEGROUP_STATUS.PENDING:
                return HttpResponse(
                    "Awaiting admin approval.", status=httplib.ACCEPTED)


class NodeGroupsHandler(OperationsHandler):
    """Node-groups API."""
    anonymous = AnonNodeGroupsHandler
    create = read = update = delete = None
    fields = DISPLAYED_NODEGROUP_FIELDS

    @api_exported('GET')
    def list(self, request):
        """List of node groups."""
        return NodeGroup.objects.all()

    @api_exported('POST')
    def accept(self, request):
        """Accept nodegroup enlistment(s).

        :param uuid: The UUID (or list of UUIDs) of the nodegroup(s) to accept.
        :type name: basestring (or list of basestrings)

        This method is reserved to admin users.
        """
        if request.user.is_superuser:
            uuids = request.data.getlist('uuid')
            for uuid in uuids:
                nodegroup = get_object_or_404(NodeGroup, uuid=uuid)
                nodegroup.accept()
            return HttpResponse("Nodegroup(s) accepted.", status=httplib.OK)
        else:
            raise PermissionDenied("That method is reserved to admin users.")

    @api_exported('POST')
    def reject(self, request):
        """Reject nodegroup enlistment(s).

        :param uuid: The UUID (or list of UUIDs) of the nodegroup(s) to reject.
        :type name: basestring (or list of basestrings)

        This method is reserved to admin users.
        """
        if request.user.is_superuser:
            uuids = request.data.getlist('uuid')
            for uuid in uuids:
                nodegroup = get_object_or_404(NodeGroup, uuid=uuid)
                nodegroup.reject()
            return HttpResponse("Nodegroup(s) rejected.", status=httplib.OK)
        else:
            raise PermissionDenied("That method is reserved to admin users.")

    @classmethod
    def resource_uri(cls):
        return ('nodegroups_handler', [])


def check_nodegroup_access(request, nodegroup):
    """Validate API access by worker for `nodegroup`.

    This supports a nodegroup worker accessing its nodegroup object on
    the API.  If the request is done by anyone but the worker for this
    particular nodegroup, the function raises :class:`PermissionDenied`.
    """
    try:
        key = extract_oauth_key(request)
    except Unauthorized as e:
        raise PermissionDenied(unicode(e))

    if key != nodegroup.api_key:
        raise PermissionDenied(
            "Only allowed for the %r worker." % nodegroup.name)


class NodeGroupHandler(OperationsHandler):
    """Node-group API."""

    create = update = delete = None
    fields = DISPLAYED_NODEGROUP_FIELDS

    def read(self, request, uuid):
        """GET a node group."""
        return get_object_or_404(NodeGroup, uuid=uuid)

    @classmethod
    def resource_uri(cls, nodegroup=None):
        if nodegroup is None:
            uuid = 'uuid'
        else:
            uuid = nodegroup.uuid
        return ('nodegroup_handler', [uuid])

    @api_exported('POST')
    def update_leases(self, request, uuid):
        leases = get_mandatory_param(request.data, 'leases')
        nodegroup = get_object_or_404(NodeGroup, uuid=uuid)
        check_nodegroup_access(request, nodegroup)
        leases = json.loads(leases)
        new_leases = DHCPLease.objects.update_leases(nodegroup, leases)
        if len(new_leases) > 0:
            nodegroup.add_dhcp_host_maps(
                {ip: leases[ip] for ip in new_leases if ip in leases})
        return HttpResponse("Leases updated.", status=httplib.OK)


DISPLAYED_NODEGROUP_FIELDS = (
    'ip', 'management', 'interface', 'subnet_mask',
    'broadcast_ip', 'ip_range_low', 'ip_range_high')


class NodeGroupInterfacesHandler(OperationsHandler):
    """NodeGroupInterfaces API."""
    create = read = update = delete = None
    fields = DISPLAYED_NODEGROUP_FIELDS

    @api_exported('GET')
    def list(self, request, uuid):
        """List of NodeGroupInterfaces of a NodeGroup."""
        nodegroup = get_object_or_404(NodeGroup, uuid=uuid)
        return NodeGroupInterface.objects.filter(nodegroup=nodegroup)

    @api_exported('POST')
    def new(self, request, uuid):
        """Create a new NodeGroupInterface for this NodeGroup.

        :param ip: Static IP of the interface.
        :type ip: basestring (IP Address)
        :param interface: Name of the interface.
        :type interface: basestring
        :param management: The service(s) MAAS should manage on this interface.
        :type management: Vocabulary `NODEGROUPINTERFACE_MANAGEMENT`
        :param subnet_mask: Subnet mask, e.g. 255.0.0.0.
        :type subnet_mask: basestring (IP Address)
        :param broadcast_ip: Broadcast address for this subnet.
        :type broadcast_ip: basestring (IP Address)
        :param router_ip: Address of default gateway.
        :type router_ip: basestring (IP Address)
        :param ip_range_low: Lowest IP address to assign to clients.
        :type ip_range_low: basestring (IP Address)
        :param ip_range_high: Highest IP address to assign to clients.
        :type ip_range_high: basestring (IP Address)
        """
        nodegroup = get_object_or_404(NodeGroup, uuid=uuid)
        form = NodeGroupInterfaceForm(request.data)
        if form.is_valid():
            return form.save(
                nodegroup=nodegroup)
        else:
            raise ValidationError(form.errors)

    @classmethod
    def resource_uri(cls, nodegroup=None):
        if nodegroup is None:
            uuid = 'uuid'
        else:
            uuid = nodegroup.uuid
        return ('nodegroupinterfaces_handler', [uuid])


class NodeGroupInterfaceHandler(OperationsHandler):
    """NodeGroupInterface API."""
    create = delete = None
    fields = DISPLAYED_NODEGROUP_FIELDS

    def read(self, request, uuid, interface):
        """List of NodeGroupInterfaces of a NodeGroup."""
        nodegroup = get_object_or_404(NodeGroup, uuid=uuid)
        nodegroupinterface = get_object_or_404(
            NodeGroupInterface, nodegroup=nodegroup, interface=interface)
        return nodegroupinterface

    def update(self, request, uuid, interface):
        """Update a specific NodeGroupInterface.

        :param ip: Static IP of the interface.
        :type ip: basestring (IP Address)
        :param interface: Name of the interface.
        :type interface: basestring
        :param management: The service(s) MAAS should manage on this interface.
        :type management: Vocabulary `NODEGROUPINTERFACE_MANAGEMENT`
        :param subnet_mask: Subnet mask, e.g. 255.0.0.0.
        :type subnet_mask: basestring (IP Address)
        :param broadcast_ip: Broadcast address for this subnet.
        :type broadcast_ip: basestring (IP Address)
        :param router_ip: Address of default gateway.
        :type router_ip: basestring (IP Address)
        :param ip_range_low: Lowest IP address to assign to clients.
        :type ip_range_low: basestring (IP Address)
        :param ip_range_high: Highest IP address to assign to clients.
        :type ip_range_high: basestring (IP Address)
        """
        nodegroup = get_object_or_404(NodeGroup, uuid=uuid)
        nodegroupinterface = get_object_or_404(
            NodeGroupInterface, nodegroup=nodegroup, interface=interface)
        data = get_overrided_query_dict(
            model_to_dict(nodegroupinterface), request.data)
        form = NodeGroupInterfaceForm(data, instance=nodegroupinterface)
        if form.is_valid():
            return form.save()
        else:
            raise ValidationError(form.errors)

    @classmethod
    def resource_uri(cls, nodegroup=None, interface=None):
        if nodegroup is None:
            uuid = 'uuid'
        else:
            uuid = nodegroup.uuid
        if interface is None:
            interface_name = 'interface'
        else:
            interface_name = interface.interface
        return ('nodegroupinterface_handler', [uuid, interface_name])


class AccountHandler(OperationsHandler):
    """Manage the current logged-in user."""
    create = read = update = delete = None

    @api_exported('POST')
    def create_authorisation_token(self, request):
        """Create an authorisation OAuth token and OAuth consumer.

        :return: a json dict with three keys: 'token_key',
            'token_secret' and 'consumer_key' (e.g.
            {token_key: 's65244576fgqs', token_secret: 'qsdfdhv34',
            consumer_key: '68543fhj854fg'}).
        :rtype: string (json)

        """
        profile = request.user.get_profile()
        consumer, token = profile.create_authorisation_token()
        return {
            'token_key': token.key, 'token_secret': token.secret,
            'consumer_key': consumer.key,
            }

    @api_exported('POST')
    def delete_authorisation_token(self, request):
        """Delete an authorisation OAuth token and the related OAuth consumer.

        :param token_key: The key of the token to be deleted.
        :type token_key: basestring
        """
        profile = request.user.get_profile()
        token_key = get_mandatory_param(request.data, 'token_key')
        profile.delete_authorisation_token(token_key)
        return rc.DELETED

    @classmethod
    def resource_uri(cls, *args, **kwargs):
        return ('account_handler', [])


class TagHandler(OperationsHandler):
    """Manage individual Tags."""
    create = None
    model = Tag
    fields = (
        'name',
        'definition',
        'comment',
        )

    def read(self, request, name):
        """Read a specific Node."""
        return Tag.objects.get_tag_or_404(name=name, user=request.user)

    def update(self, request, name):
        """Update a specific `Tag`.
        """
        tag = Tag.objects.get_tag_or_404(name=name, user=request.user,
            to_edit=True)
        model_dict = model_to_dict(tag)
        old_definition = model_dict['definition']
        data = get_overrided_query_dict(model_dict, request.data)
        form = TagForm(data, instance=tag)
        if form.is_valid():
            try:
                new_tag = form.save(commit=False)
                new_tag.save()
                if new_tag.definition != old_definition:
                    new_tag.populate_nodes()
                form.save_m2m()
            except DatabaseError as e:
                raise ValidationError(e)
            return new_tag
        else:
            raise ValidationError(form.errors)

    def delete(self, request, name):
        """Delete a specific Node."""
        tag = Tag.objects.get_tag_or_404(name=name,
            user=request.user, to_edit=True)
        tag.delete()
        return rc.DELETED

    # XXX: JAM 2012-09-25 This is currently a POST because of bug:
    #      http://pad.lv/1049933
    #      Essentially, if you have one 'GET' op, then you can no longer get
    #      the Tag object itself from a plain 'GET' without op.
    @api_exported('POST')
    def nodes(self, request, name):
        """Get the list of nodes that have this tag."""
        return Tag.objects.get_nodes(name, user=request.user)

    @classmethod
    def resource_uri(cls, tag=None):
        # See the comment in NodeHandler.resource_uri
        tag_name = 'tag_name'
        if tag is not None:
            tag_name = tag.name
        return ('tag_handler', (tag_name, ))


class TagsHandler(OperationsHandler):
    """Manage collection of Tags."""
    create = read = update = delete = None

    @api_exported('POST')
    def new(self, request):
        """Create a new `Tag`.
        """
        return create_tag(request)

    @api_exported('GET')
    def list(self, request):
        """List Tags.
        """
        return Tag.objects.all()

    @classmethod
    def resource_uri(cls, *args, **kwargs):
        return ('tags_handler', [])


def create_tag(request):
    """Service an http request to create a tag.

    :param request: The http request for this node to be created.
    :return: A `Tag`.
    :rtype: :class:`maasserver.models.Tag`.
    :raises: ValidationError
    """
    if not request.user.is_superuser:
        raise PermissionDenied()
    form = TagForm(request.data)
    if form.is_valid():
        new_tag = form.save(commit=False)
        new_tag.save()
        new_tag.populate_nodes()
        form.save_m2m()
        return new_tag
    else:
        raise ValidationError(form.errors)


class MAASHandler(OperationsHandler):
    """Manage the MAAS' itself."""
    create = read = update = delete = None

    @api_exported('POST')
    def set_config(self, request):
        """Set a config value.

        :param name: The name of the config item to be set.
        :type name: basestring
        :param name: The value of the config item to be set.
        :type value: json object
        """
        name = get_mandatory_param(
            request.data, 'name', validators.String(min=1))
        value = get_mandatory_param(request.data, 'value')
        Config.objects.set_config(name, value)
        return rc.ALL_OK

    @api_exported('GET')
    def get_config(self, request):
        """Get a config value.

        :param name: The name of the config item to be retrieved.
        :type name: basestring
        """
        name = get_mandatory_param(request.GET, 'name')
        value = Config.objects.get_config(name)
        return HttpResponse(json.dumps(value), content_type='application/json')


# Title section for the API documentation.  Matches in style, format,
# etc. whatever render_api_docs() produces, so that you can concatenate
# the two.
api_doc_title = dedent("""
    ========
    MAAS API
    ========
    """.lstrip('\n'))


def render_api_docs():
    """Render ReST documentation for the REST API.

    This module's docstring forms the head of the documentation; details of
    the API methods follow.

    :return: Documentation, in ReST, for the API.
    :rtype: :class:`unicode`
    """
    module = sys.modules[__name__]
    output = StringIO()
    line = partial(print, file=output)

    line(getdoc(module))
    line()
    line()
    line('Operations')
    line('----------')
    line()

    handlers = find_api_handlers(module)
    for doc in generate_api_docs(handlers):
        uri_template = doc.resource_uri_template
        exports = doc.handler.exports.items()
        for (http_method, operation), function in sorted(exports):
            line("``%s %s``" % (http_method, uri_template), end="")
            if operation is not None:
                line(" ``op=%s``" % operation)
            line()
            docstring = getdoc(function)
            if docstring is not None:
                for docline in docstring.splitlines():
                    line("  ", docline, sep="")
                line()

    return output.getvalue()


def reST_to_html_fragment(a_str):
    parts = core.publish_parts(source=a_str, writer_name='html')
    return parts['body_pre_docinfo'] + parts['fragment']


def api_doc(request):
    """Get ReST documentation for the REST API."""
    # Generate the documentation and keep it cached.  Note that we can't do
    # that at the module level because the API doc generation needs Django
    # fully initialized.
    return render_to_response(
        'maasserver/api_doc.html',
        {'doc': reST_to_html_fragment(render_api_docs())},
        context_instance=RequestContext(request))


def get_boot_purpose(node):
    """Return a suitable "purpose" for this boot, e.g. "install"."""
    # XXX: allenap bug=1031406 2012-07-31: The boot purpose is still in
    # flux. It may be that there will just be an "ephemeral" environment and
    # an "install" environment, and the differing behaviour between, say,
    # enlistment and commissioning - both of which will use the "ephemeral"
    # environment - will be governed by varying the preseed or PXE
    # configuration.
    if node is None:
        # This node is enlisting, for which we use a commissioning image.
        return "commissioning"
    elif node.status == NODE_STATUS.COMMISSIONING:
        # It is commissioning.
        return "commissioning"
    elif node.status == NODE_STATUS.ALLOCATED:
        # Install the node if netboot is enabled, otherwise boot locally.
        if node.netboot:
            return "install"
        else:
            return "local"  # TODO: Investigate.
    else:
        # Just poweroff? TODO: Investigate. Perhaps even send an IPMI signal
        # to turn off power.
        return "poweroff"


def pxeconfig(request):
    """Get the PXE configuration given a node's details.

    Returns a JSON object corresponding to a
    :class:`provisioningserver.kernel_opts.KernelParameters` instance.

    :param mac: MAC address to produce a boot configuration for.
    """
    mac = get_mandatory_param(request.GET, 'mac')

    macaddress = get_one(MACAddress.objects.filter(mac_address=mac))
    if macaddress is None:
        # Default to i386 as a works-for-all solution. This will not support
        # non-x86 architectures, but for now this assumption holds.
        node = None
        arch, subarch = ARCHITECTURE.i386, "generic"
        preseed_url = compose_enlistment_preseed_url()
        hostname = 'maas-enlist'
    else:
        node = macaddress.node
        arch, subarch = node.architecture, "generic"
        preseed_url = compose_preseed_url(node)
        hostname = node.hostname

    if node is None or node.status == NODE_STATUS.COMMISSIONING:
        series = Config.objects.get_config('commissioning_distro_series')
    else:
        series = node.get_distro_series()

    purpose = get_boot_purpose(node)
    domain = 'local.lan'  # TODO: This is probably not enough!
    server_address = get_maas_facing_server_address()

    params = KernelParameters(
        arch=arch, subarch=subarch, release=series, purpose=purpose,
        hostname=hostname, domain=domain, preseed_url=preseed_url,
        log_host=server_address, fs_host=server_address)

    return HttpResponse(
        json.dumps(params._asdict()),
        content_type="application/json")


class BootImagesHandler(OperationsHandler):

    @classmethod
    def resource_uri(cls):
        return ('boot_images_handler', [])

    @api_exported('POST')
    def report_boot_images(self, request):
        """Report images available to net-boot nodes from.

        :param images: A list of dicts, each describing a boot image with
            these properties: `architecture`, `subarchitecture`, `release`,
            `purpose`, all as in the code that determines TFTP paths for
            these images.
        """
        check_nodegroup_access(request, NodeGroup.objects.ensure_master())
        images = json.loads(get_mandatory_param(request.data, 'images'))

        for image in images:
            BootImage.objects.register_image(
                architecture=image['architecture'],
                subarchitecture=image.get('subarchitecture', 'generic'),
                release=image['release'],
                purpose=image['purpose'])

        if len(images) == 0:
            warning = dedent("""\
                No boot images have been imported yet.  Either the
                maas-import-pxe-files script has not run yet, or it failed.

                Try running it manually.  If it succeeds, this message will
                go away within 5 minutes.
                """)
            register_persistent_error(COMPONENT.IMPORT_PXE_FILES, warning)
        else:
            discard_persistent_error(COMPONENT.IMPORT_PXE_FILES)

        return HttpResponse("OK")


def describe(request):
    """Return a description of the whole MAAS API.

    Returns a JSON object describing the whole MAAS API.
    """
    module = sys.modules[__name__]
    description = {
        "doc": "MAAS API",
        "handlers": [
            describe_handler(handler)
            for handler in find_api_handlers(module)
            ],
        }
    return HttpResponse(
        json.dumps(description),
        content_type="application/json")
