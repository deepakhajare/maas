# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The MAAS command-line interface."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "CommandError",
    ]

import argparse
import locale
import sys

from bzrlib import osutils
from maascli.utils import parse_docstring


modules = {
    "api": "maascli.api",
    }


def main(argv=None):
    # Set up the process's locale; this helps bzrlib decode command-line
    # arguments in the next step.
    locale.setlocale(locale.LC_ALL, "")
    if argv is None:
        argv = sys.argv[:1] + osutils.get_unicode_argv()

    # Create the base argument parser.
    parser = argparse.ArgumentParser(
        description="Control MAAS using its API from the command-line.",
        prog=argv[0], epilog="http://maas.ubuntu.com/")
    subparsers = parser.add_subparsers(title="modules")

    # Register declared modules.
    for name, module in sorted(modules.items()):
        if isinstance(module, (str, unicode)):
            module = __import__(module, fromlist=True)
        help_title, help_body = parse_docstring(module)
        subparser = subparsers.add_parser(
            name, help=help_title, description=help_body)
        register(module, subparser)

    # Run, doing polite things with exceptions.
    try:
        options = parser.parse_args(argv[1:])
        options.execute(options)
    except KeyboardInterrupt:
        raise SystemExit(1)
    except StandardError as error:
        if __debug__:
            raise
        else:
            sys.stderr.write("%s\n" % error)
            raise SystemExit(2)


def register(module, parser):
    """Register commands in `module` with the given argument parser."""
    subparsers = parser.add_subparsers(title="actions")
    commands = {
        name: command for name, command in vars(module).items()
        if name.startswith("cmd_")
        }
    for name, command in commands.items():
        command_name = "-".join(name.split("_")[1:])
        help_title, help_body = parse_docstring(command)
        parser = subparsers.add_parser(
            command_name, help=help_title, description=help_body)
        parser.set_defaults(execute=command(parser))


CommandError = SystemExit
