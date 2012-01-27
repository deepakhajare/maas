# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""API."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "api_doc",
    "generate_api_doc",
    "NodeHandler",
    "NodeMacsHandler",
    ]

from functools import wraps
import types

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    )
from django.shortcuts import (
    get_object_or_404,
    render_to_response,
    )
from django.template import RequestContext
from docutils import core
from maasserver.forms import NodeWithMACAddressesForm
from maasserver.macaddress import validate_mac
from maasserver.models import (
    MACAddress,
    Node,
    )
from piston.doc import generate_doc
from piston.handler import (
    BaseHandler,
    HandlerMetaClass,
    )
from piston.utils import rc


def bad_request(message):
    resp = rc.BAD_REQUEST
    resp.write(': %s' % message)
    return resp


def format_error_message(error_dict):
    messages = []
    for k, v in error_dict.iteritems():
        if isinstance(v, list):
            messages.append("%s: %s" % (k, "".join(v)))
        else:
            messages.append("%s: %s" % (k, v))
    return "Invalid input: " + " / ".join(messages)


def validate_and_save(obj):
    try:
        obj.full_clean()
        obj.save()
        return obj
    except ValidationError, e:
        return bad_request(format_error_message(e.message_dict))


def validate_mac_address(mac_address):
    try:
        validate_mac(mac_address)
        return True, None
    except ValidationError:
        return False, bad_request('Invalid MAC Address.')


def perm_denied_handler(view_func):
    def _decorator(request, *args, **kwargs):
        try:
            response = view_func(request, *args, **kwargs)
            return response
        except PermissionDenied:
            return rc.FORBIDDEN
    return wraps(view_func)(_decorator)


def api_exported(operation_name=True):
    def _decorator(func):
        if operation_name == 'create':
            raise Exception("Cannot define a 'create' operation.")
        func._api_exported = operation_name
        return func
    return _decorator


# The parameter used to specify the requested operation for POST API calls.
OP_PARAM = 'op'


class OperationHandlerMetaClass(HandlerMetaClass):
    def __init__(cls, name, bases, dct):
        super(OperationHandlerMetaClass, cls).__init__(name, bases, dct)
        # Register all the exported methods.
        cls._available_api_methods = {}
        api_docs = ['\n']
        for name, value in dct.iteritems():
            if isinstance(value, types.FunctionType):
                if name == 'create':
                    raise Exception("Cannot define a 'create' method.")
                operation_name = getattr(value, '_api_exported', None)
                if operation_name is not None:
                    api_name = (
                        name if operation_name is True else operation_name)
                    cls._available_api_methods[api_name] = value
                    doc = "Method '%s' (op=%s):\n\t%s" % (
                        api_name, api_name, value.__doc__)
                    api_docs.append(doc)

        # Define a 'create' method that will route requests to the methods
        # registered in _available_api_methods.
        def create(cls, request, *args, **kwargs):
            op = request.data.get(OP_PARAM, None)
            if not isinstance(op, unicode):
                return bad_request('Unknown operation.')
            elif op not in cls._available_api_methods:
                return bad_request('Unknown operation: %s.' % op)
            else:
                method = cls._available_api_methods[op]
                return method(cls, request, *args, **kwargs)

        # Update the __doc__ for the 'create' method.
        doc = "Operate on nodes collection. The actual method to execute\
               depends on the value of the '%s' parameter." % OP_PARAM
        create.__doc__ = doc + '\n- '.join(api_docs)
        # Add the 'create' method.
        setattr(cls, 'create', create)


class NodeHandler(BaseHandler):
    """Manage individual Nodes."""
    allowed_methods = ('GET', 'DELETE', 'PUT')
    model = Node
    fields = ('system_id', 'hostname', ('macaddress_set', ('mac_address',)))

    @perm_denied_handler
    def read(self, request, system_id):
        """Read a specific Node."""
        return Node.objects.get_visible_node_or_404(
            system_id=system_id, user=request.user)

    @perm_denied_handler
    def update(self, request, system_id):
        """Update a specific Node."""
        node = Node.objects.get_visible_node_or_404(
            system_id=system_id, user=request.user)
        for key, value in request.data.items():
            setattr(node, key, value)
        return validate_and_save(node)

    @perm_denied_handler
    def delete(self, request, system_id):
        """Delete a specific Node."""
        node = Node.objects.get_visible_node_or_404(
            system_id=system_id, user=request.user)
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


