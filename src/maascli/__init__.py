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

import locale
from os.path import (
    dirname,
    join,
    )
import sys

from bzrlib import osutils

# Add `lib` in this package's directory to sys.path.
sys.path.insert(0, join(dirname(__file__), "lib"))

from commandant import builtins
from commandant.controller import CommandController
import maascli.api


def main(argv=None):
    # Set up the process's locale; this helps bzrlib decode command-line
    # arguments in the next step.
    locale.setlocale(locale.LC_ALL, "")
    if argv is None:
        argv = sys.argv[:1] + osutils.get_unicode_argv()
    controller = CommandController(
        program_name=argv[0],
        program_version="1.0",
        program_summary="Control MAAS using its API from the command-line.",
        program_url="http://maas.ubuntu.com/")
    # At this point controller.load_path(...) can be used to load commands
    # from a pre-agreed location on the filesystem, so that the command set
    # will grow and shrink with the installed packages.
    controller.load_module(maascli.api)
    controller.load_module(maascli.api.command_module())
    controller.load_module(builtins)
    controller.install_bzrlib_hooks()
    # Run, doing polite things with exceptions.
    try:
        controller.run(argv[1:])
    except KeyboardInterrupt:
        raise SystemExit(1)
    except StandardError as error:
        if __debug__:
            raise
        else:
            sys.stderr.write("%s\n" % error)
            raise SystemExit(2)
