# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver API."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from abc import (
    ABCMeta,
    abstractproperty,
    )
from base64 import b64encode
from collections import namedtuple
from datetime import (
    datetime,
    timedelta,
    )
from functools import partial
import httplib
from itertools import izip
import json
import os
import random
import shutil

from apiclient.maas_client import MAASClient
from celery.app import app_or_default
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.http import QueryDict
from fixtures import Fixture
from maasserver import api
from maasserver.api import (
    DISPLAYED_NODEGROUP_FIELDS,
    extract_constraints,
    extract_oauth_key,
    extract_oauth_key_from_auth_header,
    get_oauth_token,
    get_overrided_query_dict,
    )
from maasserver.enum import (
    ARCHITECTURE,
    ARCHITECTURE_CHOICES,
    COMPONENT,
    DISTRO_SERIES,
    NODE_AFTER_COMMISSIONING_ACTION,
    NODE_STATUS,
    NODE_STATUS_CHOICES_DICT,
    NODEGROUP_STATUS,
    NODEGROUPINTERFACE_MANAGEMENT,
    )
from maasserver.exceptions import Unauthorized
from maasserver.fields import mac_error_msg
from maasserver.forms import DEFAULT_ZONE_NAME
from maasserver.models import (
    BootImage,
    Config,
    DHCPLease,
    MACAddress,
    Node,
    NodeGroup,
    NodeGroupInterface,
    Tag,
    )
from maasserver.models.user import (
    create_auth_token,
    get_auth_tokens,
    )
from maasserver.preseed import (
    compose_enlistment_preseed_url,
    compose_preseed_url,
    )
from maasserver.refresh_worker import refresh_worker
from maasserver.testing import (
    reload_object,
    reload_objects,
    )
from maasserver.testing.factory import factory
from maasserver.testing.oauthclient import OAuthAuthenticatedClient
from maasserver.testing.testcase import (
    AdminLoggedInTestCase,
    LoggedInTestCase,
    TestCase,
    )
from maasserver.tests.test_forms import make_interface_settings
from maasserver.utils import map_enum
from maasserver.utils.orm import get_one
from maasserver.worker_user import get_worker_user
from maastesting.celery import CeleryFixture
from maastesting.djangotestcase import TransactionTestCase
from maastesting.fakemethod import FakeMethod
from maastesting.matchers import ContainsAll
from metadataserver.models import (
    NodeKey,
    NodeUserData,
    )
from metadataserver.nodeinituser import get_node_init_user
from mock import Mock
from provisioningserver import (
    kernel_opts,
    tasks,
    )
from provisioningserver.auth import get_recorded_nodegroup_uuid
from provisioningserver.dhcp.leases import send_leases
from provisioningserver.enum import (
    POWER_TYPE,
    POWER_TYPE_CHOICES,
    )
from provisioningserver.kernel_opts import KernelParameters
from provisioningserver.omshell import Omshell
from provisioningserver.pxe import tftppath
from provisioningserver.testing.boot_images import make_boot_image_params
from testresources import FixtureResource
from testtools.matchers import (
    AllMatch,
    Contains,
    Equals,
    MatchesListwise,
    MatchesStructure,
    StartsWith,
    )


class APIv10TestMixin:

    def get_uri(self, path):
        """GET an API V1 uri.

        :return: The API uri.
        """
        api_root = '/api/1.0/'
        return api_root + path


class TestModuleHelpers(TestCase):

    def make_fake_request(self, auth_header):
        """Create a very simple fake request, with just an auth header."""
        FakeRequest = namedtuple('FakeRequest', ['META'])
        return FakeRequest(META={'HTTP_AUTHORIZATION': auth_header})

    def test_extract_oauth_key_from_auth_header_returns_key(self):
        token = factory.getRandomString(18)
        self.assertEqual(
            token,
            extract_oauth_key_from_auth_header(
                factory.make_oauth_header(oauth_token=token)))

    def test_extract_oauth_key_from_auth_header_returns_None_if_missing(self):
        self.assertIs(None, extract_oauth_key_from_auth_header(''))

    def test_extract_oauth_key_raises_Unauthorized_if_no_auth_header(self):
        self.assertRaises(
            Unauthorized,
            extract_oauth_key, self.make_fake_request(None))

    def test_extract_oauth_key_raises_Unauthorized_if_no_key(self):
        self.assertRaises(
            Unauthorized,
            extract_oauth_key, self.make_fake_request(''))

    def test_extract_oauth_key_returns_key(self):
        token = factory.getRandomString(18)
        self.assertEqual(
            token,
            extract_oauth_key(self.make_fake_request(
                factory.make_oauth_header(oauth_token=token))))

    def test_get_oauth_token_finds_token(self):
        user = factory.make_user()
        consumer, token = user.get_profile().create_authorisation_token()
        self.assertEqual(
            token,
            get_oauth_token(
                self.make_fake_request(
                    factory.make_oauth_header(oauth_token=token.key))))

    def test_get_oauth_token_raises_Unauthorized_for_unknown_token(self):
        fake_token = factory.getRandomString(18)
        header = factory.make_oauth_header(oauth_token=fake_token)
        self.assertRaises(
            Unauthorized,
            get_oauth_token, self.make_fake_request(header))

    def test_extract_constraints_ignores_unknown_parameters(self):
        unknown_parameter = "%s=%s" % (
            factory.getRandomString(),
            factory.getRandomString(),
            )
        self.assertEqual(
            {}, extract_constraints(QueryDict(unknown_parameter)))

    def test_extract_constraints_extracts_name(self):
        name = factory.getRandomString()
        self.assertEqual(
            {'hostname': name},
            extract_constraints(QueryDict('name=%s' % name)))

    def test_get_overrided_query_dict_returns_QueryDict(self):
        defaults = {factory.getRandomString(): factory.getRandomString()}
        results = get_overrided_query_dict(defaults, QueryDict(''))
        expected_results = QueryDict('').copy()
        expected_results.update(defaults)
        self.assertEqual(expected_results, results)

    def test_get_overrided_query_dict_values_in_data_replaces_defaults(self):
        key = factory.getRandomString()
        defaults = {key: factory.getRandomString()}
        data_value = factory.getRandomString()
        data = {key: data_value}
        results = get_overrided_query_dict(defaults, data)
        self.assertEqual([data_value], results.getlist(key))


class MultipleUsersScenarios:
    """A mixin that uses testscenarios to repeat a testcase as different
    users.

    The scenarios should inject a `userfactory` variable that will
    be called to produce the user used in the tests e.g.:

    class ExampleTest(MultipleUsersScenarios, TestCase):
        scenarios = [
            ('anon', dict(userfactory=lambda: AnonymousUser())),
            ('user', dict(userfactory=factory.make_user)),
            ('admin', dict(userfactory=factory.make_admin)),
            ]

        def test_something(self):
            pass

    The test `test_something` with be run 3 times: one with a anonymous user
    logged in, once with a simple (non-admin) user logged in and once with
    an admin user logged in.
    """

    __metaclass__ = ABCMeta

    scenarios = abstractproperty(
        "The scenarios as defined by testscenarios.")

    def setUp(self):
        super(MultipleUsersScenarios, self).setUp()
        user = self.userfactory()
        if not user.is_anonymous():
            password = factory.getRandomString()
            user.set_password(password)
            user.save()
            self.logged_in_user = user
            self.client.login(
                username=self.logged_in_user.username, password=password)


class EnlistmentAPITest(APIv10TestMixin, MultipleUsersScenarios, TestCase):
    """Enlistment tests."""
    scenarios = [
        ('anon', dict(userfactory=lambda: AnonymousUser())),
        ('user', dict(userfactory=factory.make_user)),
        ('admin', dict(userfactory=factory.make_admin)),
        ]

    def test_POST_new_creates_node(self):
        architecture = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': 'diane',
                'architecture': architecture,
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertIn('application/json', response['Content-Type'])
        self.assertEqual('diane', parsed_result['hostname'])
        self.assertNotEqual(0, len(parsed_result.get('system_id')))
        [diane] = Node.objects.filter(hostname='diane')
        self.assertEqual(architecture, diane.architecture)

    def test_POST_new_creates_node_with_arch_only(self):
        architecture = factory.getRandomChoice(
            [choice for choice in ARCHITECTURE_CHOICES
             if choice[0].endswith('/generic')])
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': 'diane',
                'architecture': architecture.split('/')[0],
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertIn('application/json', response['Content-Type'])
        self.assertEqual('diane', parsed_result['hostname'])
        self.assertNotEqual(0, len(parsed_result.get('system_id')))
        [diane] = Node.objects.filter(hostname='diane')
        self.assertEqual(architecture, diane.architecture)

    def test_POST_new_creates_node_with_subarchitecture(self):
        # The API allows a Node to be created.
        architecture = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': 'diane',
                'architecture': architecture.split('/')[0],
                'subarchitecture': architecture.split('/')[1],
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertIn('application/json', response['Content-Type'])
        self.assertEqual('diane', parsed_result['hostname'])
        self.assertNotEqual(0, len(parsed_result.get('system_id')))
        [diane] = Node.objects.filter(hostname='diane')
        self.assertEqual(architecture, diane.architecture)

    def test_POST_new_fails_node_with_double_subarchitecture(self):
        architecture = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': 'diane',
                'architecture': architecture,
                'subarchitecture': architecture.split('/')[1],
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })
        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertEqual("Subarchitecture cannot be specified twice.",
            response.content)

    def test_POST_new_power_type_defaults_to_asking_config(self):
        architecture = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        response = self.client.post(
            self.get_uri('nodes/'), {
                'op': 'new',
                'architecture': architecture,
                'mac_addresses': ['00:11:22:33:44:55'],
                })
        node = Node.objects.get(
            system_id=json.loads(response.content)['system_id'])
        self.assertEqual(POWER_TYPE.DEFAULT, node.power_type)

    def test_POST_new_associates_mac_addresses(self):
        # The API allows a Node to be created and associated with MAC
        # Addresses.
        architecture = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': 'diane',
                'architecture': architecture,
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })
        diane = get_one(Node.objects.filter(hostname='diane'))
        self.assertItemsEqual(
            ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            [mac.mac_address for mac in diane.macaddress_set.all()])

    def test_POST_new_initializes_nodegroup_to_master_by_default(self):
        hostname = factory.make_name('host')
        self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': hostname,
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'mac_addresses': [factory.getRandomMACAddress()],
            })
        self.assertEqual(
            NodeGroup.objects.ensure_master(),
            Node.objects.get(hostname=hostname).nodegroup)

    def test_POST_with_no_hostname_auto_populates_hostname(self):
        architecture = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'architecture': architecture,
                'mac_addresses': ['aa:BB:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })
        node = Node.objects.get(
            system_id=json.loads(response.content)['system_id'])
        self.assertEqual('node-aabbccddeeff.local', node.hostname)

    def test_POST_fails_without_operation(self):
        # If there is no operation ('op=operation_name') specified in the
        # request data, a 'Bad request' response is returned.
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'hostname': 'diane',
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', 'invalid'],
            })

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertIn('text/html', response['Content-Type'])
        self.assertEqual(
            "Unrecognised signature: POST None",
            response.content)

    def test_POST_fails_if_mac_duplicated(self):
        # Mac Addresses should be unique.
        mac = 'aa:bb:cc:dd:ee:ff'
        factory.make_mac_address(mac)
        architecture = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'architecture': architecture,
                'hostname': factory.getRandomString(),
                'mac_addresses': [mac],
            })
        parsed_result = json.loads(response.content)

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertIn('application/json', response['Content-Type'])
        self.assertEqual(
            ["Mac address %s already in use." % mac],
            parsed_result['mac_addresses'])

    def test_POST_fails_with_bad_operation(self):
        # If the operation ('op=operation_name') specified in the
        # request data is unknown, a 'Bad request' response is returned.
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'invalid_operation',
                'hostname': 'diane',
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', 'invalid'],
            })

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertEqual(
            "Unrecognised signature: POST invalid_operation",
            response.content)

    def test_POST_new_rejects_invalid_data(self):
        # If the data provided to create a node with an invalid MAC
        # Address, a 'Bad request' response is returned.
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': 'diane',
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', 'invalid'],
            })
        parsed_result = json.loads(response.content)

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertIn('application/json', response['Content-Type'])
        self.assertEqual(
            ["One or more MAC addresses is invalid."],
            parsed_result['mac_addresses'])

    def test_POST_invalid_architecture_returns_bad_request(self):
        # If the architecture name provided to create a node is not a valid
        # architecture name, a 'Bad request' response is returned.
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': 'diane',
                'mac_addresses': ['aa:bb:cc:dd:ee:ff'],
                'architecture': 'invalid-architecture',
            })
        parsed_result = json.loads(response.content)

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertIn('application/json', response['Content-Type'])
        self.assertItemsEqual(['architecture'], parsed_result)


class NonAdminEnlistmentAPITest(APIv10TestMixin, MultipleUsersScenarios,
                                TestCase):
    # Enlistment tests for non-admin users.

    scenarios = [
        ('anon', dict(userfactory=lambda: AnonymousUser())),
        ('user', dict(userfactory=factory.make_user)),
        ]

    def test_POST_non_admin_creates_node_in_declared_state(self):
        # Upon non-admin enlistment, a node goes into the Declared
        # state.  Deliberate approval is required before we start
        # reinstalling the system, wiping its disks etc.
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': factory.getRandomString(),
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff'],
            })
        self.assertEqual(httplib.OK, response.status_code)
        system_id = json.loads(response.content)['system_id']
        self.assertEqual(
            NODE_STATUS.DECLARED,
            Node.objects.get(system_id=system_id).status)


class AnonymousEnlistmentAPITest(APIv10TestMixin, TestCase):
    # Enlistment tests specific to anonymous users.

    def test_POST_accept_not_allowed(self):
        # An anonymous user is not allowed to accept an anonymously
        # enlisted node.  That would defeat the whole purpose of holding
        # those nodes for approval.
        node_id = factory.make_node(status=NODE_STATUS.DECLARED).system_id
        response = self.client.post(
            self.get_uri('nodes/'), {'op': 'accept', 'nodes': [node_id]})
        self.assertEqual(
            (httplib.UNAUTHORIZED, "You must be logged in to accept nodes."),
            (response.status_code, response.content))

    def test_POST_returns_limited_fields(self):
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'hostname': factory.getRandomString(),
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })
        parsed_result = json.loads(response.content)
        self.assertItemsEqual(
            [
                'hostname',
                'system_id',
                'macaddress_set',
                'architecture',
                'status',
                'netboot',
                'power_type',
                'power_parameters',
                'tag_names',
            ],
            list(parsed_result))


