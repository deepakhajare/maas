# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Node objects."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "CONSTRAINTS_JUJU_MAP",
    "CONSTRAINTS_MAAS_MAP",
    "NODE_TRANSITIONS",
    "Node",
    "update_hardware_details",
    ]

from itertools import (
    imap,
    islice,
    repeat,
    )
import math
import random
from string import whitespace
from uuid import uuid1

from django.contrib.auth.models import User
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    )
from django.db.models import (
    BooleanField,
    CharField,
    ForeignKey,
    IntegerField,
    Manager,
    ManyToManyField,
    Q,
    )
from django.shortcuts import get_object_or_404
from lxml import etree
from maasserver import DefaultMeta
from maasserver.enum import (
    ARCHITECTURE,
    ARCHITECTURE_CHOICES,
    DISTRO_SERIES,
    DISTRO_SERIES_CHOICES,
    NODE_AFTER_COMMISSIONING_ACTION,
    NODE_AFTER_COMMISSIONING_ACTION_CHOICES,
    NODE_PERMISSION,
    NODE_STATUS,
    NODE_STATUS_CHOICES,
    NODE_STATUS_CHOICES_DICT,
    )
from maasserver.exceptions import NodeStateViolation
from maasserver.fields import (
    JSONObjectField,
    XMLField,
    )
from maasserver.models.cleansave import CleanSave
from maasserver.models.config import Config
from maasserver.models.dhcplease import DHCPLease
from maasserver.models.tag import Tag
from maasserver.models.timestampedmodel import TimestampedModel
from maasserver.utils import (
    get_db_state,
    strip_domain,
    )
from maasserver.utils.orm import (
    get_first,
    get_one,
    )
from piston.models import Token
from provisioningserver.enum import (
    POWER_TYPE,
    POWER_TYPE_CHOICES,
    )
from provisioningserver.tasks import (
    power_off,
    power_on,
    remove_dhcp_host_map,
    )


def generate_node_system_id():
    return 'node-%s' % uuid1()


# Mapping of constraint names as used by juju to Node field names
CONSTRAINTS_JUJU_MAP = {
    'maas-name': 'hostname',
    'maas-tags': 'tags',
    'arch': 'architecture',
    'cpu': 'cpu_count',
    'mem': 'memory',
    }


# Mapping of constraint names as used by the maas api to Node field names
CONSTRAINTS_MAAS_MAP = {
    'name': 'hostname',
    'tags': 'tags',
    'arch': 'architecture',
    'cpu_count': 'cpu_count',
    'mem': 'memory',
    }


# Information about valid node status transitions.
# The format is:
# {
#  old_status1: [
#      new_status11,
#      new_status12,
#      new_status13,
#      ],
# ...
# }
#
NODE_TRANSITIONS = {
    None: [
        NODE_STATUS.DECLARED,
        NODE_STATUS.MISSING,
        NODE_STATUS.RETIRED,
        ],
    NODE_STATUS.DECLARED: [
        NODE_STATUS.COMMISSIONING,
        NODE_STATUS.MISSING,
        NODE_STATUS.READY,
        NODE_STATUS.RETIRED,
        ],
    NODE_STATUS.COMMISSIONING: [
        NODE_STATUS.FAILED_TESTS,
        NODE_STATUS.READY,
        NODE_STATUS.RETIRED,
        NODE_STATUS.MISSING,
        ],
    NODE_STATUS.FAILED_TESTS: [
        NODE_STATUS.COMMISSIONING,
        NODE_STATUS.MISSING,
        NODE_STATUS.RETIRED,
        ],
    NODE_STATUS.READY: [
        NODE_STATUS.ALLOCATED,
        NODE_STATUS.RESERVED,
        NODE_STATUS.RETIRED,
        NODE_STATUS.MISSING,
        ],
    NODE_STATUS.RESERVED: [
        NODE_STATUS.READY,
        NODE_STATUS.ALLOCATED,
        NODE_STATUS.RETIRED,
        NODE_STATUS.MISSING,
        ],
    NODE_STATUS.ALLOCATED: [
        NODE_STATUS.READY,
        NODE_STATUS.RETIRED,
        NODE_STATUS.MISSING,
        ],
    NODE_STATUS.MISSING: [
        NODE_STATUS.DECLARED,
        NODE_STATUS.READY,
        NODE_STATUS.ALLOCATED,
        NODE_STATUS.COMMISSIONING,
        ],
    NODE_STATUS.RETIRED: [
        NODE_STATUS.DECLARED,
        NODE_STATUS.READY,
        NODE_STATUS.MISSING,
        ],
    }


