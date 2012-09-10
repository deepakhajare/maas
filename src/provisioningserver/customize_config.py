# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Management command: customize a config file.

Use this when there's absolutely no way around adding a custom MAAS section
to an existing config file.  It appends the custom section on first run, but
on subsequent runs, replaces the existing custom section in-place.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'add_arguments',
    'run',
    ]

from provisioningserver.utils import write_custom_config_section


def add_arguments(parser):
    parser.add_argument(
        '--encoding', dest='encoding', default='utf-8',
        help="Encoding to use when reading and writing config.")
    parser.add_argument(
        '--file', dest='file', default=None,
        help="Configuration file that you want to customize.")


def run(args):
    """Customize a config file.

    Reads a custom configuration section from standard input, and the given
    configuration file.  Prints to standard output a copy of the file with
    the custom section appended, or substituted for an existing custom
    section if there already was one.
    """