class SimpleUserLoggedInEnlistmentAPITest(APIv10TestMixin, LoggedInTestCase):
    # Enlistment tests specific to simple (non-admin) users.

    def test_POST_accept_not_allowed(self):
        # An non-admin user is not allowed to accept an anonymously
        # enlisted node.  That would defeat the whole purpose of holding
        # those nodes for approval.
        node_id = factory.make_node(status=NODE_STATUS.DECLARED).system_id
        response = self.client.post(
            self.get_uri('nodes/'), {'op': 'accept', 'nodes': [node_id]})
        self.assertEqual(
            (httplib.FORBIDDEN,
                "You don't have the required permission to accept the "
                "following node(s): %s." % node_id),
            (response.status_code, response.content))

    def test_POST_accept_all_does_not_accept_anything(self):
        # It is not an error for a non-admin user to attempt to accept all
        # anonymously enlisted nodes, but only those for which he/she has
        # admin privs will be accepted, which currently equates to none of
        # them.
        factory.make_node(status=NODE_STATUS.DECLARED),
        factory.make_node(status=NODE_STATUS.DECLARED),
        response = self.client.post(
            self.get_uri('nodes/'), {'op': 'accept_all'})
        self.assertEqual(httplib.OK, response.status_code)
        nodes_returned = json.loads(response.content)
        self.assertEqual([], nodes_returned)

    def test_POST_simple_user_cannot_set_power_type_and_parameters(self):
        new_power_address = factory.getRandomString()
        response = self.client.post(
            self.get_uri('nodes/'), {
                'op': 'new',
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'power_type': POWER_TYPE.WAKE_ON_LAN,
                'power_parameters_power_address': new_power_address,
                'mac_addresses': ['AA:BB:CC:DD:EE:FF'],
                })

        node = Node.objects.get(
            system_id=json.loads(response.content)['system_id'])
        self.assertEqual(
                (httplib.OK, '', POWER_TYPE.DEFAULT),
                (response.status_code, node.power_parameters,
                    node.power_type))

    def test_POST_returns_limited_fields(self):
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': factory.getRandomString(),
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })
        parsed_result = json.loads(response.content)
        self.assertItemsEqual(
            [
                'hostname',
                'system_id',
                'macaddress_set',
                'architecture',
                'status',
                'netboot',
                'power_type',
                'power_parameters',
                'resource_uri',
                'tag_names',
            ],
            list(parsed_result))


class AdminLoggedInEnlistmentAPITest(APIv10TestMixin, AdminLoggedInTestCase):
    # Enlistment tests specific to admin users.

    def test_POST_new_creates_node_default_values_for_power_settings(self):
        architecture = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        mac_address = 'AA:BB:CC:DD:EE:FF'
        response = self.client.post(
            self.get_uri('nodes/'), {
                'op': 'new',
                'architecture': architecture,
                'mac_addresses': [mac_address],
                })
        node = Node.objects.get(
            system_id=json.loads(response.content)['system_id'])
        self.assertAttributes(
            node,
            dict(
                architecture=architecture, power_type=POWER_TYPE.DEFAULT,
                power_parameters=''))

    def test_POST_new_sets_power_type_if_admin(self):
        response = self.client.post(
            self.get_uri('nodes/'), {
                'op': 'new',
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'power_type': POWER_TYPE.WAKE_ON_LAN,
                'mac_addresses': ['00:11:22:33:44:55'],
                })
        node = Node.objects.get(
            system_id=json.loads(response.content)['system_id'])
        self.assertEqual(POWER_TYPE.WAKE_ON_LAN, node.power_type)
        self.assertEqual('', node.power_parameters)

    def test_POST_new_sets_power_parameters_field(self):
        # The api allows the setting of a Node's power_parameters field.
        # Create a power_parameter valid for the selected power_type.
        new_mac_address = factory.getRandomMACAddress()
        response = self.client.post(
            self.get_uri('nodes/'), {
                'op': 'new',
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'power_type': POWER_TYPE.WAKE_ON_LAN,
                'power_parameters_mac_address': new_mac_address,
                'mac_addresses': ['AA:BB:CC:DD:EE:FF'],
                })

        node = Node.objects.get(
            system_id=json.loads(response.content)['system_id'])
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            {'mac_address': new_mac_address},
            reload_object(node).power_parameters)

    def test_POST_updates_power_parameters_rejects_unknown_param(self):
        hostname = factory.getRandomString()
        response = self.client.post(
            self.get_uri('nodes/'), {
                'op': 'new',
                'hostname': hostname,
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'power_type': POWER_TYPE.WAKE_ON_LAN,
                'power_parameters_unknown_param': factory.getRandomString(),
                'mac_addresses': [factory.getRandomMACAddress()],
                })

        self.assertEqual(
            (
                httplib.BAD_REQUEST,
                {'power_parameters': ["Unknown parameter(s): unknown_param."]}
            ),
            (response.status_code, json.loads(response.content)))
        self.assertFalse(Node.objects.filter(hostname=hostname).exists())

    def test_POST_new_sets_power_parameters_skip_check(self):
        # The api allows to skip the validation step and set arbitrary
        # power parameters.
        param = factory.getRandomString()
        response = self.client.post(
            self.get_uri('nodes/'), {
                'op': 'new',
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'power_type': POWER_TYPE.WAKE_ON_LAN,
                'power_parameters_param': param,
                'power_parameters_skip_check': 'true',
                'mac_addresses': ['AA:BB:CC:DD:EE:FF'],
                })

        node = Node.objects.get(
            system_id=json.loads(response.content)['system_id'])
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            {'param': param},
            reload_object(node).power_parameters)

    def test_POST_admin_creates_node_in_commissioning_state(self):
        # When an admin user enlists a node, it goes into the
        # Commissioning state.
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': factory.getRandomString(),
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff'],
            })
        self.assertEqual(httplib.OK, response.status_code)
        system_id = json.loads(response.content)['system_id']
        self.assertEqual(
            NODE_STATUS.COMMISSIONING,
            Node.objects.get(system_id=system_id).status)

    def test_POST_returns_limited_fields(self):
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': factory.getRandomString(),
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })
        parsed_result = json.loads(response.content)
        self.assertItemsEqual(
            [
                'hostname',
                'system_id',
                'macaddress_set',
                'architecture',
                'status',
                'netboot',
                'power_type',
                'power_parameters',
                'resource_uri',
                'tag_names',
            ],
            list(parsed_result))

    def test_POST_accept_all(self):
        # An admin user can accept all anonymously enlisted nodes.
        nodes = [
            factory.make_node(status=NODE_STATUS.DECLARED),
            factory.make_node(status=NODE_STATUS.DECLARED),
            ]
        response = self.client.post(
            self.get_uri('nodes/'), {'op': 'accept_all'})
        self.assertEqual(httplib.OK, response.status_code)
        nodes_returned = json.loads(response.content)
        self.assertSetEqual(
            {node.system_id for node in nodes},
            {node["system_id"] for node in nodes_returned})


class AnonymousIsRegisteredAPITest(APIv10TestMixin, TestCase):

    def test_is_registered_returns_True_if_node_registered(self):
        mac_address = factory.getRandomMACAddress()
        factory.make_mac_address(mac_address)
        response = self.client.get(
            self.get_uri('nodes/'),
            {'op': 'is_registered', 'mac_address': mac_address})
        self.assertEqual(
            (httplib.OK, "true"),
            (response.status_code, response.content))

    def test_is_registered_returns_False_if_mac_registered_node_retired(self):
        mac_address = factory.getRandomMACAddress()
        mac = factory.make_mac_address(mac_address)
        mac.node.status = NODE_STATUS.RETIRED
        mac.node.save()
        response = self.client.get(
            self.get_uri('nodes/'),
            {'op': 'is_registered', 'mac_address': mac_address})
        self.assertEqual(
            (httplib.OK, "false"),
            (response.status_code, response.content))

    def test_is_registered_normalizes_mac_address(self):
        # These two non-normalized MAC addresses are the same.
        non_normalized_mac_address = 'AA-bb-cc-dd-ee-ff'
        non_normalized_mac_address2 = 'aabbccddeeff'
        factory.make_mac_address(non_normalized_mac_address)
        response = self.client.get(
            self.get_uri('nodes/'),
            {
                'op': 'is_registered',
                'mac_address': non_normalized_mac_address2
            })
        self.assertEqual(
            (httplib.OK, "true"),
            (response.status_code, response.content))

    def test_is_registered_returns_False_if_node_not_registered(self):
        mac_address = factory.getRandomMACAddress()
        response = self.client.get(
            self.get_uri('nodes/'),
            {'op': 'is_registered', 'mac_address': mac_address})
        self.assertEqual(
            (httplib.OK, "false"),
            (response.status_code, response.content))


class NodeAnonAPITest(APIv10TestMixin, TestCase):

    def test_anon_nodes_GET(self):
        # Anonymous requests to the API without a specified operation
        # get a "Bad Request" response.
        response = self.client.get(self.get_uri('nodes/'))

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)

    def test_anon_api_doc(self):
        # The documentation is accessible to anon users.
        response = self.client.get(self.get_uri('doc/'))

        self.assertEqual(httplib.OK, response.status_code)

    def test_node_init_user_cannot_access(self):
        token = NodeKey.objects.get_token_for_node(factory.make_node())
        client = OAuthAuthenticatedClient(get_node_init_user(), token)
        response = client.get(self.get_uri('nodes/'), {'op': 'list'})
        self.assertEqual(httplib.FORBIDDEN, response.status_code)


class AnonAPITestCase(APIv10TestMixin, TestCase):
    """Base class for anonymous API tests."""


class APITestCase(APIv10TestMixin, TestCase):
    """Base class for logged-in API tests.

    :ivar logged_in_user: A user who is currently logged in and can access
        the API.
    :ivar client: Authenticated API client (unsurprisingly, logged in as
        `logged_in_user`).
    """

    def setUp(self):
        super(APITestCase, self).setUp()
        self.logged_in_user = factory.make_user(
            username='test', password='test')
        self.client = OAuthAuthenticatedClient(self.logged_in_user)

    def become_admin(self):
        """Promote the logged-in user to admin."""
        self.logged_in_user.is_superuser = True
        self.logged_in_user.save()

    def assertResponseCode(self, expected_code, response):
        if response.status_code != expected_code:
            self.fail("Expected %s response, got %s:\n%s" % (
                expected_code, response.status_code, response.content))


def extract_system_ids(parsed_result):
    """List the system_ids of the nodes in `parsed_result`."""
    return [node.get('system_id') for node in parsed_result]


class NodeAPILoggedInTest(APIv10TestMixin, LoggedInTestCase):

    def test_nodes_GET_logged_in(self):
        # A (Django) logged-in user can access the API.
        node = factory.make_node()
        response = self.client.get(self.get_uri('nodes/'), {'op': 'list'})
        parsed_result = json.loads(response.content)

        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual([node.system_id], extract_system_ids(parsed_result))


