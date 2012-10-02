# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Celery jobs for managing tags.

"""

from provisioningserver.auth import (
    get_recorded_api_credentials,
    get_recorded_maas_url,
    get_recorded_nodegroup_uuid,
    )


def process_node_tags(tag_name, tag_definition):
    """Update the nodes for a new/changed tag definition.

    :param tag_name: Name of the tag to update nodes for
    :param tag_definition: Tag definition
    """
    maas_url = get_recorded_maas_url()
    if maas_url is None:
        task_logger.debug("Not updating tags: don't have API URL yet.")
        return
    api_credentials = get_recorded_api_credentials()
    if api_credentials is None:
        task_logger.debug("Not updating tags: don't have API key yet.")
        return
    nodegroup_uuid = get_recorded_nodegroup_uuid()
    if nodegroup_uuid is None:
        task_logger.debug("Not updating tags: don't have UUID yet.")
        return
    # FIXME: Get nodes to process
    # FIXME: Fetch node XML in batches
    # FIXME:   For each XML in each batch:
    # FIXME:     Figure out which nodes tag applies to
    # FIXME:   Call back to API to update tag for nodes that match
