# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the metadata API."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from collections import namedtuple
import httplib
from io import BytesIO
import json

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from maasserver.enum import NODE_STATUS
from maasserver.exceptions import (
    MAASAPINotFound,
    Unauthorized,
    )
from maasserver.models import SSHKey
from maasserver.testing import reload_object
from maasserver.testing.factory import factory
from maasserver.testing.oauthclient import OAuthAuthenticatedClient
from maastesting.djangotestcase import DjangoTestCase
from metadataserver import api
from metadataserver.api import (
    check_version,
    get_node_for_mac,
    get_node_for_request,
    get_queried_node,
    make_list_response,
    make_text_response,
    MetaDataHandler,
    UnknownMetadataVersion,
    )
from metadataserver.models import (
    NodeCommissionResult,
    NodeKey,
    NodeUserData,
    )
from metadataserver.nodeinituser import get_node_init_user
from provisioningserver.enum import POWER_TYPE


class TestHelpers(DjangoTestCase):
    """Tests for the API helper functions."""

    def fake_request(self, **kwargs):
        """Produce a cheap fake request, fresh from the sweat shop.

        Pass as arguments any header items you want to include.
        """
        return namedtuple('FakeRequest', ['META'])(kwargs)

    def test_make_text_response_presents_text_as_text_plain(self):
        input_text = "Hello."
        response = make_text_response(input_text)
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(input_text, response.content)

    def test_make_list_response_presents_list_as_newline_separated_text(self):
        response = make_list_response(['aaa', 'bbb'])
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual("aaa\nbbb", response.content)

    def test_check_version_accepts_latest(self):
        check_version('latest')
        # The test is that we get here without exception.
        pass

    def test_check_version_reports_unknown_version(self):
        self.assertRaises(UnknownMetadataVersion, check_version, '1.0')

    def test_get_node_for_request_finds_node(self):
        node = factory.make_node()
        token = NodeKey.objects.get_token_for_node(node)
        request = self.fake_request(
            HTTP_AUTHORIZATION=factory.make_oauth_header(
                oauth_token=token.key))
        self.assertEqual(node, get_node_for_request(request))

    def test_get_node_for_request_reports_missing_auth_header(self):
        self.assertRaises(
            Unauthorized,
            get_node_for_request, self.fake_request())

    def test_get_node_for_mac_refuses_if_anonymous_access_disabled(self):
        self.patch(settings, 'ALLOW_UNSAFE_METADATA_ACCESS', False)
        self.assertRaises(
            PermissionDenied, get_node_for_mac, factory.getRandomMACAddress())

    def test_get_node_for_mac_raises_404_for_unknown_mac(self):
        self.assertRaises(
            MAASAPINotFound, get_node_for_mac, factory.getRandomMACAddress())

    def test_get_node_for_mac_finds_node_by_mac(self):
        mac = factory.make_mac_address()
        self.assertEqual(mac.node, get_node_for_mac(mac.mac_address))

    def test_get_queried_node_looks_up_by_mac_if_given(self):
        mac = factory.make_mac_address()
        self.assertEqual(
            mac.node,
            get_queried_node(object(), for_mac=mac.mac_address))

    def test_get_queried_node_looks_up_oauth_key_by_default(self):
        node = factory.make_node()
        token = NodeKey.objects.get_token_for_node(node)
        request = self.fake_request(
            HTTP_AUTHORIZATION=factory.make_oauth_header(
                oauth_token=token.key))
        self.assertEqual(node, get_queried_node(request))


