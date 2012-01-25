# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import (
    print_function,
    unicode_literals,
    )

import test_fakecobbler

__metaclass__ = type
__all__ = [
    test_fakecobbler,
    ]

from os.path import dirname

from django.utils.unittest import defaultTestLoader


def suite():
    return defaultTestLoader.discover(dirname(__file__))
