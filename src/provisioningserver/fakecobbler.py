# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import (
    print_function,
    unicode_literals,
    )

"""Fake, synchronous Cobbler XMLRPC service for testing."""

__metaclass__ = type
__all__ = [
    'FakeCobbler',
    'FakeTwistedProxy',
    'fake_token',
    ]

from random import Random
from twisted.internet.defer import inlineCallbacks, returnValue
from xmlrpclib import Fault


randomizer = Random()

sequence_no = randomizer.randint(0, 99999)


def get_unique_int():
    global sequence_no
    result = sequence_no
    sequence_no += 1
    return result


def fake_token(user=None):
    elements = ['token', '%s' % get_unique_int()]
    if user is not None:
        elements.append(user)
    return '-'.join(elements)


class FakeTwistedProxy:
    """Fake Twisted XMLRPC proxy that forwards calls to a `FakeCobbler`."""

    def __init__(self, fake_cobbler):
        self.fake_cobbler = fake_cobbler

    @inlineCallbacks
    def callRemote(self, method, *args):
        callee = getattr(self.fake_cobbler, method, None)
        assert callee is not None, "Unknown Cobbler method: %s" % method
        result = yield callee(*args)
        returnValue(result)


class FakeCobbler:
    """Fake implementation of the Cobbler XMLRPC API.

    :param passwords: A dict mapping user names to their passwords.

    :ivar tokens: A dict mapping valid auth tokens to their users.
    :ivar distros: A dict mapping distro names to dicts describing distros.
    """

    def __init__(self, passwords=None):
        if passwords is None:
            self.passwords = {}
        else:
            self.passwords = passwords

        self.tokens = {}
        self.distros = {}

    def fake_check_token(self, token):
        """Not part of the faked API: check token validity."""
        if token not in self.tokens:
            raise Exception("invalid token: %s" % token)

    def login(self, user, password):
        if user != self.passwords.get(password, object()):
            raise Fault("login failed (%s)" % user)
        token = fake_token(user)
        self.tokens[token] = user
        return token

    def new_distro(self, token):
        self.fake_check_token(token)
        pass

    def remove_distro(self, name, token, recurse=True):
        self.fake_check_token(token)
        pass

    def get_distro_handle(self, name, token):
        self.fake_check_token(token)
        pass

    def find_distros(self, criteria):
        pass

    def get_distros(self):
        pass

    def modify_distro(self, handle, key, value, token):
        self.fake_check_token(token)
        pass

    def save_distro(self, handle, token):
        self.fake_check_token(token)
        pass

    def new_image(self, name, token):
        self.fake_check_token(token)
        pass

    def remove_image(self, name, token, recurse=True):
        self.fake_check_token(token)
        pass

    def get_image_handle(self, name, token):
        self.fake_check_token(token)
        pass

    def find_images(self, criteria):
        pass

    def get_images(self):
        pass

    def modify_image(self, handle, key, value, token):
        self.fake_check_token(token)
        pass

    def save_image(self, handle, token):
        self.fake_check_token(token)
        pass

    def new_profile(self, name, token):
        self.fake_check_token(token)
        pass

    def remove_profile(self, name, token, recurse=True):
        self.fake_check_token(token)
        pass

    def get_profile_handle(self, name, token):
        self.fake_check_token(token)
        pass

    def find_profiles(self, criteria):
        pass

    def get_profiles(self):
        pass

    def modify_profile(self, handle, key, value, token):
        self.fake_check_token(token)
        pass

    def save_profile(self, handle, token):
        self.fake_check_token(token)
        pass

    def new_system(self, name, token):
        self.fake_check_token(token)
        pass

    def remove_system(self, name, token, recurse=True):
        self.fake_check_token(token)
        pass

    def get_system_handle(self, name, token):
        self.fake_check_token(token)
        pass

    def find_systems(self, criteria):
        pass

    def get_systems(self):
        pass

    def modify_system(self, handle, key, value, token):
        self.fake_check_token(token)
        pass

    def save_system(self, handle, token):
        self.fake_check_token(token)
        pass

    def get_system_as_rendered(self, name):
        pass

    def get_changed_systems(self, seconds_since_epoch):
        pass

    def power_system(self, operation, token):
        self.fake_check_token(token)
        pass

    def read_or_write_kickstart_template(self, path, read, contents, token):
        self.fake_check_token(token)
        pass

    def read_or_write_kickstart_snippet(self, path, read, contents, token):
        self.fake_check_token(token)
        pass

    def sync(self, token):
        self.fake_check_token(token)
        pass
