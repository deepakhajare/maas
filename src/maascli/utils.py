# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for the command-line interface."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "parse_docstring",
    ]

from functools import partial
from inspect import getdoc
import re
from textwrap import dedent


re_paragraph_splitter = re.compile(
    r"(?:\r\n){2,}|\r{2,}|\n{2,}", re.MULTILINE)

paragraph_split = re_paragraph_splitter.split
docstring_split = partial(paragraph_split, maxsplit=1)
remove_line_breaks = lambda string: (
    " ".join(line.strip() for line in string.splitlines()))

newline = "\n"
empty = ""


def parse_docstring(thing):
    doc = thing if isinstance(thing, (str, unicode)) else getdoc(thing)
    doc = empty if doc is None else doc.expandtabs().strip()
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
    body = (newline + newline).join(
        paragraph.replace("\r\n", newline).replace("\r", newline)
        for paragraph in paragraphs)
    return title, body
