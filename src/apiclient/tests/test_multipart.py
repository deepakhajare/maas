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
import re
from textwrap import dedent

from apiclient.multipart import (
    encode_multipart_data,
    get_content_type,
    )
from maastesting.factory import factory
from maastesting.testcase import TestCase
from testtools.matchers import EndsWith


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
        params = {"op": "add", "filename": "foo"}
        fileObj = BytesIO(b"random data")
        files = {"file": fileObj}
        body, headers = encode_multipart_data(params, files)

        expected_body_regex = b"""\
            --(?P<boundary>.+)
            Content-Disposition: form-data; name="filename"
            MIME-Version: 1.0
            Content-Type: text/plain; charset="utf-8"
            Content-Transfer-Encoding: quoted-printable

            foo
            --(?P=boundary)
            Content-Disposition: form-data; name="op"
            MIME-Version: 1.0
            Content-Type: text/plain; charset="utf-8"
            Content-Transfer-Encoding: quoted-printable

            add
            --(?P=boundary)
            Content-Disposition: form-data; name="file"; filename="file"
            MIME-Version: 1.0
            Content-Type: application/octet-stream

            random data
            --(?P=boundary)--"""
        expected_body_regex = dedent(expected_body_regex)
        #expected_body_regex = b"\r\n".join(expected_body_regex.splitlines())
        expected_body = re.compile(expected_body_regex, re.MULTILINE)
        self.assertRegexpMatches(body, expected_body)

        boundary = expected_body.match(body).group("boundary")
        expected_headers = {
            "Content-Length": str(len(body)),
            "Content-Type": 'multipart/form-data; boundary="%s"' % boundary,
            "MIME-Version": "1.0",
            }
        self.assertEqual(expected_headers, headers)