class NodeManager(Manager):
    """A utility to manage the collection of Nodes."""

    def filter_by_ids(self, query, ids=None):
        """Filter `query` result set by system_id values.

        :param query: A QuerySet of Nodes.
        :type query: django.db.models.query.QuerySet_
        :param ids: Optional set of ids to filter by.  If given, nodes whose
            system_ids are not in `ids` will be ignored.
        :type param_ids: Sequence
        :return: A filtered version of `query`.

        .. _django.db.models.query.QuerySet: https://docs.djangoproject.com/
           en/dev/ref/models/querysets/

        """
        if ids is None:
            return query
        else:
            return query.filter(system_id__in=ids)

    def get_nodes(self, user, perm, ids=None, prefetch_mac=False):
        """Fetch Nodes on which the User_ has the given permission.

        :param user: The user that should be used in the permission check.
        :type user: User_
        :param perm: The permission to check.
        :type perm: a permission string from NODE_PERMISSION
        :param ids: If given, limit result to nodes with these system_ids.
        :type ids: Sequence.
        :param prefetch_mac: If set to True, prefetch the macaddress_set
            values. This is useful for UI stuff that uses MAC addresses in the
            http links.

        .. _User: https://
           docs.djangoproject.com/en/dev/topics/auth/
           #django.contrib.auth.models.User

        """
        if user.is_superuser:
            nodes = self.all()
        else:
            if perm == NODE_PERMISSION.VIEW:
                nodes = self.filter(Q(owner__isnull=True) | Q(owner=user))
            elif perm == NODE_PERMISSION.EDIT:
                nodes = self.filter(owner=user)
            elif perm == NODE_PERMISSION.ADMIN:
                nodes = self.none()
            else:
                raise NotImplementedError(
                    "Invalid permission check (invalid permission name: %s)." %
                    perm)

        if prefetch_mac:
            nodes = nodes.prefetch_related('macaddress_set')
        return self.filter_by_ids(nodes, ids)

    def get_allocated_visible_nodes(self, token, ids):
        """Fetch Nodes that were allocated to the User_/oauth token.

        :param user: The user whose nodes to fetch
        :type user: User_
        :param token: The OAuth token associated with the Nodes.
        :type token: piston.models.Token.
        :param ids: Optional set of IDs to filter by. If given, nodes whose
            system_ids are not in `ids` will be ignored.
        :type param_ids: Sequence

        .. _User: https://
           docs.djangoproject.com/en/dev/topics/auth/
           #django.contrib.auth.models.User
        """
        if ids is None:
            nodes = self.filter(token=token)
        else:
            nodes = self.filter(token=token, system_id__in=ids)
        return nodes

    def get_node_or_404(self, system_id, user, perm):
        """Fetch a `Node` by system_id.  Raise exceptions if no `Node` with
        this system_id exist or if the provided user has not the required
        permission on this `Node`.

        :param name: The system_id.
        :type name: str
        :param user: The user that should be used in the permission check.
        :type user: django.contrib.auth.models.User
        :param perm: The permission to assert that the user has on the node.
        :type perm: basestring
        :raises: django.http.Http404_,
            :class:`maasserver.exceptions.PermissionDenied`.

        .. _django.http.Http404: https://
           docs.djangoproject.com/en/dev/topics/http/views/
           #the-http404-exception
        """
        node = get_object_or_404(Node, system_id=system_id)
        if user.has_perm(perm, node):
            return node
        else:
            raise PermissionDenied()

    def get_available_node_for_acquisition(self, for_user, constraints=None):
        """Find a `Node` to be acquired by the given user.

        :param for_user: The user who is to acquire the node.
        :type for_user: :class:`django.contrib.auth.models.User`
        :param constraints: Optional selection constraints.  If given, only
            nodes matching these constraints are considered.
        :type constraints: :class:`dict`
        :return: A matching `Node`, or None if none are available.
        """
        from maasserver.models.node_constraint_filter import constrain_nodes
        available_nodes = self.get_nodes(for_user, NODE_PERMISSION.VIEW)
        available_nodes = available_nodes.filter(status=NODE_STATUS.READY)
        available_nodes = constrain_nodes(available_nodes, constraints)
        return get_first(available_nodes)

    def stop_nodes(self, ids, by_user):
        """Request on given user's behalf that the given nodes be shut down.

        Shutdown is only requested for nodes that the user has ownership
        privileges for; any other nodes in the request are ignored.

        :param ids: The `system_id` values for nodes to be shut down.
        :type ids: Sequence
        :param by_user: Requesting user.
        :type by_user: User_
        :return: Those Nodes for which shutdown was actually requested.
        :rtype: list
        """
        nodes = self.get_nodes(by_user, NODE_PERMISSION.EDIT, ids=ids)
        processed_nodes = []
        for node in nodes:
            power_params = node.get_effective_power_parameters()
            node_power_type = node.get_effective_power_type()
            # WAKE_ON_LAN does not support poweroff.
            if node_power_type != POWER_TYPE.WAKE_ON_LAN:
                power_off.apply_async(
                    queue=node.work_queue, args=[node_power_type],
                    kwargs=power_params)
            processed_nodes.append(node)
        return processed_nodes

    def start_nodes(self, ids, by_user, user_data=None):
        """Request on given user's behalf that the given nodes be started up.

        Power-on is only requested for nodes that the user has ownership
        privileges for; any other nodes in the request are ignored.

        :param ids: The `system_id` values for nodes to be started.
        :type ids: Sequence
        :param by_user: Requesting user.
        :type by_user: User_
        :param user_data: Optional blob of user-data to be made available to
            the nodes through the metadata service.  If not given, any
            previous user data is used.
        :type user_data: basestring
        :return: Those Nodes for which power-on was actually requested.
        :rtype: list
        """
        # Avoid circular imports.
        from metadataserver.models import NodeUserData

        nodes = self.get_nodes(by_user, NODE_PERMISSION.EDIT, ids=ids)
        for node in nodes:
            NodeUserData.objects.set_user_data(node, user_data)
        processed_nodes = []
        for node in nodes:
            power_params = node.get_effective_power_parameters()
            node_power_type = node.get_effective_power_type()
            if node_power_type == POWER_TYPE.WAKE_ON_LAN:
                mac = power_params.get('mac_address')
                do_start = (mac != '' and mac is not None)
            else:
                do_start = True
            if do_start:
                power_on.apply_async(
                    queue=node.work_queue, args=[node_power_type],
                    kwargs=power_params)
                processed_nodes.append(node)
        return processed_nodes


