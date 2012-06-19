# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""PXE configuration management."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'PXEConfig',
    ]


import os

from celeryconfig import (
    PXE_TARGET_DIR,
    PXE_TEMPLATES_DIR,
    )


class PXEConfig:
    """PXE Configuration management.

    Encapsulation of PXE config templates and parameter substitution.

    :param arch: The architecture of the context node.
    :type arch: string
    :param subarch: The sub-architecture of the context node. This is
        optional because some architectures such as i386 don't have a
        sub-architecture.  If not passed, a directory name of "generic"
        is used in the subarch part of the path to the target file.
    :type subarch: string
    """

    def __init__(self, arch, subarch=None):
        if subarch is None:
            subarch = "generic"
        template_basedir = PXE_TEMPLATES_DIR
        target_basedir = PXE_TARGET_DIR

        self.template = os.path.join(template_basedir, "maas.template")

        self.target_dir = os.path.join(
            target_basedir,
            arch,
            subarch)

    def get_template(self):
        with open(self.template, "rb") as f:
            return f.read()
