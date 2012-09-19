# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Encoding of MIME multipart data."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'encode_multipart_data',
    'encode_multipart_message',
    'prepare_multipart_message',
    ]

from collections import Mapping
from email.generator import Generator
from email.message import Message
from io import (
    BytesIO,
    IOBase,
    )
from itertools import chain
import mimetypes


def get_content_type(*names):
    """Return the MIME content type for the file with the given name."""
    for name in names:
        if name is not None:
            mimetype, encoding = mimetypes.guess_type(name)
            if mimetype is not None:
                return mimetype
    else:
        return "application/octet-stream"


def attach_bytes(payload, name, content):
    payload.add_header("Content-Disposition", "form-data", name=name)
    payload.set_payload(content)
    payload.set_type("application/octet-stream")


def attach_string(payload, name, content):
    payload.add_header("Content-Disposition", "form-data", name=name)
    payload.set_payload(content.encode("utf-8"))
    payload.set_type("text/plain")
    payload.set_charset("utf-8")


def attach_file(payload, name, content):
    payload.add_header(
        "Content-Disposition", "form-data", name=name, filename=name)
    payload.set_payload(content.read())
    names = name, getattr(content, "name", None)
    payload.set_type(get_content_type(*names))


def attach(payload, name, content):
    if isinstance(content, bytes):
        attach_bytes(payload, name, content)
    elif isinstance(content, unicode):
        attach_string(payload, name, content)
    elif isinstance(content, IOBase):
        attach_file(payload, name, content)
    elif callable(content):
        with content() as content:
            attach(payload, name, content)
    else:
        raise AssertionError(
            "%r is unrecognised: %r" % (name, content))


def prepare_multipart_message(data):
    payload = Message()
    payload.set_type("multipart/form-data")

    for name, content in data:
        data_payload = Message()
        attach(data_payload, name, content)
        payload.attach(data_payload)

    return payload


def encode_multipart_message(payload):
    buf = BytesIO()
    generator = Generator(buf, False)
    generator._write_headers = lambda self: None  # Ignore.
    generator.flatten(payload)
    payload.add_header("Content-Length", "%d" % buf.tell())
    return payload.items(), buf.getvalue()


def encode_multipart_data(data, files):
    """Create a MIME multipart payload from L{data} and L{files}.

    **Note** that this function is deprecated. Use `prepare_multipart_message`
    and `encode_multipart_message` instead.

    @param data: A mapping of names (ASCII strings) to data (byte string).
    @param files: A mapping of names (ASCII strings) to file objects ready to
        be read.
    @return: A 2-tuple of C{(body, headers)}, where C{body} is a a byte string
        and C{headers} is a dict of headers to add to the enclosing request in
        which this payload will travel.
    """
    if isinstance(data, Mapping):
        data = data.items()
    if isinstance(files, Mapping):
        files = files.items()
    payload = prepare_multipart_message(chain(data, files))
    headers, body = encode_multipart_message(payload)
    return body, dict(headers)
