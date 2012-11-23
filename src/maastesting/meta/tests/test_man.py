# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of MAAS's man pages."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from glob import iglob
from os.path import (
    basename,
    getmtime,
    join,
    relpath,
    splitext,
    )

from maastesting.testcase import TestCase
from testtools.matchers import (
    AfterPreprocessing,
    Equals,
    FileExists,
    GreaterThan,
    MatchesAny,
    )

from . import root


class TestFreshness(TestCase):
    """Ensure that the man pages are up-to-date.

    The man pages in ``${root}/man`` are generated from sources in
    ``${root}/docs/man``. They're not generated at package build time because
    that currently requires a fully built Django+MAAS stack. Keeping the man
    pages in the tree and regulating them here is a reasonable compromise.
    """

    scenarios = [
        (relpath(filename, root), {"source": filename})
        for filename in iglob(join(root, "docs", "man", "*.rst"))
        ]

    @property
    def target(self):
        name, ext = splitext(self.source)
        return join(root, "man", basename(name))

    def test_generated_and_up_to_date(self):
        self.assertThat(self.target, FileExists())
        ref = getmtime(self.source)
        is_up_to_date = MatchesAny(GreaterThan(ref), Equals(ref))
        file_is_up_to_date = AfterPreprocessing(getmtime, is_up_to_date)
        self.assertThat(self.target, file_is_up_to_date)
