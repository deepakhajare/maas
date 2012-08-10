# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for management of node-group workers' API credentials."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver import auth


def make_credentials():
    """Produce a tuple of API credentials."""
    return (
        factory.make_name('consumer-key'),
        factory.make_name('resource-token'),
        factory.make_name('resource-secret'),
        )


def represent_credentials(credentials):
    """Represent a tuple of API credentials as a credentials string."""
    return ':'.join(credentials)


class TestAuth(TestCase):

    def test_record_api_credentials_records_credentials_string(self):
        self.patch(auth, 'recorded_api_credentials', None)
        creds_string = represent_credentials(make_credentials())
        auth.record_api_credentials(creds_string)
        self.assertEqual(creds_string, auth.recorded_api_credentials)

    def test_get_recorded_api_credentials_returns_credentials_as_tuple(self):
        self.patch(auth, 'recorded_api_credentials', None)
        creds = make_credentials()
        auth.record_api_credentials(represent_credentials(creds))
        self.assertEqual(creds, auth.get_recorded_api_credentials())

    def test_get_recorded_api_credentials_returns_None_without_creds(self):
        self.patch(auth, 'recorded_api_credentials', None)
        self.assertIsNone(auth.get_recorded_api_credentials())

    def test_get_recorded_nodegroup_name_vs_record_nodegroup_name(self):
        self.patch(auth, 'recorded_nodegroup_name', None)
        nodegroup_name = factory.make_name('nodegroup')
        auth.record_nodegroup_name(nodegroup_name)
        self.assertEqual(nodegroup_name, auth.get_recorded_nodegroup_name())