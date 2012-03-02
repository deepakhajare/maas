# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interact with the Provisioning API."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'get_provisioning_api_proxy',
    ]

from urllib import urlencode
import warnings
import xmlrpclib

from django.conf import settings
from django.db.models.signals import (
    post_delete,
    post_save,
    )
from django.dispatch import receiver
from maasserver.models import (
    Config,
    MACAddress,
    Node,
    )
from metadataserver.models import NodeKey


def get_provisioning_api_proxy():
    """Return a proxy to the Provisioning API.

    If ``PSERV_URL`` is not set, we attempt to return a handle to a fake proxy
    implementation. This will not be available in a packaged version of MaaS,
    in which case an error is raised.
    """
    url = settings.PSERV_URL
    if url is None:
        try:
            from maasserver import testing
        except ImportError:
            # This is probably in a package.
            raise RuntimeError("PSERV_URL must be defined.")
        else:
            warnings.warn(
                "PSERV_URL is None; using the fake Provisioning API.",
                RuntimeWarning)
            return testing.get_fake_provisioning_api_proxy()
    else:
        return xmlrpclib.ServerProxy(
            url, allow_none=True, use_datetime=True)


def get_metadata_server_url():
    """Return the URL where nodes can reach the metadata service."""
    return "http://%s/metadata/" % Config.objects.get_config('metadata-host')


def compose_metadata(node):
    """Put together metadata information for `node`.

    :param node: The node to provide with metadata.
    :type node: Node
    :return: A dict containing metadata information that will be seeded to
        the node, so that it can access the metadata service.
    """
    token = NodeKey.objects.get_token_for_node(node)
    credentials = urlencode({
        'oauth_consumer_key': token.consumer.key,
        'oauth_token_key': token.key,
        'oauth_token_secret': token.secret,
        })
    return {
        'maas-metadata-url': get_metadata_server_url(),
        'maas-metadata-credentials': credentials,
    }


@receiver(post_save, sender=Node)
def provision_post_save_Node(sender, instance, created, **kwargs):
    """Create or update nodes in the provisioning server."""
    papi = get_provisioning_api_proxy()
    nodes = papi.get_nodes_by_name([instance.system_id])
    if instance.system_id in nodes:
        profile = nodes[instance.system_id]["profile"]
    else:
        # TODO: Choose a sensible profile.
        profiles = papi.get_profiles()
        assert len(profiles) >= 1, (
            "No profiles defined in Cobbler; has "
            "cobbler-ubuntu-import been run?")
        profile = sorted(profiles)[0]
    papi.add_node(instance.system_id, profile, compose_metadata(instance))


def set_node_mac_addresses(node):
    """Update the Node's MAC addresses in the provisioning server."""
    mac_addresses = [mac.mac_address for mac in node.macaddress_set.all()]
    deltas = {node.system_id: {"mac_addresses": mac_addresses}}
    get_provisioning_api_proxy().modify_nodes(deltas)


@receiver(post_save, sender=MACAddress)
def provision_post_save_MACAddress(sender, instance, created, **kwargs):
    """Create or update MACs in the provisioning server."""
    set_node_mac_addresses(instance.node)


@receiver(post_delete, sender=Node)
def provision_post_delete_Node(sender, instance, **kwargs):
    """Delete nodes in the provisioning server."""
    papi = get_provisioning_api_proxy()
    papi.delete_nodes_by_name([instance.system_id])


@receiver(post_delete, sender=MACAddress)
def provision_post_delete_MACAddress(sender, instance, **kwargs):
    """Delete MACs in the provisioning server."""
    set_node_mac_addresses(instance.node)


def reconcile():
    papi = get_provisioning_api_proxy()
    nodes_local = {node.system_id: node for node in Node.objects.all()}
    nodes_remote = papi.get_nodes()

    missing_local = set(nodes_remote).difference(nodes_local)
    for name in missing_local:
        remote_node = nodes_remote[name]
        local_node = Node(
            system_id=remote_node["name"],
            hostname=remote_node["name"])
        local_node.save()
        for mac_address in remote_node["mac_addresses"]:
            local_node.add_mac_address(mac_address)

    missing_remote = set(nodes_local).difference(nodes_remote)
    for name in missing_remote:
        local_node = nodes_local[name]
        provision_post_save_Node(
            sender=None, instance=local_node, created=False)

    present_in_both = set(nodes_local).intersection(nodes_remote)
    for name in present_in_both:
        node_local = nodes_local[name]
        node_remote = nodes_remote[name]
        # Check that MACs are the same.
        macs_local = {
            mac.mac_address
            for mac in node_local.macaddress_set.all()
            }
        macs_remote = {
            mac for mac in node_remote["mac_addresses"]
            }
        for mac in macs_remote - macs_local:
            node_local.add_mac_address(mac)
        if len(macs_local - macs_remote) != 0:
            set_node_mac_addresses(node_local)
