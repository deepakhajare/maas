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

from os import path

from fixtures import (
    EnvironmentVariableFixture,
    Fixture,
    TempDir,
    )
from maastesting.factory import factory
from provisioningserver import config
from testtools.monkey import patch
import yaml


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
        # Clear all cached configuration. Use patch to restore state.
        self.addCleanup(patch(config, "config", None))
        self.addCleanup(patch(config, "config_filename", None))
        # Create a real configuration file, and populate it.
        config_dir = self.useFixture(TempDir()).path
        config_filename = path.join(config_dir, "config.yaml")
        with open(config_filename, "wb") as stream:
            yaml.safe_dump(self.config, stream=stream)
        # Export this filename to the environment, so that subprocesses will
        # pick up this configuration.
        config_exporter = EnvironmentVariableFixture(
            "MAAS_PROVISION_SETTINGS", config_filename)
        self.useFixture(config_exporter)
        # Set this as the configuration file in the current process.
        config.set_config_filename(config_filename)
