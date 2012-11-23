# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

"""Tests for `maasserver`."""

__metaclass__ = type
__all__ = [
    "extract_redirect",
    "get_content_links",
    "get_data",
    "get_prefixed_form_data",
    "reload_object",
    "reload_objects",
    "sample_binary_data",
    ]

import codecs
import httplib
import os
from urlparse import urlparse

from lxml.html import fromstring
from maasserver.utils.orm import get_one


def extract_redirect(http_response):
    """Extract redirect target from an http response object.

    Only the http path part of the redirect is ignored; protocol and host
    name, if present, are not included in the result.

    If the response is not a redirect, this raises :class:`ValueError` with
    a descriptive error message.

    :param http_response: A response returned from an http request.
    :type http_response: :class:`HttpResponse`
    :return: The "path" part of the target that `http_response` redirects to.
    :raises: ValueError
    """
    if http_response.status_code != httplib.FOUND:
        raise ValueError(
            "Not a redirect: http status %d.  Content: %s"
            % (http_response.status_code, http_response.content[:80]))
    target_url = http_response['Location']
    parsed_url = urlparse(target_url)
    return parsed_url.path


def reload_object(model_object):
    """Reload `obj` from the database.

    Use this when a test needs to inspect changes to model objects made by
    the API.

    If the object has been deleted, this will return None.

    :param model_object: Model object to reload.
    :type model_object: Concrete `Model` subtype.
    :return: Freshly-loaded instance of `model_object`, or None.
    :rtype: Same as `model_object`.
    """
    model_class = model_object.__class__
    return get_one(model_class.objects.filter(id=model_object.id))


def reload_objects(model_class, model_objects):
    """Reload `model_objects` of type `model_class` from the database.

    Use this when a test needs to inspect changes to model objects made by
    the API.

    If any of the objects have been deleted, they will not be included in
    the result.

    :param model_class: `Model` class to reload from.
    :type model_class: Class.
    :param model_objects: Objects to reload from the database.
    :type model_objects: Sequence of `model_class` objects.
    :return: Reloaded objects, in no particular order.
    :rtype: Sequence of `model_class` objects.
    """
    assert all(isinstance(obj, model_class) for obj in model_objects)
    return model_class.objects.filter(
        id__in=[obj.id for obj in model_objects])


def get_data(filename):
    """Utility method to read the content of files in
    src/maasserver/tests.

    Usually used to read files in src/maasserver/tests/data."""
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'tests', filename)
    return file(path).read()


def get_prefixed_form_data(prefix, data):
    """Prefix entries in a dict of form parameters with a form prefix.

    Also, add a parameter "<prefix>_submit" to indicate that the form with
    the given prefix is being submitted.

    Use this to construct a form submission if the form uses a prefix (as it
    would if there are multiple forms on the page).

    :param prefix: Form prefix string.
    :param data: A dict of form parameters.
    :return: A new dict of prefixed form parameters.
    """
    result = {'%s-%s' % (prefix, key): value for key, value in data.items()}
    result.update({'%s_submit' % prefix: 1})
    return result


def get_content_links(response, element='#content'):
    """Extract links from :class:`HttpResponse` #content element."""
    doc = fromstring(response.content)
    [content_node] = doc.cssselect(element)
    return [elem.get('href') for elem in content_node.cssselect('a')]


# Some horrible binary data that could never, ever, under any encoding
# known to man(1) survive mis-interpretation as text.
#
# The data contains a nul byte to trip up accidental string termination.
# Switch the bytes of the byte-order mark around and by design you get
# an invalid codepoint; put a byte with the high bit set between bytes
# that have it cleared, and you have a guaranteed non-UTF-8 sequence.
#
# (1) Provided, of course, that man know only about ASCII and
# UTF.
sample_binary_data = codecs.BOM64_LE + codecs.BOM64_BE + b'\x00\xff\x00'
