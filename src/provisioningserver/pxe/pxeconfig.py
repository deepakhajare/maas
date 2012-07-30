# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generating PXE configuration files.

For more about the format of these files:

http://www.syslinux.org/wiki/index.php/SYSLINUX#How_do_I_Configure_SYSLINUX.3F
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'PXEConfigFail',
    'render_pxe_config',
    ]


from os import path

import tempita


template_dir = path.join(path.dirname(__file__), 'templates')
template_filename = path.join(template_dir, "maas.template")
template = tempita.Template.from_filename(template_filename)


class PXEConfigFail(NameError):
    """Raised if there's a problem with a PXE config."""


def render_pxe_config(arch, subarch="generic", **options):
    """Render a PXE configuration file as a unicode string.

    :param arch: The architecture to write a configuration for, e.g. i386.
    :type arch: string
    :param subarch: Sub-architecture. Only needed for architectures that
        have sub-architectures, such as ARM; other architectures use
        a sub-architecture of "generic" (which is the default).
    :type subarch: string

    The `options` keywords should comprise at least:

    :param menu_title: Title that the node should show on its boot menu.
    :param kernel: TFTP path to the kernel image to boot.
    :param initrd: TFTP path to the initrd file to boot from.
    :param append: Additional parameters to append to the kernel
        command line.

    :raises PXEConfigFail: if there's a problem substituting the template
        parameters.
    """
    try:
        return template.substitute(options)
    except NameError as error:
        raise PXEConfigFail(*error.args)
