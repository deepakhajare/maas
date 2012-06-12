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

import provisioningserver.dhcp.writer


def setup():
    # Ensure stdout and stderr are line-bufferred.
    sys.stdout = fdopen(sys.stdout.fileno(), "ab", 1)
    sys.stderr = fdopen(sys.stderr.fileno(), "ab", 1)
    # Run the SIGINT handler on SIGTERM; `svc -d` sends SIGTERM.
    signal.signal(signal.SIGTERM, signal.default_int_handler)


# See http://docs.python.org/release/2.7/library/argparse.html.
argument_parser = argparse.ArgumentParser(description=__doc__)
argument_subparsers = argument_parser.add_subparsers(title="actions")


def register_action(name, module, *args, **kwargs):
    """Configure a subparser for the given name and module.

    :param module: A module that has `run` and `add_arguments` callables.
    """
    parser = argument_subparsers.add_parser(
        name, *args, help=module.run.__doc__, **kwargs)
    parser.set_defaults(handler=module.run)
    module.add_arguments(parser)
    return parser


register_action("generate-dhcp-config", provisioningserver.dhcp.writer)


def main(argv=None):
    args = argument_parser.parse_args(argv)
    try:
        setup()
        args.handler(args)
    except CalledProcessError, error:
        # TODO: Print error.cmd and error.output?
        raise SystemExit(error.returncode)
    except KeyboardInterrupt:
        pass