_xpath_processor_count = "count(//node[@id='core']/node[@class='processor'])"

# Some machines have a <size> element in their memory <node> with the total
# amount of memory, and other machines declare the size of the memory in
# individual memory banks. This expression is mean to cope with both.

_xpath_memory_bytes = (
    "sum(//node[@id='memory']/size[@units='bytes']"
        "|//node[starts-with(@id, 'memory:')]"
            "/node[starts-with(@id, 'bank:')]/size[@units='bytes'])"
       "div 1024 div 1024")


def update_hardware_details(node, xmlbytes, tag_manager):
    """Set node hardware_details from lshw output and update related fields

    This is a helper function just so it can be used in the south migration
    to do the correct updates to mem and cpu_count when hardware_details is
    first set.
    """
    try:
        doc = etree.XML(xmlbytes)
    except etree.XMLSyntaxError as e:
        raise ValidationError(
            {'hardware_details': ['Invalid XML: %s' % (e,)]})
    node.hardware_details = xmlbytes
    # Same document, many queries: use XPathEvaluator.
    evaluator = etree.XPathEvaluator(doc)
    cpu_count = evaluator(_xpath_processor_count)
    memory = evaluator(_xpath_memory_bytes)
    if not memory or math.isnan(memory):
        memory = 0
    node.cpu_count = cpu_count or 0
    node.memory = memory
    for tag in tag_manager.all():
        has_tag = evaluator(tag.definition)
        if has_tag:
            node.tags.add(tag)
        else:
            node.tags.remove(tag)
    node.save()


# Non-ambiguous characters (i.e. without 'ilousvz1250').
non_ambiguous_characters = imap(
    random.choice, repeat('abcdefghjkmnpqrtwxy346789'))


def generate_hostname(size):
    """Generate a hostname using only non-ambiguous characters."""
    return "".join(islice(non_ambiguous_characters, size))


