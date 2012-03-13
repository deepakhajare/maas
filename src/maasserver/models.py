# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""MaaS model objects."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "create_auth_token",
    "generate_node_system_id",
    "get_auth_tokens",
    "Config",
    "FileStorage",
    "NODE_STATUS",
    "Node",
    "MACAddress",
    "UserProfile",
    ]

import copy
import datetime
from errno import ENOENT
import getpass
from logging import getLogger
import os
import re
from socket import gethostname
import time
from uuid import uuid1

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.signals import post_save
from django.shortcuts import get_object_or_404
from maasserver.exceptions import (
    CannotDeleteUserException,
    PermissionDenied,
    )
from maasserver.fields import (
    JSONObjectField,
    MACAddressField,
    )
from metadataserver import nodeinituser
from piston.models import (
    Consumer,
    Token,
    )

# Special users internal to MaaS.
SYSTEM_USERS = [
    # For nodes' access to the metadata API:
    nodeinituser.user_name,
    ]


logger = getLogger('maasserver')


class CommonInfo(models.Model):
    """A base model which records the creation date and the last modification
    date.

    :ivar created: The creation date.
    :ivar updated: The last modification date.

    """
    created = models.DateField(editable=False)
    updated = models.DateTimeField(editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = datetime.date.today()
        self.updated = datetime.datetime.today()
        super(CommonInfo, self).save(*args, **kwargs)


def generate_node_system_id():
    return 'node-%s' % uuid1()


class NODE_STATUS:
    """The vocabulary of a `Node`'s possible statuses."""
    DEFAULT_STATUS = 0
    #: The node has been created and has a system ID assigned to it.
    DECLARED = 0
    #: Testing and other commissioning steps are taking place.
    COMMISSIONING = 1
    #: Smoke or burn-in testing has a found a problem.
    FAILED_TESTS = 2
    #: The node can't be contacted.
    MISSING = 3
    #: The node is in the general pool ready to be deployed.
    READY = 4
    #: The node is ready for named deployment.
    RESERVED = 5
    #: The node is powering a service from a charm or is ready for use with
    #: a fresh Ubuntu install.
    ALLOCATED = 6
    #: The node has been removed from service manually until an admin
    #: overrides the retirement.
    RETIRED = 7


NODE_STATUS_CHOICES = (
    (NODE_STATUS.DECLARED, "Declared"),
    (NODE_STATUS.COMMISSIONING, "Commissioning"),
    (NODE_STATUS.FAILED_TESTS, "Failed tests"),
    (NODE_STATUS.MISSING, "Missing"),
    (NODE_STATUS.READY, "Ready"),
    (NODE_STATUS.RESERVED, "Reserved"),
    (NODE_STATUS.ALLOCATED, "Allocated"),
    (NODE_STATUS.RETIRED, "Retired"),
)


NODE_STATUS_CHOICES_DICT = dict(NODE_STATUS_CHOICES)


class NODE_AFTER_COMMISSIONING_ACTION:
    """The vocabulary of a `Node`'s possible value for its field
    after_commissioning_action.

    """
# TODO: document this when it's stabilized.
    #:
    DEFAULT = 0
    #:
    QUEUE = 0
    #:
    CHECK = 1
    #:
    DEPLOY_12_04 = 2
    #:
    DEPLOY_11_10 = 3
    #:
    DEPLOY_11_04 = 4
    #:
    DEPLOY_10_10 = 5


NODE_AFTER_COMMISSIONING_ACTION_CHOICES = (
    (NODE_AFTER_COMMISSIONING_ACTION.QUEUE,
        "Queue for dynamic allocation to services"),
    (NODE_AFTER_COMMISSIONING_ACTION.CHECK,
        "Check compatibility and hold for future decision"),
    (NODE_AFTER_COMMISSIONING_ACTION.DEPLOY_12_04,
        "Deploy with Ubuntu 12.04 LTS"),
    (NODE_AFTER_COMMISSIONING_ACTION.DEPLOY_11_10,
        "Deploy with Ubuntu 11.10"),
    (NODE_AFTER_COMMISSIONING_ACTION.DEPLOY_11_04,
        "Deploy with Ubuntu 11.04"),
    (NODE_AFTER_COMMISSIONING_ACTION.DEPLOY_10_10,
        "Deploy with Ubuntu 10.10"),
)


NODE_AFTER_COMMISSIONING_ACTION_CHOICES_DICT = dict(
    NODE_AFTER_COMMISSIONING_ACTION_CHOICES)


# List of supported architectures.
class ARCHITECTURE:
    i386 = 'i386'
    amd64 = 'amd64'


# Architecture names.
ARCHITECTURE_CHOICES = (
    (ARCHITECTURE.i386, "i386"),
    (ARCHITECTURE.amd64, "amd64"),
)


class NodeManager(models.Manager):
    """A utility to manage the collection of Nodes."""

    # Twisted XMLRPC proxy for talking to the provisioning API.  Created
    # on demand.
    provisioning_proxy = None

    def _set_provisioning_proxy(self):
        """Set up the provisioning-API proxy if needed."""
        # Avoid circular imports.
        from maasserver.provisioning import get_provisioning_api_proxy
        if self.provisioning_proxy is None:
            self.provisioning_proxy = get_provisioning_api_proxy()

    def filter_by_ids(self, query, ids=None):
        """Filter `query` result set by system_id values.

        :param query: A queryset of Nodes.
        :type query: QuerySet_
        :param ids: Optional set of ids to filter by.  If given, nodes whose
            system_ids are not in `ids` will be ignored.
        :type param_ids: Sequence
        :return: A filtered version of `query`.
        """
        if ids is None:
            return query
        else:
            return query.filter(system_id__in=ids)

    def get_visible_nodes(self, user, ids=None):
        """Fetch Nodes visible by a User_.

        :param user: The user that should be used in the permission check.
        :type user: User_
        :param ids: If given, limit result to nodes with these system_ids.
        :type ids: Sequence.

        .. _User: https://
           docs.djangoproject.com/en/dev/topics/auth/
           #django.contrib.auth.models.User

        """
        if user.is_superuser:
            visible_nodes = self.all()
        else:
            visible_nodes = self.filter(
                models.Q(owner__isnull=True) | models.Q(owner=user))
        return self.filter_by_ids(visible_nodes, ids)

    def get_editable_nodes(self, user, ids=None):
        """Fetch Nodes a User_ has ownership privileges on.

        An admin has ownership privileges on all nodes.

        :param user: The user that should be used in the permission check.
        :type user: User_
        :param ids: If given, limit result to nodes with these system_ids.
        :type ids: Sequence.
        """
        if user.is_superuser:
            visible_nodes = self.all()
        else:
            visible_nodes = self.filter(owner=user)
        return self.filter_by_ids(visible_nodes, ids)

    def get_visible_node_or_404(self, system_id, user):
        """Fetch a `Node` by system_id.  Raise exceptions if no `Node` with
        this system_id exist or if the provided user cannot see this `Node`.

        :param name: The system_id.
        :type name: str
        :param user: The user that should be used in the permission check.
        :type user: django.contrib.auth.models.User
        :raises: django.http.Http404_,
            maasserver.exceptions.PermissionDenied_.

        .. _django.http.Http404: https://
           docs.djangoproject.com/en/dev/topics/http/views/
           #the-http404-exception
        """
        node = get_object_or_404(Node, system_id=system_id)
        if user.has_perm('access', node):
            return node
        else:
            raise PermissionDenied

    def get_available_node_for_acquisition(self, for_user):
        """Find a `Node` to be acquired by the given user.

        :param for_user: The user who is to acquire the node.
        :return: A `Node`, or None if none are available.
        """
        available_nodes = (
            self.get_visible_nodes(for_user)
                .filter(status=NODE_STATUS.READY))
        available_nodes = list(available_nodes[:1])
        if len(available_nodes) == 0:
            return None
        else:
            return available_nodes[0]

    def stop_nodes(self, ids, by_user):
        """Request on given user's behalf that the given nodes be shut down.

        Shutdown is only requested for nodes that the user has ownership
        privileges for; any other nodes in the request are ignored.

        :param ids: The `system_id` values for nodes to be shut down.
        :type ids: Sequence
        :param by_user: Requesting user.
        :type by_user: User_
        :return: Those Nodes for which shutdown was actually requested.
        :rtype: list
        """
        self._set_provisioning_proxy()
        nodes = self.get_editable_nodes(by_user, ids=ids)
        self.provisioning_proxy.stop_nodes([node.system_id for node in nodes])
        return nodes

    def start_nodes(self, ids, by_user, user_data=None):
        """Request on given user's behalf that the given nodes be started up.

        Power-on is only requested for nodes that the user has ownership
        privileges for; any other nodes in the request are ignored.

        :param ids: The `system_id` values for nodes to be started.
        :type ids: Sequence
        :param by_user: Requesting user.
        :type by_user: User_
        :param user_data: Optional blob of user-data to be made available to
            the nodes through the metadata service.  If not given, any
            previous user data is used.
        :type user_data: str
        :return: Those Nodes for which power-on was actually requested.
        :rtype: list
        """
        from metadataserver.models import NodeUserData
        self._set_provisioning_proxy()
        nodes = self.get_editable_nodes(by_user, ids=ids)
        if user_data is not None:
            for node in nodes:
                NodeUserData.objects.set_user_data(node, user_data)
        self.provisioning_proxy.start_nodes(
            [node.system_id for node in nodes])
        return nodes


class Node(CommonInfo):
    """A `Node` represents a physical machine used by the MaaS Server.

    :ivar system_id: The unique identifier for this `Node`.
        (e.g. 'node-41eba45e-4cfa-11e1-a052-00225f89f211').
    :ivar hostname: This `Node`'s hostname.
    :ivar status: This `Node`'s status. See the vocabulary
        :class:`NODE_STATUS`.
    :ivar owner: This `Node`'s owner if it's in use, None otherwise.
    :ivar after_commissioning_action: The action to perform after
        commissioning. See vocabulary
        :class:`NODE_AFTER_COMMISSIONING_ACTION`.
    :ivar objects: The :class:`NodeManager`.

    """

    system_id = models.CharField(
        max_length=41, unique=True, default=generate_node_system_id,
        editable=False)

    hostname = models.CharField(max_length=255, default='', blank=True)

    status = models.IntegerField(
        max_length=10, choices=NODE_STATUS_CHOICES, editable=False,
        default=NODE_STATUS.DEFAULT_STATUS)

    owner = models.ForeignKey(
        User, default=None, blank=True, null=True, editable=False)

    after_commissioning_action = models.IntegerField(
        choices=NODE_AFTER_COMMISSIONING_ACTION_CHOICES,
        default=NODE_AFTER_COMMISSIONING_ACTION.DEFAULT)

    architecture = models.CharField(
        max_length=10, choices=ARCHITECTURE_CHOICES, blank=False,
        default=ARCHITECTURE.i386)

    objects = NodeManager()

    def __unicode__(self):
        if self.hostname:
            return "%s (%s)" % (self.system_id, self.hostname)
        else:
            return self.system_id

    def display_status(self):
        return NODE_STATUS_CHOICES_DICT[self.status]

    def add_mac_address(self, mac_address):
        """Add a new MAC Address to this `Node`.

        :param mac_address: The MAC Address to be added.
        :type mac_address: str
        :raises: django.core.exceptions.ValidationError_

        .. _django.core.exceptions.ValidationError: https://
           docs.djangoproject.com/en/dev/ref/exceptions/
           #django.core.exceptions.ValidationError
        """

        mac = MACAddress(mac_address=mac_address, node=self)
        mac.full_clean()
        mac.save()
        return mac

    def remove_mac_address(self, mac_address):
        """Remove a MAC Address from this `Node`.

        :param mac_address: The MAC Address to be removed.
        :type mac_address: str

        """
        mac = MACAddress.objects.get(mac_address=mac_address, node=self)
        if mac:
            mac.delete()

    def acquire(self, by_user):
        """Mark commissioned node as acquired by the given user."""
        assert self.status == NODE_STATUS.READY
        assert self.owner is None
        self.status = NODE_STATUS.ALLOCATED
        self.owner = by_user

    def release(self):
        """Mark allocated or reserved node as available again."""
        assert self.status in [
            NODE_STATUS.READY,
            NODE_STATUS.ALLOCATED,
            NODE_STATUS.RESERVED,
            ]
        self.status = NODE_STATUS.READY
        self.owner = None


mac_re = re.compile(r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')


class MACAddress(CommonInfo):
    """A `MACAddress` represents a `MAC Address
    <http://en.wikipedia.org/wiki/MAC_address>`_ attached to a :class:`Node`.

    :ivar mac_address: The MAC Address.
    :ivar node: The `Node` related to this `MACAddress`.

    """
    mac_address = MACAddressField()
    node = models.ForeignKey(Node, editable=False)

    class Meta:
        verbose_name_plural = "MAC addresses"

    def __unicode__(self):
        return self.mac_address


GENERIC_CONSUMER = 'MaaS consumer'


def create_auth_token(user):
    """Create new Token and Consumer (OAuth authorisation) for `user`.

    :param user: The user to create a token for.
    :type user: User
    :return: The created Token.
    :rtype: piston.models.Token

    """
    consumer = Consumer.objects.create(
        user=user, name=GENERIC_CONSUMER, status='accepted')
    consumer.generate_random_codes()
    # This is a 'generic' consumer aimed to service many clients, hence
    # we don't authenticate the consumer with key/secret key.
    consumer.secret = ''
    consumer.save()
    token = Token.objects.create(
        user=user, token_type=Token.ACCESS, consumer=consumer,
        is_approved=True)
    token.generate_random_codes()
    return token


def get_auth_tokens(user):
    """Fetches all the user's OAuth tokens.

    :return: A QuerySet of the tokens.
    :rtype: django.db.models.query.QuerySet_

    .. _django.db.models.query.QuerySet: https://docs.djangoproject.com/
       en/dev/ref/models/querysets/

    """
    return Token.objects.select_related().filter(
        user=user, token_type=Token.ACCESS, is_approved=True).order_by('id')


class UserProfileManager(models.Manager):
    """A utility to manage the collection of UserProfile (or User).

    This should be used when dealing with UserProfiles or Users because it
    returns only users with a profile attached to them (as opposed to system
    users who don't have a profile).
    """

    def all_users(self):
        """Returns all the "real" users (the users which are not system users
        and thus have a UserProfile object attached to them).

        :return: A QuerySet of the users.
        :rtype: django.db.models.query.QuerySet_

        """
        user_ids = UserProfile.objects.all().values_list('user', flat=True)
        return User.objects.filter(id__in=user_ids)


class UserProfile(models.Model):
    """A User profile to store MaaS specific methods and fields.

    :ivar user: The related User_.

    .. _UserProfile: https://docs.djangoproject.com/
       en/dev/topics/auth/
       #storing-additional-information-about-users

    """

    objects = UserProfileManager()
    user = models.OneToOneField(User)

    def delete(self):
        if self.user.node_set.exists():
            nb_nodes = self.user.node_set.count()
            msg = (
                "User %s cannot be deleted: it still has %d node(s) "
                "deployed." % (self.user.username, nb_nodes))
            raise CannotDeleteUserException(msg)
        self.user.consumers.all().delete()
        self.user.delete()
        super(UserProfile, self).delete()

    def get_authorisation_tokens(self):
        """Fetches all the user's OAuth tokens.

        :return: A QuerySet of the tokens.
        :rtype: django.db.models.query.QuerySet_

        .. _django.db.models.query.QuerySet: https://docs.djangoproject.com/
           en/dev/ref/models/querysets/

        """
        return get_auth_tokens(self.user)

    def create_authorisation_token(self):
        """Create a new Token and its related Consumer (OAuth authorisation).

        :return: A tuple containing the Consumer and the Token that were
            created.
        :rtype: tuple

        """
        token = create_auth_token(self.user)
        return token.consumer, token

    def delete_authorisation_token(self, token_key):
        """Delete the user's OAuth token wich key token_key.

        :param token_key: The key of the token to be deleted.
        :type token_key: str
        :raises: django.http.Http404_

        """
        token = get_object_or_404(
            Token, user=self.user, token_type=Token.ACCESS, key=token_key)
        token.consumer.delete()
        token.delete()

    def __unicode__(self):
        return self.user.username


# When a user is created: create the related profile and the default
# consumer/token.
def create_user(sender, instance, created, **kwargs):
    # System users do not have profiles.
    if created and instance.username not in SYSTEM_USERS:
        # Create related UserProfile.
        profile = UserProfile.objects.create(user=instance)

        # Create initial authorisation token.
        profile.create_authorisation_token()

# Connect the 'create_user' method to the post save signal of User.
post_save.connect(create_user, sender=User)


class SSHKeys(models.Model):
    """A simple SSH public keystore that can be retrieved, a user
       can have multiple keys.

    :ivar user: The user which owns the key.
    :ivar key: The ssh public key.
    """
    user = models.ForeignKey(UserProfile)
    key = models.TextField()

    def __unicode__(self):
        return self.key


class FileStorageManager(models.Manager):
    """Manager for `FileStorage` objects.

    Store files by calling `save_file`.  No two `FileStorage` objects can
    have the same filename at the same time.  Writing new data to a file
    whose name is already in use, replaces its `FileStorage` with one
    pointing to the new data.

    Underneath, however, the storage layer will keep the old version of the
    file around indefinitely.  Thus, if the overwriting transaction rolls
    back, it may leave the new file as garbage on the filesystem; but the
    original file will not be affected.  Also, any ongoing reads from the
    old file will continue without iterruption.
    """
    # The time, in seconds, that an unreferenced file is allowed to
    # persist in order to satisfy ongoing requests.
    grace_time = 12 * 60 * 60

    def get_existing_storage(self, filename):
        """Return an existing `FileStorage` of this name, or None."""
        existing_storage = self.filter(filename=filename)
        if len(existing_storage) == 0:
            return None
        elif len(existing_storage) == 1:
            return existing_storage[0]
        else:
            raise AssertionError(
                "There are %d files called '%s'."
                % (len(existing_storage), filename))

    def save_file(self, filename, file_object):
        """Save the file to the filesystem and persist to the database.

        The file will end up in MEDIA_ROOT/storage/

        If a file of that name already existed, it will be replaced by the
        new contents.
        """
        # This probably ought to read in chunks but large files are
        # not expected.  Also note that uploading a file with the same
        # name as an existing one will cause that file to be written
        # with a new generated name, and the old one remains where it
        # is.  See https://code.djangoproject.com/ticket/6157 - the
        # Django devs consider deleting things dangerous ... ha.
        # HOWEVER - this operation would need to be atomic anyway so
        # it's safest left how it is for now (reads can overlap with
        # writes from Juju).
        content = ContentFile(file_object.read())

        storage = self.get_existing_storage(filename)
        if storage is None:
            storage = FileStorage(filename=filename)
        storage.data.save(filename, content)
        return storage

    def list_stored_files(self):
        """Find the files stored in the filesystem."""
        dirs, files = FileStorage.storage.listdir(FileStorage.upload_dir)
        return [
            os.path.join(FileStorage.upload_dir, filename)
            for filename in files]

    def list_referenced_files(self):
        """Find the names of files that are referenced from `FileStorage`.

        :return: All file paths within MEDIA ROOT (relative to MEDIA_ROOT)
            that have `FileStorage` entries referencing them.
        :rtype: frozenset
        """
        return frozenset(
            file_storage.data.name
            for file_storage in self.all())

    def is_old(self, storage_filename):
        """Is the named file in the filesystem storage old enough to be dead?

        :param storage_filename: The name under which the file is stored in
            the filesystem, relative to MEDIA_ROOT.  This need not be the
            same name as its filename as stored in the `FileStorage` object.
            It includes the name of the upload directory.
        """
        file_path = os.path.join(settings.MEDIA_ROOT, storage_filename)
        mtime = os.stat(file_path).st_mtime
        expiry = mtime + self.grace_time
        return expiry <= time.time()

    def collect_garbage(self):
        """Clean up stored files that are no longer accessible."""
        try:
            stored_files = self.list_stored_files()
        except OSError as e:
            if e.errno != ENOENT:
                raise
            logger.info(
                "Upload directory does not exist yet.  "
                "Skipping garbage collection.")
            return
        referenced_files = self.list_referenced_files()
        for path in stored_files:
            if path not in referenced_files and self.is_old(path):
                FileStorage.storage.delete(path)


class FileStorage(models.Model):
    """A simple file storage keyed on file name.

    :ivar filename: A unique file name to use for the data being stored.
    :ivar data: The file's actual data.
    """

    storage = FileSystemStorage()

    upload_dir = "storage"

    # Unix filenames can be longer than this (e.g. 255 bytes), but leave
    # some extra room for the full path, as well as a versioning suffix.
    filename = models.CharField(max_length=100, unique=True, editable=False)
    data = models.FileField(
        upload_to=upload_dir, storage=storage, max_length=255)

    objects = FileStorageManager()

    def __unicode__(self):
        return self.filename


def get_default_config():
    return {
        ## settings default values.
        # Commissioning section configuration.
        'after_commissioning': NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
        'check_compatibility': False,
        # Ubuntu section configuration.
        'fallback_master_archive': False,
        'keep_mirror_list_uptodate': False,
        'fetch_new_releases': False,
        'update_from': 'archive.ubuntu.com',
        'update_from_choice': (
            [['archive.ubuntu.com', 'archive.ubuntu.com']]),
        # Network section configuration.
        'maas_name': "%s's" % getpass.getuser().capitalize(),
        'provide_dhcp': False,
        ## /settings
        # The host name or address where the nodes can access the metadata
        # service.
        'metadata-host': gethostname(),
        }


# Default values for config options.
DEFAULT_CONFIG = get_default_config()


class ConfigManager(models.Manager):
    """A utility to manage the configuration settings.

    """

    def __init__(self):
        super(ConfigManager, self).__init__()
        self._config_changed_connections = {}

    def get_config(self, name, default=None):
        """Return the config value corresponding to the given config name.
        Return None or the provided default if the config value does not
        exist.

        :param name: The name of the config item.
        :type name: basestring
        :param name: The optional default value to return if no such config
            item exists.
        :type name: object
        :return: A config value.
        :raises: Config.MultipleObjectsReturned
        """
        try:
            return self.get(name=name).value
        except Config.DoesNotExist:
            return copy.deepcopy(DEFAULT_CONFIG.get(name, default))

    def get_config_list(self, name):
        """Return the config value list corresponding to the given config
        name.

        :param name: The name of the config items.
        :type name: basestring
        :return: A list of the config values.
        :rtype: list
        """
        return [config.value for config in self.filter(name=name)]

    def set_config(self, name, value):
        """Set or overwrite a config value.

        :param name: The name of the config item to set.
        :type name: basestring
        :param value: The value of the config item to set.
        :type value: Any jsonizable object
        """
        try:
            existing = self.get(name=name)
            existing.value = value
            existing.save()
        except Config.DoesNotExist:
            self.create(name=name, value=value)

    def config_changed_connect(self, config_name, method):
        """Connect a method to Django's 'update' signal for given config name.

        :param config_name: The name of the config item to track.
        :type config_name: basestring
        :param method: The method to be called.
        :type method: callable

        The provided callabe should follow Django's convention.  E.g:

        >>> def callable(sender, instance, created, **kwargs):
        >>>     pass
        >>>
        >>> Config.objects.config_changed_connect('config_name', callable)
        """
        connections = self._config_changed_connections.setdefault(
            config_name, [])
        connections.append(method)
        self._config_changed_connections[config_name] = connections

    def _config_changed(self, sender, instance, created, **kwargs):
        if instance.name in self._config_changed_connections:
            for connection in self._config_changed_connections[instance.name]:
                connection(sender, instance, created, **kwargs)


config_manager = ConfigManager()


class Config(models.Model):
    """Configuration settings.

    :ivar name: The name of the configuration option.
    :type name: basestring
    :ivar value: The configuration value.
    :type value: Any pickleable python object.
    """

    name = models.CharField(max_length=255, unique=False)
    value = JSONObjectField(null=True)

    objects = config_manager

    def __unicode__(self):
        return "%s: %s" % (self.name, self.value)


# Connect config_manager._config_changed the post save signal of Config.
post_save.connect(config_manager._config_changed, sender=Config)


# Register the models in the admin site.
admin.site.register(Consumer)
admin.site.register(Config)
admin.site.register(FileStorage)
admin.site.register(MACAddress)
admin.site.register(Node)
admin.site.register(SSHKeys)


class MaaSAuthorizationBackend(ModelBackend):

    supports_object_permissions = True

    def has_perm(self, user, perm, obj=None):
        if not user.is_active:
            # Deactivated users, and in particular the node-init user,
            # are prohibited from accessing maasserver services.
            return False

        # Only Nodes can be checked. We also don't support perm checking
        # when obj = None.
        if not isinstance(obj, Node):
            raise NotImplementedError(
                'Invalid permission check (invalid object type).')

        # Only the generic 'access' permission is supported.
        if perm != 'access':
            raise NotImplementedError(
                'Invalid permission check (invalid permission name).')

        return obj.owner in (None, user)


# 'provisioning' is imported so that it can register its signal handlers early
# on, before it misses anything.
from maasserver import provisioning
# We mention 'provisioning' here to silence lint warnings.
provisioning
