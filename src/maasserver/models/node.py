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
    "NODE_TRANSITIONS",
    "Node",
    "update_hardware_details",
    ]

import contextlib
import os
from string import whitespace
from uuid import uuid1

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    )
from django.db import connection
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
from maasserver.models.tag import Tag
from maasserver.models.timestampedmodel import TimestampedModel
from maasserver.utils import get_db_state
from maasserver.utils.orm import get_first
from piston.models import Token
from provisioningserver.enum import (
    POWER_TYPE,
    POWER_TYPE_CHOICES,
    )
from provisioningserver.tasks import (
    power_off,
    power_on,
    )


def generate_node_system_id():
    return 'node-%s' % uuid1()


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

    def get_nodes(self, user, perm, ids=None):
        """Fetch Nodes on which the User_ has the given permission.

        :param user: The user that should be used in the permission check.
        :type user: User_
        :param perm: The permission to check.
        :type perm: a permission string from NODE_PERMISSION
        :param ids: If given, limit result to nodes with these system_ids.
        :type ids: Sequence.

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
        if constraints is None:
            constraints = {}
        available_nodes = (
            self.get_nodes(for_user, NODE_PERMISSION.VIEW)
                .filter(status=NODE_STATUS.READY))

        if constraints.get('name'):
            available_nodes = available_nodes.filter(
                hostname=constraints['name'])
        if constraints.get('arch'):
            # GZ 2012-09-11: This only supports an exact match on arch type,
            #                using an i386 image on amd64 hardware will wait.
            available_nodes = available_nodes.filter(
                architecture=constraints['arch'])

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
                power_off.delay(node_power_type, **power_params)
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
                power_on.delay(node_power_type, **power_params)
                processed_nodes.append(node)
        return processed_nodes


def update_hardware_details(node, xmlbytes):
    """Set node hardware_details from lshw output and update related fields

    This is designed to be called with individual nodes on commissioning and
    is not optimised for batch updates.

    There are a bunch of suboptimal things here:
    * Is a function rather than method in hope south migration can reuse.
    * Doing UPDATE then transaction.commit_unless_managed doesn't work?
    * Scalar returns from xpath() work in postgres 9.2 or later only.
    """
    node.hardware_details = xmlbytes
    node.save()
    with contextlib.closing(connection.cursor()) as cursor:
        cursor.execute("SELECT"
            " array_length(xpath(%s, hardware_details), 1) AS count,"
            " (xpath(%s, hardware_details))[1]::text::bigint / 1048576 AS mem"
            " FROM maasserver_node"
            " WHERE id = %s",
            [
                "//node[@id='core']/node[@class='processor']",
                "//node[@id='memory']/size[@units='bytes']/text()",
                node.id,
            ])
        cpu_count, memory = cursor.fetchone()
        node.cpu_count = cpu_count or 0
        node.memory = memory or 0
        for tag in Tag.objects.all():
            cursor.execute(
                "SELECT xpath_exists(%s, hardware_details)"
                " FROM maasserver_node WHERE id = %s",
                [tag.definition,  node.id])
            has_tag, = cursor.fetchone()
            if has_tag:
                node.tags.add(tag)
            else:
                node.tags.remove(tag)
    node.save()


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
    :ivar tags: The list of :class:`Tag`s associated with this `Node`.
    :ivar objects: The :class:`NodeManager`.

    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    system_id = CharField(
        max_length=41, unique=True, default=generate_node_system_id,
        editable=False)

    hostname = CharField(max_length=255, default='', blank=True)

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
        max_length=10, choices=ARCHITECTURE_CHOICES, blank=False,
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
            return "%s (%s)" % (self.system_id, self.hostname)
        else:
            return self.system_id

    def tag_names(self):
        return self.tags.values_list('name', flat=True)

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
        from metadataserver.models import NodeCommissionResult

        path = settings.COMMISSIONING_SCRIPT
        if not os.path.exists(path):
            raise ValidationError(
                "Commissioning script is missing: %s" % path)
        with open(path, 'r') as f:
            commissioning_user_data = f.read()

        NodeCommissionResult.objects.clear_results(self)
        self.status = NODE_STATUS.COMMISSIONING
        self.owner = user
        self.save()
        # The commissioning profile is handled in start_nodes.
        Node.objects.start_nodes(
            [self.system_id], user, user_data=commissioning_user_data)

    def delete(self):
        # Delete the related mac addresses first.
        self.macaddress_set.all().delete()
        # Allocated nodes can't be deleted.
        if self.status == NODE_STATUS.ALLOCATED:
            raise NodeStateViolation(
                "Cannot delete node %s: node is in state %s."
                % (self.system_id, NODE_STATUS_CHOICES_DICT[self.status]))
        super(Node, self).delete()

    def set_mac_based_hostname(self, mac_address):
        mac_hostname = mac_address.replace(':', '').lower()
        domain = Config.objects.get_config("enlistment_domain")
        domain = domain.strip("." + whitespace)
        if len(domain) > 0:
            self.hostname = "node-%s.%s" % (mac_hostname, domain)
        else:
            self.hostname = "node-%s" % mac_hostname
        self.save()

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
        power_params.setdefault('ipmipower', '/usr/sbin/ipmipower')
        power_params.setdefault('power_address', 'qemu://localhost/system')
        power_params.setdefault('username', '')
        power_params.setdefault('power_id', self.system_id)

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
        update_hardware_details(self, xmlbytes)
