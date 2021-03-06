# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Preseed generation."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'compose_enlistment_preseed_url',
    'compose_preseed_url',
    'get_enlist_preseed',
    'get_preseed',
    ]

from collections import namedtuple
from os.path import join
from pipes import quote
from urllib import urlencode
from urlparse import urlparse

from django.conf import settings
from maasserver.compose_preseed import compose_preseed
from maasserver.enum import (
    NODE_STATUS,
    PRESEED_TYPE,
    )
from maasserver.models import Config
from maasserver.server_address import get_maas_facing_server_host
from maasserver.utils import absolute_reverse
import tempita


GENERIC_FILENAME = 'generic'


def get_enlist_preseed(nodegroup=None):
    """Return the enlistment preseed.

    :param nodegroup: The nodegroup used to generate the preseed.
    :return: The rendered preseed string.
    :rtype: basestring.
    """
    return render_enlistment_preseed(
        PRESEED_TYPE.ENLIST, nodegroup=nodegroup)


def get_enlist_userdata(nodegroup=None):
    """Return the enlistment preseed.

    :param nodegroup: The nodegroup used to generate the preseed.
    :return: The rendered enlistment user-data string.
    :rtype: basestring.
    """
    return render_enlistment_preseed(
        PRESEED_TYPE.ENLIST_USERDATA, nodegroup=nodegroup)


def get_preseed(node):
    """Return the preseed for a given node.  Depending on the node's status
    this will be a commissioning preseed (if the node is commissioning) or the
    standard preseed (normal installation preseed).

    :param node: The node to return preseed for.
    :type node: :class:`maasserver.models.Node`
    :return: The rendered preseed string.
    :rtype: basestring.
    """
    if node.status == NODE_STATUS.COMMISSIONING:
        return render_preseed(
            node, PRESEED_TYPE.COMMISSIONING,
            release=Config.objects.get_config('commissioning_distro_series'))
    else:
        return render_preseed(node, PRESEED_TYPE.DEFAULT,
            release=node.get_distro_series())


def get_preseed_filenames(node, prefix='', release='', default=False):
    """List possible preseed template filenames for the given node.

    :param node: The node to return template preseed filenames for.
    :type node: :class:`maasserver.models.Node`
    :param prefix: At the top level, this is the preseed type (will be used as
        a prefix in the template filenames).  Usually one of {'', 'enlist',
        'commissioning'}.
    :type prefix: basestring
    :param release: The Ubuntu release to be used.
    :type release: basestring
    :param default: Should we return the default ('generic') template as a
        last resort template?
    :type default: boolean

    Returns a list of possible preseed template filenames using the following
    lookup order:
    {prefix}_{node_architecture}_{node_subarchitecture}_{release}_{node_name}
    {prefix}_{node_architecture}_{node_subarchitecture}_{release}
    {prefix}_{node_architecture}_{node_subarchitecture}
    {prefix}_{node_architecture}
    {prefix}
    'generic'
    """
    elements = []
    # Add prefix.
    if prefix != '':
        elements.append(prefix)
    # Add architecture/sub-architecture.
    if node is not None:
        arch = split_subarch(node.architecture)
        elements.extend(arch)
    # Add release.
    elements.append(release)
    # Add hostname.
    if node is not None:
        elements.append(node.hostname)
    while elements:
        yield compose_filename(elements)
        elements.pop()
    if default:
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


def get_escape_singleton():
    """Return a singleton containing methods to escape various formats used in
    the preseed templates.
    """
    Escape = namedtuple('Escape', 'shell')
    return Escape(shell=quote)


class PreseedTemplate(tempita.Template):
    """A Tempita template specialised for preseed rendering.

    It provides a filter named 'escape' which contains methods to escape
    various formats used in the template."""

    default_namespace = dict(
        tempita.Template.default_namespace,
        escape=get_escape_singleton())


class TemplateNotFoundError(Exception):
    """The template has not been found."""

    def __init__(self, name):
        super(TemplateNotFoundError, self).__init__(name)
        self.name = name


def load_preseed_template(node, prefix, release=''):
    """Find and load a `PreseedTemplate` for the given node.

    :param node: See `get_preseed_filenames`.
    :param prefix: See `get_preseed_filenames`.
    :param release: See `get_preseed_filenames`.
    """

    def get_template(name, from_template, default=False):
        """A Tempita hook used to load the templates files.

        It is defined to preserve the context (node, name, release, default)
        since this will be called (by Tempita) called out of scope.
        """
        filenames = list(get_preseed_filenames(node, name, release, default))
        filepath, content = get_preseed_template(filenames)
        if filepath is None:
            raise TemplateNotFoundError(name)
        # This is where the closure happens: pass `get_template` when
        # instanciating PreseedTemplate.
        return PreseedTemplate(
            content, name=filepath, get_template=get_template)

    return get_template(prefix, None, default=True)


