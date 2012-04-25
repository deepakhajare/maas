# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test runner for maas and its applications."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "TestRunner",
    ]

from contextlib import contextmanager
from os import (
    environ,
    path,
    )
from time import time

from django.conf import settings
from django_nose import NoseTestSuiteRunner
from van.pg import Cluster


@contextmanager
def timing(message="%.1f seconds."):
    start = time()
    yield lambda: time() - start
    print(message % (time() - start))


class TestRunner(NoseTestSuiteRunner):
    """Custom test runner; ensures that the test database cluster is up."""

    PG_VERSION = "9.1"
    PG_BIN = "/usr/lib/postgresql/%s/bin" % PG_VERSION

    def setup_test_environment(self, *args, **kwargs):
        """Ensure that `PG_BIN` is in `PATH`."""
        super(TestRunner, self).setup_test_environment(*args, **kwargs)
        pg_bin = self.PG_BIN
        exe_path = environ.get("PATH", "").split(path.pathsep)
        if pg_bin not in exe_path:
            exe_path.insert(0, pg_bin)
            environ["PATH"] = path.pathsep.join(exe_path)

    def setup_databases(self, *args, **kwargs):
        """Fire up the db cluster, then punt to original implementation."""
        if path.isdir("db"):
            self.cluster = None
        else:
            with timing("Database cluster created in %.1f seconds."):
                self.cluster = Cluster()
                self.cluster.initdb()
                self.cluster.start()
                settings.DATABASES["default"]["NAME"] = self.cluster.createdb()
                settings.DATABASES["default"]["HOST"] = self.cluster.dbdir
        return super(TestRunner, self).setup_databases(*args, **kwargs)

    def teardown_databases(self, *args, **kwargs):
        super(TestRunner, self).teardown_databases(*args, **kwargs)
        if self.cluster is not None:
            with timing("Database cluster destroyed in %.1f seconds."):
                self.cluster.stop()
                self.cluster.cleanup()
