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
    "Command",
    "CommandError",
    "register",
    ]

from abc import (
    ABCMeta,
    abstractmethod,
    )
import argparse
import locale
import sys

from bzrlib import osutils
from maascli.utils import (
    parse_docstring,
    safe_name,
    )


modules = {
    "api": "maascli.api",
    }


class ArgumentParser(argparse.ArgumentParser):
    """Specialisation of argparse's parser with better support for subparsers.

    Specifically, the one-shot `add_subparsers` call is disabled, replaced by
    a lazily evaluated `subparsers` property.
    """

    def add_subparsers(self):
        raise NotImplementedError(
            "add_subparsers has been disabled")

    @property
    def subparsers(self):
        try:
            return self.__subparsers
        except AttributeError:
            parent = super(ArgumentParser, self)
            self.__subparsers = parent.add_subparsers(title="commands")
            return self.__subparsers


def main(argv=None):
    # Set up the process's locale; this helps bzrlib decode command-line
    # arguments in the next step.
    locale.setlocale(locale.LC_ALL, "")
    if argv is None:
        argv = sys.argv[:1] + osutils.get_unicode_argv()

    # Create the base argument parser.
    parser = ArgumentParser(
        description="Control MAAS using its API from the command-line.",
        prog=argv[0], epilog="http://maas.ubuntu.com/")

    # Register declared modules.
    for name, module in sorted(modules.items()):
        if isinstance(module, (str, unicode)):
            module = __import__(module, fromlist=True)
        help_title, help_body = parse_docstring(module)
        module_parser = parser.subparsers.add_parser(
            name, help=help_title, description=help_body)
        register(module, module_parser)

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


class Command:
    """A base class for composing commands.

    This adheres to the expectations of `register`.
    """

    __metaclass__ = ABCMeta

    def __init__(self, parser):
        super(Command, self).__init__()
        self.parser = parser

    @abstractmethod
    def __call__(self, options):
        """Execute this command."""


CommandError = SystemExit


def register(module, parser):
    """Register commands in `module` with the given argument parser.

    This looks for callable objects named `cmd_*`, calls them with a new
    subparser, and registers them as the default value for `execute` in the
    namespace.

    If the module also has a `register` function, this is also called, passing
    in the module being scanned, and the parser given to this function.
    """
    # Register commands.
    commands = {
        name[4:]: command for name, command in vars(module).items()
        if name.startswith("cmd_") and callable(command)
        }
    for name, command in commands.items():
        help_title, help_body = parse_docstring(command)
        command_parser = parser.subparsers.add_parser(
            safe_name(name), help=help_title, description=help_body)
        command_parser.set_defaults(execute=command(command_parser))
    # Extra subparser registration.
    register_module = getattr(module, "register", None)
    if callable(register_module):
        register_module(module, parser)
