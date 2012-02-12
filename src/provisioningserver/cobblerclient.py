# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import (
    print_function,
    unicode_literals,
    )

"""Wrapper for the Cobbler XMLRPC API, using Twisted.

The API looks synchronous, but under the covers, calls yield to the Twisted
reactor so that it can service other callbacks.

To use Cobbler, create a `CobblerSession` (which connects and authenticates
as appropriate).  Create, query, or manipulate cobbler objects through the
various classes derived from `CobblerObject`: `CobblerDistro` for a distro,
`CobblerImage` for an image, `CobblerProfile` for a profile, `CobblerSystem`
for a node system, and so on.  In addition, `CobblerPreseeds` manages
preseeds.
"""

__metaclass__ = type
__all__ = [
    'CobblerDistro',
    'CobblerImage',
    'CobblerPreseeds',
    'CobblerProfile',
    'CobblerRepo',
    'CobblerSystem',
    'DEFAULT_TIMEOUT',
    ]

import xmlrpclib

from twisted.internet import reactor as default_reactor
from twisted.internet.defer import (
    DeferredLock,
    inlineCallbacks,
    returnValue,
    )
from twisted.web.xmlrpc import Proxy

# Default timeout in seconds for xmlrpc requests to cobbler.
DEFAULT_TIMEOUT = 30


def tilde_to_None(data):
    """Repair Cobbler's XML-RPC response.

    Cobbler has an annoying function, `cobbler.utils.strip_none`, that is
    applied to every data structure that it sends back through its XML-RPC API
    service. It "encodes" `None` as `"~"`, and does so recursively in `list`s
    and `dict`s. It also forces all dictionary keys to be `str`, so `None`
    keys become `"None"`.

    This function attempts to repair this damage. Sadly, it may get things
    wrong - it will "repair" genuine tildes to `None` - but it's likely to be
    more correct than doing nothing - and having tildes everwhere.

    This also does not attempt to repair `"None"` dictionary keys.
    """
    if data == "~":
        return None
    elif isinstance(data, list):
        return [tilde_to_None(value) for value in data]
    elif isinstance(data, dict):
        return {key: tilde_to_None(value) for key, value in data.iteritems()}
    else:
        return data


class CobblerXMLRPCProxy(Proxy):
    """An XML-RPC proxy that attempts to repair Cobbler's broken responses.

    See `tilde_to_None` for an explanation.
    """

    def callRemote(self, method, *args):
        """See `Proxy.callRemote`.

        Uses `tilde_to_None` to repair the response.
        """
        d = Proxy.callRemote(self, method, *args)
        d.addCallback(tilde_to_None)
        return d


def looks_like_auth_expiry(exception):
    """Does `exception` look like an authentication token expired?"""
    if not hasattr(exception, 'faultString'):
        # An auth failure would come as an xmlrpclib.Fault.
        return False
    return exception.faultString.startswith("invalid token: ")


