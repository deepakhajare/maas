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


def get_cached_knowledge():
    """Get all the information that we need to know, or raise an error.

    :return: (client, nodegroup_uuid)
    """
    maas_url = get_recorded_maas_url()
    if maas_url is None:
        task_logger.error("Not updating tags: don't have API URL yet.")
        return None, None
    api_credentials = get_recorded_api_credentials()
    if api_credentials is None:
        task_logger.error("Not updating tags: don't have API key yet.")
        return None, None
    nodegroup_uuid = get_recorded_nodegroup_uuid()
    if nodegroup_uuid is None:
        task_logger.error("Not updating tags: don't have UUID yet.")
        return None, None
    client = MAASClient(MAASOAuth(*api_credentials), MAASDispatcher(),
        maas_url)
    return client, nodegroup_uuid


def get_nodes_for_node_group(client, nodegroup_uuid):
    """Retrieve the UUIDs of nodes in a particular group.

    :param client: MAAS client instance
    :param nodegroup_uuid: Node group for which to retrieve nodes
    :return: List of UUIDs for nodes in nodegroup
    """
    path = 'api/1.0/nodegroup/%s/' % (nodegroup_uuid)
    response = client.get(path, op='list_nodes')
    # XXX: Check the response code before we parse the content
    return json.loads(response.content)


def get_hardware_details_for_nodes(client, nodegroup_uuid, system_ids):
    """Retrieve the lshw output for a set of nodes.

    :param client: MAAS client
    :param system_ids: List of UUIDs of systems for which to fetch lshw data
    :return: Dictionary mapping node UUIDs to lshw output
    """
    path = 'api/1.0/nodegroup/%s/' % (nodegroup_uuid,)
    # TODO: Do we pass system_ids as a python list? Or do we json.dumps it
    #       first?
    response = client.get(
        path, op='node_hardware_details', system_ids=system_ids)
    # XXX: Check the response code before we parse the content
    return json.loads(response.content)


def update_node_tags(client, tag_name, uuid, added, removed):
    """Update the nodes relevant for a particular tag.

    :param client: MAAS client
    :param tag_name: Name of tag
    :param uuid: NodeGroup uuid of this worker. Needed for security
        permissions. (The nodegroup worker is only allowed to touch nodes in
        its nodegroup, otherwise you need to be a superuser.)
    :param added: Set of nodes to add
    :param removed: Set of nodes to remove
    """
    path = 'api/1.0/tags/%s/' % (tag_name,)
    response = client.post(path, op='update_nodes', add=added, remove=removed)
    # XXX: Check the response code before we parse the content
    return json.loads(response.content)


def signal_done(client, nodegroup_uuid, tag_name):
    """Signal that updating tags for a particular nodegroup is done.

    :param client: MAAS client
    :param nodegroup_uuid: UUID of the nodegroup for which updating is done
    :param tag_name: Name of tag
    """
    client.post('api/1.0/tags/' + tag_name, 'nodegroup_done',
        nodegroup=nodegroup_uuid)


def process_node_tags(tag_name, tag_definition, batch_size=100):
    """Update the nodes for a new/changed tag definition.

    :param tag_name: Name of the tag to update nodes for
    :param tag_definition: Tag definition
    :param batch_size: Size of batch
    """
    client, nodegroup_uuid = get_cached_knowledge()
    if not all([client, nodegroup_uuid]):
        task_logger.error('Unable to update tag: %s for definition %r'
            ' please refresh secrets, then rebuild this tag'
            % (tag_name, tag_definition))
        return
    # Get nodes to process
    nodes = get_nodes_for_node_group(client, nodegroup_uuid)
    for node in nodes:
        for i in range(0, len(nodes), batch_size):
            selected_nodes = nodes[i:i + batch_size]
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
