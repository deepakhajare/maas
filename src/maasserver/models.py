# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "generate_node_system_id",
    "NODE_STATUS",
    "Node",
    "MACAddress",
    ]

import datetime
import re
from uuid import uuid1

from django.contrib import admin
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import models
from django.shortcuts import get_object_or_404
from maasserver.macaddress import MACAddressField


class CommonInfo(models.Model):
    created = models.DateField(editable=False)
    updated = models.DateTimeField(editable=False)

    class Meta:
        abstract = True

    def save(self):
        if not self.id:
            self.created = datetime.date.today()
        self.updated = datetime.datetime.today()
        super(CommonInfo, self).save()


def generate_node_system_id():
    return 'node-%s' % uuid1()


class NODE_STATUS:
    """The vocabulary of a `Node`'s possible statuses."""
# TODO: document this when it's stabilized.
    DEFAULT_STATUS = 0
    NEW = 0
    READY = 1
    DEPLOYED = 2
    COMMISSIONED = 3
    DECOMMISSIONED = 4


NODE_STATUS_CHOICES = (
    (NODE_STATUS.NEW, u'New'),
    (NODE_STATUS.READY, u'Ready to Commission'),
    (NODE_STATUS.DEPLOYED, u'Deployed'),
    (NODE_STATUS.COMMISSIONED, u'Commissioned'),
    (NODE_STATUS.DECOMMISSIONED, u'Decommissioned'),
)


NODE_STATUS_CHOICES_DICT = dict(NODE_STATUS_CHOICES)


class NODE_AFTER_COMMISSIONING_ACTION:
    """The vocabulary of a `Node`'s possible value for its field
    after_commissioning_action.

    """
# TODO: document this when it's stabilized.
    DEFAULT = 0
    QUEUE = 0
    CHECK = 1
    DEPLOY_12_04 = 2
    DEPLOY_11_10 = 3
    DEPLOY_11_04 = 4
    DEPLOY_10_10 = 5


NODE_AFTER_COMMISSIONING_ACTION_CHOICES = (
    (NODE_AFTER_COMMISSIONING_ACTION.QUEUE,
        "Queue for dynamic allocation to services"),
    (NODE_AFTER_COMMISSIONING_ACTION.CHECK,
        "Check compatibility and hold for future decision"),
    (NODE_AFTER_COMMISSIONING_ACTION.DEPLOY_12_04,
        "Deploy with Ubuntu 12.04 LTS"),
    (NODE_AFTER_COMMISSIONING_ACTION.DEPLOY_11_10,
        "Deploy with Ubuntu 11.10"),
    (NODE_AFTER_COMMISSIONING_ACTION.DEPLOY_11_04,
        "Deploy with Ubuntu 11.04"),
    (NODE_AFTER_COMMISSIONING_ACTION.DEPLOY_10_10,
        "Deploy with Ubuntu 10.10"),
)


NODE_AFTER_COMMISSIONING_ACTION_CHOICES_DICT = dict(
    NODE_AFTER_COMMISSIONING_ACTION_CHOICES)


class NodeManager(models.Manager):
    """A utility to manage collections of Nodes."""

    def get_visible_nodes(self, user):
        """Fetch all the Nodes visible by a User_.

        :param user: The user that should be used in the permission check.
        :type user: User_

        .. _User: https://
           docs.djangoproject.com/en/dev/topics/auth/
           #django.contrib.auth.models.User

        """
        if user.is_superuser:
            return self.all()
        else:
            return self.filter(
                models.Q(owner__isnull=True) | models.Q(owner=user))

    def get_visible_node_or_404(self, system_id, user):
        """Fetch a `Node` by system_id.  Raise exceptions if no `Node` with
        this system_id exist or if the provided user cannot see this `Node`.

        :param name: The system_id.
        :type name: str
        :param user: The user that should be used in the permission check.
        :type user: django.contrib.auth.models.User
        :raises: django.http.Http404_,
            django.core.exceptions.PermissionDenied_.

        .. _django.http.Http404: https://
           docs.djangoproject.com/en/dev/topics/http/views/
           #the-http404-exception
        .. _django.core.exceptions.PermissionDenied: https://
           docs.djangoproject.com/en/dev/ref/exceptions/
           #django.core.exceptions.PermissionDenied
        """
        node = get_object_or_404(Node, system_id=system_id)
        if user.has_perm('access', node):
            return node
        else:
            raise PermissionDenied


