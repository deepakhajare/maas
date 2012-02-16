# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver models."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import codecs
from operator import attrgetter
import os
import shutil

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from maasserver.exceptions import (
    CannotDeleteUserException,
    PermissionDenied,
    )
from maasserver.models import (
    GENERIC_CONSUMER,
    MACAddress,
    Node,
    NODE_STATUS,
    NODE_STATUS_CHOICES_DICT,
    UserProfile,
    )
from maasserver.testing.factory import factory
from maastesting import TestCase
from piston.models import (
    Consumer,
    KEY_SIZE,
    SECRET_SIZE,
    Token,
    )


class NodeTest(TestCase):

    def test_system_id(self):
        """
        The generated system_id looks good.

        """
        node = factory.make_node()
        self.assertEqual(len(node.system_id), 41)
        self.assertTrue(node.system_id.startswith('node-'))

    def test_display_status(self):
        node = factory.make_node()
        self.assertEqual(
            NODE_STATUS_CHOICES_DICT[NODE_STATUS.DECLARED],
            node.display_status())

    def test_add_mac_address(self):
        node = factory.make_node()
        node.add_mac_address('AA:BB:CC:DD:EE:FF')
        macs = MACAddress.objects.filter(
            node=node, mac_address='AA:BB:CC:DD:EE:FF').count()
        self.assertEqual(1, macs)

    def test_remove_mac_address(self):
        node = factory.make_node()
        node.add_mac_address('AA:BB:CC:DD:EE:FF')
        node.remove_mac_address('AA:BB:CC:DD:EE:FF')
        macs = MACAddress.objects.filter(
            node=node, mac_address='AA:BB:CC:DD:EE:FF').count()
        self.assertEqual(0, macs)

    def test_acquire(self):
        node = factory.make_node(status=NODE_STATUS.READY)
        user = factory.make_user()
        node.acquire(user)
        self.assertEqual(user, node.owner)
        self.assertEqual(NODE_STATUS.ALLOCATED, node.status)