class TestNodeAPI(APITestCase):
    """Tests for /api/1.0/nodes/<node>/."""

    def get_node_uri(self, node):
        """Get the API URI for `node`."""
        return self.get_uri('nodes/%s/') % node.system_id

    def test_GET_returns_node(self):
        # The api allows for fetching a single Node (using system_id).
        node = factory.make_node(set_hostname=True)
        response = self.client.get(self.get_node_uri(node))

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual(node.hostname, parsed_result['hostname'])
        self.assertEqual(node.system_id, parsed_result['system_id'])

    def test_GET_returns_associated_tag(self):
        node = factory.make_node(set_hostname=True)
        tag = factory.make_tag()
        node.tags.add(tag)
        response = self.client.get(self.get_node_uri(node))

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual([tag.name], parsed_result['tag_names'])

    def test_GET_refuses_to_access_invisible_node(self):
        # The request to fetch a single node is denied if the node isn't
        # visible by the user.
        other_node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())

        response = self.client.get(self.get_node_uri(other_node))

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_GET_refuses_to_access_nonexistent_node(self):
        # When fetching a Node, the api returns a 'Not Found' (404) error
        # if no node is found.
        response = self.client.get(self.get_uri('nodes/invalid-uuid/'))

        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_POST_stop_checks_permission(self):
        node = factory.make_node()
        response = self.client.post(self.get_node_uri(node), {'op': 'stop'})
        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_POST_stop_returns_node(self):
        node = factory.make_node(owner=self.logged_in_user)
        response = self.client.post(self.get_node_uri(node), {'op': 'stop'})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            node.system_id, json.loads(response.content)['system_id'])

    def test_POST_stop_may_be_repeated(self):
        node = factory.make_node(
            owner=self.logged_in_user, mac=True,
            power_type=POWER_TYPE.WAKE_ON_LAN)
        self.client.post(self.get_node_uri(node), {'op': 'stop'})
        response = self.client.post(self.get_node_uri(node), {'op': 'stop'})
        self.assertEqual(httplib.OK, response.status_code)

    def test_POST_start_checks_permission(self):
        node = factory.make_node()
        response = self.client.post(self.get_node_uri(node), {'op': 'start'})
        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_POST_start_returns_node(self):
        node = factory.make_node(
            owner=self.logged_in_user, mac=True,
            power_type=POWER_TYPE.WAKE_ON_LAN)
        response = self.client.post(self.get_node_uri(node), {'op': 'start'})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            node.system_id, json.loads(response.content)['system_id'])

    def test_POST_start_sets_distro_series(self):
        node = factory.make_node(
            owner=self.logged_in_user, mac=True,
            power_type=POWER_TYPE.WAKE_ON_LAN)
        distro_series = factory.getRandomEnum(DISTRO_SERIES)
        response = self.client.post(
            self.get_node_uri(node),
            {'op': 'start', 'distro_series': distro_series})
        self.assertEqual(
            (httplib.OK, node.system_id),
            (response.status_code, json.loads(response.content)['system_id']))
        self.assertEqual(
            distro_series, reload_object(node).distro_series)

    def test_POST_start_validates_distro_series(self):
        node = factory.make_node(
            owner=self.logged_in_user, mac=True,
            power_type=POWER_TYPE.WAKE_ON_LAN)
        invalid_distro_series = factory.getRandomString()
        response = self.client.post(
            self.get_node_uri(node),
            {'op': 'start', 'distro_series': invalid_distro_series})
        self.assertEqual(
            (
                httplib.BAD_REQUEST,
                {'distro_series': ["Value u'%s' is not a valid choice." %
                    invalid_distro_series]}
            ),
            (response.status_code, json.loads(response.content)))

    def test_POST_start_may_be_repeated(self):
        node = factory.make_node(
            owner=self.logged_in_user, mac=True,
            power_type=POWER_TYPE.WAKE_ON_LAN)
        self.client.post(self.get_node_uri(node), {'op': 'start'})
        response = self.client.post(self.get_node_uri(node), {'op': 'start'})
        self.assertEqual(httplib.OK, response.status_code)

    def test_POST_start_stores_user_data(self):
        node = factory.make_node(
            owner=self.logged_in_user, mac=True,
            power_type=POWER_TYPE.WAKE_ON_LAN)
        user_data = (
            b'\xff\x00\xff\xfe\xff\xff\xfe' +
            factory.getRandomString().encode('ascii'))
        response = self.client.post(
            self.get_node_uri(node), {
                'op': 'start',
                'user_data': b64encode(user_data),
                })
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(user_data, NodeUserData.objects.get_user_data(node))

    def test_POST_release_releases_owned_node(self):
        owned_statuses = [
            NODE_STATUS.RESERVED,
            NODE_STATUS.ALLOCATED,
            ]
        owned_nodes = [
            factory.make_node(owner=self.logged_in_user, status=status)
            for status in owned_statuses]
        responses = [
            self.client.post(self.get_node_uri(node), {'op': 'release'})
            for node in owned_nodes]
        self.assertEqual(
            [httplib.OK] * len(owned_nodes),
            [response.status_code for response in responses])
        self.assertItemsEqual(
            [NODE_STATUS.READY] * len(owned_nodes),
            [node.status for node in reload_objects(Node, owned_nodes)])

    def test_POST_release_turns_on_netboot(self):
        node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=self.logged_in_user)
        node.set_netboot(on=False)
        self.client.post(self.get_node_uri(node), {'op': 'release'})
        self.assertTrue(reload_object(node).netboot)

    def test_POST_release_resets_distro_series(self):
        node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=self.logged_in_user,
            distro_series=factory.getRandomEnum(DISTRO_SERIES))
        self.client.post(self.get_node_uri(node), {'op': 'release'})
        self.assertEqual('', reload_object(node).distro_series)

    def test_POST_release_removes_token_and_user(self):
        node = factory.make_node(status=NODE_STATUS.READY)
        self.client.post(self.get_uri('nodes/'), {'op': 'acquire'})
        node = Node.objects.get(system_id=node.system_id)
        self.assertEqual(NODE_STATUS.ALLOCATED, node.status)
        self.assertEqual(self.logged_in_user, node.owner)
        self.assertEqual(self.client.token.key, node.token.key)
        self.client.post(self.get_node_uri(node), {'op': 'release'})
        node = Node.objects.get(system_id=node.system_id)
        self.assertIs(None, node.owner)
        self.assertIs(None, node.token)

    def test_POST_release_does_nothing_for_unowned_node(self):
        node = factory.make_node(
            status=NODE_STATUS.READY, owner=self.logged_in_user)
        response = self.client.post(
            self.get_node_uri(node), {'op': 'release'})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(NODE_STATUS.READY, reload_object(node).status)

    def test_POST_release_forbidden_if_user_cannot_edit_node(self):
        node = factory.make_node(status=NODE_STATUS.READY)
        response = self.client.post(
            self.get_node_uri(node), {'op': 'release'})
        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_POST_release_fails_for_other_node_states(self):
        releasable_statuses = [
            NODE_STATUS.RESERVED,
            NODE_STATUS.ALLOCATED,
            NODE_STATUS.READY,
            ]
        unreleasable_statuses = [
            status
            for status in map_enum(NODE_STATUS).values()
                if status not in releasable_statuses]
        nodes = [
            factory.make_node(status=status, owner=self.logged_in_user)
            for status in unreleasable_statuses]
        responses = [
            self.client.post(self.get_node_uri(node), {'op': 'release'})
            for node in nodes]
        self.assertEqual(
            [httplib.CONFLICT] * len(unreleasable_statuses),
            [response.status_code for response in responses])
        self.assertItemsEqual(
            unreleasable_statuses,
            [node.status for node in reload_objects(Node, nodes)])

    def test_POST_release_in_wrong_state_reports_current_state(self):
        node = factory.make_node(
            status=NODE_STATUS.RETIRED, owner=self.logged_in_user)
        response = self.client.post(
            self.get_node_uri(node), {'op': 'release'})
        self.assertEqual(
            (
                httplib.CONFLICT,
                "Node cannot be released in its current state ('Retired').",
            ),
            (response.status_code, response.content))

    def test_POST_release_rejects_request_from_unauthorized_user(self):
        node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())
        response = self.client.post(
            self.get_node_uri(node), {'op': 'release'})
        self.assertEqual(httplib.FORBIDDEN, response.status_code)
        self.assertEqual(NODE_STATUS.ALLOCATED, reload_object(node).status)

    def test_POST_release_allows_admin_to_release_anyones_node(self):
        node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())
        self.become_admin()
        response = self.client.post(
            self.get_node_uri(node), {'op': 'release'})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(NODE_STATUS.READY, reload_object(node).status)

    def test_POST_release_combines_with_acquire(self):
        node = factory.make_node(status=NODE_STATUS.READY)
        response = self.client.post(
            self.get_uri('nodes/'), {'op': 'acquire'})
        self.assertEqual(NODE_STATUS.ALLOCATED, reload_object(node).status)
        node_uri = json.loads(response.content)['resource_uri']
        response = self.client.post(node_uri, {'op': 'release'})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(NODE_STATUS.READY, reload_object(node).status)

    def test_PUT_updates_node(self):
        # The api allows the updating of a Node.
        node = factory.make_node(hostname='diane', owner=self.logged_in_user)
        response = self.client.put(
            self.get_node_uri(node), {'hostname': 'francis'})
        parsed_result = json.loads(response.content)

        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual('francis', parsed_result['hostname'])
        self.assertEqual(0, Node.objects.filter(hostname='diane').count())
        self.assertEqual(1, Node.objects.filter(hostname='francis').count())

    def test_PUT_ignores_unknown_fields(self):
        node = factory.make_node(
            owner=self.logged_in_user,
            after_commissioning_action=(
                NODE_AFTER_COMMISSIONING_ACTION.DEFAULT))
        field = factory.getRandomString()
        response = self.client.put(
            self.get_node_uri(node),
            {field: factory.getRandomString()}
            )

        self.assertEqual(httplib.OK, response.status_code)

    def test_PUT_admin_can_change_power_type(self):
        self.become_admin()
        original_power_type = factory.getRandomChoice(
            POWER_TYPE_CHOICES)
        new_power_type = factory.getRandomChoice(
            POWER_TYPE_CHOICES, but_not=original_power_type)
        node = factory.make_node(
            owner=self.logged_in_user,
            power_type=original_power_type,
            after_commissioning_action=(
                NODE_AFTER_COMMISSIONING_ACTION.DEFAULT))
        self.client.put(
            self.get_node_uri(node),
            {'power_type': new_power_type}
            )

        self.assertEqual(
            new_power_type, reload_object(node).power_type)

    def test_PUT_non_admin_cannot_change_power_type(self):
        original_power_type = factory.getRandomChoice(
            POWER_TYPE_CHOICES)
        new_power_type = factory.getRandomChoice(
            POWER_TYPE_CHOICES, but_not=original_power_type)
        node = factory.make_node(
            owner=self.logged_in_user,
            power_type=original_power_type,
            after_commissioning_action=(
                NODE_AFTER_COMMISSIONING_ACTION.DEFAULT))
        self.client.put(
            self.get_node_uri(node),
            {'power_type': new_power_type}
            )

        self.assertEqual(
            original_power_type, reload_object(node).power_type)

    def test_resource_uri_points_back_at_node(self):
        # When a Node is returned by the API, the field 'resource_uri'
        # provides the URI for this Node.
        node = factory.make_node(hostname='diane', owner=self.logged_in_user)
        response = self.client.put(
            self.get_node_uri(node), {'hostname': 'francis'})
        parsed_result = json.loads(response.content)

        self.assertEqual(
            self.get_uri('nodes/%s/') % (parsed_result['system_id']),
            parsed_result['resource_uri'])

    def test_PUT_rejects_invalid_data(self):
        # If the data provided to update a node is invalid, a 'Bad request'
        # response is returned.
        node = factory.make_node(hostname='diane', owner=self.logged_in_user)
        response = self.client.put(
            self.get_node_uri(node), {'hostname': 'too long' * 100})
        parsed_result = json.loads(response.content)

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertEqual(
            {'hostname':
                ['Ensure this value has at most 255 characters '
                 '(it has 800).']},
            parsed_result)

    def test_PUT_refuses_to_update_invisible_node(self):
        # The request to update a single node is denied if the node isn't
        # visible by the user.
        other_node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())

        response = self.client.put(self.get_node_uri(other_node))

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_PUT_refuses_to_update_nonexistent_node(self):
        # When updating a Node, the api returns a 'Not Found' (404) error
        # if no node is found.
        response = self.client.put(self.get_uri('nodes/no-node-here/'))

        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_PUT_updates_power_parameters_field(self):
        # The api allows the updating of a Node's power_parameters field.
        self.become_admin()
        node = factory.make_node(
            owner=self.logged_in_user,
            power_type=POWER_TYPE.WAKE_ON_LAN)
        # Create a power_parameter valid for the selected power_type.
        new_power_address = factory.getRandomMACAddress()
        response = self.client.put(
            self.get_node_uri(node),
            {'power_parameters_mac_address': new_power_address})

        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            {'mac_address': new_power_address},
            reload_object(node).power_parameters)

    def test_PUT_updates_power_parameters_accepts_only_mac_for_wol(self):
        self.become_admin()
        node = factory.make_node(
            owner=self.logged_in_user,
            power_type=POWER_TYPE.WAKE_ON_LAN)
        # Create an invalid power_parameter for WoL (not a valid
        # MAC address).
        new_power_address = factory.getRandomString()
        response = self.client.put(
            self.get_node_uri(node),
            {'power_parameters_mac_address': new_power_address})

        self.assertEqual(
            (
                httplib.BAD_REQUEST,
                {'power_parameters': ["MAC Address: %s" % mac_error_msg]},
            ),
            (response.status_code, json.loads(response.content)))

    def test_PUT_updates_power_parameters_rejects_unknown_param(self):
        self.become_admin()
        power_parameters = factory.getRandomString()
        node = factory.make_node(
            owner=self.logged_in_user,
            power_type=POWER_TYPE.WAKE_ON_LAN,
            power_parameters=power_parameters)
        response = self.client.put(
            self.get_node_uri(node),
            {'power_parameters_unknown_param': factory.getRandomString()})

        self.assertEqual(
            (
                httplib.BAD_REQUEST,
                {'power_parameters': ["Unknown parameter(s): unknown_param."]}
            ),
            (response.status_code, json.loads(response.content)))
        self.assertEqual(
            power_parameters, reload_object(node).power_parameters)

    def test_PUT_updates_power_type_default_resets_params(self):
        # If one sets power_type to DEFAULT, power_parameter gets
        # reset by default (if skip_check is not set).
        self.become_admin()
        power_parameters = factory.getRandomString()
        node = factory.make_node(
            owner=self.logged_in_user,
            power_type=POWER_TYPE.WAKE_ON_LAN,
            power_parameters=power_parameters)
        response = self.client.put(
            self.get_node_uri(node),
            {'power_type': POWER_TYPE.DEFAULT})

        node = reload_object(node)
        self.assertEqual(
            (httplib.OK, node.power_type, node.power_parameters),
            (response.status_code, POWER_TYPE.DEFAULT, ''))

    def test_PUT_updates_power_type_default_rejects_params(self):
        # If one sets power_type to DEFAULT, on cannot set power_parameters.
        self.become_admin()
        power_parameters = factory.getRandomString()
        node = factory.make_node(
            owner=self.logged_in_user,
            power_type=POWER_TYPE.WAKE_ON_LAN,
            power_parameters=power_parameters)
        new_param = factory.getRandomString()
        response = self.client.put(
            self.get_node_uri(node),
            {
                'power_type': POWER_TYPE.DEFAULT,
                'power_parameters_address': new_param,
            })

        node = reload_object(node)
        self.assertEqual(
            (
                httplib.BAD_REQUEST,
                {'power_parameters': ["Unknown parameter(s): address."]}
            ),
            (response.status_code, json.loads(response.content)))
        self.assertEqual(
            power_parameters, reload_object(node).power_parameters)

    def test_PUT_updates_power_type_default_skip_check_to_force_params(self):
        # If one sets power_type to DEFAULT, it is possible to pass
        # power_parameter_skip_check='true' to force power_parameters.
        self.become_admin()
        power_parameters = factory.getRandomString()
        node = factory.make_node(
            owner=self.logged_in_user,
            power_type=POWER_TYPE.WAKE_ON_LAN,
            power_parameters=power_parameters)
        new_param = factory.getRandomString()
        response = self.client.put(
            self.get_node_uri(node),
            {
                'power_type': POWER_TYPE.DEFAULT,
                'power_parameters_param': new_param,
                'power_parameters_skip_check': 'true',
            })

        node = reload_object(node)
        self.assertEqual(
            (httplib.OK, node.power_type, node.power_parameters),
            (response.status_code, POWER_TYPE.DEFAULT, {'param': new_param}))

    def test_PUT_updates_power_parameters_skip_ckeck(self):
        # With power_parameters_skip_check, arbitrary data
        # can be put in a Node's power_parameter field.
        self.become_admin()
        node = factory.make_node(owner=self.logged_in_user)
        new_param = factory.getRandomString()
        new_value = factory.getRandomString()
        response = self.client.put(
            self.get_node_uri(node),
           {
                'power_parameters_%s' % new_param: new_value,
                'power_parameters_skip_check': 'true',
            })

        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            {new_param: new_value}, reload_object(node).power_parameters)

    def test_PUT_updates_power_parameters_empty_string(self):
        self.become_admin()
        node = factory.make_node(
            owner=self.logged_in_user,
            power_type=POWER_TYPE.WAKE_ON_LAN,
            power_parameters=factory.getRandomString())
        response = self.client.put(
            self.get_node_uri(node),
            {'power_parameters_mac_address': ''})

        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            {'mac_address': ''},
            reload_object(node).power_parameters)

    def test_DELETE_deletes_node(self):
        # The api allows to delete a Node.
        self.become_admin()
        node = factory.make_node(set_hostname=True, owner=self.logged_in_user)
        system_id = node.system_id
        response = self.client.delete(self.get_node_uri(node))

        self.assertEqual(204, response.status_code)
        self.assertItemsEqual([], Node.objects.filter(system_id=system_id))

    def test_DELETE_cannot_delete_allocated_node(self):
        # The api allows to delete a Node.
        self.become_admin()
        node = factory.make_node(status=NODE_STATUS.ALLOCATED)
        response = self.client.delete(self.get_node_uri(node))

        self.assertEqual(
            (httplib.CONFLICT,
                "Cannot delete node %s: node is in state %s." % (
                    node.system_id,
                    NODE_STATUS_CHOICES_DICT[NODE_STATUS.ALLOCATED])),
            (response.status_code, response.content))

    def test_DELETE_deletes_node_fails_if_not_admin(self):
        # Only superusers can delete nodes.
        node = factory.make_node(set_hostname=True, owner=self.logged_in_user)
        response = self.client.delete(self.get_node_uri(node))

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_DELETE_forbidden_without_edit_permission(self):
        # A user without the edit permission cannot delete a Node.
        node = factory.make_node(set_hostname=True)
        response = self.client.delete(self.get_node_uri(node))

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_DELETE_refuses_to_delete_invisible_node(self):
        # The request to delete a single node is denied if the node isn't
        # visible by the user.
        other_node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())

        response = self.client.delete(self.get_node_uri(other_node))

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_DELETE_refuses_to_delete_nonexistent_node(self):
        # When deleting a Node, the api returns a 'Not Found' (404) error
        # if no node is found.
        response = self.client.delete(self.get_uri('nodes/no-node-here/'))

        self.assertEqual(httplib.NOT_FOUND, response.status_code)


