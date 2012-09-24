# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `start_cluster_controller` command."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from argparse import ArgumentParser
import httplib
import json

from apiclient.maas_client import MAASClient
from maastesting.factory import factory
from mock import Mock
from provisioningserver import start_cluster_controller
from provisioningserver.testing.testcase import PservTestCase


class Sleeping(Exception):
    """Exception: `sleep` has been called."""


class FakeHttpResponse:
    """Cheap simile of a Django `HttpResponse`."""
    # Needed because we can't import from django in provisioningserver
    # code.

    def __init__(self, content, status=httplib.OK):
        self.content = content
        self.status_code = status


class TestStartClusterController(PservTestCase):

    def setUp(self):
        super(TestStartClusterController, self).setUp()
        self.patch(start_cluster_controller, 'sleep', Mock(failure=Sleeping()))

    def make_connection_details(self):
        return {
            'BROKER_URL': 'http://%s/' % factory.make_name('broker'),
        }

    def prepare_response(self, http_code, content=""):
        """Prepare to return the given http response from API request."""
        self.patch(MAASClient, 'post', Mock(return_value=FakeHttpResponse(
            content, status=http_code)))

    def prepare_success_response(self):
        """Prepare to return connection details from API request."""
        details = self.make_connection_details()
        self.prepare_response(httplib.OK, json.dumps(details))
        return details

    def prepare_rejection_response(self):
        """Prepare to return "rejected" from API request."""
        self.prepare_response(httplib.FORBIDDEN)

    def prepare_pending_response(self):
        """Prepare to return "request pending" from API request."""
        self.prepare_response(httplib.ACCEPTED)

    def test_run_command(self):
        # We can't really run the script, but we can verify that (with
        # the right system functions patched out) we can run it
        # directly.
        self.patch(start_cluster_controller, 'check_call')
        self.prepare_success_response()
        parser = ArgumentParser()
        start_cluster_controller.add_arguments(parser)
        start_cluster_controller.run(parser.parse_args(()))
        self.assertNotEqual(0, start_cluster_controller.check_call.call_count)

    def test_fails_if_declined(self):
        self.prepare_rejection_response()
        self.assertRaises(
            start_cluster_controller.ClusterControllerRejected,
            start_cluster_controller.run, None)
        self.assertEqual([], start_cluster_controller.start_up.calls_list)

    def test_polls_while_pending(self):
        self.prepare_pending_response()
        self.assertRaises(Sleeping, start_cluster_controller.run, None)
        self.assertEqual([], start_cluster_controller.start_up.calls_list)

    def test_starts_up_once_accepted(self):
        self.patch(start_cluster_controller, 'start_up')
        connection_details = self.prepare_success_response()
        start_cluster_controller.run(None)
        start_cluster_controller.start_up.assert_called_once_with(
            connection_details)
