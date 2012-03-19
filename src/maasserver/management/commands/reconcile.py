# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Reconcile MAAS's view of the world with the Provisioning Server's.

The Provisioning Server is currently stateless, so this actually implies
reconciling with Cobbler.
"""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "Command",
    ]

from django.core.management.base import BaseCommand
from maasserver import (
    models,
    provisioning,
    )


def reconcile():
    papi = provisioning.get_provisioning_api_proxy()
    nodes_local = {node.system_id: node for node in models.Node.objects.all()}
    nodes_remote = papi.get_nodes()

    missing_local = set(nodes_remote).difference(nodes_local)
    for name in missing_local:
        print("remote:", name)
        remote_node = nodes_remote[name]
        local_node = models.Node(
            system_id=remote_node["name"],
            # TODO: Figure out the correct architecture.
            architecture=models.ARCHITECTURE.amd64,
            power_type=remote_node["power_type"],
            hostname=remote_node["name"])
        local_node.save()
        for mac_address in remote_node["mac_addresses"]:
            local_node.add_mac_address(mac_address)

    missing_remote = set(nodes_local).difference(nodes_remote)
    for name in missing_remote:
        print("local:", name)
        local_node = nodes_local[name]
        provisioning.provision_post_save_Node(
            sender=None, instance=local_node, created=False)

    present_in_both = set(nodes_local).intersection(nodes_remote)
    for name in present_in_both:
        print("common:", name)
        node_local = nodes_local[name]
        node_remote = nodes_remote[name]
        # Check that MACs are the same.
        macs_local = {
            mac.mac_address
            for mac in node_local.macaddress_set.all()
            }
        print("- local macs:", " ".join(sorted(macs_local)))
        macs_remote = {
            mac for mac in node_remote["mac_addresses"]
            }
        print("- remote macs:", " ".join(sorted(macs_remote)))
        for mac in macs_remote - macs_local:
            node_local.add_mac_address(mac)
        if len(macs_local - macs_remote) != 0:
            provisioning.set_node_mac_addresses(node_local)


class Command(BaseCommand):

    help = __doc__

    def handle(self, *args, **options):
        reconcile()