class NodeManagerTest(TestCase):

    def make_node(self, user=None):
        """Create a node, allocated to `user` if given."""
        if user is None:
            status = NODE_STATUS.READY
        else:
            status = NODE_STATUS.ALLOCATED
        return factory.make_node(set_hostname=True, status=status, owner=user)

    def test_filter_by_ids_filters_nodes_by_ids(self):
        nodes = [factory.make_node() for counter in range(5)]
        ids = [node.system_id for node in nodes]
        selection = slice(1, 3)
        self.assertItemsEqual(
            nodes[selection],
            Node.objects.filter_by_ids(Node.objects.all(), ids[selection]))

    def test_filter_by_ids_with_empty_list_returns_empty(self):
        factory.make_node()
        self.assertItemsEqual(
            [], Node.objects.filter_by_ids(Node.objects.all(), []))

    def test_filter_by_ids_without_ids_returns_full(self):
        node = factory.make_node()
        self.assertItemsEqual(
            [node], Node.objects.filter_by_ids(Node.objects.all(), None))

    def test_get_visible_nodes_for_user_lists_visible_nodes(self):
        """get_visible_nodes lists the nodes a user has access to.

        When run for a regular user it returns unowned nodes, and nodes
        owned by that user.
        """
        user = factory.make_user()
        visible_nodes = [self.make_node(owner) for owner in [None, user]]
        self.make_node(factory.make_user())
        self.assertItemsEqual(
            visible_nodes, Node.objects.get_visible_nodes(user))

    def test_get_visible_nodes_admin_lists_all_nodes(self):
        admin = factory.make_admin()
        owners = [
            None,
            factory.make_user(),
            factory.make_admin(),
            admin,
            ]
        nodes = [self.make_node(owner) for owner in owners]
        self.assertItemsEqual(nodes, Node.objects.get_visible_nodes(admin))

    def test_get_visible_nodes_filters_by_id(self):
        user = factory.make_user()
        nodes = [self.make_node(user) for counter in range(5)]
        ids = [node.system_id for node in nodes]
        wanted_slice = slice(0, 3)
        self.assertItemsEqual(
            nodes[wanted_slice],
            Node.objects.get_visible_nodes(user, ids=ids[wanted_slice]))

    def test_get_editable_nodes_for_user_lists_owned_nodes(self):
        user = factory.make_user()
        visible_node = self.make_node(user)
        self.make_node(None)
        self.make_node(factory.make_user())
        self.assertItemsEqual(
            [visible_node], Node.objects.get_editable_nodes(user))

    def test_get_editable_nodes_admin_lists_all_nodes(self):
        admin = factory.make_admin()
        owners = [
            None,
            factory.make_user(),
            factory.make_admin(),
            admin,
            ]
        nodes = [self.make_node(owner) for owner in owners]
        self.assertItemsEqual(nodes, Node.objects.get_editable_nodes(admin))

    def test_get_editable_nodes_filters_by_id(self):
        user = factory.make_user()
        nodes = [self.make_node(user) for counter in range(5)]
        ids = [node.system_id for node in nodes]
        wanted_slice = slice(0, 3)
        self.assertItemsEqual(
            nodes[wanted_slice],
            Node.objects.get_editable_nodes(user, ids=ids[wanted_slice]))

    def test_get_visible_node_or_404_ok(self):
        """get_visible_node_or_404 fetches nodes by system_id."""
        user = factory.make_user()
        node = self.make_node(user)
        self.assertEqual(
            node, Node.objects.get_visible_node_or_404(node.system_id, user))

    def test_get_visible_node_or_404_raises_PermissionDenied(self):
        """get_visible_node_or_404 raises PermissionDenied if the provided
        user cannot access the returned node."""
        user_node = self.make_node(factory.make_user())
        self.assertRaises(
            PermissionDenied,
            Node.objects.get_visible_node_or_404,
            user_node.system_id, factory.make_user())

    def test_get_available_node_for_acquisition_finds_available_node(self):
        user = factory.make_user()
        node = self.make_node(None)
        self.assertEqual(
            node, Node.objects.get_available_node_for_acquisition(user))

    def test_get_available_node_for_acquisition_returns_none_if_empty(self):
        user = factory.make_user()
        self.assertEqual(
            None, Node.objects.get_available_node_for_acquisition(user))

    def test_get_available_node_for_acquisition_ignores_taken_nodes(self):
        user = factory.make_user()
        available_status = NODE_STATUS.READY
        unavailable_statuses = (
            set(NODE_STATUS_CHOICES_DICT.keys()) - set([available_status]))
        for status in unavailable_statuses:
            factory.make_node(status=status)
        self.assertEqual(
            None, Node.objects.get_available_node_for_acquisition(user))

    def test_get_available_node_for_acquisition_ignores_invisible_nodes(self):
        user = factory.make_user()
        node = self.make_node()
        node.owner = factory.make_user()
        node.save()
        self.assertEqual(
            None, Node.objects.get_available_node_for_acquisition(user))

    def test_stop_nodes_stops_nodes(self):
        user = factory.make_user()
        node = self.make_node(user)
        output = Node.objects.stop_nodes([node.system_id], user)

        self.assertItemsEqual([node], output)
        self.assertEqual(
            'stop',
            Node.objects.provisioning_proxy.power_status[node.system_id])

    def test_stop_nodes_ignores_uneditable_nodes(self):
        nodes = [self.make_node(factory.make_user()) for counter in range(3)]
        ids = [node.system_id for node in nodes]
        stoppable_node = nodes[0]
        self.assertItemsEqual(
            [stoppable_node],
            Node.objects.stop_nodes(ids, stoppable_node.owner))

    def test_start_nodes_starts_nodes(self):
        user = factory.make_user()
        node = self.make_node(user)
        output = Node.objects.start_nodes([node.system_id], user)

        self.assertItemsEqual([node], output)
        self.assertEqual(
            'start',
            Node.objects.provisioning_proxy.power_status[node.system_id])

    def test_start_nodes_ignores_uneditable_nodes(self):
        nodes = [self.make_node(factory.make_user()) for counter in range(3)]
        ids = [node.system_id for node in nodes]
        startable_node = nodes[0]
        self.assertItemsEqual(
            [startable_node],
            Node.objects.start_nodes(ids, startable_node.owner))


class MACAddressTest(TestCase):

    def make_MAC(self, address):
        """Create a MAC address."""
        node = Node()
        node.save()
        return MACAddress(mac_address=address, node=node)

    def test_stores_to_database(self):
        mac = self.make_MAC('00:11:22:33:44:55')
        mac.save()
        self.assertEqual([mac], list(MACAddress.objects.all()))

    def test_invalid_address_raises_validation_error(self):
        mac = self.make_MAC('aa:bb:ccxdd:ee:ff')
        self.assertRaises(ValidationError, mac.full_clean)