class CobblerSession:
    """A session on the Cobbler XMLRPC API.

    The session can be used for many asynchronous requests, all of them
    sharing a single authentication token.

    If you're just using Cobbler's services, treat this class as a
    "connection" class: create it with the right service url, user name,
    and password, and pass it around for the various other Cobbler* classes
    to use.  After creation it's a black box except to the Cobbler client
    code.
    """

    # In an arguments list, this means "insert security token here."
    token_placeholder = object()

    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.proxy = self._make_twisted_proxy()
        self.token = None
        self.connection_count = 0
        self.authentication_lock = DeferredLock()

    def _make_twisted_proxy(self):
        """Create a Twisted XMRLPC proxy.

        For internal use only, but overridable for test purposes.
        """
        # Twisted does not encode the URL, and breaks with "Data must
        # not be unicode" if it's in Unicode.  We'll have to decode it
        # here, and hope it doesn't lead to breakage in Twisted.  We'll
        # figure out what to do about non-ASCII characters in URLs
        # later.
        return CobblerXMLRPCProxy(self.url.encode('ascii'))

    def record_state(self):
        """Return a cookie representing the session's current state.

        The cookie will change whenever the session is reconnected or
        re-authenticated.  The only valid use of this cookie is to compare
        it for equality with another one.

        If two calls return different cookies, that means that the session
        has broken in some way and been re-established between the two calls.
        """
        return (self.connection_count, self.token)

    @inlineCallbacks
    def _authenticate(self, previous_state=None):
        """Log in asynchronously.

        This is called when an API function needs authentication when the
        session isn't authenticated, but also when an XMLRPC call result
        indicates that the authentication token used for a request has
        expired.

        :param previous_state: The state of the session as recorded by
            `record_state` before the failed request was issued.  If the
            session has had to reconnect or re-authenticate since then, the
            method will assume that a concurrent authentication request has
            completed and the failed request can be retried without logging
            in again.
            If no `previous_state` is given, authentication will happen
            regardless.
        :return: A `Deferred`.
        """
        if previous_state is None:
            previous_state = self.record_state()

        yield self.authentication_lock.acquire()
        try:
            if self.record_state() == previous_state:
                # If we're here, nobody else is authenticating this
                # session.  Clear the stale token as a hint to
                # subsequent calls on the session.  If they see that the
                # session is unauthenticated they won't issue and fail,
                # but rather block for this authentication attempt to
                # complete.
                self.token = None

                # Now initiate our new authentication.
                self.token = yield self._issue_call(
                    'login', self.user, self.password)
        finally:
            self.authentication_lock.release()

    def _substitute_token(self, arg):
        """Return `arg`, or the current auth token for `token_placeholder`."""
        if arg is self.token_placeholder:
            return self.token
        else:
            return arg

    def _with_timeout(self, d, timeout=DEFAULT_TIMEOUT, reactor=None):
        """Wrap the xmlrpc call that returns "d" so that it is cancelled if
        it exceeds a timeout.

        :param d: The Deferred to cancel.
        :param timeout: timeout in seconds, defaults to 30.
        :param reactor: override the default reactor, useful for testing.
        """
        if reactor is None:
            reactor = default_reactor
        delayed_call = reactor.callLater(timeout, d.cancel)

        def cancel_timeout(passthrough):
            if not delayed_call.called:
                delayed_call.cancel()
            return passthrough
        return d.addBoth(cancel_timeout)

    def _issue_call(self, method, *args):
        """Initiate call to XMLRPC method.

        :param method: Name of XMLRPC method to invoke.
        :param *args: Arguments for the call.  If any of them is
            `token_placeholder`, the current security token will be
            substituted in its place.
        :return: `Deferred`.
        """
        # Twisted XMLRPC does not encode the method name, but breaks if
        # we give it in Unicode.  Encode it here; thankfully we're
        # dealing with ASCII only in method names.
        method = method.encode('ascii')
        args = map(self._substitute_token, args)
        d = self._with_timeout(self.proxy.callRemote(method, *args))
        return d

    @inlineCallbacks
    def call(self, method, *args):
        """Initiate call to XMLRPC `method` by name, through Twisted.

        This is for use by the Cobbler wrapper API only.  Don't call it
        directly; instead, ensure that the wrapper API supports the
        method you want to call.

        Initiates XMLRPC call, yields back to the reactor until it's ready
        with a response, then returns the response.  Use this as if it were
        a synchronous XMLRPC call; but be aware that it lets the reactor run
        other code in the meantime.

        :param method: Name of XMLRPC method to call.
        :param *args: Positional arguments for the XMLRPC call.
        :return: A `Deferred` representing the call.
        """
        original_state = self.record_state()
        uses_auth = (self.token_placeholder in args)
        need_auth = (uses_auth and self.token is None)
        if not need_auth:
            # It looks like we're authenticated.  Issue the call.  If we
            # then find out that our authentication token is invalid, we
            # can retry it later.
            try:
                result = yield self._issue_call(method, *args)
            except xmlrpclib.Fault as e:
                if uses_auth and looks_like_auth_expiry(e):
                    need_auth = True
                else:
                    raise

        if need_auth:
            # We weren't authenticated when we started, but we should be
            # now.  Make the final attempt.
            yield self._authenticate(original_state)
            result = yield self._issue_call(method, *args)
        returnValue(result)


class CobblerObjectType(type):
    """Metaclass of Cobbler objects."""

    def __new__(mtype, name, bases, attributes):
        """Build a new `CobblerObject` class.

        Ensure that `known_attributes` and `required_attributes` are both
        frozensets. This indicates that they should not be modified at
        run-time, and it also improves performance of several methods, most
        notably `_trim_attributes`.
        """
        if "known_attributes" in attributes:
            attributes["known_attributes"] = frozenset(
                attributes["known_attributes"])
        if "required_attributes" in attributes:
            attributes["required_attributes"] = frozenset(
                attributes["required_attributes"])
        return super(CobblerObjectType, mtype).__new__(
            mtype, name, bases, attributes)


