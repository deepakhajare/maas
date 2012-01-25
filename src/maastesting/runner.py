# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test runner for maas and its applications."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "TestRunner",
    ]

from subprocess import check_call

from django_nose import NoseTestSuiteRunner
from testresources import OptimisingTestSuite


class TestRunner(NoseTestSuiteRunner):
    """Custom test runner; ensures that the test database cluster is up."""

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = super(TestRunner, self).build_suite(
            test_labels, extra_tests, **kwargs)
        return OptimisingTestSuite(suite)

    def setup_databases(self, *args, **kwargs):
        """Fire up the db cluster, then punt to original implementation."""
        check_call(['utilities/maasdb', 'start', './db/', 'disposable'])
        return super(TestRunner, self).setup_databases(*args, **kwargs)