class TestNodesAPI(APITestCase):
    """Tests for /api/1.0/nodes/."""

    def test_POST_new_creates_node(self):
        # The API allows a non-admin logged-in user to create a Node.
        architecture = factory.getRandomChoice(ARCHITECTURE_CHOICES)
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': factory.getRandomString(),
                'architecture': architecture,
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '22:bb:cc:dd:ee:ff'],
            })

        self.assertEqual(httplib.OK, response.status_code)

    def test_POST_new_when_logged_in_creates_node_in_declared_state(self):
        # When a user enlists a node, it goes into the Declared state.
        # This will change once we start doing proper commissioning.
        response = self.client.post(
            self.get_uri('nodes/'),
            {
                'op': 'new',
                'hostname': factory.getRandomString(),
                'architecture': factory.getRandomChoice(ARCHITECTURE_CHOICES),
                'after_commissioning_action':
                    NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
                'mac_addresses': ['aa:bb:cc:dd:ee:ff'],
            })
        self.assertEqual(httplib.OK, response.status_code)
        system_id = json.loads(response.content)['system_id']
        self.assertEqual(
            NODE_STATUS.DECLARED,
            Node.objects.get(system_id=system_id).status)

    def test_GET_list_lists_nodes(self):
        # The api allows for fetching the list of Nodes.
        node1 = factory.make_node()
        node2 = factory.make_node(
            set_hostname=True, status=NODE_STATUS.ALLOCATED,
            owner=self.logged_in_user)
        response = self.client.get(self.get_uri('nodes/'), {'op': 'list'})
        parsed_result = json.loads(response.content)

        self.assertEqual(httplib.OK, response.status_code)
        self.assertItemsEqual(
            [node1.system_id, node2.system_id],
            extract_system_ids(parsed_result))

    def test_GET_list_without_nodes_returns_empty_list(self):
        # If there are no nodes to list, the "list" op still works but
        # returns an empty list.
        response = self.client.get(self.get_uri('nodes/'), {'op': 'list'})
        self.assertItemsEqual([], json.loads(response.content))

    def test_GET_list_orders_by_id(self):
        # Nodes are returned in id order.
        nodes = [factory.make_node() for counter in range(3)]
        response = self.client.get(self.get_uri('nodes/'), {'op': 'list'})
        parsed_result = json.loads(response.content)
        self.assertSequenceEqual(
            [node.system_id for node in nodes],
            extract_system_ids(parsed_result))

    def test_GET_list_with_id_returns_matching_nodes(self):
        # The "list" operation takes optional "id" parameters.  Only
        # nodes with matching ids will be returned.
        ids = [factory.make_node().system_id for counter in range(3)]
        matching_id = ids[0]
        response = self.client.get(self.get_uri('nodes/'), {
            'op': 'list',
            'id': [matching_id],
        })
        parsed_result = json.loads(response.content)
        self.assertItemsEqual(
            [matching_id], extract_system_ids(parsed_result))

    def test_GET_list_with_nonexistent_id_returns_empty_list(self):
        # Trying to list a nonexistent node id returns a list containing
        # no nodes -- even if other (non-matching) nodes exist.
        existing_id = factory.make_node().system_id
        nonexistent_id = existing_id + factory.getRandomString()
        response = self.client.get(self.get_uri('nodes/'), {
            'op': 'list',
            'id': [nonexistent_id],
        })
        self.assertItemsEqual([], json.loads(response.content))

    def test_GET_list_with_ids_orders_by_id(self):
        # Even when ids are passed to "list," nodes are returned in id
        # order, not necessarily in the order of the id arguments.
        ids = [factory.make_node().system_id for counter in range(3)]
        response = self.client.get(self.get_uri('nodes/'), {
            'op': 'list',
            'id': list(reversed(ids)),
        })
        parsed_result = json.loads(response.content)
        self.assertSequenceEqual(ids, extract_system_ids(parsed_result))

    def test_GET_list_with_some_matching_ids_returns_matching_nodes(self):
        # If some nodes match the requested ids and some don't, only the
        # matching ones are returned.
        existing_id = factory.make_node().system_id
        nonexistent_id = existing_id + factory.getRandomString()
        response = self.client.get(self.get_uri('nodes/'), {
            'op': 'list',
            'id': [existing_id, nonexistent_id],
        })
        parsed_result = json.loads(response.content)
        self.assertItemsEqual(
            [existing_id], extract_system_ids(parsed_result))

    def test_GET_list_with_macs_returns_matching_nodes(self):
        # The "list" operation takes optional "mac_address" parameters.  Only
        # nodes with matching MAC addresses will be returned.
        macs = [factory.make_mac_address() for counter in range(3)]
        matching_mac = macs[0].mac_address
        matching_system_id = macs[0].node.system_id
        response = self.client.get(self.get_uri('nodes/'), {
            'op': 'list',
            'mac_address': [matching_mac],
        })
        parsed_result = json.loads(response.content)
        self.assertItemsEqual(
            [matching_system_id], extract_system_ids(parsed_result))

    def test_GET_list_allocated_returns_only_allocated_with_user_token(self):
        # If the user's allocated nodes have different session tokens,
        # list_allocated should only return the nodes that have the
        # current request's token on them.
        node_1 = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=self.logged_in_user,
            token=get_auth_tokens(self.logged_in_user)[0])
        second_token = create_auth_token(self.logged_in_user)
        factory.make_node(
            owner=self.logged_in_user, status=NODE_STATUS.ALLOCATED,
            token=second_token)

        user_2 = factory.make_user()
        create_auth_token(user_2)
        factory.make_node(
            owner=self.logged_in_user, status=NODE_STATUS.ALLOCATED,
            token=second_token)

        # At this point we have two nodes owned by the same user but
        # allocated with different tokens, and a third node allocated to
        # someone else entirely.  We expect list_allocated to
        # return the node with the same token as the one used in
        # self.client, which is the one we set on node_1 above.

        response = self.client.get(self.get_uri('nodes/'), {
            'op': 'list_allocated'})
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertItemsEqual(
            [node_1.system_id], extract_system_ids(parsed_result))

    def test_GET_list_allocated_filters_by_id(self):
        # list_allocated takes an optional list of 'id' parameters to
        # filter returned results.
        current_token = get_auth_tokens(self.logged_in_user)[0]
        nodes = []
        for i in range(3):
            nodes.append(factory.make_node(
                status=NODE_STATUS.ALLOCATED,
                owner=self.logged_in_user, token=current_token))

        required_node_ids = [nodes[0].system_id, nodes[1].system_id]
        response = self.client.get(self.get_uri('nodes/'), {
            'op': 'list_allocated',
            'id': required_node_ids,
        })
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertItemsEqual(
            required_node_ids, extract_system_ids(parsed_result))

    def test_POST_acquire_returns_available_node(self):
        # The "acquire" operation returns an available node.
        available_status = NODE_STATUS.READY
        node = factory.make_node(status=available_status, owner=None)
        response = self.client.post(self.get_uri('nodes/'), {'op': 'acquire'})
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual(node.system_id, parsed_result['system_id'])

    def test_POST_acquire_allocates_node(self):
        # The "acquire" operation allocates the node it returns.
        available_status = NODE_STATUS.READY
        node = factory.make_node(status=available_status, owner=None)
        self.client.post(self.get_uri('nodes/'), {'op': 'acquire'})
        node = Node.objects.get(system_id=node.system_id)
        self.assertEqual(self.logged_in_user, node.owner)

    def test_POST_acquire_fails_if_no_node_present(self):
        # The "acquire" operation returns a Conflict error if no nodes
        # are available.
        response = self.client.post(self.get_uri('nodes/'), {'op': 'acquire'})
        # Fails with Conflict error: resource can't satisfy request.
        self.assertEqual(httplib.CONFLICT, response.status_code)

    def test_POST_ignores_already_allocated_node(self):
        factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())
        response = self.client.post(self.get_uri('nodes/'), {'op': 'acquire'})
        self.assertEqual(httplib.CONFLICT, response.status_code)

    def test_POST_acquire_chooses_candidate_matching_constraint(self):
        # If "acquire" is passed a constraint, it will go for a node
        # matching that constraint even if there's tons of other nodes
        # available.
        # (Creating lots of nodes here to minimize the chances of this
        # passing by accident).
        available_nodes = [
            factory.make_node(status=NODE_STATUS.READY, owner=None)
            for counter in range(20)]
        desired_node = random.choice(available_nodes)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'name': desired_node.hostname,
        })
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual(desired_node.hostname, parsed_result['hostname'])

    def test_POST_acquire_would_rather_fail_than_disobey_constraint(self):
        # If "acquire" is passed a constraint, it won't return a node
        # that does not meet that constraint.  Even if it means that it
        # can't meet the request.
        factory.make_node(status=NODE_STATUS.READY, owner=None)
        desired_node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'name': desired_node.system_id,
        })
        self.assertEqual(httplib.CONFLICT, response.status_code)

    def test_POST_acquire_ignores_unknown_constraint(self):
        node = factory.make_node(status=NODE_STATUS.READY, owner=None)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            factory.getRandomString(): factory.getRandomString(),
        })
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual(node.system_id, parsed_result['system_id'])

    def test_POST_acquire_allocates_node_by_name(self):
        # Positive test for name constraint.
        # If a name constraint is given, "acquire" attempts to allocate
        # a node of that name.
        node = factory.make_node(status=NODE_STATUS.READY, owner=None)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'name': node.hostname,
        })
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            node.hostname, json.loads(response.content)['hostname'])

    def test_POST_acquire_treats_unknown_name_as_resource_conflict(self):
        # A name constraint naming an unknown node produces a resource
        # conflict: most likely the node existed but has changed or
        # disappeared.
        # Certainly it's not a 404, since the resource named in the URL
        # is "nodes/," which does exist.
        factory.make_node(status=NODE_STATUS.READY, owner=None)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'name': factory.getRandomString(),
        })
        self.assertEqual(httplib.CONFLICT, response.status_code)

    def test_POST_acquire_allocates_node_by_arch(self):
        # Asking for a particular arch acquires a node with that arch.
        node = factory.make_node(
            status=NODE_STATUS.READY, architecture=ARCHITECTURE.i386)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'arch': 'i386/generic',
        })
        self.assertEqual(httplib.OK, response.status_code)
        response_json = json.loads(response.content)
        self.assertEqual(node.architecture, response_json['architecture'])

    def test_POST_acquire_treats_unknown_arch_as_resource_conflict(self):
        # Asking for an unknown arch returns an HTTP conflict
        factory.make_node(status=NODE_STATUS.READY)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'arch': 'sparc',
        })
        self.assertEqual(httplib.CONFLICT, response.status_code)

    def test_POST_acquire_allocates_node_by_cpu(self):
        # Asking for enough cpu acquires a node with at least that.
        node = factory.make_node(status=NODE_STATUS.READY, cpu_count=3)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'cpu_count': 2,
        })
        self.assertResponseCode(httplib.OK, response)
        response_json = json.loads(response.content)
        self.assertEqual(node.system_id, response_json['system_id'])

    def test_POST_acquire_fails_with_invalid_cpu(self):
        # Asking for an invalid amount of cpu returns a bad request.
        factory.make_node(status=NODE_STATUS.READY)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'cpu_count': 'plenty',
        })
        self.assertResponseCode(httplib.BAD_REQUEST, response)

    def test_POST_acquire_allocates_node_by_mem(self):
        # Asking for enough memory acquires a node with at least that.
        node = factory.make_node(status=NODE_STATUS.READY, memory=1024)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'mem': 1024,
        })
        self.assertResponseCode(httplib.OK, response)
        response_json = json.loads(response.content)
        self.assertEqual(node.system_id, response_json['system_id'])

    def test_POST_acquire_fails_with_invalid_mem(self):
        # Asking for an invalid amount of cpu returns a bad request.
        factory.make_node(status=NODE_STATUS.READY)
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'mem': 'bags',
        })
        self.assertResponseCode(httplib.BAD_REQUEST, response)

    def test_POST_acquire_allocates_node_by_tags(self):
        # Asking for particular tags acquires a node with those tags.
        node = factory.make_node(status=NODE_STATUS.READY)
        node_tag_names = ["fast", "stable", "cute"]
        node.tags = [factory.make_tag(t) for t in node_tag_names]
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'tags': 'fast, stable',
        })
        self.assertResponseCode(httplib.OK, response)
        response_json = json.loads(response.content)
        self.assertEqual(node_tag_names, response_json['tag_names'])

    def test_POST_acquire_fails_without_all_tags(self):
        # Asking for particular tags does not acquire if no node has all tags.
        node1 = factory.make_node(status=NODE_STATUS.READY)
        node1.tags = [factory.make_tag(t) for t in ("fast", "stable", "cute")]
        node2 = factory.make_node(status=NODE_STATUS.READY)
        node2.tags = [factory.make_tag("cheap")]
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'tags': 'fast, cheap',
        })
        self.assertResponseCode(httplib.CONFLICT, response)

    def test_POST_acquire_fails_with_unknown_tags(self):
        # Asking for a tag that does not exist gives a specific error.
        node = factory.make_node(status=NODE_STATUS.READY)
        node.tags = [factory.make_tag("fast")]
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'acquire',
            'tags': 'fast, hairy',
        })
        self.assertResponseCode(httplib.BAD_REQUEST, response)

    def test_POST_acquire_sets_a_token(self):
        # "acquire" should set the Token being used in the request on
        # the Node that is allocated.
        available_status = NODE_STATUS.READY
        node = factory.make_node(status=available_status, owner=None)
        self.client.post(self.get_uri('nodes/'), {'op': 'acquire'})
        node = Node.objects.get(system_id=node.system_id)
        oauth_key = self.client.token.key
        self.assertEqual(oauth_key, node.token.key)

    def test_POST_accept_gets_node_out_of_declared_state(self):
        # This will change when we add provisioning.  Until then,
        # acceptance gets a node straight to Ready state.
        self.become_admin()
        target_state = NODE_STATUS.COMMISSIONING

        node = factory.make_node(status=NODE_STATUS.DECLARED)
        response = self.client.post(
            self.get_uri('nodes/'),
            {'op': 'accept', 'nodes': [node.system_id]})
        accepted_ids = [
            accepted_node['system_id']
            for accepted_node in json.loads(response.content)]
        self.assertEqual(
            (httplib.OK, [node.system_id]),
            (response.status_code, accepted_ids))
        self.assertEqual(target_state, reload_object(node).status)

    def test_POST_quietly_accepts_empty_set(self):
        response = self.client.post(self.get_uri('nodes/'), {'op': 'accept'})
        self.assertEqual(
            (httplib.OK, "[]"), (response.status_code, response.content))

    def test_POST_accept_rejects_impossible_state_changes(self):
        self.become_admin()
        acceptable_states = set([
            NODE_STATUS.DECLARED,
            NODE_STATUS.COMMISSIONING,
            NODE_STATUS.READY,
            ])
        unacceptable_states = (
            set(map_enum(NODE_STATUS).values()) - acceptable_states)
        nodes = {
            status: factory.make_node(status=status)
            for status in unacceptable_states}
        responses = {
            status: self.client.post(
                self.get_uri('nodes/'), {
                    'op': 'accept',
                    'nodes': [node.system_id],
                    })
            for status, node in nodes.items()}
        # All of these attempts are rejected with Conflict errors.
        self.assertEqual(
            {status: httplib.CONFLICT for status in unacceptable_states},
            {
                status: responses[status].status_code
                for status in unacceptable_states})

        for status, response in responses.items():
            # Each error describes the problem.
            self.assertIn("Cannot accept node enlistment", response.content)
            # Each error names the node it encountered a problem with.
            self.assertIn(nodes[status].system_id, response.content)
            # Each error names the node state that the request conflicted
            # with.
            self.assertIn(NODE_STATUS_CHOICES_DICT[status], response.content)

    def test_POST_accept_fails_if_node_does_not_exist(self):
        self.become_admin()
        node_id = factory.getRandomString()
        response = self.client.post(
            self.get_uri('nodes/'), {'op': 'accept', 'nodes': [node_id]})
        self.assertEqual(
            (httplib.BAD_REQUEST, "Unknown node(s): %s." % node_id),
            (response.status_code, response.content))

    def test_POST_accept_accepts_multiple_nodes(self):
        # This will change when we add provisioning.  Until then,
        # acceptance gets a node straight to Ready state.
        self.become_admin()
        target_state = NODE_STATUS.COMMISSIONING

        nodes = [
            factory.make_node(status=NODE_STATUS.DECLARED)
            for counter in range(2)]
        node_ids = [node.system_id for node in nodes]
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'accept',
            'nodes': node_ids,
            })
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            [target_state] * len(nodes),
            [reload_object(node).status for node in nodes])

    def test_POST_accept_returns_actually_accepted_nodes(self):
        self.become_admin()
        acceptable_nodes = [
            factory.make_node(status=NODE_STATUS.DECLARED)
            for counter in range(2)
            ]
        accepted_node = factory.make_node(status=NODE_STATUS.READY)
        nodes = acceptable_nodes + [accepted_node]
        response = self.client.post(self.get_uri('nodes/'), {
            'op': 'accept',
            'nodes': [node.system_id for node in nodes],
            })
        self.assertEqual(httplib.OK, response.status_code)
        accepted_ids = [
            node['system_id'] for node in json.loads(response.content)]
        self.assertItemsEqual(
            [node.system_id for node in acceptable_nodes], accepted_ids)
        self.assertNotIn(accepted_node.system_id, accepted_ids)


