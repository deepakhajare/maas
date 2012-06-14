# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Preseed module."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


GENERIC_FILENAME = 'generic'


# XXX: rvb 2012-06-14 bug=1013146:  'precise' is hardcoded here.
def get_preseed_filenames(node, type, release='precise'):
    """List possible preseed template filenames for the given node.

    :param node: The node to return template preseed filenames for.
    :type node: :class:`maasserver.models.Node`
    :param type: The preseed type (will be used as a prefix in the template
        filenames).  Usually one of {'', 'enlist', 'commissioning'}.
    :type type: basestring
    :param release: The Ubuntu release to be used.
    :type type: basestring

    Returns a list of possible preseed template filenames using the following
    lookup order:
    {type}_{node_architecture}_{node_subarchitecture}_{release}_{node_hostname}
    {type}_{node_architecture}_{node_subarchitecture}_{release}
    {type}_{node_architecture}
    {type}
    'generic'
    """
    elements = (
        [type] + split_subarch(node.architecture) + [release, node.hostname])
    return _create_triange_combination(elements) + [GENERIC_FILENAME]


def _create_triange_combination(elements):
    """Given a list of string elements, return a list of filenames given by
    composing (using the method 'compose_filename') all the elements, then
    all elements but the last, etc.

    >>> _create_triange_combination(['A', 'B', 'C'])
    ['A_B_C', 'A_B', 'A']
    """
    filenames = map(
        compose_filename,
        [elements[:i + 1] for i in range(len(elements))])
    filenames.reverse()
    return filenames


def split_subarch(architecture):
    return architecture.split('/')


COMPOSE_FILENAME_SEPARATOR = '_'


def compose_filename(elements):
    return COMPOSE_FILENAME_SEPARATOR.join(elements)
