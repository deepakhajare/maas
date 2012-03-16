# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for testing with RabbitMQ."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "RabbitServerSettings",
    "RabbitServerResource",
    ]

from fixtures import Fixture
from rabbitfixture.server import RabbitServer
from testresources import TestResource
from testtools.monkey import MonkeyPatcher


class RabbitServerSettings(Fixture):
    """
    This patches the active Django settings to point the application at the
    ephemeral RabbitMQ server specified by the given configuration.
    """

    def __init__(self, config):
        super(RabbitServerSettings, self).__init__()
        self.config = config

    def setUp(self):
        super(RabbitServerSettings, self).setUp()
        from django.conf import settings
        patcher = MonkeyPatcher()
        patcher.add_patch(
            settings, "RABBITMQ_HOST", "%s:%d" % (
                self.config.hostname, self.config.port))
        patcher.add_patch(settings, "RABBITMQ_USERID", "guest")
        patcher.add_patch(settings, "RABBITMQ_PASSWORD", "guest")
        patcher.add_patch(settings, "RABBITMQ_VIRTUAL_HOST", "/")
        patcher.add_patch(settings, "RABBITMQ_PUBLISH", True)
        self.addCleanup(patcher.restore)
        patcher.patch()


class RabbitServerResource(TestResource):
    """A `TestResource` that wraps a `RabbitServer`.

    :ivar server: A `RabbitServer`.
    """

    def __init__(self, config=None):
        """See `TestResource.__init__`.

        :param config: An optional instance of
            `rabbitfixture.server.RabbitServerResources`.
        """
        super(RabbitServerResource, self).__init__()
        self.server = RabbitServer(config)

    def clean(self, resource):
        """See `TestResource.clean`."""
        resource.cleanUp()

    def make(self, dependency_resources):
        """See `TestResource.make`."""
        self.server.setUp()
        return self.server

    def isDirty(self):
        """See `TestResource.isDirty`.

        Always returns ``True`` because it's difficult to figure out if an
        `RabbitMQ` server has been used, and it will be very quick to reset
        once we have the management plugin.

        Also, somewhat confusingly, `testresources` uses `self._dirty` to
        figure out whether or not to recreate the resource in `self.reset`.
        That's only set by calling `self.dirtied`, which is fiddly from a
        test. For now we assume that it doesn't matter if it's dirty or not;
        tests need to ensure they're using uniquely named queues and/or
        exchanges, or explicity purge things during set-up.
        """
        return True

    def reset(self, old_resource, result=None):
        """See `TestResource.reset`."""
        # XXX: GavinPanella 2011-01-20 bug=???: When it becomes possible to
        # install rabbitmq-management on Precise this could be changed to
        # properly reset the running server.
        return super(RabbitServerResource, self).reset(old_resource, result)
