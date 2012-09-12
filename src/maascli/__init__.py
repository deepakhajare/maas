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
from os.path import join, dirname
import sys


# Insert all eggs in the current directory into sys.path.
sys.path[:0] = iglob(join(dirname(__file__), "*.egg"))


def main():
    print("Hello, World!")
