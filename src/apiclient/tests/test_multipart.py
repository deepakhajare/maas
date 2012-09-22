# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test multipart MIME helpers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from io import BytesIO
from os import urandom

from apiclient.multipart import (
    encode_multipart_data,
    get_content_type,
    )
from django.core.files.uploadhandler import MemoryFileUploadHandler
from django.http.multipartparser import MultiPartParser
from maastesting.factory import factory
from maastesting.testcase import TestCase
from testtools.matchers import (
    EndsWith,
    StartsWith,
    )


class SpewingUploadHandler(MemoryFileUploadHandler):

    def handle_raw_input(
        self, input_data, META, content_length, boundary, encoding=None):
        print("handle_raw_input", locals())
        return super(SpewingUploadHandler, self).handle_raw_input(
            input_data, META, content_length, boundary, encoding)

    def new_file(self, *args, **kwargs):
        print("new_file", locals())
        return super(SpewingUploadHandler, self).new_file(*args, **kwargs)

    def receive_data_chunk(self, raw_data, start):
        print("receive_data_chunk", locals())
        return super(SpewingUploadHandler, self).receive_data_chunk(
            raw_data, start)

    def file_complete(self, file_size):
        print("file_complete", locals())
        return super(SpewingUploadHandler, self).file_complete(file_size)


# TODO: only pass base64 encoded field data; Django doesn't appear to
# understand quoted-printable.


class TestMultiPart(TestCase):

    def test_get_content_type_guesses_type(self):
        guess = get_content_type('text.txt')
        self.assertEqual('text/plain', guess)
        self.assertIsInstance(guess, bytes)

    def test_encode_multipart_data_produces_bytes(self):
        data = {
            factory.getRandomString():
                factory.getRandomString().encode('ascii'),
        }
        files = {
            factory.getRandomString():
                BytesIO(factory.getRandomString().encode('ascii')),
            }
        body, headers = encode_multipart_data(data, files)
        self.assertIsInstance(body, bytes)

    def test_encode_multipart_data_closes_with_closing_boundary_line(self):
        data = {b'foo': factory.getRandomString().encode('ascii')}
        files = {b'bar': BytesIO(factory.getRandomString().encode('ascii'))}
        body, headers = encode_multipart_data(data, files)
        self.assertThat(body, EndsWith(b'--'))

    def test_encode_multipart_data(self):
        # The encode_multipart_data() function should take a list of
        # parameters and files and encode them into a MIME
        # multipart/form-data suitable for posting to the MAAS server.
        params = {"op": "add", "foo": "bar\u1234"}
        random_data = urandom(32)
        files = {"baz": BytesIO(random_data)}
        body, headers = encode_multipart_data(params, files)

        # Parse it with Django's MultiPartParser, a curiously ugly and RFC
        # non-compliant concoction. It also coerces all field names, field
        # data, and filenames into Unicode strings using the "replace" error
        # strategy, so be warned that your data may be silently mangled.
        handler = MemoryFileUploadHandler()
        meta = {
            "HTTP_CONTENT_TYPE": headers["Content-Type"],
            "HTTP_CONTENT_LENGTH": headers["Content-Length"],
            }
        parser = MultiPartParser(
            META=meta, input_data=BytesIO(body),
            upload_handlers=[handler])
        post, files = parser.parse()

        self.assertEqual(
            {name: [value] for name, value in params.items()},
            post)
        self.assertSetEqual({"baz"}, set(files))
        self.assertEqual(random_data, files["baz"].read())

        self.assertEqual("%s" % len(body), headers["Content-Length"])
        self.assertThat(
            headers["Content-Type"],
            StartsWith("multipart/form-data; boundary="))
