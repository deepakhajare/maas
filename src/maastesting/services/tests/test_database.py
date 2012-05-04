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

from contextlib import closing
from os import (
    getpid,
    path,
    )
from StringIO import StringIO
from subprocess import CalledProcessError
import sys

from maastesting.services import database
from maastesting.services.database import (
    Cluster,
    ClusterFixture,
    path_with_pg_bin,
    PG_BIN,
    ProcessSemaphore,
    repr_pid,
    )
from maastesting.testcase import TestCase
from testtools.matchers import (
    DirExists,
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


class TestCluster(TestCase):

    make = Cluster

    def test_init(self):
        # The datadir passed into the Cluster constructor is resolved to an
        # absolute path.
        datadir = path.join(self.make_dir(), "locks")
        cluster = self.make(path.relpath(datadir))
        self.assertEqual(datadir, cluster.datadir)

    def patch_check_call(self, returncode=0):
        calls = []

        def check_call(command, **options):
            calls.append((command, options))
            if returncode != 0:
                raise CalledProcessError(returncode, command)

        self.patch(database, "check_call", check_call)
        return calls

    def test_execute(self):
        calls = self.patch_check_call()
        cluster = self.make(self.make_dir())
        cluster.execute("true")
        [(command, options)] = calls
        self.assertEqual(("true",), command)
        self.assertIn("env", options)
        env = options["env"]
        self.assertEqual(cluster.datadir, env.get("PGDATA"))
        self.assertEqual(cluster.datadir, env.get("PGHOST"))
        self.assertThat(
            env.get("PATH", ""),
            StartsWith(PG_BIN + path.pathsep))

    def test_exists(self):
        cluster = self.make(self.make_dir())
        # The PG_VERSION file is used as a marker of existence.
        version_file = path.join(cluster.datadir, "PG_VERSION")
        self.assertThat(version_file, Not(FileExists()))
        self.assertFalse(cluster.exists)
        open(version_file, "wb").close()
        self.assertTrue(cluster.exists)

    def test_pidfile(self):
        self.assertEqual(
            "/some/where/postmaster.pid",
            self.make("/some/where").pidfile)

    def test_logfile(self):
        self.assertEqual(
            "/some/where/backend.log",
            self.make("/some/where").logfile)

    def test_running(self):
        calls = self.patch_check_call(returncode=0)
        cluster = self.make("/some/where")
        self.assertTrue(cluster.running)
        [(command, options)] = calls
        self.assertEqual(("pg_ctl", "status"), command)

    def test_running_not(self):
        self.patch_check_call(returncode=1)
        cluster = self.make("/some/where")
        self.assertFalse(cluster.running)

    def test_running_error(self):
        self.patch_check_call(returncode=2)
        cluster = self.make("/some/where")
        self.assertRaises(
            CalledProcessError, getattr, cluster, "running")

    def test_create(self):
        cluster = self.make(self.make_dir())
        cluster.create()
        self.assertTrue(cluster.exists)
        self.assertFalse(cluster.running)

    def test_start_and_stop(self):
        cluster = self.make(self.make_dir())
        cluster.create()
        try:
            cluster.start()
            self.assertTrue(cluster.running)
        finally:
            cluster.stop()
            self.assertFalse(cluster.running)

    def test_connect(self):
        cluster = self.make(self.make_dir())
        cluster.create()
        self.addCleanup(cluster.stop)
        cluster.start()
        with closing(cluster.connect()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("SELECT 1")
                self.assertEqual([(1,)], cur.fetchall())

    def test_databases(self):
        cluster = self.make(self.make_dir())
        cluster.create()
        self.addCleanup(cluster.stop)
        cluster.start()
        self.assertEqual(
            {"postgres", "template0", "template1"},
            cluster.databases)

    def test_createdb_and_dropdb(self):
        cluster = self.make(self.make_dir())
        cluster.create()
        self.addCleanup(cluster.stop)
        cluster.start()
        cluster.createdb("setherial")
        self.assertEqual(
            {"postgres", "template0", "template1", "setherial"},
            cluster.databases)
        cluster.dropdb("setherial")
        self.assertEqual(
            {"postgres", "template0", "template1"},
            cluster.databases)

    def test_destroy(self):
        cluster = self.make(self.make_dir())
        cluster.create()
        cluster.destroy()
        self.assertFalse(cluster.exists)
        self.assertFalse(cluster.running)
        self.assertThat(cluster.datadir, Not(DirExists()))


class TestClusterFixture(TestCluster):

    def make(self, *args, **kwargs):
        fixture = ClusterFixture(*args, **kwargs)
        # Run the basic fixture set-up so that clean-ups can be added.
        super(ClusterFixture, fixture).setUp()
        return fixture

    def test_init_fixture(self):
        fixture = self.make("/some/where")
        self.assertEqual(False, fixture.preserve)
        self.assertIsInstance(fixture.lock, ProcessSemaphore)
        self.assertEqual(
            path.join(fixture.datadir, "locks"),
            fixture.lock.lockdir)

    def test_createdb_no_preserve(self):
        fixture = self.make(self.make_dir(), preserve=False)
        self.addCleanup(fixture.stop)
        fixture.start()
        fixture.createdb("danzig")
        self.assertIn("danzig", fixture.databases)
        # The database is only created if it does not already exist.
        fixture.createdb("danzig")
        # Creating a database arranges for it to be dropped when stopping the
        # fixture.
        fixture.cleanUp()
        self.assertNotIn("danzig", fixture.databases)

    def test_createdb_preserve(self):
        fixture = self.make(self.make_dir(), preserve=True)
        self.addCleanup(fixture.stop)
        fixture.start()
        fixture.createdb("emperor")
        self.assertIn("emperor", fixture.databases)
        # The database is only created if it does not already exist.
        fixture.createdb("emperor")
        # Creating a database arranges for it to be dropped when stopping the
        # fixture.
        fixture.cleanUp()
        self.assertIn("emperor", fixture.databases)

    def test_dropdb(self):
        fixture = self.make(self.make_dir())
        self.addCleanup(fixture.stop)
        fixture.start()
        # The database is only dropped if it exists.
        fixture.dropdb("diekrupps")
        fixture.dropdb("diekrupps")

    def test_stop_locked(self):
        # The cluster is not stopped if a lock is held.
        fixture = self.make(self.make_dir())
        self.addCleanup(fixture.stop)
        fixture.start()
        fixture.lock.acquire()
        fixture.stop()
        self.assertTrue(fixture.running)
        fixture.lock.release()
        fixture.stop()
        self.assertFalse(fixture.running)

    def test_destroy_locked(self):
        # The cluster is not destroyed if a lock is held.
        fixture = self.make(self.make_dir())
        fixture.create()
        fixture.lock.acquire()
        fixture.destroy()
        self.assertTrue(fixture.exists)
        fixture.lock.release()
        fixture.destroy()
        self.assertFalse(fixture.exists)

    def test_use_no_preserve(self):
        # The cluster is stopped and destroyed when preserve=False.
        with self.make(self.make_dir(), preserve=False) as fixture:
            self.assertTrue(fixture.exists)
            self.assertTrue(fixture.running)
        self.assertFalse(fixture.exists)
        self.assertFalse(fixture.running)

    def test_use_no_preserve_cluster_already_exists(self):
        # The cluster is stopped but *not* destroyed when preserve=False if it
        # existed before the fixture was put into use.
        fixture = self.make(self.make_dir(), preserve=False)
        fixture.create()
        with fixture:
            self.assertTrue(fixture.exists)
            self.assertTrue(fixture.running)
        self.assertTrue(fixture.exists)
        self.assertFalse(fixture.running)

    def test_use_preserve(self):
        # The cluster is not stopped and destroyed when preserve=True.
        with self.make(self.make_dir(), preserve=True) as fixture:
            self.assertTrue(fixture.exists)
            self.assertTrue(fixture.running)
            fixture.createdb("gallhammer")
        self.assertTrue(fixture.exists)
        self.assertFalse(fixture.running)
        self.addCleanup(fixture.stop)
        fixture.start()
        self.assertIn("gallhammer", fixture.databases)


class TestActions(TestCase):

    class Finished(Exception):
        """A marker exception used for breaking out."""

    def test_run(self):
        cluster = ClusterFixture(self.make_dir())
        self.addCleanup(cluster.stop)

        # Instead of sleeping, check the cluster is running, then break out.
        def sleep_patch(time):
            self.assertTrue(cluster.running)
            self.assertIn("maas", cluster.databases)
            raise self.Finished

        self.patch(database, "sleep", sleep_patch)
        self.assertRaises(self.Finished, database.action_run, cluster)

    def test_shell(self):
        cluster = ClusterFixture(self.make_dir())
        self.addCleanup(cluster.stop)

        def shell_patch(database):
            self.assertEqual("maas", database)
            raise self.Finished

        self.patch(cluster, "shell", shell_patch)
        self.assertRaises(self.Finished, database.action_shell, cluster)

    def test_status_running(self):
        cluster = ClusterFixture(self.make_dir())
        self.addCleanup(cluster.stop)
        cluster.start()
        self.patch(sys, "stdout", StringIO())
        code = self.assertRaises(
            SystemExit, database.action_status, cluster).code
        self.assertEqual(0, code)
        self.assertEqual(
            "%s: running\n" % cluster.datadir,
            sys.stdout.getvalue())

    def test_status_not_running(self):
        cluster = ClusterFixture(self.make_dir())
        cluster.create()
        self.patch(sys, "stdout", StringIO())
        code = self.assertRaises(
            SystemExit, database.action_status, cluster).code
        self.assertEqual(1, code)
        self.assertEqual(
            "%s: not running\n" % cluster.datadir,
            sys.stdout.getvalue())

    def test_status_not_created(self):
        cluster = ClusterFixture(self.make_dir())
        self.patch(sys, "stdout", StringIO())
        code = self.assertRaises(
            SystemExit, database.action_status, cluster).code
        self.assertEqual(2, code)
        self.assertEqual(
            "%s: not created\n" % cluster.datadir,
            sys.stdout.getvalue())

    def test_stop(self):
        cluster = ClusterFixture(self.make_dir())
        self.addCleanup(cluster.stop)
        cluster.start()
        database.action_stop(cluster)
        self.assertFalse(cluster.running)
        self.assertTrue(cluster.exists)

    def test_stop_when_locked(self):
        cluster = ClusterFixture(self.make_dir())
        self.addCleanup(cluster.stop)
        cluster.start()
        self.addCleanup(cluster.lock.release)
        cluster.lock.acquire()
        self.patch(sys, "stderr", StringIO())
        error = self.assertRaises(
            SystemExit, database.action_stop, cluster)
        self.assertEqual(2, error.code)
        self.assertThat(
            sys.stderr.getvalue(), StartsWith(
                "%s: cluster is locked by:" % cluster.datadir))
        self.assertTrue(cluster.running)

    def test_destroy(self):
        cluster = ClusterFixture(self.make_dir())
        self.addCleanup(cluster.stop)
        cluster.start()
        database.action_destroy(cluster)
        self.assertFalse(cluster.running)
        self.assertFalse(cluster.exists)

    def test_destroy_when_locked(self):
        cluster = ClusterFixture(self.make_dir())
        cluster.create()
        cluster.lock.acquire()
        self.patch(sys, "stderr", StringIO())
        error = self.assertRaises(
            SystemExit, database.action_destroy, cluster)
        self.assertEqual(2, error.code)
        self.assertThat(
            sys.stderr.getvalue(), StartsWith(
                "%s: cluster is locked by:" % cluster.datadir))
        self.assertTrue(cluster.exists)