class TestViews(DjangoTestCase):
    """Tests for the API views."""

    def make_node_client(self, node=None):
        """Create a test client logged in as if it were `node`."""
        if node is None:
            node = factory.make_node()
        token = NodeKey.objects.get_token_for_node(node)
        return OAuthAuthenticatedClient(get_node_init_user(), token)

    def call_signal(self, client=None, version='latest', files={}, **kwargs):
        """Call the API's signal method.

        :param client: Optional client to POST with.  If omitted, will create
            one for a commissioning node.
        :param version: API version to post on.  Defaults to "latest".
        :param files: Optional dict of files to attach.  Maps file name to
            file contents.
        :param **kwargs: Any other keyword parameters are passed on directly
            to the "signal" call.
        """
        if client is None:
            client = self.make_node_client(factory.make_node(
                status=NODE_STATUS.COMMISSIONING))
        params = {
            'op': 'signal',
            'status': 'OK',
        }
        params.update(kwargs)
        for name, content in files.items():
            params[name] = BytesIO(content)
            params[name].name = name
        url = reverse('metadata-version', args=[version])
        return client.post(url, params)

    def test_no_anonymous_access(self):
        self.assertEqual(
            httplib.UNAUTHORIZED,
            self.client.get(reverse('metadata')).status_code)

    def test_metadata_index_shows_latest(self):
        client = self.make_node_client()
        self.assertIn('latest', client.get(reverse('metadata')).content)

    def test_metadata_index_shows_only_known_versions(self):
        client = self.make_node_client()
        for item in client.get(reverse('metadata')).content.splitlines():
            check_version(item)
        # The test is that we get here without exception.
        pass

    def test_version_index_shows_meta_data(self):
        client = self.make_node_client()
        url = reverse('metadata-version', args=['latest'])
        items = client.get(url).content.splitlines()
        self.assertIn('meta-data', items)

    def test_version_index_does_not_show_user_data_if_not_available(self):
        client = self.make_node_client()
        url = reverse('metadata-version', args=['latest'])
        items = client.get(url).content.splitlines()
        self.assertNotIn('user-data', items)

    def test_version_index_shows_user_data_if_available(self):
        node = factory.make_node()
        NodeUserData.objects.set_user_data(node, b"User data for node")
        client = self.make_node_client(node)
        url = reverse('metadata-version', args=['latest'])
        items = client.get(url).content.splitlines()
        self.assertIn('user-data', items)

    def test_meta_data_view_lists_fields(self):
        # Some fields only are returned if there is data related to them.
        user, _ = factory.make_user_with_keys(n_keys=2, username='my-user')
        node = factory.make_node(owner=user)
        client = self.make_node_client(node=node)
        url = reverse('metadata-meta-data', args=['latest', ''])
        response = client.get(url)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertItemsEqual(
            MetaDataHandler.fields, response.content.split())

    def test_meta_data_view_is_sorted(self):
        client = self.make_node_client()
        url = reverse('metadata-meta-data', args=['latest', ''])
        response = client.get(url)
        attributes = response.content.split()
        self.assertEqual(sorted(attributes), attributes)

    def test_meta_data_unknown_item_is_not_found(self):
        client = self.make_node_client()
        url = reverse('metadata-meta-data', args=['latest', 'UNKNOWN-ITEM'])
        response = client.get(url)
        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_get_attribute_producer_supports_all_fields(self):
        handler = MetaDataHandler()
        producers = map(handler.get_attribute_producer, handler.fields)
        self.assertNotIn(None, producers)

    def test_meta_data_local_hostname_returns_hostname(self):
        hostname = factory.getRandomString()
        client = self.make_node_client(factory.make_node(hostname=hostname))
        url = reverse('metadata-meta-data', args=['latest', 'local-hostname'])
        response = client.get(url)
        self.assertEqual(
            (httplib.OK, hostname),
            (response.status_code, response.content.decode('ascii')))
        self.assertIn('text/plain', response['Content-Type'])

    def test_meta_data_instance_id_returns_system_id(self):
        node = factory.make_node()
        client = self.make_node_client(node)
        url = reverse('metadata-meta-data', args=['latest', 'instance-id'])
        response = client.get(url)
        self.assertEqual(
            (httplib.OK, node.system_id),
            (response.status_code, response.content.decode('ascii')))
        self.assertIn('text/plain', response['Content-Type'])

    def test_user_data_view_returns_binary_data(self):
        data = b"\x00\xff\xff\xfe\xff"
        node = factory.make_node()
        NodeUserData.objects.set_user_data(node, data)
        client = self.make_node_client(node)
        response = client.get(reverse('metadata-user-data', args=['latest']))
        self.assertEqual('application/octet-stream', response['Content-Type'])
        self.assertIsInstance(response.content, str)
        self.assertEqual(
            (httplib.OK, data), (response.status_code, response.content))

    def test_user_data_for_node_without_user_data_returns_not_found(self):
        client = self.make_node_client()
        response = client.get(reverse('metadata-user-data', args=['latest']))
        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_public_keys_not_listed_for_node_without_public_keys(self):
        url = reverse('metadata-meta-data', args=['latest', ''])
        client = self.make_node_client()
        response = client.get(url)
        self.assertNotIn(
            'public-keys', response.content.decode('ascii').split('\n'))

    def test_public_keys_listed_for_node_with_public_keys(self):
        user, _ = factory.make_user_with_keys(n_keys=2, username='my-user')
        node = factory.make_node(owner=user)
        url = reverse('metadata-meta-data', args=['latest', ''])
        client = self.make_node_client(node=node)
        response = client.get(url)
        self.assertIn(
            'public-keys', response.content.decode('ascii').split('\n'))

    def test_public_keys_for_node_without_public_keys_returns_not_found(self):
        url = reverse('metadata-meta-data', args=['latest', 'public-keys'])
        client = self.make_node_client()
        response = client.get(url)
        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_public_keys_for_node_returns_list_of_keys(self):
        user, _ = factory.make_user_with_keys(n_keys=2, username='my-user')
        node = factory.make_node(owner=user)
        url = reverse('metadata-meta-data', args=['latest', 'public-keys'])
        client = self.make_node_client(node=node)
        response = client.get(url)
        self.assertEqual(httplib.OK, response.status_code)
        keys = SSHKey.objects.filter(user=user).values_list('key', flat=True)
        expected_response = '\n'.join(keys)
        self.assertItemsEqual(
            expected_response,
            response.content.decode('ascii'))
        self.assertIn('text/plain', response['Content-Type'])

    def test_public_keys_url_with_additional_slashes(self):
        # The metadata service also accepts urls with any number of additional
        # slashes after 'metadata': e.g. http://host/metadata///rest-of-url.
        user, _ = factory.make_user_with_keys(n_keys=2, username='my-user')
        node = factory.make_node(owner=user)
        url = reverse('metadata-meta-data', args=['latest', 'public-keys'])
        # Insert additional slashes.
        url = url.replace('metadata', 'metadata/////')
        client = self.make_node_client(node=node)
        response = client.get(url)
        keys = SSHKey.objects.filter(user=user).values_list('key', flat=True)
        self.assertItemsEqual(
            '\n'.join(keys),
            response.content.decode('ascii'))

    def test_other_user_than_node_cannot_signal_commissioning_result(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = OAuthAuthenticatedClient(factory.make_user())
        response = self.call_signal(client)
        self.assertEqual(httplib.FORBIDDEN, response.status_code)
        self.assertEqual(
            NODE_STATUS.COMMISSIONING, reload_object(node).status)

    def test_signaling_commissioning_result_does_not_affect_other_node(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(
            node=factory.make_node(status=NODE_STATUS.COMMISSIONING))
        response = self.call_signal(client, status='OK')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            NODE_STATUS.COMMISSIONING, reload_object(node).status)

    def test_signaling_requires_status_code(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        url = reverse('metadata-version', args=['latest'])
        response = client.post(url, {'op': 'signal'})
        self.assertEqual(httplib.BAD_REQUEST, response.status_code)

    def test_signaling_rejects_unknown_status_code(self):
        response = self.call_signal(status=factory.getRandomString())
        self.assertEqual(httplib.BAD_REQUEST, response.status_code)

    def test_signaling_refuses_if_node_in_unexpected_state(self):
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        client = self.make_node_client(node=node)
        response = self.call_signal(client)
        self.assertEqual(
            (
                httplib.CONFLICT,
                "Node wasn't commissioning (status is Declared)",
            ),
            (response.status_code, response.content))

    def test_signaling_accepts_WORKING_status(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        response = self.call_signal(client, status='WORKING')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            NODE_STATUS.COMMISSIONING, reload_object(node).status)

    def test_signaling_WORKING_keeps_owner(self):
        user = factory.make_user()
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        node.owner = user
        node.save()
        client = self.make_node_client(node=node)
        response = self.call_signal(client, status='WORKING')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(user, reload_object(node).owner)

    def test_signaling_commissioning_success_makes_node_Ready(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        response = self.call_signal(client, status='OK')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(NODE_STATUS.READY, reload_object(node).status)

    def test_signaling_commissioning_success_is_idempotent(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        self.call_signal(client, status='OK')
        response = self.call_signal(client, status='OK')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(NODE_STATUS.READY, reload_object(node).status)

    def test_signaling_commissioning_success_clears_owner(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        node.owner = factory.make_user()
        node.save()
        client = self.make_node_client(node=node)
        response = self.call_signal(client, status='OK')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(None, reload_object(node).owner)

    def test_signaling_commissioning_failure_makes_node_Failed_Tests(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        response = self.call_signal(client, status='FAILED')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(NODE_STATUS.FAILED_TESTS, reload_object(node).status)

    def test_signaling_commissioning_failure_is_idempotent(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        self.call_signal(client, status='FAILED')
        response = self.call_signal(client, status='FAILED')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(NODE_STATUS.FAILED_TESTS, reload_object(node).status)

    def test_signaling_commissioning_failure_sets_node_error(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        error_text = factory.getRandomString()
        response = self.call_signal(client, status='FAILED', error=error_text)
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(error_text, reload_object(node).error)

    def test_signaling_commissioning_failure_clears_owner(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        node.owner = factory.make_user()
        node.save()
        client = self.make_node_client(node=node)
        response = self.call_signal(client, status='FAILED')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(None, reload_object(node).owner)

    def test_signaling_no_error_clears_existing_error(self):
        node = factory.make_node(
            status=NODE_STATUS.COMMISSIONING, error=factory.getRandomString())
        client = self.make_node_client(node=node)
        response = self.call_signal(client)
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual('', reload_object(node).error)

    def test_signalling_stores_files_for_any_status(self):
        statuses = ['WORKING', 'OK', 'FAILED']
        filename = factory.getRandomString()
        nodes = {
            status: factory.make_node(status=NODE_STATUS.COMMISSIONING)
            for status in statuses}
        for status, node in nodes.items():
            client = self.make_node_client(node=node)
            self.call_signal(
                client, status=status,
                files={filename: factory.getRandomString().encode('ascii')})
        self.assertEqual(
            {status: filename for status in statuses},
            {
                status: NodeCommissionResult.objects.get(node=node).name
                for status, node in nodes.items()})

    def test_signal_stores_file_contents(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        text = factory.getRandomString().encode('ascii')
        response = self.call_signal(client, files={'file.txt': text})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            text, NodeCommissionResult.objects.get_data(node, 'file.txt'))

    def test_signal_decodes_file_from_UTF8(self):
        unicode_text = '<\u2621>'
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        response = self.call_signal(
            client, files={'file.txt': unicode_text.encode('utf-8')})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            unicode_text,
            NodeCommissionResult.objects.get_data(node, 'file.txt'))

    def test_signal_stores_multiple_files(self):
        contents = {
            factory.getRandomString(): factory.getRandomString().encode(
                'ascii')
            for counter in range(3)}
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        response = self.call_signal(client, files=contents)
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            contents,
            {
                result.name: result.data
                for result in node.nodecommissionresult_set.all()
            })

    def test_signal_stores_files_up_to_documented_size_limit(self):
        # The documented size limit for commissioning result files:
        # one megabyte.  What happens above this limit is none of
        # anybody's business, but files up to this size should work.
        size_limit = 2 ** 20
        contents = factory.getRandomString(size_limit, spaces=True)
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        response = self.call_signal(
            client, files={'output.txt': contents.encode('utf-8')})
        self.assertEqual(httplib.OK, response.status_code)
        stored_data = NodeCommissionResult.objects.get_data(
            node, 'output.txt')
        self.assertEqual(size_limit, len(stored_data))

    def test_signal_stores_lshw_file_on_node(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING, memory=512)
        client = self.make_node_client(node=node)
        xmlbytes = "<t\xe9st/>".encode("utf-8")
        response = self.call_signal(client, files={'01-lshw.out': xmlbytes})
        self.assertEqual(httplib.OK, response.status_code)
        node = reload_object(node)
        self.assertEqual(xmlbytes, node.hardware_details)
        self.assertEqual(0, node.memory)

    def test_signal_refuses_bad_power_type(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        response = self.call_signal(client, power_type="foo")
        self.assertEqual(
            (httplib.BAD_REQUEST, "Bad power_type 'foo'"),
            (response.status_code, response.content))

    def test_signal_power_type_stores_params(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        params = dict(
            power_address=factory.getRandomString(),
            power_user=factory.getRandomString(),
            power_pass=factory.getRandomString())
        response = self.call_signal(
            client, power_type="IPMI", power_parameters=json.dumps(params))
        self.assertEqual(httplib.OK, response.status_code, response.content)
        node = reload_object(node)
        self.assertEqual(
            POWER_TYPE.IPMI, node.power_type)
        self.assertEqual(
            params, node.power_parameters)

    def test_signal_power_type_lower_case_works(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        params = dict(
            power_address=factory.getRandomString(),
            power_user=factory.getRandomString(),
            power_pass=factory.getRandomString())
        response = self.call_signal(
            client, power_type="ipmi", power_parameters=json.dumps(params))
        self.assertEqual(httplib.OK, response.status_code, response.content)
        node = reload_object(node)
        self.assertEqual(
            params, node.power_parameters)

    def test_signal_invalid_power_parameters(self):
        node = factory.make_node(status=NODE_STATUS.COMMISSIONING)
        client = self.make_node_client(node=node)
        response = self.call_signal(
            client, power_type="ipmi", power_parameters="badjson")
        self.assertEqual(
            (httplib.BAD_REQUEST, "Failed to parse json power_parameters"),
            (response.status_code, response.content))

    def test_api_retrieves_node_metadata_by_mac(self):
        mac = factory.make_mac_address()
        url = reverse(
            'metadata-meta-data-by-mac',
            args=['latest', mac.mac_address, 'instance-id'])
        response = self.client.get(url)
        self.assertEqual(
            (httplib.OK, mac.node.system_id),
            (response.status_code, response.content))

    def test_api_retrieves_node_userdata_by_mac(self):
        mac = factory.make_mac_address()
        user_data = factory.getRandomString().encode('ascii')
        NodeUserData.objects.set_user_data(mac.node, user_data)
        url = reverse(
            'metadata-user-data-by-mac', args=['latest', mac.mac_address])
        response = self.client.get(url)
        self.assertEqual(
            (httplib.OK, user_data),
            (response.status_code, response.content))

    def test_api_normally_disallows_anonymous_node_metadata_access(self):
        self.patch(settings, 'ALLOW_UNSAFE_METADATA_ACCESS', False)
        mac = factory.make_mac_address()
        url = reverse(
            'metadata-meta-data-by-mac',
            args=['latest', mac.mac_address, 'instance-id'])
        response = self.client.get(url)
        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_netboot_off(self):
        node = factory.make_node(netboot=True)
        client = self.make_node_client(node=node)
        url = reverse('metadata-version', args=['latest'])
        response = client.post(url, {'op': 'netboot_off'})
        node = reload_object(node)
        self.assertFalse(node.netboot, response)

    def test_netboot_on(self):
        node = factory.make_node(netboot=False)
        client = self.make_node_client(node=node)
        url = reverse('metadata-version', args=['latest'])
        response = client.post(url, {'op': 'netboot_on'})
        node = reload_object(node)
        self.assertTrue(node.netboot, response)

    def test_anonymous_netboot_off(self):
        node = factory.make_node(netboot=True)
        anon_netboot_off_url = reverse(
            'metadata-node-by-id', args=['latest', node.system_id])
        response = self.client.post(
            anon_netboot_off_url, {'op': 'netboot_off'})
        node = reload_object(node)
        self.assertEqual(
            (httplib.OK, False),
            (response.status_code, node.netboot),
            response)

    def test_anonymous_get_enlist_preseed(self):
        # The preseed for enlistment can be obtained anonymously.
        anon_enlist_preseed_url = reverse(
            'metadata-enlist-preseed', args=['latest'])
        # Fake the preseed so we're just exercising the view.
        fake_preseed = factory.getRandomString()
        self.patch(api, "get_enlist_preseed", lambda: fake_preseed)
        response = self.client.get(
            anon_enlist_preseed_url, {'op': 'get_enlist_preseed'})
        self.assertEqual(
            (httplib.OK,
             "text/plain",
             fake_preseed),
            (response.status_code,
             response["Content-Type"],
             response.content),
            response)

    def test_anonymous_get_preseed(self):
        # The preseed for a node can be obtained anonymously.
        node = factory.make_node()
        anon_node_url = reverse(
            'metadata-node-by-id',
            args=['latest', node.system_id])
        # Fake the preseed so we're just exercising the view.
        fake_preseed = factory.getRandomString()
        self.patch(api, "get_preseed", lambda node: fake_preseed)
        response = self.client.get(
            anon_node_url, {'op': 'get_preseed'})
        self.assertEqual(
            (httplib.OK,
             "text/plain",
             fake_preseed),
            (response.status_code,
             response["Content-Type"],
             response.content),
            response)


class TestEnlistViews(DjangoTestCase):
    """Tests for the enlistment metadata views."""

    def test_get_instance_id(self):
        # instance-id must be available
        md_url = reverse('enlist-metadata-meta-data',
            args=['latest', 'instance-id'])
        response = self.client.get(md_url)
        self.assertEqual(
            (httplib.OK, "text/plain"),
            (response.status_code, response["Content-Type"]))
        # just insist content is non-empty. It doesn't matter what it is.
        self.assertTrue(response.content)

    def test_get_hostname(self):
        # instance-id must be available
        md_url = reverse(
            'enlist-metadata-meta-data', args=['latest', 'local-hostname'])
        response = self.client.get(md_url)
        self.assertEqual(
            (httplib.OK, "text/plain"),
            (response.status_code, response["Content-Type"]))
        # just insist content is non-empty. It doesn't matter what it is.
        self.assertTrue(response.content)

    def test_public_keys_returns_404_but_does_not_raise_exception(self):
        # An enlisting node has no SSH keys, but it does request them
        # (bug 1058313).  The request should fail, but without the log
        # noise of an exception.
        md_url = reverse(
            'enlist-metadata-meta-data', args=['latest', 'public-keys'])
        response = self.client.get(md_url)
        self.assertEqual(
            (httplib.NOT_FOUND, "No SSH keys available for this node."),
            (response.status_code, response.content))

    def test_metadata_bogus_is_404(self):
        md_url = reverse('enlist-metadata-meta-data',
            args=['latest', 'BOGUS'])
        response = self.client.get(md_url)
        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_get_userdata(self):
        # instance-id must be available
        ud_url = reverse('enlist-metadata-user-data', args=['latest'])
        fake_preseed = factory.getRandomString()
        self.patch(api, "get_enlist_userdata", lambda: fake_preseed)
        response = self.client.get(ud_url)
        self.assertEqual(
            (httplib.OK, "text/plain", fake_preseed),
            (response.status_code, response["Content-Type"], response.content),
            response)

    def test_metadata_list(self):
        # /enlist/latest/metadata request should list available keys
        md_url = reverse('enlist-metadata-meta-data', args=['latest', ""])
        response = self.client.get(md_url)
        self.assertEqual(
            (httplib.OK, "text/plain"),
            (response.status_code, response["Content-Type"]))
        self.assertTrue('instance-id' in response.content.splitlines())
        self.assertTrue('local-hostname' in response.content.splitlines())

    def test_api_version_contents_list(self):
        # top level api (/enlist/latest/) must list 'metadata' and 'userdata'
        md_url = reverse('enlist-version', args=['latest'])
        response = self.client.get(md_url)
        self.assertEqual(
            (httplib.OK, "text/plain"),
            (response.status_code, response["Content-Type"]))
        self.assertTrue('user-data' in response.content.splitlines())
        self.assertTrue('meta-data' in response.content.splitlines())