class MACAddressAPITest(APITestCase):

    def createNodeWithMacs(self, owner=None):
        node = factory.make_node(owner=owner)
        mac1 = node.add_mac_address('aa:bb:cc:dd:ee:ff')
        mac2 = node.add_mac_address('22:bb:cc:dd:aa:ff')
        return node, mac1, mac2

    def test_macs_GET(self):
        # The api allows for fetching the list of the MAC address for a node.
        node, mac1, mac2 = self.createNodeWithMacs()
        response = self.client.get(
            self.get_uri('nodes/%s/macs/') % node.system_id)
        parsed_result = json.loads(response.content)

        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(2, len(parsed_result))
        self.assertEqual(
            mac1.mac_address, parsed_result[0]['mac_address'])
        self.assertEqual(
            mac2.mac_address, parsed_result[1]['mac_address'])

    def test_macs_GET_forbidden(self):
        # When fetching MAC addresses, the api returns a 'Forbidden' (403)
        # error if the node is not visible to the logged-in user.
        other_node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())
        response = self.client.get(
            self.get_uri('nodes/%s/macs/') % other_node.system_id)

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_macs_GET_not_found(self):
        # When fetching MAC addresses, the api returns a 'Not Found' (404)
        # error if no node is found.
        response = self.client.get(self.get_uri('nodes/invalid-id/macs/'))

        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_macs_GET_node_not_found(self):
        # When fetching a MAC address, the api returns a 'Not Found' (404)
        # error if the MAC address does not exist.
        node = factory.make_node()
        response = self.client.get(
            self.get_uri(
                'nodes/%s/macs/00-aa-22-cc-44-dd/') % node.system_id)

        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_macs_GET_node_forbidden(self):
        # When fetching a MAC address, the api returns a 'Forbidden' (403)
        # error if the node is not visible to the logged-in user.
        other_node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())
        response = self.client.get(
            self.get_uri(
                'nodes/%s/macs/0-aa-22-cc-44-dd/') % other_node.system_id)

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_macs_GET_node_bad_request(self):
        # When fetching a MAC address, the api returns a 'Bad Request' (400)
        # error if the MAC address is not valid.
        node = factory.make_node()
        response = self.client.get(
            self.get_uri('nodes/%s/macs/invalid-mac/') % node.system_id)

        self.assertEqual(400, response.status_code)

    def test_macs_POST_add_mac(self):
        # The api allows to add a MAC address to an existing node.
        node = factory.make_node(owner=self.logged_in_user)
        nb_macs = MACAddress.objects.filter(node=node).count()
        response = self.client.post(
            self.get_uri('nodes/%s/macs/') % node.system_id,
            {'mac_address': '01:BB:CC:DD:EE:FF'})
        parsed_result = json.loads(response.content)

        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual('01:BB:CC:DD:EE:FF', parsed_result['mac_address'])
        self.assertEqual(
            nb_macs + 1,
            MACAddress.objects.filter(node=node).count())

    def test_macs_POST_add_mac_without_edit_perm(self):
        # Adding a MAC address to a node requires the NODE_PERMISSION.EDIT
        # permission.
        node = factory.make_node()
        response = self.client.post(
            self.get_uri('nodes/%s/macs/') % node.system_id,
            {'mac_address': '01:BB:CC:DD:EE:FF'})

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_macs_POST_add_mac_invalid(self):
        # A 'Bad Request' response is returned if one tries to add an invalid
        # MAC address to a node.
        node = self.createNodeWithMacs(self.logged_in_user)[0]
        response = self.client.post(
            self.get_uri('nodes/%s/macs/') % node.system_id,
            {'mac_address': 'invalid-mac'})
        parsed_result = json.loads(response.content)

        self.assertEqual(400, response.status_code)
        self.assertEqual(['mac_address'], list(parsed_result))
        self.assertEqual(
            ["Enter a valid MAC address (e.g. AA:BB:CC:DD:EE:FF)."],
            parsed_result['mac_address'])

    def test_macs_DELETE_mac(self):
        # The api allows to delete a MAC address.
        node, mac1, mac2 = self.createNodeWithMacs(self.logged_in_user)
        nb_macs = node.macaddress_set.count()
        response = self.client.delete(
            self.get_uri('nodes/%s/macs/%s/') % (
                node.system_id, mac1.mac_address))

        self.assertEqual(204, response.status_code)
        self.assertEqual(
            nb_macs - 1,
            node.macaddress_set.count())

    def test_macs_DELETE_mac_forbidden(self):
        # When deleting a MAC address, the api returns a 'Forbidden' (403)
        # error if the node is not visible to the logged-in user.
        node, mac1, _ = self.createNodeWithMacs()
        other_node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())
        response = self.client.delete(
            self.get_uri('nodes/%s/macs/%s/') % (
                other_node.system_id, mac1.mac_address))

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_macs_DELETE_not_found(self):
        # When deleting a MAC address, the api returns a 'Not Found' (404)
        # error if no existing MAC address is found.
        node = factory.make_node(owner=self.logged_in_user)
        response = self.client.delete(
            self.get_uri('nodes/%s/macs/%s/') % (
                node.system_id, '00-aa-22-cc-44-dd'))

        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_macs_DELETE_forbidden(self):
        # When deleting a MAC address, the api returns a 'Forbidden'
        # (403) error if the user does not have the 'edit' permission on the
        # node.
        node = factory.make_node(owner=self.logged_in_user)
        response = self.client.delete(
            self.get_uri('nodes/%s/macs/%s/') % (
                node.system_id, '00-aa-22-cc-44-dd'))

        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_macs_DELETE_bad_request(self):
        # When deleting a MAC address, the api returns a 'Bad Request' (400)
        # error if the provided MAC address is not valid.
        node = factory.make_node()
        response = self.client.delete(
            self.get_uri('nodes/%s/macs/%s/') % (
                node.system_id, 'invalid-mac'))

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)


class AccountAPITest(APITestCase):

    def test_create_authorisation_token(self):
        # The api operation create_authorisation_token returns a json dict
        # with the consumer_key, the token_key and the token_secret in it.
        response = self.client.post(
            self.get_uri('account/'), {'op': 'create_authorisation_token'})
        parsed_result = json.loads(response.content)

        self.assertEqual(
            ['consumer_key', 'token_key', 'token_secret'],
            sorted(parsed_result))
        self.assertIsInstance(parsed_result['consumer_key'], basestring)
        self.assertIsInstance(parsed_result['token_key'], basestring)
        self.assertIsInstance(parsed_result['token_secret'], basestring)

    def test_delete_authorisation_token_not_found(self):
        # If the provided token_key does not exist (for the currently
        # logged-in user), the api returns a 'Not Found' (404) error.
        response = self.client.post(
            self.get_uri('account/'),
            {'op': 'delete_authorisation_token', 'token_key': 'no-such-token'})

        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_delete_authorisation_token_bad_request_no_token(self):
        # token_key is a mandatory parameter when calling
        # delete_authorisation_token. It it is not present in the request's
        # parameters, the api returns a 'Bad Request' (400) error.
        response = self.client.post(
            self.get_uri('account/'), {'op': 'delete_authorisation_token'})

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)


class MediaRootFixture(Fixture):
    """Create and clear-down a `settings.MEDIA_ROOT` directory.

    The directory must not previously exist.
    """

    def setUp(self):
        super(MediaRootFixture, self).setUp()
        self.path = settings.MEDIA_ROOT
        if os.path.exists(self.path):
            raise AssertionError("See media/README")
        self.addCleanup(shutil.rmtree, self.path, ignore_errors=True)
        os.mkdir(self.path)


class FileStorageAPITestMixin:

    def setUp(self):
        super(FileStorageAPITestMixin, self).setUp()
        media_root = self.useFixture(MediaRootFixture()).path
        self.tmpdir = os.path.join(media_root, "testing")
        os.mkdir(self.tmpdir)

    def make_upload_file(self, name=None, contents=None):
        """Make a temp upload file named `name` with contents `contents`.

        :return: The full file path of the file that was created.
        """
        return factory.make_file(
            location=self.tmpdir, name=name, contents=contents)

    def _create_API_params(self, op=None, filename=None, fileObj=None):
        params = {}
        if op is not None:
            params["op"] = op
        if filename is not None:
            params["filename"] = filename
        if fileObj is not None:
            params["file"] = fileObj
        return params

    def make_API_POST_request(self, op=None, filename=None, fileObj=None):
        """Make an API POST request and return the response."""
        params = self._create_API_params(op, filename, fileObj)
        return self.client.post(self.get_uri('files/'), params)

    def make_API_GET_request(self, op=None, filename=None, fileObj=None):
        """Make an API GET request and return the response."""
        params = self._create_API_params(op, filename, fileObj)
        return self.client.get(self.get_uri('files/'), params)


class AnonymousFileStorageAPITest(FileStorageAPITestMixin, AnonAPITestCase):

    def test_get_works_anonymously(self):
        factory.make_file_storage(filename="foofilers", data=b"give me rope")
        response = self.make_API_GET_request("get", "foofilers")

        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(b"give me rope", response.content)


class FileStorageAPITest(FileStorageAPITestMixin, APITestCase):

    def test_add_file_succeeds(self):
        filepath = self.make_upload_file()

        with open(filepath) as f:
            response = self.make_API_POST_request("add", "foo", f)

        self.assertEqual(httplib.CREATED, response.status_code)

    def test_add_file_fails_with_no_filename(self):
        filepath = self.make_upload_file()

        with open(filepath) as f:
            response = self.make_API_POST_request("add", fileObj=f)

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertEqual("Filename not supplied", response.content)

    def test_add_file_fails_with_no_file_attached(self):
        response = self.make_API_POST_request("add", "foo")

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertEqual("File not supplied", response.content)

    def test_add_file_fails_with_too_many_files(self):
        filepath = self.make_upload_file(name="foo")
        filepath2 = self.make_upload_file(name="foo2")

        with open(filepath) as f, open(filepath2) as f2:
            response = self.client.post(
                self.get_uri('files/'),
                {
                    "op": "add",
                    "filename": "foo",
                    "file": f,
                    "file2": f2,
                })

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertEqual("Exactly one file must be supplied", response.content)

    def test_add_file_can_overwrite_existing_file_of_same_name(self):
        # Write file one.
        filepath = self.make_upload_file(contents="file one")
        with open(filepath) as f:
            response = self.make_API_POST_request("add", "foo", f)
        self.assertEqual(httplib.CREATED, response.status_code)

        # Write file two with the same name but different contents.
        filepath = self.make_upload_file(contents="file two")
        with open(filepath) as f:
            response = self.make_API_POST_request("add", "foo", f)
        self.assertEqual(httplib.CREATED, response.status_code)

        # Retrieve the file and check its contents are the new contents.
        response = self.make_API_GET_request("get", "foo")
        self.assertEqual("file two", response.content)

    def test_get_file_succeeds(self):
        factory.make_file_storage(filename="foofilers", data=b"give me rope")
        response = self.make_API_GET_request("get", "foofilers")

        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(b"give me rope", response.content)

    def test_get_file_fails_with_no_filename(self):
        response = self.make_API_GET_request("get")

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertEqual("Filename not supplied", response.content)

    def test_get_file_fails_with_missing_file(self):
        response = self.make_API_GET_request("get", filename="missingfilename")

        self.assertEqual(httplib.NOT_FOUND, response.status_code)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertEqual("File not found", response.content)