class Node(CleanSave, TimestampedModel):
    """A `Node` represents a physical machine used by the MAAS Server.

    :ivar system_id: The unique identifier for this `Node`.
        (e.g. 'node-41eba45e-4cfa-11e1-a052-00225f89f211').
    :ivar hostname: This `Node`'s hostname.
    :ivar status: This `Node`'s status. See the vocabulary
        :class:`NODE_STATUS`.
    :ivar owner: This `Node`'s owner if it's in use, None otherwise.
    :ivar after_commissioning_action: The action to perform after
        commissioning. See vocabulary
        :class:`NODE_AFTER_COMMISSIONING_ACTION`.
    :ivar power_type: The :class:`POWER_TYPE` that determines how this
        node will be powered on.  If not given, the default will be used as
        configured in the `node_power_type` setting.
    :ivar nodegroup: The `NodeGroup` this `Node` belongs to.
    :ivar tags: The list of :class:`Tag`s associated with this `Node`.
    :ivar objects: The :class:`NodeManager`.

    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    system_id = CharField(
        max_length=41, unique=True, default=generate_node_system_id,
        editable=False)

    hostname = CharField(max_length=255, default='', blank=True, unique=True)

    status = IntegerField(
        max_length=10, choices=NODE_STATUS_CHOICES, editable=False,
        default=NODE_STATUS.DEFAULT_STATUS)

    owner = ForeignKey(
        User, default=None, blank=True, null=True, editable=False)

    after_commissioning_action = IntegerField(
        choices=NODE_AFTER_COMMISSIONING_ACTION_CHOICES,
        default=NODE_AFTER_COMMISSIONING_ACTION.DEFAULT)

    distro_series = CharField(
        max_length=10, choices=DISTRO_SERIES_CHOICES, null=True,
        blank=True, default='')

    distro_series = CharField(
        max_length=10, choices=DISTRO_SERIES_CHOICES, null=True,
        blank=True, default=None)

    architecture = CharField(
        max_length=31, choices=ARCHITECTURE_CHOICES, blank=False,
        default=ARCHITECTURE.i386)

    # Juju expects the following standard constraints, which are stored here
    # as a basic optimisation over querying the hardware_details field.
    cpu_count = IntegerField(default=0)
    memory = IntegerField(default=0)

    hardware_details = XMLField(default=None, blank=True, null=True)

    # For strings, Django insists on abusing the empty string ("blank")
    # to mean "none."
    power_type = CharField(
        max_length=10, choices=POWER_TYPE_CHOICES, null=False, blank=True,
        default=POWER_TYPE.DEFAULT)

    # JSON-encoded set of parameters for power control.
    power_parameters = JSONObjectField(blank=True, default="")

    token = ForeignKey(
        Token, db_index=True, null=True, editable=False, unique=False)

    error = CharField(max_length=255, blank=True, default='')

    netboot = BooleanField(default=True)

    # This field can't be null, but we can't enforce that in the
    # database schema because we can only create the default value from
    # a complete schema, after schema migration.  We can't use custom
    # model validation either, because the node forms need to set their
    # default values *after* saving the form (with commit=False), which
    # incurs validation before the default values are set.
    # So all we can do is set blank=False, and make the field editable
    # to cajole Django out of skipping it during "model" (actually model
    # form) validation.
    nodegroup = ForeignKey(
        'maasserver.NodeGroup', editable=True, null=True, blank=False)

    tags = ManyToManyField(Tag)

    objects = NodeManager()

    def __unicode__(self):
        if self.hostname:
            return "%s (%s)" % (self.system_id, self.fqdn)
        else:
            return self.system_id

    @property
    def fqdn(self):
        """Fully qualified domain name for this node.

        If MAAS manages DNS for this node, the domain part of the
        hostname (if present), is replaced by the domain configured
        on the cluster controller.
        If not, simply return the node's hostname.
        """
        # Avoid circular imports.
        from maasserver.dns import is_dns_managed
        if is_dns_managed(self.nodegroup):
            # If the hostname field contains a domain, strip it.
            hostname = strip_domain(self.hostname)
            # Build the FQDN by using the hostname and nodegroup.name
            # as the domain name.
            return '%s.%s' % (hostname, self.nodegroup.name)
        else:
            return self.hostname

    def tag_names(self):
        # We don't use self.tags.values_list here because this does not
        # take advantage of the cache.
        return [tag.name for tag in self.tags.all()]

    def clean_status(self):
        """Check a node's status transition against the node-status FSM."""
        old_status = get_db_state(self, 'status')
        if self.status == old_status:
            # No transition is always a safe transition.
            pass
        elif self.status in NODE_TRANSITIONS.get(old_status, ()):
            # Valid transition.
            pass
        else:
            # Transition not permitted.
            error_text = "Invalid transition: %s -> %s." % (
                NODE_STATUS_CHOICES_DICT.get(old_status, "Unknown"),
                NODE_STATUS_CHOICES_DICT.get(self.status, "Unknown"),
                )
            raise NodeStateViolation(error_text)

    def clean(self, *args, **kwargs):
        super(Node, self).clean(*args, **kwargs)
        self.clean_status()

    def display_status(self):
        """Return status text as displayed to the user.

        The UI representation is taken from NODE_STATUS_CHOICES_DICT and may
        interpolate the variable "owner" to reflect the username of the node's
        current owner, if any.
        """
        status_text = NODE_STATUS_CHOICES_DICT[self.status]
        if self.status == NODE_STATUS.ALLOCATED:
            # The User is represented as its username in interpolation.
            # Don't just say self.owner.username here, or there will be
            # trouble with unowned nodes!
            return "%s to %s" % (status_text, self.owner)
        else:
            return status_text

    def add_mac_address(self, mac_address):
        """Add a new MAC address to this `Node`.

        :param mac_address: The MAC address to be added.
        :type mac_address: basestring
        :raises: django.core.exceptions.ValidationError_

        .. _django.core.exceptions.ValidationError: https://
           docs.djangoproject.com/en/dev/ref/exceptions/
           #django.core.exceptions.ValidationError
        """
        # Avoid circular imports
        from maasserver.models import MACAddress

        mac = MACAddress(mac_address=mac_address, node=self)
        mac.save()
        return mac

    def remove_mac_address(self, mac_address):
        """Remove a MAC address from this `Node`.

        :param mac_address: The MAC address to be removed.
        :type mac_address: str

        """
        # Avoid circular imports
        from maasserver.models import MACAddress

        mac = MACAddress.objects.get(mac_address=mac_address, node=self)
        if mac:
            mac.delete()

    def accept_enlistment(self, user):
        """Accept this node's (anonymous) enlistment.

        This call makes sense only on a node in Declared state, i.e. one that
        has been anonymously enlisted and is now waiting for a MAAS user to
        accept that enlistment as authentic.  Calling it on a node that is in
        Ready or Commissioning state, however, is not an error -- it probably
        just means that somebody else has beaten you to it.

        :return: This node if it has made the transition from Declared, or
            None if it was already in an accepted state.
        """
        accepted_states = [NODE_STATUS.READY, NODE_STATUS.COMMISSIONING]
        if self.status in accepted_states:
            return None
        if self.status != NODE_STATUS.DECLARED:
            raise NodeStateViolation(
                "Cannot accept node enlistment: node %s is in state %s."
                % (self.system_id, NODE_STATUS_CHOICES_DICT[self.status]))

        self.start_commissioning(user)
        return self

    def start_commissioning(self, user):
        """Install OS and self-test a new node."""
        # Avoid circular imports.
        from metadataserver.commissioning.user_data import generate_user_data
        from metadataserver.models import NodeCommissionResult

        commissioning_user_data = generate_user_data()
        NodeCommissionResult.objects.clear_results(self)
        self.status = NODE_STATUS.COMMISSIONING
        self.owner = user
        self.save()
        # The commissioning profile is handled in start_nodes.
        Node.objects.start_nodes(
            [self.system_id], user, user_data=commissioning_user_data)

    def delete(self):
        # Allocated nodes can't be deleted.
        if self.status == NODE_STATUS.ALLOCATED:
            raise NodeStateViolation(
                "Cannot delete node %s: node is in state %s."
                % (self.system_id, NODE_STATUS_CHOICES_DICT[self.status]))
        nodegroup = self.nodegroup
        if nodegroup.get_managed_interface() is not None:
            # Delete the host map(s) in the DHCP server.
            macs = self.macaddress_set.values_list('mac_address', flat=True)
            leases = DHCPLease.objects.filter(
                mac__in=macs, nodegroup=nodegroup)
            for lease in leases:
                task_kwargs = dict(
                    ip_address=lease.ip,
                    server_address="127.0.0.1",
                    omapi_key=nodegroup.dhcp_key)
                remove_dhcp_host_map.apply_async(
                    queue=nodegroup.uuid, kwargs=task_kwargs)
        # Delete the related mac addresses.
        self.macaddress_set.all().delete()

        super(Node, self).delete()

    def set_random_hostname(self):
        """Set 5 character `hostname` using non-ambiguous characters.

        Using 5 letters from the set 'abcdefghjkmnpqrtwxy346789' we get
        9,765,625 combinations (pow(25, 5)).

        Note that having a hostname starting with a number is perfectly
        valid, see
        http://en.wikipedia.org/wiki/Hostname#Restrictions_on_valid_host_names
        """
        domain = Config.objects.get_config("enlistment_domain")
        domain = domain.strip("." + whitespace)
        while True:
            new_hostname = generate_hostname(5)
            if len(domain) > 0:
                self.hostname = "%s.%s" % (new_hostname, domain)
            else:
                self.hostname = "%s" % new_hostname
            try:
                self.save()
            except ValidationError:
                pass
            else:
                break

    def get_effective_power_type(self):
        """Get power-type to use for this node.

        If no power type has been set for the node, get the configured
        default.
        """
        if self.power_type == POWER_TYPE.DEFAULT:
            power_type = Config.objects.get_config('node_power_type')
            if power_type == POWER_TYPE.DEFAULT:
                raise ValueError(
                    "Node power type is set to the default, but "
                    "the default is not yet configured.  The default "
                    "needs to be configured to another, more useful value.")
        else:
            power_type = self.power_type
        return power_type

    def get_primary_mac(self):
        """Return the primary :class:`MACAddress` for this node."""
        macs = self.macaddress_set.order_by('created')[:1]
        if len(macs) > 0:
            return macs[0]
        else:
            return None

    def get_effective_kernel_options(self):
        """Determine any special kernel parameters for this node.

        :return: (tag, kernel_options)
            tag is a Tag object or None. If None, the kernel_options came from
            the global setting.
            kernel_options, a string indicating extra kernel_options that
            should be used when booting this node. May be None if no tags match
            and no global setting has been configured.
        """
        # First, see if there are any tags associated with this node that has a
        # custom kernel parameter
        tags = self.tags.filter(kernel_opts__isnull=False)
        tags = tags.order_by('name')[:1]
        tag = get_one(tags)
        if tag is not None:
            return tag, tag.kernel_opts
        global_value = Config.objects.get_config('kernel_opts')
        return None, global_value

    @property
    def work_queue(self):
        """The name of the queue for tasks specific to this node."""
        return self.nodegroup.work_queue

    def get_distro_series(self):
        """Return the distro series to install that node."""
        use_default_distro_series = (
            not self.distro_series or
            self.distro_series == DISTRO_SERIES.default)
        if use_default_distro_series:
            return Config.objects.get_config('default_distro_series')
        else:
            return self.distro_series

    def set_distro_series(self, series=''):
        """Set the distro series to install that node."""
        self.distro_series = series
        self.save()

    def get_effective_power_parameters(self):
        """Return effective power parameters, including any defaults."""
        if self.power_parameters:
            power_params = self.power_parameters.copy()
        else:
            # An empty power_parameters comes out as an empty unicode string!
            power_params = {}

        power_params.setdefault('system_id', self.system_id)
        power_params.setdefault('virsh', '/usr/bin/virsh')
        power_params.setdefault('fence_cdu', '/usr/sbin/fence_cdu')
        power_params.setdefault('ipmipower', '/usr/sbin/ipmipower')
        power_params.setdefault(
            'ipmi_chassis_config', '/usr/sbin/ipmi-chassis-config')
        power_params.setdefault('ipmi_config', 'ipmi.conf')
        power_params.setdefault('power_address', 'qemu://localhost/system')
        power_params.setdefault('username', '')
        power_params.setdefault('power_id', self.system_id)
        power_params.setdefault('power_driver', '')

        # The "mac" parameter defaults to the node's primary MAC
        # address, but only if no power parameters were set at all.
        if not self.power_parameters:
            primary_mac = self.get_primary_mac()
            if primary_mac is not None:
                power_params['mac_address'] = primary_mac.mac_address
        return power_params

    def acquire(self, user, token=None):
        """Mark commissioned node as acquired by the given user and token."""
        assert self.owner is None
        assert token is None or token.user == user
        self.status = NODE_STATUS.ALLOCATED
        self.owner = user
        self.token = token
        self.save()

    def release(self):
        """Mark allocated or reserved node as available again and power off."""
        Node.objects.stop_nodes([self.system_id], self.owner)
        self.status = NODE_STATUS.READY
        self.owner = None
        self.token = None
        self.set_netboot()
        self.save()

    def set_netboot(self, on=True):
        """Set netboot on or off."""
        self.netboot = on
        self.save()

    def set_hardware_details(self, xmlbytes):
        """Set the `lshw -xml` output"""
        update_hardware_details(self, xmlbytes, Tag.objects)
