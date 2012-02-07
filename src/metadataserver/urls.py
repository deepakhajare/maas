# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Metadata API URLs."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'urlpatterns',
    ]

from django.conf.urls.defaults import (
    patterns,
    url,
    )


urlpatterns = patterns(
    'metadataserver.api',
    url(r'(?P<version>[^/]+)/meta-data/', 'meta_data', name='meta_data'),
    url(r'(?P<version>[^/]+)/user-data/', 'user_data', name='user_data'),
    url(r'(?P<version>[^/]+)/', 'version', name='version'),
    url(r'', 'versions_index', name='metadata'),
    )