def get_hostname_and_path(url):
    """Return a tuple of the hostname and the hierarchical path from a url."""
    parsed_url = urlparse(url)
    return parsed_url.hostname, parsed_url.path


def get_preseed_context(release='', nodegroup=None):
    """Return the node-independent context dictionary to be used to render
    preseed templates.

    :param release: See `get_preseed_filenames`.
    :param nodegroup: The nodegroup used to generate the preseed.
    :return: The context dictionary.
    :rtype: dict.
    """
    server_host = get_maas_facing_server_host(nodegroup=nodegroup)
    main_archive_hostname, main_archive_directory = get_hostname_and_path(
        Config.objects.get_config('main_archive'))
    ports_archive_hostname, ports_archive_directory = get_hostname_and_path(
        Config.objects.get_config('ports_archive'))
    base_url = nodegroup.maas_url if nodegroup is not None else None
    return {
        'main_archive_hostname': main_archive_hostname,
        'main_archive_directory': main_archive_directory,
        'ports_archive_hostname': ports_archive_hostname,
        'ports_archive_directory': ports_archive_directory,
        'release': release,
        'server_host': server_host,
        'server_url': absolute_reverse('nodes_handler', base_url=base_url),
        'metadata_enlist_url': absolute_reverse('enlist', base_url=base_url),
        'http_proxy': Config.objects.get_config('http_proxy'),
        }


def get_node_preseed_context(node, release=''):
    """Return the node-dependent context dictionary to be used to render
    preseed templates.

    :param node: See `get_preseed_filenames`.
    :param release: See `get_preseed_filenames`.
    :return: The context dictionary.
    :rtype: dict.
    """
    # Create the url and the url-data (POST parameters) used to turn off
    # PXE booting once the install of the node is finished.
    node_disable_pxe_url = absolute_reverse(
        'metadata-node-by-id', args=['latest', node.system_id],
        base_url=node.nodegroup.maas_url)
    node_disable_pxe_data = urlencode({'op': 'netboot_off'})
    return {
        'node': node,
        'preseed_data': compose_preseed(node),
        'node_disable_pxe_url': node_disable_pxe_url,
        'node_disable_pxe_data': node_disable_pxe_data,
    }


def render_enlistment_preseed(prefix, release='', nodegroup=None):
    """Return the enlistment preseed.

    :param prefix: See `get_preseed_filenames`.
    :param release: See `get_preseed_filenames`.
    :param nodegroup: The nodegroup used to generate the preseed.
    :return: The rendered preseed string.
    :rtype: basestring.
    """
    template = load_preseed_template(None, prefix, release)
    context = get_preseed_context(release, nodegroup=nodegroup)
    return template.substitute(**context)


def render_preseed(node, prefix, release=''):
    """Return the preseed for the given node.

    :param node: See `get_preseed_filenames`.
    :param prefix: See `get_preseed_filenames`.
    :param release: See `get_preseed_filenames`.
    :return: The rendered preseed string.
    :rtype: basestring.
    """
    template = load_preseed_template(node, prefix, release)
    nodegroup = node.nodegroup
    context = get_preseed_context(release, nodegroup=nodegroup)
    context.update(get_node_preseed_context(node, release))
    return template.substitute(**context)


def compose_enlistment_preseed_url(nodegroup=None):
    """Compose enlistment preseed URL.

    :param nodegroup: The nodegroup used to generate the preseed.
    """
    # Always uses the latest version of the metadata API.
    base_url = nodegroup.maas_url if nodegroup is not None else None
    version = 'latest'
    return absolute_reverse(
        'metadata-enlist-preseed', args=[version],
        query={'op': 'get_enlist_preseed'}, base_url=base_url)


def compose_preseed_url(node):
    """Compose a metadata URL for `node`'s preseed data."""
    # Always uses the latest version of the metadata API.
    version = 'latest'
    base_url = node.nodegroup.maas_url
    return absolute_reverse(
        'metadata-node-by-id', args=[version, node.system_id],
        query={'op': 'get_preseed'}, base_url=base_url)