class TestTagAPI(APITestCase):
    """Tests for /api/1.0/tags/<tagname>/."""

    def get_tag_uri(self, tag):
        """Get the API URI for `tag`."""
        return self.get_uri('tags/%s/') % tag.name

    def test_DELETE_requires_admin(self):
        tag = factory.make_tag()
        response = self.client.delete(self.get_tag_uri(tag))
        self.assertEqual(httplib.FORBIDDEN, response.status_code)
        self.assertItemsEqual([tag], Tag.objects.filter(id=tag.id))

    def test_DELETE_removes_tag(self):
        self.become_admin()
        tag = factory.make_tag()
        response = self.client.delete(self.get_tag_uri(tag))
        self.assertEqual(httplib.NO_CONTENT, response.status_code)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_DELETE_404(self):
        self.become_admin()
        response = self.client.delete(self.get_uri('tags/no-tag/'))
        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_GET_returns_tag(self):
        # The api allows for fetching a single Node (using system_id).
        tag = factory.make_tag('tag-name')
        response = self.client.get(self.get_uri('tags/tag-name/'))

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual(tag.name, parsed_result['name'])
        self.assertEqual(tag.definition, parsed_result['definition'])
        self.assertEqual(tag.comment, parsed_result['comment'])

    def test_GET_refuses_to_access_nonexistent_node(self):
        # When fetching a Tag, the api returns a 'Not Found' (404) error
        # if no tag is found.
        response = self.client.get(self.get_uri('tags/no-such-tag/'))
        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_PUT_refuses_non_superuser(self):
        tag = factory.make_tag()
        response = self.client.put(self.get_tag_uri(tag),
                                   {'comment': 'A special comment'})
        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_PUT_updates_tag(self):
        self.become_admin()
        tag = factory.make_tag()
        # Note that 'definition' is not being sent
        response = self.client.put(self.get_tag_uri(tag),
            {'name': 'new-tag-name', 'comment': 'A random comment'})

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual('new-tag-name', parsed_result['name'])
        self.assertEqual('A random comment', parsed_result['comment'])
        self.assertEqual(tag.definition, parsed_result['definition'])
        self.assertFalse(Tag.objects.filter(name=tag.name).exists())
        self.assertTrue(Tag.objects.filter(name='new-tag-name').exists())

    def test_PUT_updates_node_associations(self):
        node1 = factory.make_node()
        node1.set_hardware_details('<node><foo /></node>')
        node2 = factory.make_node()
        node2.set_hardware_details('<node><bar /></node>')
        tag = factory.make_tag(definition='/node/foo')
        tag.populate_nodes()
        self.assertItemsEqual([tag.name], node1.tag_names())
        self.assertItemsEqual([], node2.tag_names())
        self.become_admin()
        response = self.client.put(self.get_tag_uri(tag),
            {'definition': '/node/bar'})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertItemsEqual([], node1.tag_names())
        self.assertItemsEqual([tag.name], node2.tag_names())

    def test_POST_nodes_with_no_nodes(self):
        tag = factory.make_tag()
        response = self.client.post(self.get_tag_uri(tag), {'op': 'nodes'})

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual([], parsed_result)

    def test_POST_nodes_returns_nodes(self):
        tag = factory.make_tag()
        node1 = factory.make_node()
        # Create a second node that isn't tagged.
        factory.make_node()
        node1.tags.add(tag)
        response = self.client.post(self.get_tag_uri(tag), {'op': 'nodes'})

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual([node1.system_id],
                         [r['system_id'] for r in parsed_result])

    def test_POST_nodes_hides_invisible_nodes(self):
        user2 = factory.make_user()
        node1 = factory.make_node()
        node1.set_hardware_details('<node><foo /></node>')
        node2 = factory.make_node(status=NODE_STATUS.ALLOCATED, owner=user2)
        node2.set_hardware_details('<node><bar /></node>')
        tag = factory.make_tag(definition='/node')
        tag.populate_nodes()
        response = self.client.post(self.get_tag_uri(tag), {'op': 'nodes'})

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual([node1.system_id],
                         [r['system_id'] for r in parsed_result])
        # However, for the other user, they should see the result
        client2 = OAuthAuthenticatedClient(user2)
        response = client2.post(self.get_tag_uri(tag), {'op': 'nodes'})
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertItemsEqual([node1.system_id, node2.system_id],
                              [r['system_id'] for r in parsed_result])

    def test_PUT_invalid_definition(self):
        self.become_admin()
        node = factory.make_node()
        node.set_hardware_details('<node ><child /></node>')
        tag = factory.make_tag(definition='//child')
        tag.populate_nodes()
        self.assertItemsEqual([tag.name], node.tag_names())
        response = self.client.put(self.get_tag_uri(tag),
            {'definition': 'invalid::tag'})

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        # The tag should not be modified
        tag = reload_object(tag)
        self.assertItemsEqual([tag.name], node.tag_names())
        self.assertEqual('//child', tag.definition)


class TestTagsAPI(APITestCase):

    def test_GET_list_without_tags_returns_empty_list(self):
        response = self.client.get(self.get_uri('tags/'), {'op': 'list'})
        self.assertItemsEqual([], json.loads(response.content))

    def test_POST_new_refuses_non_admin(self):
        name = factory.getRandomString()
        response = self.client.post(
            self.get_uri('tags/'),
            {
                'op': 'new',
                'name': name,
                'comment': factory.getRandomString(),
                'definition': factory.getRandomString(),
            })
        self.assertEqual(httplib.FORBIDDEN, response.status_code)
        self.assertFalse(Tag.objects.filter(name=name).exists())

    def test_POST_new_creates_tag(self):
        self.become_admin()
        name = factory.getRandomString()
        definition = '//node'
        comment = factory.getRandomString()
        response = self.client.post(
            self.get_uri('tags/'),
            {
                'op': 'new',
                'name': name,
                'comment': comment,
                'definition': definition,
            })
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual(name, parsed_result['name'])
        self.assertEqual(comment, parsed_result['comment'])
        self.assertEqual(definition, parsed_result['definition'])
        self.assertTrue(Tag.objects.filter(name=name).exists())

    def test_POST_new_invalid_tag_name(self):
        self.become_admin()
        # We do not check the full possible set of invalid names here, a more
        # thorough check is done in test_tag, we just check that we get a
        # reasonable error here.
        invalid = 'invalid:name'
        definition = '//node'
        comment = factory.getRandomString()
        response = self.client.post(
            self.get_uri('tags/'),
            {
                'op': 'new',
                'name': invalid,
                'comment': comment,
                'definition': definition,
            })
        self.assertEqual(httplib.BAD_REQUEST, response.status_code,
            'We did not get BAD_REQUEST for an invalid tag name: %r'
            % (invalid,))
        self.assertFalse(Tag.objects.filter(name=invalid).exists())

    def test_POST_new_populates_nodes(self):
        self.become_admin()
        node1 = factory.make_node()
        node1.set_hardware_details('<node><child /></node>')
        # Create another node that doesn't have a 'child'
        node2 = factory.make_node()
        node2.set_hardware_details('<node />')
        self.assertItemsEqual([], node1.tag_names())
        self.assertItemsEqual([], node2.tag_names())
        name = factory.getRandomString()
        definition = '/node/child'
        comment = factory.getRandomString()
        response = self.client.post(
            self.get_uri('tags/'),
            {
                'op': 'new',
                'name': name,
                'comment': comment,
                'definition': definition,
            })
        self.assertEqual(httplib.OK, response.status_code)
        self.assertItemsEqual([name], node1.tag_names())
        self.assertItemsEqual([], node2.tag_names())


class MAASAPIAnonTest(APIv10TestMixin, TestCase):
    # The MAAS' handler is not accessible to anon users.

    def test_anon_get_config_forbidden(self):
        response = self.client.get(
            self.get_uri('maas/'),
            {'op': 'get_config'})

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_anon_set_config_forbidden(self):
        response = self.client.post(
            self.get_uri('maas/'),
            {'op': 'set_config'})

        self.assertEqual(httplib.FORBIDDEN, response.status_code)


class MAASAPITest(APITestCase):

    def test_simple_user_get_config_forbidden(self):
        response = self.client.get(
            self.get_uri('maas/'),
            {'op': 'get_config'})

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_simple_user_set_config_forbidden(self):
        response = self.client.post(
            self.get_uri('maas/'),
            {'op': 'set_config'})

        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_get_config_requires_name_param(self):
        self.become_admin()
        response = self.client.get(
            self.get_uri('maas/'),
            {
                'op': 'get_config',
            })

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertEqual("No provided name!", response.content)

    def test_get_config_returns_config(self):
        self.become_admin()
        name = factory.getRandomString()
        value = factory.getRandomString()
        Config.objects.set_config(name, value)
        response = self.client.get(
            self.get_uri('maas/'),
            {
                'op': 'get_config',
                'name': name,
            })

        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertIn('application/json', response['Content-Type'])
        self.assertEqual(value, parsed_result)

    def test_set_config_requires_name_param(self):
        self.become_admin()
        response = self.client.post(
            self.get_uri('maas/'),
            {
                'op': 'set_config',
                'value': factory.getRandomString(),
            })

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertEqual("No provided name!", response.content)

    def test_set_config_requires_string_name_param(self):
        self.become_admin()
        value = factory.getRandomString()
        response = self.client.post(
            self.get_uri('maas/'),
            {
                'op': 'set_config',
                'name': '',  # Invalid empty name.
                'value': value,
            })

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertEqual(
           "Invalid name: Please enter a value", response.content)

    def test_set_config_requires_value_param(self):
        self.become_admin()
        response = self.client.post(
            self.get_uri('maas/'),
            {
                'op': 'set_config',
                'name': factory.getRandomString(),
            })

        self.assertEqual(httplib.BAD_REQUEST, response.status_code)
        self.assertEqual("No provided value!", response.content)

    def test_admin_set_config(self):
        self.become_admin()
        name = factory.getRandomString()
        value = factory.getRandomString()
        response = self.client.post(
            self.get_uri('maas/'),
            {
                'op': 'set_config',
                'name': name,
                'value': value,
            })

        self.assertEqual(httplib.OK, response.status_code)
        stored_value = Config.objects.get_config(name)
        self.assertEqual(stored_value, value)


class APIErrorsTest(APIv10TestMixin, TransactionTestCase):

    def test_internal_error_generates_proper_api_response(self):
        error_message = factory.getRandomString()

        # Monkey patch api.create_node to have it raise a RuntimeError.
        def raise_exception(*args, **kwargs):
            raise RuntimeError(error_message)
        self.patch(api, 'create_node', raise_exception)
        response = self.client.post(self.get_uri('nodes/'), {'op': 'new'})

        self.assertEqual(
            (httplib.INTERNAL_SERVER_ERROR, error_message),
            (response.status_code, response.content))


class TestAnonymousCommissioningTimeout(APIv10TestMixin, TestCase):
    """Testing of commissioning timeout API."""

    def test_check_with_no_action(self):
        node = factory.make_node(status=NODE_STATUS.READY)
        self.client.post(
            self.get_uri('nodes/'), {'op': 'check_commissioning'})
        # Anything that's not commissioning should be ignored.
        node = reload_object(node)
        self.assertEqual(NODE_STATUS.READY, node.status)

    def test_check_with_commissioning_but_not_expired_node(self):
        node = factory.make_node(
            status=NODE_STATUS.COMMISSIONING)
        self.client.post(
            self.get_uri('nodes/'), {'op': 'check_commissioning'})
        node = reload_object(node)
        self.assertEqual(NODE_STATUS.COMMISSIONING, node.status)

    def test_check_with_commissioning_and_expired_node(self):
        # Have an interval 1 second longer than the timeout.
        interval = timedelta(seconds=1, minutes=settings.COMMISSIONING_TIMEOUT)
        updated_at = datetime.now() - interval
        node = factory.make_node(
            status=NODE_STATUS.COMMISSIONING, created=datetime.now(),
            updated=updated_at)

        self.client.post(
            self.get_uri('nodes/'), {'op': 'check_commissioning'})
        node = reload_object(node)
        self.assertEqual(NODE_STATUS.FAILED_TESTS, node.status)


