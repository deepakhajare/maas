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
from functools import partial
from inspect import getdoc
import locale
import re
import sys
from textwrap import dedent

from bzrlib import osutils


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
        subparser = subparsers.add_parser(name, help=module.__doc__)
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
    """Register commands here with the given argument parser."""
    if isinstance(module, (str, unicode)):
        module = __import__(module, fromlist=True)
    subparsers = parser.add_subparsers(title="actions")
    commands = {
        name: command for name, command in vars(module).items()
        if name.startswith("cmd_")
        }
    for name, command in commands.items():
        command_name = "-".join(name.split("_")[1:])
        parser = subparsers.add_parser(command_name, help=command.__doc__)
        execute = command(parser)
        parser.set_defaults(execute=execute)


CommandError = SystemExit


re_paragraph_splitter = re.compile(
    r"(?:\r\n|\r|\n){2,}", re.MULTILINE)

paragraph_split = re_paragraph_splitter.split
docstring_split = partial(paragraph_split, maxsplit=1)
remove_line_breaks = lambda string: (
    " ".join(line.strip() for line in string.splitlines()))

newline = "\n"
empty = ""


def parse_docstring(thing):
    doc = getdoc(thing)
    doc = empty if doc is None else doc.expandtabs()
    # Break the docstring into two parts: title and body.
    parts = docstring_split(doc)
    if len(parts) == 2:
        title, body = parts[0], dedent(parts[1])
    else:
        title, body = parts[0], empty
    # Remove line breaks from the title line.
    title = remove_line_breaks(title)
    # Remove line breaks from non-indented paragraphs in the body.
    paragraphs = []
    for paragraph in paragraph_split(body):
        if not paragraph[:1].isspace():
            paragraph = remove_line_breaks(paragraph)
        paragraphs.append(paragraph)
    # Rejoin the paragraphs, normalising on newline.
    body = newline.join(
        paragraph.replace("\r\n", newline).replace("\r", newline)
        for paragraph in paragraphs)
    return (
        (None if len(title) == 0 else title),
        (None if len(body) == 0 else body))
