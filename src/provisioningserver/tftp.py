# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Twisted Application Plugin for the MAAS TFTP server."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "TFTPBackend",
    ]

from io import BytesIO
import re

from tftp.backend import (
    FilesystemSynchronousBackend,
    IReader,
    )
from zope.interface import implementer


@implementer(IReader)
class BytesReader:

    def __init__(self, data):
        super(BytesReader, self).__init__()
        self.buffer = BytesIO(data)
        self.size = len(data)

    def read(self, size):
        return self.buffer.read(size)

    def finish(self):
        self.buffer.close()


class TFTPBackend(FilesystemSynchronousBackend):

    re_config_file = re.compile(
        r'^maas/(?P<arch>[^/]+)/(?P<subarch>[^/]+)/'
        r'pxelinux[.]cfg/(?P<name>[^/]+)$')

    def __init__(self, base_path, generator_url):
        super(TFTPBackend, self).__init__(
            base_path, can_read=True, can_write=False)
        self.generator_url = generator_url

    def get_reader(self, file_name):
        config_file_match = self.re_config_file.match(file_name)
        if config_file_match is None:
            return super(TFTPBackend, self).get_reader(file_name)
        else:
            arch, subarch, name = config_file_match.groups()
            # TODO: return an actual PXE config file.
            config_file = repr((arch, subarch, name)) + b"\n"
            return BytesReader(config_file)
