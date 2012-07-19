# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""MAAS Provisioning Configuration."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "Config",
    "get",
    ]

from getpass import getuser
from os import environ
from threading import RLock

from formencode import Schema
from formencode.validators import (
    Int,
    RequireIfPresent,
    String,
    URL,
    )
from provisioningserver.pxe.tftppath import locate_tftp_path
import yaml


class ConfigOops(Schema):
    """Configuration validator for OOPS options."""

    if_key_missing = None

    directory = String(if_missing=b"")
    reporter = String(if_missing=b"")

    chained_validators = (
        RequireIfPresent("reporter", present="directory"),
        )


class ConfigBroker(Schema):
    """Configuration validator for message broker options."""

    if_key_missing = None

    host = String(if_missing=b"localhost")
    port = Int(min=1, max=65535, if_missing=5673)
    username = String(if_missing=getuser())
    password = String(if_missing=b"test")
    vhost = String(if_missing="/")


class ConfigCobbler(Schema):
    """Configuration validator for connecting to Cobbler."""

    if_key_missing = None

    url = URL(
        add_http=True, require_tld=False,
        if_missing=b"http://localhost/cobbler_api",
        )
    username = String(if_missing=getuser())
    password = String(if_missing=b"test")


class ConfigTFTP(Schema):
    """Configuration validator for the TFTP service."""

    if_key_missing = None

    root = String(if_missing=locate_tftp_path())
    port = Int(min=1, max=65535, if_missing=5244)
    generator = URL(
        add_http=True, require_tld=False,
        if_missing=b"http://localhost:5243/api/1.0/pxeconfig",
        )


class Config(Schema):
    """Configuration validator."""

    if_key_missing = None

    interface = String(if_empty=b"", if_missing=b"127.0.0.1")
    port = Int(min=1, max=65535, if_missing=5241)
    username = String(not_empty=True, if_missing=getuser())
    password = String(not_empty=True)
    logfile = String(if_empty=b"pserv.log", if_missing=b"pserv.log")
    oops = ConfigOops
    broker = ConfigBroker
    cobbler = ConfigCobbler
    tftp = ConfigTFTP

    @classmethod
    def parse(cls, stream):
        """Load a YAML configuration from `stream` and validate."""
        return cls.to_python(yaml.safe_load(stream))

    @classmethod
    def load(cls, filename):
        """Load a YAML configuration from `filename` and validate."""
        with open(filename, "rb") as stream:
            return cls.parse(stream)

    @classmethod
    def field(target, *steps):
        """Obtain a field by following `steps`."""
        for step in steps:
            target = target.fields[step]
        return target


config = None
config_lock = RLock()


def get():
    """Load and return the MAAS provisioning configuration.

    The file used is obtained from the `MAAS_PROVISION_SETTINGS` environment
    variable, or `/etc/maas/pserv.yaml` if that is not defined.

    Once the configuration has loaded successfully, it is cached. Subsequent
    calls to this function will return the cached configuration.

    This function is thread-safe.
    """
    global config
    with config_lock:
        if config is None:
            config_filename = (
                environ["MAAS_PROVISION_SETTINGS"]
                if "MAAS_PROVISION_SETTINGS" in environ
                else "/etc/maas/pserv.yaml")
            config = Config.load(config_filename)
        return config
