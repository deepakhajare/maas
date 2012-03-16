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
    ]

from fixtures import Fixture
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
