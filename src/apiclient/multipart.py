# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Encoding of MIME multipart data."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import mimetypes
import random
import string


def _random_string(length):
    return ''.join(random.choice(string.letters) for ii in range(length + 1))


def _get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def _encode_field(field_name, data, boundary):
    return ('--' + boundary,
            'Content-Disposition: form-data; name="%s"' % field_name,
            '', str(data))


def _encode_file(name, fileObj, boundary):
    return ('--' + boundary,
            'Content-Disposition: form-data; name="%s"; filename="%s"' %
                (name, name),
            'Content-Type: %s' % _get_content_type(name),
            '', fileObj.read())


def encode_multipart_data(data, files):
    """Create a MIME multipart payload from L{data} and L{files}.

    @param data: A mapping of names (ASCII strings) to data (byte string).
    @param files: A mapping of names (ASCII strings) to file objects ready to
        be read.
    @return: A 2-tuple of C{(body, headers)}, where C{body} is a a byte string
        and C{headers} is a dict of headers to add to the enclosing request in
        which this payload will travel.
    """
    boundary = _random_string(30)

    lines = []
    for name in data:
        lines.extend(_encode_field(name, data[name], boundary))
    for name in files:
        lines.extend(_encode_file(name, files[name], boundary))
    lines.extend(('--%s--' % boundary, ''))
    body = '\r\n'.join(lines)

    headers = {'content-type': 'multipart/form-data; boundary=' + boundary,
               'content-length': str(len(body))}

    return body, headers

