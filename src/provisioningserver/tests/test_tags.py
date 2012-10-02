# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for tag updating."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from apiclient.testing.credentials import make_api_credentials
from maastesting.factory import factory
from provisioningserver.auth import (
    record_api_credentials,
    record_maas_url,
    record_nodegroup_uuid,
    )
from provisioningserver.testing.testcase import PservTestCase


class TestTagUpdating(PservTestCase):

    def set_maas_url(self):
        record_maas_url(
            'http://127.0.0.1/%s' % factory.make_name('path'))

    def set_api_credentials(self):
        record_api_credentials(':'.join(make_api_credentials()))

    def set_node_group_uuid(self):
        nodegroup_uuid = factory.make_name('nodegroupuuid')
        record_nodegroup_uuid(nodegroup_uuid)

    # FIXME
