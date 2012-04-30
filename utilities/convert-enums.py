#!/usr/bin/env python2.7
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generate JavaScript enum definitions based on their python definitions.

MAAS defines its enums as simple classes, with the enum items as attributes.
Running this script produces a source text containing the JavaScript
equivalents of the same enums, so that JavaScript code can make use of them.

The script takes one option: --src=DIRECTORY.  DIRECTORY is where the MAAS
modules (maasserver, metadataserver, provisioningserver) can be found.

The resulting JavaScript module is printed to standard output.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type

from argparse import ArgumentParser
from datetime import datetime
from imp import (
    find_module,
    load_module,
    )
import json
from operator import itemgetter
import os.path
import sys
from textwrap import dedent


# Header.  Will be written on top of the output.
header = dedent("""\
    /*
    Generated file.  DO NOT EDIT.

    This file was generated by %(script)s,
    on %(timestamp)s.
    */

    """
    % {'script': sys.argv[0], 'timestamp': datetime.now()})


def get_module(src_path, package, name='enum'):
    """Attempt to load a given module.

    This makes some assumptions about directory structure: it is assumed
    that the module is directly in a package of the given name, which in turn
    should be directly in the search path.

    :param src_path: The path to search in.
    :param package: The package to load the requested module from.
    :param name: Name of module to load.
    :return: The imported module, or None if it was not found.
    """
    path = os.path.join(src_path, package)
    try:
        found_module = find_module(name, [path])
    except ImportError:
        # No enum module here.  Ignore this package or directory.
        return None
    return load_module(name, *found_module)


def find_enum_modules(src_path):
    """Find MAAS "enum" modules in the packages in src_path.

    This assumes that all MAAS enums can be found in
    <src_path>/<package>/enum.py.

    :param src_path: The path to search in.
    :return: A list of "enum" modules found in packages in src_path.
    """
    return filter(None, [
        get_module(src_path, package, 'enum')
        for package in os.listdir(src_path)])


def is_enum(item):
    """Does the given python item look like an enum?

    :param item: An item imported from a MAAS enum module.
    :return: Bool.
    """
    return isinstance(item, type) and item.__name__ == item.__name__.upper()


def get_enum_classes(module):
    """Collect all enum classes exported from loaded `module`."""
    return filter(is_enum, (module.__dict__[name] for name in module.__all__))


def serialize_value(value):
    """Represent an enumeration item's value in JavaScript."""
    if value is None:
        return 'null'
    elif isinstance(value, basestring):
        return json.dumps(value)
    else:
        return value


def serialize_item(key, value):
    """Represent one key/value pair as a line in a JavaScript enum."""
    return "    %s: %s" % (key, serialize_value(value))


def serialize_dict_items(enum):
    """Represent the items of a dict as a block of JavaScript."""
    items = sorted(enum.items(), key=itemgetter(1))
    lines = [("    %s: %s" % (key, value)) for key, value in items]
    return ',\n'.join(serialize_item(key, value) for key, value in items)


def serialize_enum(enum):
    """Represent a MAAS enum class in JavaScript."""
    # Import lazily to make use of initialized path.
    from maasserver import map_enum

    head = "var %s = {\n" % enum.__name__
    foot = "\n};"
    return head + serialize_dict_items(map_enum(enum)) + foot


def parse_args():
    """Parse options & arguments."""
    default_src = os.path.join(os.path.dirname(sys.path[0]), 'src')
    parser = ArgumentParser(
        "Generate JavaScript enums based on python enums modules")
    parser.add_argument(
        '--src', metavar='SOURCE_DIRECTORY', type=str, default=default_src,
        help="Look for the MAAS packages in SOURCE_DIRECTORY.")
    return parser.parse_args()


def main(args):
    enum_modules = find_enum_modules(args.src)
    enums = sum((get_enum_classes(module) for module in enum_modules), [])
    dumps = (serialize_enum(enum) for enum in enums)
    print(header + "\n\n".join(dumps))


if __name__ == "__main__":
    args = parse_args()
    # Add src directory so that we can import from MAAS packages.
    sys.path.append(args.src)
    main(args)
