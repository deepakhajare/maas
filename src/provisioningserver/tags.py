# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Celery jobs for managing tags.

"""

import json

from apiclient.maas_client import (
    MAASClient,
    MAASDispatcher,
    MAASOAuth,
    )

from provisioningserver.auth import (
    get_recorded_api_credentials,
    get_recorded_maas_url,
    get_recorded_nodegroup_uuid,
    )

from provisioningserver.logging import task_logger


def get_nodes_for_node_group(client, nodegroup_uuid):
    """Retrieve the UUIDs of nodes in a particular group.

    :param client: MAAS client instance
    :param nodegroup_uuid: Node group for which to retrieve nodes
    :return: List of UUIDs for nodes in nodegroup
    """
    client.post('api/1.0/nodegroup/' + nodegroup_uuid, 'get_system_ids',
        nodegroup=nodegroup_uuid)


def get_lshw_output_for_nodes(client, nodegroup_uuid, nodes):
    """Retrieve the lshw output for a set of nodes.

    :param client: MAAS client
    :param nodes: List of UUIDs of nodes for which to fetch lshw data
    :return: Dictionary mapping node UUIDs to lshw output
    """
    client.post('api/1.0/nodegroup/' + nodegroup_uuid,
        'node_lshw', nodes=json.dump(nodes))


def update_node_tags(client, tag_name, added, removed):
    """Update the nodes relevant for a particular tag.

    :param client: MAAS client
    :param tag_name: Name of tag
    :param added: Set of nodes to add
    :param removed: Set of nodes to remove
    """
    client.post('api/1.0/tags/', 'update-nodes', tag_name=tag_name,
        matched=json.dump({"add": added, "remove": removed}))


def signal_done(client, nodegroup_uuid, tag_name):
    """Signal that updating tags for a particular nodegroup is done.

    :param client: MAAS client
    :param nodegroup_uuid: UUID of the nodegroup for which updating is done
    :param tag_name: Name of tag
    """
    client.get('api/1.0/tags/' + tag_name, 'done', nodegroup=nodegroup_uuid)


def process_node_tags(tag_name, tag_definition, batch_size=100):
    """Update the nodes for a new/changed tag definition.

    :param tag_name: Name of the tag to update nodes for
    :param tag_definition: Tag definition
    :param batch_size: Size of batch
    """
    maas_url = get_recorded_maas_url()
    if maas_url is None:
        task_logger.debug("Not updating tags: don't have API URL yet.")
        return
    api_credentials = get_recorded_api_credentials()
    if api_credentials is None:
        task_logger.debug("Not updating tags: don't have API key yet.")
        return
    client = MAASClient(MAASOAuth(*api_credentials), MAASDispatcher(),
        maas_url)
    nodegroup_uuid = get_recorded_nodegroup_uuid()
    if nodegroup_uuid is None:
        task_logger.debug("Not updating tags: don't have UUID yet.")
        return
    # Get nodes to process
    nodes = get_nodes_for_node_group(client, nodegroup_uuid)
    for node in nodes:
        for i in range(0, len(nodes), batch_size):
            selected_nodes = nodes[i:i+batch_size]
            # Fetch node XML in batches
            lshw_output = get_lshw_output_for_nodes(client, selected_nodes)
            matched_nodes = set()
            unmatched_nodes = set()
            for node, hw_xml in lshw_output.iteritems():
                # FIXME: Check if hw_xml matches tag_definition
                if True:
                    matched_nodes.add(node)
                else:
                    unmatched_nodes.add(node)
            update_node_tags(client, tag_name, matched_nodes, unmatched_nodes)
    signal_done(client, tag_name)