class CobblerObject:
    """Abstract base class: a type of object in Cobbler's XMLRPC API.

    This defines the common interface to cobbler's distros, profiles,
    systems, and other objects it stores in its database and exposes
    through its API.  Implement a new type by inheriting from this class.
    """

    __metaclass__ = CobblerObjectType

    # What are objects of this type called in the Cobbler API?
    object_type = None

    # What's the plural of object_type, if not object_type + "s"?
    object_type_plural = None

    # What attributes do we expect to support for this type of object?
    # Only these attributes are allowed.  This is here to force us to
    # keep an accurate record of which attributes we use for which types
    # of objects.
    # Some attributes in Cobbler uses dashes as separators, others use
    # underscores.  In MaaS, use only underscores.
    known_attributes = []

    # What attributes does Cobbler require for this type of object?
    required_attributes = []

    def __init__(self, session, name):
        """Reference an object in Cobbler.

        :param session: A `CobblerSession`.
        :param name: Name for this object.
        """
        self.session = session
        self.name = name

    def _get_handle(self):
        """Retrieve the object's handle."""
        method = self._name_method('get_%s_handle')
        return self.session.call(
            method, self.name, self.session.token_placeholder)

    @classmethod
    def _name_method(cls, name_template, plural=False):
        """Interpolate object_type into a method name template.

        For example, on `CobblerSystem`, "get_%s_handle" would be
        interpolated into "get_system_handle" and "get_%s" with plural=True
        becomes "get_systems".
        """
        if plural:
            type_name = (cls.object_type_plural or '%ss' % cls.object_type)
        else:
            type_name = cls.object_type
        return name_template % type_name

    @classmethod
    def _normalize_attribute(cls, attribute_name):
        """Normalize an attribute name.

        Cobbler mixes dashes and underscores in attribute names.  MaaS may
        pass attributes as keyword arguments internally, where dashes are not
        an option.  Hide the distinction by looking up the proper name in
        `known_attributes`.

        :param attribute_name: An attribute name, possibly using underscores
            where Cobbler expects dashes.
        :return: A Cobbler-style attribute name, using either dashes or
            underscores as used by Cobbler.
        """
        if attribute_name in cls.known_attributes:
            # Already spelled the way Cobbler likes it.
            return attribute_name

        attribute_name = attribute_name.replace('_', '-')
        if attribute_name in cls.known_attributes:
            # Cobbler wants this one with dashes.
            return attribute_name

        attribute_name = attribute_name.replace('-', '_')
        assert attribute_name in cls.known_attributes, (
            "Unknown attribute for %s: %s."
            % (cls.object_type, attribute_name))
        return attribute_name

    @classmethod
    @inlineCallbacks
    def find(cls, session, **kwargs):
        """Find objects in the database.

        :param session: The `CobblerSession` to operate in.  No authentication
            is required.
        :param **kwargs: Optional search criteria, e.g.
            hostname="*.maas3.example.com" to limit the search to items with
            a hostname attribute that ends in ".maas3.example.com".
        :return: A list of matching `cls` objects.
        """
        method = cls._name_method("find_%s")
        criteria = dict(
            (cls._normalize_attribute(key), value)
            for key, value in kwargs.items())
        result = yield session.call(method, criteria)
        returnValue([cls(session, name) for name in result])

    @classmethod
    def _trim_attributes(cls, attributes):
        """Return a dict containing only keys from `known_attributes`.

        If `attributes` is `None` - which can happen when querying a
        non-existent object - this returns `None`.
        """
        if attributes is None:
            return None
        else:
            return {
                name: value
                for name, value in attributes.iteritems()
                if name in cls.known_attributes
                }

    @classmethod
    @inlineCallbacks
    def get_all_values(cls, session):
        """Load the attributes for all objects of this type.

        :return: A `Deferred` that delivers a dict, mapping objects' names
            to dicts containing their respective attributes.
        """
        method = cls._name_method("get_%s", plural=True)
        results = yield session.call(method)
        results = (cls._trim_attributes(result) for result in results)
        returnValue(dict((obj['name'], obj) for obj in results))

    def get_values(self):
        """Load the object's attributes as a dict.

        :return: A `Deferred` that delivers a dict containing the object's
            attribute names and values.
        """
        d = self.session.call(self._name_method("get_%s"), self.name)
        d.addCallback(self._trim_attributes)
        return d

    @classmethod
    @inlineCallbacks
    def new(cls, session, name, attributes):
        """Create an object in Cobbler.

        :param session: A `CobblerSession` to operate in.
        :param name: Identifying name for the new object.
        :param attributes: Dict mapping attribute names to values.
        """
        if 'name' in attributes:
            assert attributes['name'] == name, (
                "Creating %s called '%s', but 'name' attribute is '%s'."
                % (cls.object_type, name, attributes['name']))
        else:
            attributes['name'] = name
        missing_attributes = (
            set(cls.required_attributes).difference(attributes))
        assert len(missing_attributes) == 0, (
            "Required attributes for %s missing: %s"
            % (cls.object_type, missing_attributes))

        args = dict(
            (cls._normalize_attribute(key), value)
            for key, value in attributes.iteritems())

        # Overwrite any existing object of the same name.  Unfortunately
        # this parameter goes into the "attributes," and seems to be
        # stored along with them.  Its value doesn't matter.
        args.setdefault('clobber', True)

        success = yield session.call(
            'xapi_object_edit', cls.object_type, name, 'add', args,
            session.token_placeholder)
        if not success:
            raise RuntimeError(
                "Cobbler refused to create %s '%s'.  Attributes: %s"
                % (cls.object_type, name, args))
        returnValue(cls(session, name))

    @inlineCallbacks
    def modify(self, delta):
        """Modify an object in Cobbler.

        :param name: Identifying name for the existing object.
        :param attributes: Dict mapping attribute names to values.
        """
        args = dict(
            (self._normalize_attribute(key), value)
            for key, value in delta.iteritems())
        # TODO: Restrict delta in the same way that known_attributes is used
        # to restrict attributes during object creations.
        success = yield self.session.call(
            'xapi_object_edit', self.object_type, self.name, 'edit', args,
            self.session.token_placeholder)
        if not success:
            raise RuntimeError(
                "Cobbler refused to modify %s '%s'.  Attributes: %s"
                % (self.object_type, self.name, args))

    @inlineCallbacks
    def delete(self, recurse=True):
        """Delete this object.  Its name must be known.

        :param recurse: Delete dependent objects recursively?
        """
        assert self.name is not None, (
            "Can't delete %s; don't know its name." % self.object_type)
        method = self._name_method('remove_%s')
        yield self.session.call(
            method, self.name, self.session.token_placeholder, recurse)


