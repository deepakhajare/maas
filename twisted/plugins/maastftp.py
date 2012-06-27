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

from os import getcwd

from tftp.backend import FilesystemSynchronousBackend
from tftp.protocol import TFTP
from twisted.application import internet
from twisted.application.service import IServiceMaker
from twisted.plugin import IPlugin
from twisted.python import usage
from zope.interface import implementer

# Construct objects which *provide* the relevant interfaces. The name of
# these variables is irrelevant, as long as there are *some* names bound
# to providers of IPlugin and IServiceMaker.

@implementer(IServiceMaker, IPlugin)
class TFTPServiceMaker:
    """Create a service for the Twisted plugin."""

    options = usage.Options

    def __init__(self, name, description):
        self.tapname = name
        self.description = description

    def makeService(self, options):
        base = getcwd()
        factory = TFTP(FilesystemSynchronousBackend(base))
        return internet.UDPServer(1069, factory)


service = TFTPServiceMaker("maas-tftp", "...")  # TODO: finish
