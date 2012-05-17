# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing utilities."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'extract_word_list',
    ]

import re


def extract_word_list(string):
    """Return a list of words from a string.

    Words are any string of 1 or more characters, not including commas,
    semi-colons, or whitespace.
    """
    return re.findall("[^,;\s]+", string)
