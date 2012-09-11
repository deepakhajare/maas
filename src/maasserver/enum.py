# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enumerations meaningful to the maasserver application."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'ARCHITECTURE',
    'ARCHITECTURE_CHOICES',
    'DNS_DHCP_MANAGEMENT',
    'DNS_DHCP_MANAGEMENT_CHOICES',
    'NODEGROUP_STATUS',
    'NODEGROUP_STATUS_CHOICES',
    'NODE_PERMISSION',
    'NODE_STATUS',
    'NODE_STATUS_CHOICES',
    'NODE_STATUS_CHOICES_DICT',
    'PRESEED_TYPE',
    ]

from collections import OrderedDict


class NODE_STATUS:
    """The vocabulary of a `Node`'s possible statuses."""
    # A node starts out as READY.
    DEFAULT_STATUS = 0

    #: The node has been created and has a system ID assigned to it.
    DECLARED = 0
    #: Testing and other commissioning steps are taking place.
    COMMISSIONING = 1
    #: Smoke or burn-in testing has a found a problem.
    FAILED_TESTS = 2
    #: The node can't be contacted.
    MISSING = 3
    #: The node is in the general pool ready to be deployed.
    READY = 4
    #: The node is ready for named deployment.
    RESERVED = 5
    #: The node is powering a service from a charm or is ready for use with
    #: a fresh Ubuntu install.
    ALLOCATED = 6
    #: The node has been removed from service manually until an admin
    #: overrides the retirement.
    RETIRED = 7


# Django choices for NODE_STATUS: sequence of tuples (key, UI
# representation).
NODE_STATUS_CHOICES = (
    (NODE_STATUS.DECLARED, "Declared"),
    (NODE_STATUS.COMMISSIONING, "Commissioning"),
    (NODE_STATUS.FAILED_TESTS, "Failed tests"),
    (NODE_STATUS.MISSING, "Missing"),
    (NODE_STATUS.READY, "Ready"),
    (NODE_STATUS.RESERVED, "Reserved"),
    (NODE_STATUS.ALLOCATED, "Allocated"),
    (NODE_STATUS.RETIRED, "Retired"),
)


NODE_STATUS_CHOICES_DICT = OrderedDict(NODE_STATUS_CHOICES)


class NODE_AFTER_COMMISSIONING_ACTION:
    """The vocabulary of a `Node`'s possible value for its field
    after_commissioning_action.

    """
# TODO: document this when it's stabilized.
    #:
    DEFAULT = 0
    #:
    QUEUE = 0
    #:
    #CHECK = 1
    #:
    #DEPLOY_12_04 = 2


NODE_AFTER_COMMISSIONING_ACTION_CHOICES = (
    (NODE_AFTER_COMMISSIONING_ACTION.QUEUE,
        "Queue for dynamic allocation to services"),
    #(NODE_AFTER_COMMISSIONING_ACTION.CHECK,
    #    "Check compatibility and hold for future decision"),
    #(NODE_AFTER_COMMISSIONING_ACTION.DEPLOY_12_04,
    #    "Deploy with Ubuntu 12.04 LTS"),
)


NODE_AFTER_COMMISSIONING_ACTION_CHOICES_DICT = dict(
    NODE_AFTER_COMMISSIONING_ACTION_CHOICES)


class ARCHITECTURE:
    """List of supported architectures."""
    #:
    i386 = 'i386'
    #:
    amd64 = 'amd64'


# Architecture names.
ARCHITECTURE_CHOICES = (
    (ARCHITECTURE.i386, "i386"),
    (ARCHITECTURE.amd64, "amd64"),
)


class NODE_PERMISSION:
    """Permissions relating to nodes."""
    VIEW = 'view_node'
    EDIT = 'edit_node'
    ADMIN = 'admin_node'


class PRESEED_TYPE:
    """Types of preseed documents that can be generated."""
    DEFAULT = ''
    COMMISSIONING = 'commissioning'
    ENLIST = 'enlist'
    ENLIST_USERDATA = 'enlist_userdata'


class DNS_DHCP_MANAGEMENT:
    NONE = 'none'
    DHCP_ONLY = 'dhcp_only'
    DNS_AND_DHCP = 'dns_and_dhcp'


DNS_DHCP_MANAGEMENT_CHOICES = (
    (DNS_DHCP_MANAGEMENT.NONE, "Don't manage either"),
    (DNS_DHCP_MANAGEMENT.DHCP_ONLY, "Manage DHCP"),
    (DNS_DHCP_MANAGEMENT.DNS_AND_DHCP, "Manage DNS and DHCP"),
)


class NODEGROUP_STATUS:
    """The vocabulary of a `NodeGroup`'s possible statuses."""
    # A nodegroup starts out as PENDING.
    DEFAULT_STATUS = 0

    #: The nodegroup has been created and awaits approval.
    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2


# Django choices for NODEGROUP_STATUS: sequence of tuples (key, UI
# representation).
NODEGROUP_STATUS_CHOICES = (
    (NODEGROUP_STATUS.PENDING, "Pending"),
    (NODEGROUP_STATUS.ACCEPTED, "Accepted"),
    (NODEGROUP_STATUS.REJECTED, "Rejected"),
    )
