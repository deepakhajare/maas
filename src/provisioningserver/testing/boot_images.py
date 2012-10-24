# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test helpers for boot-image parameters."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'make_boot_image_params',
    'make_boot_image_params_on_wire',
    ]

from maasserver.testing.factory import factory


def make_boot_image_params():
    """Create an arbitrary dict of boot-image parameters.

    These are the parameters that together describe a kind of boot that we
    may need a kernel and initrd for: architecture, sub-architecture,
    Ubuntu release, and boot purpose.  See the `tftppath` module for how
    these fit together.
    """
    fields = dict(
        nodegroup=factory.make_node_group(),
        architecture=factory.make_name('architecture'),
        subarchitecture=factory.make_name('subarchitecture'),
        release=factory.make_name('release'),
        purpose=factory.make_name('purpose'))
    return fields


def make_boot_image_params_on_wire(image_params=None):
    """As for make_boot_image_params except the parameters are suitable for
    transmission to the API, i.e. they are serializable.
    """
    if image_params is None:
        image_params = make_boot_image_params()
    image_params = dict(
        image_params, nodegroup=image_params['nodegroup'].uuid)
    return image_params