class CobblerProfile(CobblerObject):
    """A profile.

    See `CobblerObject` for common object-management properties.
    """
    object_type = 'profile'
    known_attributes = [
        'distro',
        'comment',
        'enable-menu',
        'kickstart',
        'kopts',
        'kopts_post'
        'mgmt_classes',
        'name',
        'name_servers',
        'name_servers_search',
        'owners',
        'repos',
        'template-files',
        'virt_auto_boot',
        'virt_bridge',
        'virt_cpus',
        'virt_file_size',
        'virt_disk_driver',
        'virt_path',
        'virt_ram',
        ]
    required_attributes = [
        'name',
        'distro',
        ]


class CobblerImage(CobblerObject):
    """An operating system image.

    See `CobblerObject` for common object-management properties.
    """
    object_type = "image"
    known_attributes = [
        'arch',
        # Set breed to 'debian' for Ubuntu.
        'breed',
        'comment',
        'file',
        'image_type',
        'name',
        'os_version',
        'owners',
        'virt_auto_boot',
        'virt_bridge',
        'virt_cpus',
        'virt_disk_driver',
        'virt_file_size',
        'virt_path',
        'virt_ram',
        'virt_type',
        ]


class CobblerDistro(CobblerObject):
    """A distribution.

    See `CobblerObject` for common object-management properties.
    """
    object_type = 'distro'
    known_attributes = [
        'breed',
        'comment',
        # Path to initrd image:
        'initrd',
        # Path to kernel:
        'kernel',
        'kopts',
        'ksmeta',
        'mgmt-classes',
        # Identifier:
        'name',
        'os-version',
        'owners',
        'template-files',
        ]
    required_attributes = [
        'initrd',
        'kernel',
        'name',
        ]


class CobblerRepo(CobblerObject):
    """A repository.

    See `CobblerObject` for common object-management properties.
    """
    object_type = 'repo'
    known_attributes = [
        'arch',
        'comment',
        'createrepo_flags',
        'environment',
        'keep_updated',
        'mirror',
        'mirror_locally',
        'name',
        'owners',
        'priority',
        ]
    required_attributes = [
        'name',
        'mirror',
        ]