class NodesHandler(BaseHandler):
    """Manage collection of Nodes / Create Nodes."""
    __metaclass__ = OperationHandlerMetaClass
    allowed_methods = ('GET', 'POST',)

    def read(self, request):
        """Read all Nodes."""
        return Node.objects.get_visible_nodes(request.user).order_by('id')

    @api_exported('new')
    def new(self, request):
        """Create a new Node."""
        form = NodeWithMACAddressesForm(request.data)
        if form.is_valid():
            node = form.save()
            return node
        else:
            return bad_request(format_error_message(form.errors))

    @classmethod
    def resource_uri(cls, *args, **kwargs):
        return ('nodes_handler', [])


class NodeMacsHandler(BaseHandler):
    """
    Manage all the MAC Addresses linked to a Node / Create a new MAC Address
    for a Node.

    """
    allowed_methods = ('GET', 'POST',)

    @perm_denied_handler
    def read(self, request, system_id):
        """Read all MAC Addresses related to a Node."""
        node = Node.objects.get_visible_node_or_404(
            user=request.user, system_id=system_id)

        return MACAddress.objects.filter(node=node).order_by('id')

    def create(self, request, system_id):
        """Create a MAC Address for a specified Node."""
        try:
            node = Node.objects.get_visible_node_or_404(
                user=request.user, system_id=system_id)
            mac = node.add_mac_address(request.data.get('mac_address', None))
            return mac
        except ValidationError, e:
            return bad_request(format_error_message(e.message_dict))

    @classmethod
    def resource_uri(cls, *args, **kwargs):
        return ('node_macs_handler', ['system_id'])


class NodeMacHandler(BaseHandler):
    """Manage a MAC Address linked to a Node."""
    allowed_methods = ('GET', 'DELETE')
    fields = ('mac_address',)
    model = MACAddress

    @perm_denied_handler
    def read(self, request, system_id, mac_address):
        """Read a MAC Address related to a Node."""
        node = Node.objects.get_visible_node_or_404(
            user=request.user, system_id=system_id)

        valid, response = validate_mac_address(mac_address)
        if not valid:
            return response
        return get_object_or_404(
            MACAddress, node=node, mac_address=mac_address)

    @perm_denied_handler
    def delete(self, request, system_id, mac_address):
        """Delete a specific MAC Address for the specified Node."""
        valid, response = validate_mac_address(mac_address)
        if not valid:
            return response

        node = Node.objects.get_visible_node_or_404(
            user=request.user, system_id=system_id)

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


def generate_api_doc():
    docs = (
        generate_doc(NodesHandler),
        generate_doc(NodeHandler),
        generate_doc(NodeMacsHandler),
        generate_doc(NodeMacHandler),
        )

    messages = ['MaaS API\n========\n\n']
    for doc in docs:
        for method in doc.get_methods():
            messages.append(
                "%s %s\n  %s\n\n" % (
                    method.http_name, doc.resource_uri_template,
                    method.doc))
    return ''.join(messages)


def reST_to_html_fragment(a_str):
    parts = core.publish_parts(source=a_str, writer_name='html')
    return parts['body_pre_docinfo'] + parts['fragment']


_API_DOC = None


def api_doc(request):
    # Generate the documentation and keep it cached.  Note that we can't do
    # that at the module level because the API doc generation needs Django
    # fully initialized.
    global _API_DOC
    if _API_DOC is None:
        _API_DOC = generate_api_doc()
    return render_to_response(
        'maasserver/api_doc.html',
        {'doc': reST_to_html_fragment(generate_api_doc())},
        context_instance=RequestContext(request))
