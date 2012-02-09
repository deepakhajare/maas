# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interact with the Provisioning API."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from pprint import pprint
from sys import stderr
from uuid import uuid1
import xmlrpclib

from django.db.models.signals import (
    post_delete,
    post_save,
    )
from django.dispatch import receiver
from maasserver.models import (
    MACAddress,
    Node,
    )


def get_provisioning_api_proxy():
    """Return a proxy to the Provisioning API."""
    url = "http://localhost:8001/api"
    return xmlrpclib.ServerProxy(
        url, allow_none=True, use_datetime=True)


@receiver(post_save, sender=Node)
def provision_post_save_Node(sender, instance, created, **kwargs):
    """Create or update nodes in the provisioning server."""
    # Create or update the node in the provisioning prov.
    papi = get_provisioning_api_proxy()
    nodes = papi.get_nodes_by_name([instance.system_id])
    if instance.system_id in nodes:
        profile = nodes[instance.system_id]["profile"]
    else:
        # TODO: Get these from somewhere.
        distro = papi.add_distro(
            "distro-%s" % uuid1().get_hex(),
            "initrd", "kernel")
        profile = papi.add_profile(
            "profile-%s" % uuid1().get_hex(),
            distro)
    papi.add_node(instance.system_id, profile)


@receiver(post_save, sender=MACAddress)
def provision_post_save_MACAddress(sender, instance, created, **kwargs):
    """Create or update MACs in the provisioning server."""
    pprint(("SAVE", locals()), stderr)


@receiver(post_delete, sender=Node)
def provision_post_delete_Node(sender, instance, using, **kwargs):
    """Delete nodes in the provisioning server."""
    pprint(("DELETE", locals()), stderr)
    papi = get_provisioning_api_proxy()
    papi.delete_nodes_by_name([instance.system_id])


@receiver(post_delete, sender=MACAddress)
def provision_post_delete_MACAddress(sender, instance, using, **kwargs):
    """Delete MACs in the provisioning server."""
    pprint(("DELETE", locals()), stderr)
