# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maastesting.fixtures`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os

from fixtures import EnvironmentVariableFixture
from maastesting.factory import factory
from maastesting.fixtures import (
    ProxiesDisabledFixture,
    TempWDFixture,
    )
from maastesting.testcase import TestCase


class TestProxiedDisabledFixture(TestCase):
    """Tests for :class:`ProxiesDisabledFixture`."""

    def test_removes_http_proxy_from_environment(self):
        http_proxy = factory.make_name("http-proxy")
        initial = EnvironmentVariableFixture("http_proxy", http_proxy)
        self.useFixture(initial)
        # On entry, http_proxy is removed from the environment.
        with ProxiesDisabledFixture():
            self.assertNotIn("http_proxy", os.environ)
        # On exit, http_proxy is restored.
        self.assertEqual(http_proxy, os.environ.get("http_proxy"))

    def test_removes_https_proxy_from_environment(self):
        https_proxy = factory.make_name("https-proxy")
        initial = EnvironmentVariableFixture("https_proxy", https_proxy)
        self.useFixture(initial)
        # On entry, https_proxy is removed from the environment.
        with ProxiesDisabledFixture():
            self.assertNotIn("https_proxy", os.environ)
        # On exit, http_proxy is restored.
        self.assertEqual(https_proxy, os.environ.get("https_proxy"))


class TestTempWDFixture(TestCase):

    def test_changes_dir_and_cleans_up(self):
        orig_cwd = os.getcwd()
        with TempWDFixture() as temp_wd:
            new_cwd = os.getcwd()
            self.assertTrue(os.path.isdir(temp_wd.path))
            self.assertNotEqual(orig_cwd, new_cwd)
            self.assertEqual(new_cwd, temp_wd.path)
        final_cwd = os.getcwd()
        self.assertEqual(orig_cwd, final_cwd)
        self.assertFalse(os.path.isdir(new_cwd))