class UserProfileTest(TestCase):

    def assertTokenValid(self, token):
        self.assertIsInstance(token.key, basestring)
        self.assertEqual(KEY_SIZE, len(token.key))
        self.assertIsInstance(token.secret, basestring)
        self.assertEqual(SECRET_SIZE, len(token.secret))

    def assertConsumerValid(self, consumer):
        self.assertIsInstance(consumer.key, basestring)
        self.assertEqual(KEY_SIZE, len(consumer.key))
        self.assertEqual('', consumer.secret)

    def test_profile_creation(self):
        # A profile is created each time a user is created.
        user = factory.make_user()
        self.assertIsInstance(user.get_profile(), UserProfile)
        self.assertEqual(user, user.get_profile().user)

    def test_consumer_creation(self):
        # A generic consumer is created each time a user is created.
        user = factory.make_user()
        consumers = Consumer.objects.filter(user=user, name=GENERIC_CONSUMER)
        self.assertEqual([user], [consumer.user for consumer in consumers])
        self.assertConsumerValid(consumers[0])

    def test_token_creation(self):
        # A token is created each time a user is created.
        user = factory.make_user()
        tokens = Token.objects.filter(user=user)
        self.assertEqual([user], [token.user for token in tokens])
        self.assertTokenValid(tokens[0])

    def test_create_authorisation_token(self):
        user = factory.make_user()
        profile = user.get_profile()
        consumer, token = profile.create_authorisation_token()
        self.assertEqual(consumer, token.consumer)
        self.assertEqual(user, token.user)
        self.assertEqual(user, consumer.user)
        self.assertConsumerValid(consumer)
        self.assertTokenValid(token)

    def test_get_authorisation_tokens(self):
        user = factory.make_user()
        other_user = factory.make_user()
        profile = user.get_profile()
        other_profile = other_user.get_profile()
        _, token = profile.create_authorisation_token()
        other_profile.create_authorisation_token()
        tokens = profile.get_authorisation_tokens()
        # This user has 2 tokens: the one that was created automatically
        # when the user was created plus the one we've created manually.
        self.assertEqual(2, tokens.count())
        self.assertEqual(token, list(tokens.order_by('id'))[1])

    def test_delete(self):
        # Deleting a profile also deletes the related user.
        profile = factory.make_user().get_profile()
        profile_id = profile.id
        profile.delete()
        self.assertFalse(User.objects.filter(id=profile_id).exists())
        self.assertFalse(
            UserProfile.objects.filter(id=profile_id).exists())

    def test_delete_consumers_tokens(self):
        # Deleting a profile deletes the related tokens and consumers.
        profile = factory.make_user().get_profile()
        token_ids, consumer_ids = zip(*[
            map(attrgetter('id'), profile.create_authorisation_token())
            for i in range(3)])
        profile.delete()
        self.assertFalse(Consumer.objects.filter(id__in=consumer_ids).exists())
        self.assertFalse(Token.objects.filter(id__in=token_ids).exists())

    def test_delete_attached_nodes(self):
        # Cannot delete a user with nodes attached to it.
        profile = factory.make_user().get_profile()
        factory.make_node(owner=profile.user)
        message = (
            "User %s cannot be deleted: it still has 1 node\(s\) deployed\." %
            profile.user.username)
        self.assertRaisesRegexp(
            CannotDeleteUserException, message, profile.delete)


class FileStorageTest(TestCase):
    """Testing of the :class:`FileStorage` model."""

    FILEPATH = settings.MEDIA_ROOT

    def setUp(self):
        super(FileStorageTest, self).setUp()
        os.mkdir(self.FILEPATH)
        self.addCleanup(shutil.rmtree, self.FILEPATH)

    def test_creation(self):
        storage = factory.make_file_storage(filename="myfile", data=b"mydata")
        expected = ["myfile", "mydata"]
        actual = [storage.filename, storage.data.read()]
        self.assertEqual(expected, actual)

    def test_creation_writes_a_file(self):
        # The development settings say to write a file starting at
        # /var/tmp/maas, so check one is actually written there.  The field
        # itself is hard-coded to make a directory called "storage".
        factory.make_file_storage(filename="myfile", data=b"mydata")

        expected_filename = os.path.join(
            self.FILEPATH, "storage", "myfile")

        with open(expected_filename) as f:
            self.assertEqual("mydata", f.read())

    def test_stores_binary_data(self):
        # This horrible binary data could never, ever, under any
        # encoding known to man be intepreted as text.  Switch the bytes
        # of the byte-order mark around and by design you get an invalid
        # codepoint; put a byte with the high bit set between bytes that
        # have it cleared, and you have a guaranteed non-UTF-8 sequence.
        binary_data = codecs.BOM64_LE + codecs.BOM64_BE + b'\x00\xff\x00'
        # And yet, because FileStorage supports binary data, it comes
        # out intact.
        storage = factory.make_file_storage(filename="x", data=binary_data)
        self.assertEqual(binary_data, storage.data.read())