class Node(CommonInfo):
    """A `Node` represents a physical machine used by the MaaS Server."""

    #: The unique identifier for this `Node`.
    #: (e.g. 'node-41eba45e-4cfa-11e1-a052-00225f89f211').
    system_id = models.CharField(
        max_length=41, unique=True, default=generate_node_system_id,
        editable=False)

    #: This `Node`'s hostname.
    hostname = models.CharField(max_length=255, default='', blank=True)

    #: This `Node`'s status. See the vocabulary :class:`NODE_STATUS`.
    status = models.IntegerField(
        max_length=10, choices=NODE_STATUS_CHOICES, editable=False,
        default=NODE_STATUS.DEFAULT_STATUS)

    #: This `Node`'s owner if it's in use, None otherwise.
    owner = models.ForeignKey(
        User, default=None, blank=True, null=True, editable=False)

    #: The action to perform after commissioning.
    #: See vocabulary :class:`NODE_AFTER_COMMISSIONING_ACTION`.
    after_commissioning_action = models.IntegerField(
        choices=NODE_AFTER_COMMISSIONING_ACTION_CHOICES,
        default=NODE_AFTER_COMMISSIONING_ACTION.DEFAULT)

    #: The :class:`NodeManager`.
    objects = NodeManager()

    def __unicode__(self):
        if self.hostname:
            return u"%s (%s)" % (self.system_id, self.hostname)
        else:
            return self.system_id

    def display_status(self):
        return NODE_STATUS_CHOICES_DICT[self.status]

    def add_mac_address(self, mac_address):
        """Add a new MAC Address to this `Node`.

        :param mac_address: The MAC Address to be added.
        :type mac_address: str
        :raises: django.core.exceptions.ValidationError_

        .. _django.core.exceptions.ValidationError: https://
           docs.djangoproject.com/en/dev/ref/exceptions/
           #django.core.exceptions.ValidationError
        """

        mac = MACAddress(mac_address=mac_address, node=self)
        mac.full_clean()
        mac.save()
        return mac

    def remove_mac_address(self, mac_address):
        """Remove a MAC Address from this `Node`.

        :param mac_address: The MAC Address to be removed.
        :type mac_address: str

        """
        mac = MACAddress.objects.get(mac_address=mac_address, node=self)
        if mac:
            mac.delete()


mac_re = re.compile(r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')


class MACAddress(CommonInfo):
    """A `MACAddress` represents a `MAC Address
    <http://en.wikipedia.org/wiki/MAC_address>`_ attached to a :class:`Node`.
    """
    mac_address = MACAddressField()
    node = models.ForeignKey(Node, editable=False)

    class Meta:
        verbose_name_plural = "MAC addresses"

    def __unicode__(self):
        return self.mac_address


# Register the models in the admin site.
admin.site.register(Node)
admin.site.register(MACAddress)


class MaaSAuthorizationBackend(ModelBackend):

    supports_object_permissions = True

    def has_perm(self, user, perm, obj=None):
        # Only Nodes can be checked. We also don't support perm checking
        # when obj = None.
        if not isinstance(obj, Node):
            raise NotImplementedError(
                'Invalid permission check (invalid object type).')

        # Only the generic 'access' permission is supported.
        if perm != 'access':
            raise NotImplementedError(
                'Invalid permission check (invalid permission name).')

        return obj.owner in (None, user)
