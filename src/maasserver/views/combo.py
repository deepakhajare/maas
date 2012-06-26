# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Combo view."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'get_combo_view',
    ]

from functools import partial
import os

from convoy.combo import (
    combine_files,
    parse_qs,
    )
from django.conf import settings as django_settings
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    )

# Static root computed from this very file.
LOCAL_STATIC_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'static')


def get_location(abs_location=None, rel_location=None):
    """Return the absolute location of a static ressource.

    If the given absolute location (abs_location) is not None: return it.
    If the STATIC_ROOT setting is not null, use it as the root for the given
    relative location.
    Otherwise, use LOCAL_STATIC_ROOT as the root for the given relative
    location.

    :param abs_location: An optional absolute location.
    :type abs_location: basestring
    :param rel_location: A list of path elements composing the relative
        location where the static ressources can be found.
    :param rel_location: A list of path elements or None.
    :type rel_location: list
    :return: The absolute path.
    :rtype: basestring
    """
    if rel_location is None:
        rel_location = ['']
    if abs_location is not None:
        return abs_location
    elif django_settings.STATIC_ROOT:
        return os.path.join(
            django_settings.STATIC_ROOT, *rel_location)
    else:
        return os.path.join(LOCAL_STATIC_ROOT, *rel_location)


def get_combo_view(abs_location=None, rel_location=None):
    """Return a Django view to serve static ressources using a combo loader.

    :param abs_location: An optional absolute location.
    :type abs_location: basestring or None
    :param rel_location: A list of path elements composing the relative
        location where the static ressources can be found.
    :type rel_location: list or None
    :return: A Django view method.
    :rtype: callable
    """
    location = get_location(
        abs_location=abs_location, rel_location=rel_location)
    return partial(combo_view, location=location)


def combo_view(request, location, encoding='utf8'):
    """Handle a request for combining a set of files.

    The files are searched in the absolute location `abs_location` (if
    defined) or in the relative location `rel_location`.
    """
    fnames = parse_qs(request.META.get("QUERY_STRING", ""))

    if fnames:
        if fnames[0].endswith('.js'):
            content_type = 'text/javascript; charset=UTF-8'
        elif fnames[0].endswith('.css'):
            content_type = 'text/css'
        else:
            return HttpResponseBadRequest("Invalid file type requested.")
        content = "".join(
            [content.decode(encoding) for content in combine_files(
               fnames, location, resource_prefix='/', rewrite_urls=True)])

        return HttpResponse(
            content_type=content_type, status=200, content=content)

    return HttpResponseNotFound()
