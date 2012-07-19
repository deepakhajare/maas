# Copyright 2005-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the psmaas TAP."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "ConfigFixture",
    ]

from fixtures import Fixture
from maastesting.factory import factory
import provisioningserver.config


class ConfigFixture(Fixture):

    def __init__(self, config=None):
        super(ConfigFixture, self).__init__()
        # The smallest config snippet that will validate.
        self.config = {
            "password": factory.getRandomString(),
            }
        if config is not None:
            self.config.update(config)

    def setUp(self):
        super(ConfigFixture, self).setUp()
        # Restore the cached config to its current state on exit.
        self.addCleanup(
            setattr, provisioningserver.config, "config",
            provisioningserver.config.config)
        # Set the cached config to something predefined.
        provisioningserver.config.config = (
            provisioningserver.config.Config.to_python(self.config))