class TestPXEConfigAPI(AnonAPITestCase):

    def get_params(self):
        return {'mac': factory.make_mac_address().mac_address}

    def get_optional_params(self):
        return ['mac']

    def get_pxeconfig(self, params=None):
        """Make a request to `pxeconfig`, and return its response dict."""
        if params is None:
            params = self.get_params()
        response = self.client.get(reverse('pxeconfig'), params)
        return json.loads(response.content)

    def test_pxeconfig_returns_json(self):
        response = self.client.get(reverse('pxeconfig'), self.get_params())
        self.assertThat(
            (
                response.status_code,
                response['Content-Type'],
                response.content,
                response.content,
            ),
            MatchesListwise(
                (
                    Equals(httplib.OK),
                    Equals("application/json"),
                    StartsWith(b'{'),
                    Contains('arch'),
                )),
            response)

    def test_pxeconfig_returns_all_kernel_parameters(self):
        self.assertThat(
            self.get_pxeconfig(),
            ContainsAll(KernelParameters._fields))

    def test_pxeconfig_defaults_to_i386_when_node_unknown(self):
        # As a lowest-common-denominator, i386 is chosen when the node is not
        # yet known to MAAS.
        expected_arch = tuple(ARCHITECTURE.i386.split('/'))
        params_out = self.get_pxeconfig()
        observed_arch = params_out["arch"], params_out["subarch"]
        self.assertEqual(expected_arch, observed_arch)

    def test_pxeconfig_uses_fixed_hostname_for_enlisting_node(self):
        new_mac = factory.getRandomMACAddress()
        self.assertEqual(
            'maas-enlist',
            self.get_pxeconfig({'mac': new_mac}).get('hostname'))

    def test_pxeconfig_uses_enlistment_domain_for_enlisting_node(self):
        new_mac = factory.getRandomMACAddress()
        self.assertEqual(
            Config.objects.get_config('enlistment_domain'),
            self.get_pxeconfig({'mac': new_mac}).get('domain'))

    def test_pxeconfig_splits_domain_from_node_hostname(self):
        host = factory.make_name('host')
        domain = factory.make_name('domain')
        full_hostname = '.'.join([host, domain])
        node = factory.make_node(hostname=full_hostname)
        mac = factory.make_mac_address(node=node)
        pxe_config = self.get_pxeconfig(params={'mac': mac.mac_address})
        self.assertEqual(host, pxe_config.get('hostname'))
        self.assertNotIn(domain, pxe_config.values())

    def test_pxeconfig_uses_nodegroup_domain_for_node(self):
        mac = factory.make_mac_address()
        self.assertEqual(
            mac.node.nodegroup.name,
            self.get_pxeconfig({'mac': mac.mac_address}).get('domain'))

    def get_without_param(self, param):
        """Request a `pxeconfig()` response, but omit `param` from request."""
        params = self.get_params()
        del params[param]
        return self.client.get(reverse('pxeconfig'), params)

    def silence_get_ephemeral_name(self):
        # Silence `get_ephemeral_name` to avoid having to fetch the
        # ephemeral name from the filesystem.
        self.patch(
            kernel_opts, 'get_ephemeral_name',
            FakeMethod(result=factory.getRandomString()))

    def test_pxeconfig_requires_mac_address(self):
        # The `mac` parameter is mandatory.
        self.silence_get_ephemeral_name()
        self.assertEqual(
            httplib.BAD_REQUEST,
            self.get_without_param("mac").status_code)

    def test_pxeconfig_has_enlistment_preseed_url_for_unknown_node(self):
        self.silence_get_ephemeral_name()
        params = self.get_params()
        params['mac'] = factory.getRandomMACAddress()
        response = self.client.get(reverse('pxeconfig'), params)
        self.assertEqual(
            compose_enlistment_preseed_url(),
            json.loads(response.content)["preseed_url"])

    def test_pxeconfig_has_preseed_url_for_known_node(self):
        params = self.get_params()
        node = MACAddress.objects.get(mac_address=params['mac']).node
        response = self.client.get(reverse('pxeconfig'), params)
        self.assertEqual(
            compose_preseed_url(node),
            json.loads(response.content)["preseed_url"])

    def test_get_boot_purpose_unknown_node(self):
        # A node that's not yet known to MAAS is assumed to be enlisting,
        # which uses a "commissioning" image.
        self.assertEqual("commissioning", api.get_boot_purpose(None))

    def test_get_boot_purpose_known_node(self):
        # The following table shows the expected boot "purpose" for each set
        # of node parameters.
        options = [
            ("poweroff", {"status": NODE_STATUS.DECLARED}),
            ("commissioning", {"status": NODE_STATUS.COMMISSIONING}),
            ("poweroff", {"status": NODE_STATUS.FAILED_TESTS}),
            ("poweroff", {"status": NODE_STATUS.MISSING}),
            ("poweroff", {"status": NODE_STATUS.READY}),
            ("poweroff", {"status": NODE_STATUS.RESERVED}),
            ("install", {"status": NODE_STATUS.ALLOCATED, "netboot": True}),
            ("local", {"status": NODE_STATUS.ALLOCATED, "netboot": False}),
            ("poweroff", {"status": NODE_STATUS.RETIRED}),
            ]
        node = factory.make_node()
        for purpose, parameters in options:
            for name, value in parameters.items():
                setattr(node, name, value)
            self.assertEqual(purpose, api.get_boot_purpose(node))

    def test_pxeconfig_uses_boot_purpose(self):
        fake_boot_purpose = factory.make_name("purpose")
        self.patch(api, "get_boot_purpose", lambda node: fake_boot_purpose)
        response = self.client.get(reverse('pxeconfig'), self.get_params())
        self.assertEqual(
            fake_boot_purpose,
            json.loads(response.content)["purpose"])


class TestNodeGroupsAPI(APIv10TestMixin, MultipleUsersScenarios, TestCase):
    scenarios = [
        ('anon', dict(userfactory=lambda: AnonymousUser())),
        ('user', dict(userfactory=factory.make_user)),
        ('admin', dict(userfactory=factory.make_admin)),
        ]

    resources = (
        ('celery', FixtureResource(CeleryFixture())),
        )

    def test_reverse_points_to_nodegroups_api(self):
        self.assertEqual(
            self.get_uri('nodegroups/'), reverse('nodegroups_handler'))

    def test_nodegroups_index_lists_nodegroups(self):
        # The nodegroups index lists node groups for the MAAS.
        nodegroup = factory.make_node_group()
        response = self.client.get(
            reverse('nodegroups_handler'), {'op': 'list'})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            [{
                'uuid': nodegroup.uuid,
                'status': nodegroup.status,
                'name': nodegroup.name,
            }],
            json.loads(response.content))


class TestAnonNodeGroupsAPI(AnonAPITestCase):

    resources = (
        ('celery', FixtureResource(CeleryFixture())),
        )

    def create_configured_master(self):
        master = NodeGroup.objects.ensure_master()
        master.uuid = factory.getRandomUUID()
        master.save()

    def test_refresh_calls_refresh_worker(self):
        nodegroup = factory.make_node_group()
        response = self.client.post(
            reverse('nodegroups_handler'), {'op': 'refresh_workers'})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(nodegroup.uuid, get_recorded_nodegroup_uuid())

    def test_refresh_does_not_return_secrets(self):
        # The response from "refresh" contains only an innocuous
        # confirmation.  Anyone can call this method, so it mustn't
        # reveal anything sensitive.
        response = self.client.post(
            reverse('nodegroups_handler'), {'op': 'refresh_workers'})
        self.assertEqual(
            (httplib.OK, "Sending worker refresh."),
            (response.status_code, response.content))

    def test_register_nodegroup_creates_nodegroup_and_interfaces(self):
        self.create_configured_master()
        name = factory.make_name('name')
        uuid = factory.getRandomUUID()
        interface = make_interface_settings()
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'register',
                'name': name,
                'uuid': uuid,
                'interfaces': json.dumps([interface]),
            })
        nodegroup = NodeGroup.objects.get(uuid=uuid)
        # The nodegroup was created with its interface.  Its status is
        # 'PENDING'.
        self.assertEqual(
            (name, NODEGROUP_STATUS.PENDING),
            (nodegroup.name, nodegroup.status))
        self.assertThat(
            nodegroup.nodegroupinterface_set.all()[0],
            MatchesStructure.byEquality(**interface))
        # The response code is 'ACCEPTED': the nodegroup now needs to be
        # validated by an admin.
        self.assertEqual(httplib.ACCEPTED, response.status_code)

    def test_register_nodegroup_returns_credentials_if_master(self):
        name = factory.make_name('name')
        uuid = factory.getRandomUUID()
        fake_broker_url = factory.make_name('fake-broker_url')
        celery_conf = app_or_default().conf
        self.patch(celery_conf, 'BROKER_URL', fake_broker_url)
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'register',
                'name': name,
                'uuid': uuid,
            })
        self.assertEqual(httplib.OK, response.status_code, response)
        parsed_result = json.loads(response.content)
        self.assertEqual(
            ({'BROKER_URL': fake_broker_url}, uuid),
            (parsed_result, NodeGroup.objects.ensure_master().uuid))

    def test_register_nodegroup_configures_master_if_unconfigured(self):
        name = factory.make_name('name')
        uuid = factory.getRandomUUID()
        interface = make_interface_settings()
        self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'register',
                'name': name,
                'uuid': uuid,
                'interfaces': json.dumps([interface]),
            })
        master = NodeGroup.objects.ensure_master()
        self.assertThat(
            master.nodegroupinterface_set.all()[0],
            MatchesStructure.byEquality(**interface))
        self.assertEqual(NODEGROUP_STATUS.ACCEPTED, master.status)

    def test_register_nodegroup_uses_default_zone_name(self):
        uuid = factory.getRandomUUID()
        self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'register',
                'uuid': uuid,
            })
        master = NodeGroup.objects.ensure_master()
        self.assertEqual(
            (NODEGROUP_STATUS.ACCEPTED, DEFAULT_ZONE_NAME),
            (master.status, master.name))

    def test_register_accepts_only_one_managed_interface(self):
        self.create_configured_master()
        name = factory.make_name('name')
        uuid = factory.getRandomUUID()
        # This will try to create 2 "managed" interfaces.
        interface1 = make_interface_settings()
        interface1['management'] = NODEGROUPINTERFACE_MANAGEMENT.DHCP
        interface2 = interface1.copy()
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'register',
                'name': name,
                'uuid': uuid,
                'interfaces': json.dumps([interface1, interface2]),
            })
        self.assertEqual(
            (
                httplib.BAD_REQUEST,
                {'interfaces':
                    [
                        "Only one managed interface can be configured for "
                        "this nodegroup"
                    ]},
            ),
            (response.status_code, json.loads(response.content)))

    def test_register_nodegroup_validates_data(self):
        self.create_configured_master()
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'register',
                'name': factory.make_name('name'),
                'uuid': factory.getRandomUUID(),
                'interfaces': 'invalid data',
            })
        self.assertEqual(
            (
                httplib.BAD_REQUEST,
                {'interfaces': ['Invalid json value.']},
            ),
            (response.status_code, json.loads(response.content)))

    def test_register_nodegroup_twice_does_not_update_nodegroup(self):
        nodegroup = factory.make_node_group()
        nodegroup.status = NODEGROUP_STATUS.PENDING
        nodegroup.save()
        name = factory.make_name('name')
        uuid = nodegroup.uuid
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'register',
                'name': name,
                'uuid': uuid,
            })
        new_nodegroup = NodeGroup.objects.get(uuid=uuid)
        self.assertEqual(
            (nodegroup.name, NODEGROUP_STATUS.PENDING),
            (new_nodegroup.name, new_nodegroup.status))
        # The response code is 'ACCEPTED': the nodegroup still needs to be
        # validated by an admin.
        self.assertEqual(httplib.ACCEPTED, response.status_code)

    def test_register_rejected_nodegroup_fails(self):
        nodegroup = factory.make_node_group()
        nodegroup.status = NODEGROUP_STATUS.REJECTED
        nodegroup.save()
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'register',
                'name': factory.make_name('name'),
                'uuid': nodegroup.uuid,
                'interfaces': json.dumps([]),
            })
        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_register_accepted_cluster_gets_credentials(self):
        fake_broker_url = factory.make_name('fake-broker_url')
        celery_conf = app_or_default().conf
        self.patch(celery_conf, 'BROKER_URL', fake_broker_url)
        nodegroup = factory.make_node_group()
        nodegroup.status = NODEGROUP_STATUS.ACCEPTED
        nodegroup.save()
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'register',
                'name': factory.make_name('name'),
                'uuid': nodegroup.uuid,
            })
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertIn('application/json', response['Content-Type'])
        self.assertEqual({'BROKER_URL': fake_broker_url}, parsed_result)


def dict_subset(obj, fields):
    """Return a dict of a subset of the fields/values of an object."""
    undefined = object()
    values = (getattr(obj, field, undefined) for field in fields)
    return {
        field: value for field, value in izip(fields, values)
        if value is not undefined
     }


class TestNodeGroupInterfacesAPI(APITestCase):

    def test_list_lists_interfaces(self):
        self.become_admin()
        nodegroup = factory.make_node_group()
        response = self.client.get(
            reverse('nodegroupinterfaces_handler', args=[nodegroup.uuid]),
            {'op': 'list'})
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            [
                dict_subset(interface, DISPLAYED_NODEGROUP_FIELDS)
                for interface in nodegroup.nodegroupinterface_set.all()
            ],
            json.loads(response.content))

    def test_list_only_available_to_admin(self):
        nodegroup = factory.make_node_group()
        response = self.client.get(
            reverse('nodegroupinterfaces_handler', args=[nodegroup.uuid]),
            {'op': 'list'})
        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_new_creates_interface(self):
        self.become_admin()
        nodegroup = factory.make_node_group(
            management=NODEGROUPINTERFACE_MANAGEMENT.UNMANAGED)

        settings = make_interface_settings()
        query_data = dict(settings, op="new")
        response = self.client.post(
            reverse('nodegroupinterfaces_handler', args=[nodegroup.uuid]),
            query_data)
        self.assertEqual(httplib.OK, response.status_code, response.content)
        expected_result = settings
        new_interface = NodeGroupInterface.objects.get(
            nodegroup=nodegroup, interface=settings['interface'])
        self.assertThat(
            new_interface,
            MatchesStructure.byEquality(**expected_result))

    def test_new_validates_data(self):
        self.become_admin()
        nodegroup = factory.make_node_group()
        response = self.client.post(
            reverse('nodegroupinterfaces_handler', args=[nodegroup.uuid]),
            {'op': 'new', 'ip': 'invalid ip'})
        self.assertEqual(
            (
                httplib.BAD_REQUEST,
                {'ip': ["Enter a valid IPv4 or IPv6 address."]},
            ),
            (response.status_code, json.loads(response.content)))

    def test_new_only_available_to_admin(self):
        nodegroup = factory.make_node_group()
        response = self.client.get(
            reverse('nodegroupinterfaces_handler', args=[nodegroup.uuid]),
            {'op': 'new'})
        self.assertEqual(httplib.FORBIDDEN, response.status_code)


class TestNodeGroupInterfaceAPI(APITestCase):

    def test_read_interface(self):
        self.become_admin()
        nodegroup = factory.make_node_group()
        interface = nodegroup.get_managed_interface()
        response = self.client.get(
            reverse(
                'nodegroupinterface_handler',
                args=[nodegroup.uuid, interface.interface]))
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            dict_subset(interface, DISPLAYED_NODEGROUP_FIELDS),
            json.loads(response.content))

    def test_update_interface(self):
        self.become_admin()
        nodegroup = factory.make_node_group()
        interface = nodegroup.get_managed_interface()
        get_ip_in_network = partial(
            factory.getRandomIPInNetwork, interface.network)
        new_ip_range_high = next(
            ip for ip in iter(get_ip_in_network, None)
            if ip != interface.ip_range_high)
        response = self.client.put(
            reverse(
                'nodegroupinterface_handler',
                args=[nodegroup.uuid, interface.interface]),
            {'ip_range_high': new_ip_range_high})
        self.assertEqual(
            (httplib.OK, new_ip_range_high),
            (response.status_code, reload_object(interface).ip_range_high))


