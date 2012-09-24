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
from itertools import repeat
import json
import re
from urllib import urlencode
from urlparse import (
    parse_qsl,
    urlparse,
    )

from provisioningserver.enum import ARP_HTYPE
from provisioningserver.kernel_opts import KernelParameters
from provisioningserver.pxe.config import render_pxe_config
from provisioningserver.utils import deferred
from tftp.backend import (
    FilesystemSynchronousBackend,
    IReader,
    )
from twisted.web.client import getPage
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
    """A partially dynamic read-only TFTP server.

    Static files such as kernels and initrds, as well as any non-MAAS files
    that the system may already be set up to serve, are served up normally.
    But PXE configurations are generated on the fly.

    When a PXE configuration file is requested, the server asynchronously
    requests the appropriate parameters from the API (at a configurable
    "generator URL") and generates a config file based on those.

    The regular expressions `re_config_file` and `re_mac_address` specify
    which files the server generates on the fly.  Any other requests are
    passed on to the filesystem.

    Passing requests on to the API must be done very selectively, because
    failures cause the boot process to halt. This is why the expression for
    matching the MAC address is so narrowly defined: PXELINUX attempts to
    fetch files at many similar paths which must not be passed on.
    """

    get_page = staticmethod(getPage)
    render_pxe_config = staticmethod(render_pxe_config)

    # PXELINUX represents a MAC address in IEEE 802 hyphen-separated
    # format.  See http://www.syslinux.org/wiki/index.php/PXELINUX.
    re_mac_address_octet = r'[0-9a-f]{2}'
    re_mac_address = re.compile(
        "-".join(repeat(re_mac_address_octet, 6)))

    # We assume that the ARP HTYPE (hardware type) that PXELINUX sends is
    # always Ethernet.
    re_config_file = re.compile(
        r'''
        # Optional leading slash(es).
        ^/*
        pxelinux[.]cfg    # PXELINUX expects this.
        /
        {htype:02x}    # ARP HTYPE.
        -
        (?P<mac>{re_mac_address.pattern})    # Capture MAC.
        $
        '''.format(
            htype=ARP_HTYPE.ETHERNET,
            re_mac_address=re_mac_address),
        re.VERBOSE)

    def __init__(self, base_path, generator_url):
        """
        :param base_path: The root directory for this TFTP server.
        :param generator_url: The URL which can be queried for the PXE
            config. See `get_generator_url` for the types of queries it is
            expected to accept.
        """
        super(TFTPBackend, self).__init__(
            base_path, can_read=True, can_write=False)
        self.generator_url = urlparse(generator_url)

    def get_generator_url(self, params):
        """Calculate the URL, including query, from which we can fetch
        additional configuration parameters.

        :param params: A dict, or iterable suitable for updating a dict, of
            additional query parameters.
        """
        query = {}
        # Merge parameters from the generator URL.
        query.update(parse_qsl(self.generator_url.query))
        # Merge parameters obtained from the request.
        query.update(params)
        # Merge updated query into the generator URL.
        url = self.generator_url._replace(query=urlencode(query))
        # TODO: do something more intelligent with unicode URLs here; see
        # apiclient.utils.ascii_url() for inspiration.
        return url.geturl().encode("ascii")

    @deferred
    def get_kernel_params(self, params):
        """Return kernel parameters obtained from the API.

        :param params: Parameters so far obtained, typically from the file
            path requested.
        :return: A `KernelParameters` instance.
        """
        url = self.get_generator_url(params)

        def reassemble(data):
            return KernelParameters(**data)

        d = self.get_page(url)
        d.addCallback(json.loads)
        d.addCallback(reassemble)
        return d

    @deferred
    def get_config_reader(self, params):
        """Return an `IReader` for a PXE config.

        :param params: Parameters so far obtained, typically from the file
            path requested.
        """
        def generate_config(kernel_params):
            config = self.render_pxe_config(
                kernel_params=kernel_params, **params)
            return config.encode("utf-8")

        d = self.get_kernel_params(params)
        d.addCallback(generate_config)
        d.addCallback(BytesReader)
        return d

    @deferred
    def get_reader(self, file_name):
        """See `IBackend.get_reader()`.

        If `file_name` matches `re_config_file` then the response is obtained
        from a server. Otherwise the filesystem is used to service the
        response.
        """
        config_file_match = self.re_config_file.match(file_name)
        if config_file_match is None:
            return super(TFTPBackend, self).get_reader(file_name)
        else:
            params = config_file_match.groupdict()
            return self.get_config_reader(params)
