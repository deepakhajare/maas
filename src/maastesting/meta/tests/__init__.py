# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the MAAS source tree as a whole."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "root",
    ]

from os.path import (
    abspath,
    dirname,
    join,
    pardir,
    )


root = abspath(join(dirname(__file__), pardir, pardir, pardir, pardir))