def explain_unexpected_response(expected_status, response):
    """Return human-readable failure message: unexpected http response."""
    return "Unexpected http status (expected %s): %s - %s" % (
        expected_status,
        response.status_code,
        response.content,
        )


def make_worker_client(nodegroup):
    """Create a test client logged in as if it were `nodegroup`."""
    return OAuthAuthenticatedClient(
        get_worker_user(), token=nodegroup.api_token)


class TestNodeGroupAPI(APITestCase):

    resources = (
        ('celery', FixtureResource(CeleryFixture())),
        )

    def test_reverse_points_to_nodegroup(self):
        nodegroup = factory.make_node_group()
        self.assertEqual(
            self.get_uri('nodegroups/%s/' % nodegroup.uuid),
            reverse('nodegroup_handler', args=[nodegroup.uuid]))

    def test_GET_returns_node_group(self):
        nodegroup = factory.make_node_group()
        response = self.client.get(
            reverse('nodegroup_handler', args=[nodegroup.uuid]))
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual(
            nodegroup.uuid, json.loads(response.content).get('uuid'))

    def test_GET_returns_404_for_unknown_node_group(self):
        response = self.client.get(
            self.get_uri('nodegroups/%s/' % factory.make_name('nodegroup')))
        self.assertEqual(httplib.NOT_FOUND, response.status_code)

    def test_update_leases_processes_empty_leases_dict(self):
        nodegroup = factory.make_node_group()
        factory.make_dhcp_lease(nodegroup=nodegroup)
        client = make_worker_client(nodegroup)
        response = client.post(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {
                'op': 'update_leases',
                'leases': json.dumps({}),
            })
        self.assertEqual(
            (httplib.OK, "Leases updated."),
            (response.status_code, response.content))
        self.assertItemsEqual(
            [], DHCPLease.objects.filter(nodegroup=nodegroup))

    def test_update_leases_stores_leases(self):
        self.patch(Omshell, 'create')
        nodegroup = factory.make_node_group()
        lease = factory.make_random_leases()
        client = make_worker_client(nodegroup)
        response = client.post(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {
                'op': 'update_leases',
                'leases': json.dumps(lease),
            })
        self.assertEqual(
            (httplib.OK, "Leases updated."),
            (response.status_code, response.content))
        self.assertItemsEqual(
            lease.keys(), [
                lease.ip
                for lease in DHCPLease.objects.filter(nodegroup=nodegroup)])

    def test_update_leases_adds_new_leases_on_worker(self):
        nodegroup = factory.make_node_group()
        client = make_worker_client(nodegroup)
        self.patch(Omshell, 'create', FakeMethod())
        new_leases = factory.make_random_leases()
        response = client.post(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {
                'op': 'update_leases',
                'leases': json.dumps(new_leases),
            })
        self.assertEqual(
            (httplib.OK, "Leases updated."),
            (response.status_code, response.content))
        self.assertEqual(
            [(new_leases.keys()[0], new_leases.values()[0])],
            Omshell.create.extract_args())

    def test_update_leases_does_not_add_old_leases(self):
        self.patch(Omshell, 'create')
        nodegroup = factory.make_node_group()
        client = make_worker_client(nodegroup)
        self.patch(tasks, 'add_new_dhcp_host_map', FakeMethod())
        response = client.post(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {
                'op': 'update_leases',
                'leases': json.dumps(factory.make_random_leases()),
            })
        self.assertEqual(
            (httplib.OK, "Leases updated."),
            (response.status_code, response.content))
        self.assertEqual([], tasks.add_new_dhcp_host_map.calls)

    def test_worker_calls_update_leases(self):
        # In bug 1041158, the worker's upload_leases task tried to call
        # the update_leases API at the wrong URL path.  It has the right
        # path now.
        nodegroup = factory.make_node_group()
        refresh_worker(nodegroup)
        self.patch(MAASClient, 'post', Mock())
        leases = factory.make_random_leases()
        send_leases(leases)
        nodegroup_path = reverse(
            'nodegroup_handler', args=[nodegroup.uuid])
        nodegroup_path = nodegroup_path.decode('ascii').lstrip('/')
        MAASClient.post.assert_called_once_with(
            nodegroup_path, 'update_leases', leases=json.dumps(leases))

    def test_accept_accepts_nodegroup(self):
        nodegroups = [factory.make_node_group() for i in range(3)]
        uuids = [nodegroup.uuid for nodegroup in nodegroups]
        self.become_admin()
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'accept',
                'uuid': uuids,
            })
        self.assertEqual(
            (httplib.OK, "Nodegroup(s) accepted."),
            (response.status_code, response.content))
        self.assertThat(
            [nodegroup.status for nodegroup in
             reload_objects(NodeGroup, nodegroups)],
            AllMatch(Equals(NODEGROUP_STATUS.ACCEPTED)))

    def test_accept_reserved_to_admin(self):
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'accept',
                'uuid': factory.getRandomString(),
            })
        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_reject_rejects_nodegroup(self):
        nodegroups = [factory.make_node_group() for i in range(3)]
        uuids = [nodegroup.uuid for nodegroup in nodegroups]
        self.become_admin()
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'reject',
                'uuid': uuids,
            })
        self.assertEqual(
            (httplib.OK, "Nodegroup(s) rejected."),
            (response.status_code, response.content))
        self.assertThat(
            [nodegroup.status for nodegroup in
             reload_objects(NodeGroup, nodegroups)],
            AllMatch(Equals(NODEGROUP_STATUS.REJECTED)))

    def test_reject_reserved_to_admin(self):
        response = self.client.post(
            reverse('nodegroups_handler'),
            {
                'op': 'reject',
                'uuid': factory.getRandomString(),
            })
        self.assertEqual(httplib.FORBIDDEN, response.status_code)


def log_in_as_normal_user(client):
    """Log `client` in as a normal user."""
    password = factory.getRandomString()
    user = factory.make_user(password=password)
    client.login(username=user.username, password=password)
    return user


class TestNodeGroupAPIAuth(APIv10TestMixin, TestCase):
    """Authorization tests for nodegroup API."""

    def test_nodegroup_requires_authentication(self):
        nodegroup = factory.make_node_group()
        response = self.client.get(
            reverse('nodegroup_handler', args=[nodegroup.uuid]))
        self.assertEqual(httplib.UNAUTHORIZED, response.status_code)

    def test_update_leases_works_for_nodegroup_worker(self):
        nodegroup = factory.make_node_group()
        client = make_worker_client(nodegroup)
        response = client.post(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {'op': 'update_leases', 'leases': json.dumps({})})
        self.assertEqual(
            httplib.OK, response.status_code,
            explain_unexpected_response(httplib.OK, response))

    def test_update_leases_does_not_work_for_normal_user(self):
        nodegroup = factory.make_node_group()
        log_in_as_normal_user(self.client)
        response = self.client.post(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {'op': 'update_leases', 'leases': json.dumps({})})
        self.assertEqual(
            httplib.FORBIDDEN, response.status_code,
            explain_unexpected_response(httplib.FORBIDDEN, response))

    def test_update_leases_does_not_let_worker_update_other_nodegroup(self):
        requesting_nodegroup = factory.make_node_group()
        about_nodegroup = factory.make_node_group()
        client = make_worker_client(requesting_nodegroup)
        response = client.post(
            reverse('nodegroup_handler', args=[about_nodegroup.uuid]),
            {'op': 'update_leases', 'leases': json.dumps({})})
        self.assertEqual(
            httplib.FORBIDDEN, response.status_code,
            explain_unexpected_response(httplib.FORBIDDEN, response))

    def test_nodegroup_list_nodes_requires_authentication(self):
        nodegroup = factory.make_node_group()
        response = self.client.get(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {'op': 'list_nodes'})
        self.assertEqual(httplib.UNAUTHORIZED, response.status_code)

    def test_nodegroup_list_nodes_does_not_work_for_normal_user(self):
        nodegroup = factory.make_node_group()
        log_in_as_normal_user(self.client)
        response = self.client.get(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {'op': 'list_nodes'})
        self.assertEqual(
            httplib.FORBIDDEN, response.status_code,
            explain_unexpected_response(httplib.FORBIDDEN, response))

    def test_nodegroup_list_nodes_works_for_nodegroup_worker(self):
        nodegroup = factory.make_node_group()
        node = factory.make_node(nodegroup=nodegroup)
        client = make_worker_client(nodegroup)
        response = client.get(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {'op': 'list_nodes'})
        self.assertEqual(
            httplib.OK, response.status_code,
            explain_unexpected_response(httplib.OK, response))
        parsed_result = json.loads(response.content)
        self.assertItemsEqual([node.system_id], parsed_result)

    def make_node_hardware_details_request(self, client, nodegroup=None):
        if nodegroup is None:
            nodegroup = factory.make_node_group()
        node = factory.make_node(nodegroup=nodegroup)
        return client.get(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {'op': 'node_hardware_details', 'system_ids': [node.system_id]})

    def test_GET_node_hardware_details_requires_authentication(self):
        response = self.make_node_hardware_details_request(self.client)
        self.assertEqual(httplib.UNAUTHORIZED, response.status_code)

    def test_GET_node_hardware_details_refuses_nonworker(self):
        log_in_as_normal_user(self.client)
        response = self.make_node_hardware_details_request(self.client)
        self.assertEqual(
            httplib.FORBIDDEN, response.status_code,
            explain_unexpected_response(httplib.FORBIDDEN, response))

    def test_GET_node_hardware_details_returns_hardware_details(self):
        nodegroup = factory.make_node_group()
        hardware_details = '<node />'
        node = factory.make_node(nodegroup=nodegroup)
        node.set_hardware_details(hardware_details)
        client = make_worker_client(nodegroup)
        response = client.get(
            reverse('nodegroup_handler', args=[nodegroup.uuid]),
            {'op': 'node_hardware_details', 'system_ids': [node.system_id]})
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual([[node.system_id, hardware_details]], parsed_result)

    def test_GET_node_hardware_details_does_not_see_other_groups(self):
        hardware_details = '<node />'
        nodegroup_mine = factory.make_node_group()
        nodegroup_theirs = factory.make_node_group()
        node_mine = factory.make_node(nodegroup=nodegroup_mine)
        node_mine.set_hardware_details(hardware_details)
        node_theirs = factory.make_node(nodegroup=nodegroup_theirs)
        node_theirs.set_hardware_details(hardware_details)
        client = make_worker_client(nodegroup_mine)
        response = client.get(
            reverse('nodegroup_handler', args=[nodegroup_mine.uuid]),
            {'op': 'node_hardware_details',
             'system_ids': [node_mine.system_id, node_theirs.system_id]})
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        self.assertEqual([[node_mine.system_id, hardware_details]],
                         parsed_result)

    def test_GET_node_hardware_details_with_no_details(self):
        nodegroup = factory.make_node_group()
        client = make_worker_client(nodegroup)
        response = self.make_node_hardware_details_request(client, nodegroup)
        self.assertEqual(httplib.OK, response.status_code)
        parsed_result = json.loads(response.content)
        node_system_id = parsed_result[0][0]
        self.assertEqual([[node_system_id, None]], parsed_result)


class TestBootImagesAPI(APITestCase):

    resources = (
        ('celery', FixtureResource(CeleryFixture())),
        )

    def report_images(self, images, client=None):
        if client is None:
            client = self.client
        return client.post(
            reverse('boot_images_handler'),
            {'op': 'report_boot_images', 'images': json.dumps(images)})

    def test_report_boot_images_does_not_work_for_normal_user(self):
        NodeGroup.objects.ensure_master()
        log_in_as_normal_user(self.client)
        response = self.report_images([])
        self.assertEqual(httplib.FORBIDDEN, response.status_code)

    def test_report_boot_images_works_for_master_worker(self):
        client = make_worker_client(NodeGroup.objects.ensure_master())
        response = self.report_images([], client=client)
        self.assertEqual(httplib.OK, response.status_code)

    def test_report_boot_images_stores_images(self):
        image = make_boot_image_params()
        client = make_worker_client(NodeGroup.objects.ensure_master())
        response = self.report_images([image], client=client)
        self.assertEqual(
            (httplib.OK, "OK"),
            (response.status_code, response.content))
        self.assertTrue(
            BootImage.objects.have_image(**image))

    def test_report_boot_images_ignores_unknown_image_properties(self):
        image = make_boot_image_params()
        image['nonesuch'] = factory.make_name('nonesuch'),
        client = make_worker_client(NodeGroup.objects.ensure_master())
        response = self.report_images([image], client=client)
        self.assertEqual(
            (httplib.OK, "OK"),
            (response.status_code, response.content))

    def test_report_boot_images_warns_if_no_images_found(self):
        recorder = self.patch(api, 'register_persistent_error')
        client = make_worker_client(NodeGroup.objects.ensure_master())

        response = self.report_images([], client=client)
        self.assertEqual(
            (httplib.OK, "OK"),
            (response.status_code, response.content))

        self.assertIn(
            COMPONENT.IMPORT_PXE_FILES,
            [args[0][0] for args in recorder.call_args_list])

    def test_report_boot_images_removes_warning_if_images_found(self):
        self.patch(api, 'register_persistent_error')
        self.patch(api, 'discard_persistent_error')
        client = make_worker_client(NodeGroup.objects.ensure_master())

        response = self.report_images(
            [make_boot_image_params()], client=client)
        self.assertEqual(
            (httplib.OK, "OK"),
            (response.status_code, response.content))

        self.assertItemsEqual(
            [],
            api.register_persistent_error.call_args_list)
        api.discard_persistent_error.assert_called_once_with(
            COMPONENT.IMPORT_PXE_FILES)

    def test_worker_calls_report_boot_images(self):
        refresh_worker(NodeGroup.objects.ensure_master())
        self.patch(MAASClient, 'post')
        self.patch(tftppath, 'list_boot_images', Mock(return_value=[]))

        tasks.report_boot_images.delay()

        MAASClient.post.assert_called_once_with(
            reverse('boot_images_handler').lstrip('/'), 'report_boot_images',
            images=json.dumps([]))


class TestDescribe(AnonAPITestCase):
    """Tests for the `describe` view."""

    def test_describe_returns_json(self):
        response = self.client.get(reverse('describe'))
        self.assertThat(
            (response.status_code,
             response['Content-Type'],
             response.content,
             response.content),
            MatchesListwise(
                (Equals(httplib.OK),
                 Equals("application/json"),
                 StartsWith(b'{'),
                 Contains('name'))),
            response)

    def test_describe(self):
        response = self.client.get(reverse('describe'))
        description = json.loads(response.content)
        self.assertSetEqual({"doc", "handlers"}, set(description))
        self.assertIsInstance(description["handlers"], list)
