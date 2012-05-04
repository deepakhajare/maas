# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maastesting.services.database."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from os import (
    getpid,
    path,
    )

from maastesting.services.database import (
    path_with_pg_bin,
    PG_BIN,
    ProcessSemaphore,
    repr_pid,
    )
from maastesting.testcase import TestCase
from testtools.matchers import (
    FileExists,
    Not,
    StartsWith,
    )


class TestFunctions(TestCase):

    def test_path_with_pg_bin(self):
        self.assertEqual(PG_BIN, path_with_pg_bin(""))
        self.assertEqual(
            PG_BIN + path.pathsep + "/bin:/usr/bin",
            path_with_pg_bin("/bin:/usr/bin"))

    def test_repr_pid_not_a_number(self):
        self.assertEqual("alice", repr_pid("alice"))
        self.assertEqual("'alice and bob'", repr_pid("alice and bob"))

    def test_repr_pid_not_a_process(self):
        self.assertEqual("0 (*unknown*)", repr_pid(0))

    def test_repr_pid_this_process(self):
        pid = getpid()
        self.assertThat(repr_pid(pid), StartsWith("%d (" % pid))


class TestProcessSemaphore(TestCase):

    def test_init(self):
        lockdir = self.make_dir()
        psem = ProcessSemaphore(lockdir)
        self.assertEqual(lockdir, psem.lockdir)
        self.assertEqual(
            path.join(lockdir, "%s" % getpid()),
            psem.lockfile)

    def test_acquire(self):
        psem = ProcessSemaphore(
            path.join(self.make_dir(), "locks"))
        psem.acquire()
        self.assertThat(psem.lockfile, FileExists())
        self.assertTrue(psem.locked)
        self.assertEqual([getpid()], psem.locked_by)

    def test_release(self):
        psem = ProcessSemaphore(
            path.join(self.make_dir(), "locks"))
        psem.acquire()
        psem.release()
        self.assertThat(psem.lockfile, Not(FileExists()))
        self.assertFalse(psem.locked)
        self.assertEqual([], psem.locked_by)
