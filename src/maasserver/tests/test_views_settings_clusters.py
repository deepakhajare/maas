# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver clusters views."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import httplib

from django.core.urlresolvers import reverse
from lxml.html import fromstring
from maasserver.enum import (
    NODEGROUP_STATUS,
    )
from maasserver.models import (
    NodeGroup,
    )
from maasserver.testing import (
    extract_redirect,
    get_content_links,
    reload_object,
    reload_objects,
    )
from maasserver.testing.factory import factory
from maasserver.testing.rabbit import uses_rabbit_fixture
from maasserver.testing.testcase import (
    AdminLoggedInTestCase,
    LoggedInTestCase,
    TestCase,
    )
from maastesting.matchers import ContainsAll
from testtools.matchers import MatchesListwise, Contains
from provisioningserver.enum import POWER_TYPE_CHOICES


class ClusterListingTest(AdminLoggedInTestCase):

    def test_settings_lists_accepted_clusters(self):
        nodegroups = {
            factory.make_node_group(status=NODEGROUP_STATUS.ACCEPTED),
            factory.make_node_group(status=NODEGROUP_STATUS.PENDING),
            factory.make_node_group(status=NODEGROUP_STATUS.REJECTED),
            }
        links = get_content_links(self.client.get(reverse('settings')))
        nodegroup_edit_links = [
            reverse('cluster-edit', args=[nodegroup.uuid])
            for nodegroup in nodegroups]
        self.assertThat(
            links,
            ContainsAll(nodegroup_edit_links))

class ClusterEditTest(AdminLoggedInTestCase):

    def test_can_delete_cluster(self):
        nodegroup = factory.make_node_group()
        delete_link = reverse('cluster-delete', args=[nodegroup.uuid])
        response = self.client.post(delete_link, {'post': 'yes'})
        self.assertEqual(httplib.FOUND, response.status_code)
        self.assertFalse(
            NodeGroup.objects.filter(uuid=nodegroup.uuid).exists())

