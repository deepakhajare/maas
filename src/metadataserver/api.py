# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Metadata API."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'metadata_index',
    'meta_data',
    'version_index',
    'user_data',
    ]

from django.http import HttpResponse
from piston.handler import BaseHandler


class UnknownMetadataVersion(RuntimeError):
    """Not a known metadata version."""


def make_text_response(contents):
    """Create a response containing `contents` as plain text."""
    return HttpResponse(contents, mimetype='text/plain')


def make_list_response(items):
    """Create an `HttpResponse` listing `items`, one per line."""
    return make_text_response('\n'.join(items))


def check_version(version):
    """Check that `version` is a supported metadata version."""
    if version != 'latest':
        raise UnknownMetadataVersion("Unknown metadata version: %s" % version)


class MetadataViewHandler(BaseHandler):
    allowed_methods = ('GET',)

    def read(self, request):
        return make_list_response(self.fields)


class IndexHandler(MetadataViewHandler):
    """Top-level metadata listing."""

    fields = ('latest',)


class VersionIndexHandler(MetadataViewHandler):
    """Listing for a given metadata version."""

    fields = ('meta-data', 'user-data')

    def read(self, request, version):
        check_version(version)
        return super(VersionIndexHandler, self).read(request)


class MetaDataHandler(VersionIndexHandler):
    """Meta-data listing for a given version."""

    fields = ('local-hostname',)


class UserDataHandler(MetadataViewHandler):
    """User-data blob for a given version."""
    def read(self, request, version):
        check_version(version)
        data = b"User data here."
        return HttpResponse(data, mimetype='application/octet-stream')
