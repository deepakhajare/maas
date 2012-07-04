# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Twisted Application Plugin for the MAAS TFTP server."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from io import BytesIO
from os import getcwd
import re

from tftp.backend import (
    FilesystemSynchronousBackend,
    IReader,
    )
from tftp.protocol import TFTP
from twisted.application import internet
from twisted.application.service import IServiceMaker
from twisted.plugin import IPlugin
from twisted.python import usage
from zope.interface import implementer


@implementer(IReader)
class BytesReader:

    def __init__(self, data):
        super(BytesReader, self).__init__()
        self.buffer = BytesIO(data)

    def read(self, size):
        return self.buffer.read(size)

    def finish(self):
        self.buffer.close()


class TFTPBackend(FilesystemSynchronousBackend):

    re_config_file = re.compile(
        r'^maas/([^/]+)/([^/]+)/pxelinux[.]cfg/([^/]+)$')

    def get_reader(self, file_name):
        config_file_match = self.re_config_file.match(file_name)
        if config_file_match is None:
            return super(TFTPBackend, self).get_reader(file_name)
        else:
            arch, subarch, name = config_file_match.groups()
            # TODO: return an actual PXE config file.
            config_file = repr((arch, subarch, name)) + b"\n"
            return BytesReader(config_file)


@implementer(IServiceMaker, IPlugin)
class TFTPServiceMaker:
    """Create a service for the Twisted plugin."""

    options = usage.Options

    def __init__(self, name, description):
        self.tapname = name
        self.description = description

    def makeService(self, options):
        base = getcwd()
        backend = TFTPBackend(base, can_write=False)
        factory = TFTP(backend)
        return internet.UDPServer(1069, factory)
