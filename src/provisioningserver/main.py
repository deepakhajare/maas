#!/usr/bin/env python2.7
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Command-line interface for the MAAS provisioning component."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type

import argparse
from os import fdopen
import signal
from subprocess import CalledProcessError
import sys


def setup():
    # Ensure stdout and stderr are line-bufferred.
    sys.stdout = fdopen(sys.stdout.fileno(), "ab", 1)
    sys.stderr = fdopen(sys.stderr.fileno(), "ab", 1)
    # Run the SIGINT handler on SIGTERM; `svc -d` sends SIGTERM.
    signal.signal(signal.SIGTERM, signal.default_int_handler)


# See http://docs.python.org/release/2.7/library/argparse.html.
argument_parser = argparse.ArgumentParser(description=__doc__)
argument_subparsers = argument_parser.add_subparsers(title="actions")


def add_action(name, handler, *args, **kwargs):
    """Configure a subparser for the given name and function."""
    parser = argument_subparsers.add_parser(
        name, *args, help=handler.__doc__, **kwargs)
    parser.set_defaults(handler=handler)
    return parser


def get_action(name):
    """Retrieve the named subparser."""
    return argument_subparsers.choices[name]


def action_print_args(args):
    """Print the arguments passed in."""
    print(args)


# Register actions.
add_action("print", action_print_args)


# Customise argument lists for individual actions.
get_action("print").add_argument(
    "--hello", dest="hello", action="store", metavar="WHO")


def main(args=None):
    args = argument_parser.parse_args(args)
    try:
        setup()
        args.handler(args)
    except CalledProcessError, error:
        # TODO: Print error.cmd and error.output?
        raise SystemExit(error.returncode)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
