# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The MAAS command-line interface."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from glob import iglob
from os.path import (
    dirname,
    join,
    )
import sys

# Add `lib` in the current directory into sys.path.
sys.path[:0] = iglob(join(dirname(__file__), "lib"))

from commandant import builtins
from commandant.controller import CommandController


def main(argv=sys.argv):
    controller = CommandController(
        program_name=__name__, program_version="2.0",
        program_summary="Control MAAS using its API from the command-line.",
        program_url="http://maas.ubuntu.com/")
    # At this point controller.load_path(...) can be used to load commands
    # from a pre-agreed location on the filesystem, so that the command set
    # will grow and shrink with the installed packages.
    controller.load_module(builtins)
    controller.install_bzrlib_hooks()
    controller.run(argv[1:])