class CobblerSystem(CobblerObject):
    """A computer (node) on the network.

    See `CobblerObject` for common object-management properties.
    """
    object_type = 'system'
    known_attributes = [
        'boot_files',
        'comment',
        'fetchable_files',
        'gateway',
        # FQDN:
        'hostname',
        # Space-separated key=value pairs:
        'kernel_options'
        'kickstart',
        'kopts',
        'kopts_post',
        # Space-separated key=value pairs for preseed:
        'ks_meta',
        'mgmt_classes',
        # A special dict; see below.
        'modify_interface',
        # Unqualified host name:
        'name',
        'name_servers',
        'name_servers_search',
        # Bool.
        'netboot_enabled',
# TODO: Is this for ILO?
        'power_address',
        'power_id',
        'power_pass',
        'power_type',
        'power_user',
        # Conventionally a distroseries-architecture combo.
        'profile',
        'template_files',
        'uid',
        'virt_path',
        'virt_type',
        ]
    required_attributes = [
        'name',
        'profile',
        ]

    # The modify_interface dict can contain:
    #  * "macaddress-eth0" etc.
    #  * "ipaddress-eth0" etc.
    #  * "dnsname-eth0" etc.

    @classmethod
    def _callPowerMultiple(cls, session, operation, system_names):
        """Call API's "background_power_system" method.

        :return: Deferred.
        """
        d = session.call(
            'background_power_system',
            {'power': operation, 'systems': system_names},
            session.token_placeholder)
        return d

    @classmethod
    def powerOnMultiple(cls, session, system_names):
        """Initiate power-on for multiple systems.

        There is no notification; we don't know if it succeeds or fails.

        :return: Deferred.
        """
        return cls._callPowerMultiple(session, 'on', system_names)

    @classmethod
    def powerOffMultiple(cls, session, system_names):
        """Initiate power-off for multiple systems.

        There is no notification; we don't know if it succeeds or fails.

        :return: Deferred.
        """
        return cls._callPowerMultiple(session, 'off', system_names)

    @classmethod
    def rebootMultiple(cls, session, system_names):
        """Initiate reboot for multiple systems.

        There is no notification; we don't know if it succeeds or fails.

        :return: Deferred.
        """
        return cls._callPowerMultiple(session, 'reboot', system_names)

    @inlineCallbacks
    def _callPower(self, operation):
        """Call API's "power_system" method."""
        handle = yield self._get_handle()
        yield self.session.call(
            'power_system', handle, operation,
            self.session.token_placeholder)

    def powerOn(self):
        """Turn system on.

        :return: Deferred.
        """
        return self._callPower('on')

    def powerOff(self):
        """Turn system on.

        :return: Deferred.
        """
        return self._callPower('off')

    def reboot(self):
        """Turn system on.

        :return: Deferred.
        """
        return self._callPower('reboot')


class CobblerPreseeds:
    """Manage preseeds."""

    def __init__(self, session):
        self.session = session

    def read_template(self, path):
        """Read a preseed template.

        :return: Deferred.
        """
        return self.session.call(
            'read_or_write_kickstart_template', path, True, '',
            self.session.token_placeholder)

    def write_template(self, path, contents):
        """Write a preseed template.

        :param path: Filesystem path for the template.  Must be in
            /var/lib/cobbler/kickstarts or /etc/cobbler
        :param contents: Text of the template.
        :return: Deferred.
        """
        return self.session.call(
            'read_or_write_kickstart_template', path, False, contents,
            self.session.token_placeholder)

    def get_templates(self):
        """Return the registered preseed templates."""
        return self.session.call(
            'get_kickstart_templates', self.session.token_placeholder)

    def read_snippet(self, path):
        """Read a preseed snippet.

        :return: Deferred.
        """
        return self.session.call(
            'read_or_write_snippet', path, True, '',
            self.session.token_placeholder)

    def write_snippet(self, path, contents):
        """Write a preseed snippet.

        :param path: Filesystem path for the snippet.  Must be in
            /var/lib/cobbler/snippets
        :param contents: Text of the snippet.
        :return: Deferred.
        """
        return self.session.call(
            'read_or_write_snippet', path, False, contents,
            self.session.token_placeholder)

    def get_snippets(self):
        """Return the registered preseed snippets."""
        return self.session.call(
            'get_snippets', self.session.token_placeholder)

    def sync_netboot_configs(self):
        """Update netmasq and tftpd configurations.

        :return: Deferred.
        """
        return self.session.call('sync', self.session.token_placeholder)
