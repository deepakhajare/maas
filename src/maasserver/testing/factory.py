# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test object factories."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "factory",
    ]

from io import BytesIO
import random
import time

from django.contrib.auth.models import User
from maasserver.models import (
    ARCHITECTURE,
    FileStorage,
    MACAddress,
    Node,
    NODE_STATUS,
    SSHKey,
    )
from maasserver.testing import get_data
from maasserver.testing.enum import map_enum
import maastesting.factory


class Factory(maastesting.factory.Factory):

    def getRandomEnum(self, enum):
        """Pick a random item from an enumeration class.

        :param enum: An enumeration class such as `NODE_STATUS`.
        :return: The value of one of its items.
        """
        return random.choice(list(map_enum(enum).values()))

    def getRandomChoice(self, choices, but_not=None):
        """Pick a random item from `choices`.

        :param choices: A sequence of choices in Django form choices format:
            [
                ('choice_id_1', "Choice name 1"),
                ('choice_id_2', "Choice name 2"),
            ]
        :param but_not: A list of choices'ids to exclude.
        :type but_not: Sequence.
        :return: The "id" portion of a random choice out of `choices`.
        """
        if but_not is None:
            but_not = []
        return random.choice(
            [choice for choice in choices if choice[0] not in but_not])[0]

    def make_node(self, hostname='', set_hostname=False, status=None,
                  architecture=ARCHITECTURE.i386, **kwargs):
        # hostname=None is a valid value, hence the set_hostname trick.
        if hostname is '' and set_hostname:
            hostname = self.getRandomString(255)
        if status is None:
            status = NODE_STATUS.DEFAULT_STATUS
        node = Node(
            hostname=hostname, status=status, architecture=architecture,
            **kwargs)
        node.save()
        return node

    def make_mac_address(self, address):
        """Create a MAC address."""
        node = Node()
        node.save()
        mac = MACAddress(mac_address=address, node=node)
        mac.save()
        return mac

    def make_user(self, username=None, password=None, email=None):
        if username is None:
            username = self.getRandomString(10)
        if email is None:
            email = '%s@example.com' % self.getRandomString(10)
        if password is None:
            password = 'test'
        return User.objects.create_user(
            username=username, password=password, email=email)

    def make_sshkey(self, user):
        key_string = get_data('data/test_rsa.pub')
        key = SSHKey(key=key_string, user=user)
        key.save()
        return key

    def make_user_with_keys(self, n_keys=2, **kwargs):
        """Create a user with n `SSHKey`.

        Additional keyword arguments are passed to `make_user()`.

        Keys will have a comment of the form: <username>-key-<i> where i
        is the key index.
        """
        user = self.make_user(**kwargs)
        for i in range(n_keys):
            SSHKey(
                user=user,
                key='ssh-rsa KEY %s-key-%d' % (user.username, i)).save()
        return user

    def make_admin(self, username=None, password=None, email=None):
        admin = self.make_user(
            username=username, password=password, email=email)
        admin.is_superuser = True
        admin.save()
        return admin

    def make_file_storage(self, filename=None, data=None):
        if filename is None:
            filename = self.getRandomString(100)
        if data is None:
            data = self.getRandomString(1024).encode('ascii')

        return FileStorage.objects.save_file(filename, BytesIO(data))

    def make_oauth_header(self, **kwargs):
        """Fake an OAuth authorization header.

        This will use arbitrary values.  Pass as keyword arguments any
        header items that you wish to override.
        """
        items = {
            'realm': self.getRandomString(),
            'oauth_nonce': random.randint(0, 99999),
            'oauth_timestamp': time.time(),
            'oauth_consumer_key': self.getRandomString(18),
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_version': '1.0',
            'oauth_token': self.getRandomString(18),
            'oauth_signature': "%%26%s" % self.getRandomString(32),
        }
        items.update(kwargs)
        return "OAuth " + ", ".join([
            '%s="%s"' % (key, value) for key, value in items.items()])


# Create factory singleton.
factory = Factory()
