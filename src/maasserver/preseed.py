# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Preseed generation."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import base64
from os.path import join

from django.conf import settings
import tempita


GENERIC_FILENAME = 'generic'


# XXX: rvb 2012-06-14 bug=1013146:  'precise' is hardcoded here.
def get_preseed_filenames(node, prefix, release='precise'):
    """List possible preseed template filenames for the given node.

    :param node: The node to return template preseed filenames for.
    :type node: :class:`maasserver.models.Node`
    :param prefix: At the top level, this is the preseed type (will be used as
        a prefix in the template filenames).  Usually one of {'', 'enlist',
        'commissioning'}.
    :type prefix: basestring
    :param release: The Ubuntu release to be used.
    :type release: basestring

    Returns a list of possible preseed template filenames using the following
    lookup order:
    {type}_{node_architecture}_{node_subarchitecture}_{release}_{node_hostname}
    {type}_{node_architecture}_{node_subarchitecture}_{release}
    {type}_{node_architecture}
    {type}
    'generic'
    """
    arch = split_subarch(node.architecture)
    elements = [prefix] + arch + [release, node.hostname]
    while elements:
        yield compose_filename(elements)
        elements.pop()
    yield GENERIC_FILENAME


def split_subarch(architecture):
    """Split the architecture and the subarchitecture."""
    return architecture.split('/')


def compose_filename(elements):
    """Create a preseed filename from a list of elements."""
    return '_'.join(elements)


def get_preseed_template(filenames):
    """Get the path and content for the first template found.

    :param filenames: An iterable of relative filenames.
    """
    assert not isinstance(filenames, basestring)
    for location in settings.PRESEED_TEMPLATE_LOCATIONS:
        for filename in filenames:
            filepath = join(location, filename)
            try:
                with open(filepath, "rb") as stream:
                    content = stream.read()
                    return filepath, content
            except IOError:
                pass  # Ignore.
    else:
        return None, None


class PreseedTemplate(tempita.Template):
    """A Tempita template specialised for preseed rendering."""

    default_namespace = dict(
        tempita.Template.default_namespace,
        b64decode=base64.b64decode,
        b64encode=base64.b64encode,
        urlsafe_b64decode=base64.urlsafe_b64decode,
        urlsafe_b64encode=base64.urlsafe_b64encode)


class TemplateNotFoundError(Exception):
    """The template has not been found."""

    def __init__(self, name):
        super(TemplateNotFoundError, self).__init__(name)
        self.name = name


def load_preseed_template(node, prefix, release="precise"):
    """Find and load a `PreseedTemplate` for the given node.

    :param node: See `get_preseed_filenames`.
    :param prefix: See `get_preseed_filenames`.
    :param release: See `get_preseed_filenames`.
    """

    def get_template(name, from_template):
        filenames = get_preseed_filenames(node, prefix, release)
        filepath, content = get_preseed_template(filenames)
        if filepath is None:
            raise TemplateNotFoundError(name)
        return PreseedTemplate(
            content, name=filepath, get_template=get_template)

    return get_template("", None)
