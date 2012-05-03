# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Manage a PostgreSQL database service."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "Cluster",
    "ClusterFixture",
    ]

import argparse
from contextlib import closing
from errno import (
    EEXIST,
    ENOENT,
    ENOTEMPTY,
    )
from os import (
    devnull,
    environ,
    fdopen,
    getpid,
    makedirs,
    path,
    rmdir,
    unlink,
    )
import pipes
from shutil import rmtree
import signal
from subprocess import (
    CalledProcessError,
    check_call,
    )
import sys
from time import sleep

from fixtures import Fixture
import psycopg2


PG_VERSION = "9.1"
PG_BIN = "/usr/lib/postgresql/%s/bin" % PG_VERSION


def path_with_pg_bin(exe_path):
    """Return `exe_path` with `PG_BIN` added."""
    exe_path = exe_path.split(path.pathsep)
    if PG_BIN not in exe_path:
        exe_path.insert(0, PG_BIN)
    return path.pathsep.join(exe_path)


class Cluster:
    """Represents a PostgreSQL cluster, running or not."""

    def __init__(self, datadir):
        self.datadir = path.abspath(datadir)

    def execute(self, *command, **options):
        """Execute a command with an environment suitable for this cluster."""
        env = options.pop("env", environ).copy()
        env["PATH"] = path_with_pg_bin(env.get("PATH", ""))
        env["PGDATA"] = env["PGHOST"] = self.datadir
        check_call(command, env=env, **options)

    @property
    def exists(self):
        """Whether or not this cluster exists on disk."""
        version_file = path.join(self.datadir, "PG_VERSION")
        return path.exists(version_file)

    @property
    def pidfile(self):
        """The (expected) pidfile for a running cluster.

        Does *not* guarantee that the pidfile exists.
        """
        return path.join(self.datadir, "postmaster.pid")

    @property
    def logfile(self):
        """The log file used (or will be used) by this cluster."""
        return path.join(self.datadir, "backend.log")

    @property
    def running(self):
        """Whether this cluster is running or not."""
        with open(devnull, "rb") as null:
            try:
                self.execute("pg_ctl", "status", stdout=null)
            except CalledProcessError, error:
                if error.returncode == 1:
                    return False
                else:
                    raise
            else:
                return True

    def create(self):
        """Create this cluster, if it does not exist."""
        if not self.exists:
            if not path.isdir(self.datadir):
                makedirs(self.datadir)
            self.execute("pg_ctl", "init", "-s", "-o", "-E utf8 -A trust")

    def start(self):
        """Start this cluster, if it's not already started."""
        if not self.running:
            self.create()
            # pg_ctl options:
            #  -l <file> -- log file.
            #  -s -- no informational messages.
            #  -w -- wait until startup is complete.
            # postgres options:
            #  -h <arg> -- host name; empty arg means Unix socket only.
            #  -F -- don't bother fsync'ing.
            #  -k -- socket directory.
            self.execute(
                "pg_ctl", "start", "-l", self.logfile, "-s", "-w",
                "-o", "-h '' -F -k %s" % pipes.quote(self.datadir))

    def connect(self, database="template1", autocommit=True):
        """Connect to this cluster.

        Starts the cluster if necessary.
        """
        self.start()
        connection = psycopg2.connect(
            database=database, host=self.datadir)
        connection.autocommit = autocommit
        return connection

    @property
    def databases(self):
        """The names of databases in this cluster."""
        with closing(self.connect("postgres")) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("SELECT datname FROM pg_catalog.pg_database")
                return {name for (name,) in cur.fetchall()}

    def createdb(self, name):
        """Create the named database."""
        with closing(self.connect()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("CREATE DATABASE %s" % name)

    def dropdb(self, name):
        """Drop the named database."""
        with closing(self.connect()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("DROP DATABASE %s" % name)

    def stop(self):
        """Stop this cluster, if started."""
        if self.running:
            # pg_ctl options:
            #  -w -- wait for shutdown to complete.
            #  -m <mode> -- shutdown mode.
            self.execute("pg_ctl", "stop", "-s", "-w", "-m", "fast")

    def destroy(self):
        """Destroy this cluster, if it exists.

        The cluster will be stopped if it's started.
        """
        if self.exists:
            self.stop()
            rmtree(self.datadir)


class ClusterFixture(Cluster, Fixture):
    """A fixture for a `Cluster`."""

    def __init__(self, datadir, leave=False):
        """
        @param leave: Leave the cluster and its databases behind, even if this
            fixture creates them.
        """
        super(ClusterFixture, self).__init__(datadir)
        self.leave = leave

    @property
    def lockdir(self):
        return path.join(self.datadir, "locks")

    @property
    def lockfile(self):
        return path.join(self.lockdir, "%d" % getpid())

    def lock(self):
        # Declare self as a user.
        try:
            makedirs(self.lockdir)
        except OSError, error:
            if error.errno != EEXIST:
                raise
        open(self.lockfile, "w").close()

    def unlock(self):
        # Remove self as a user.
        try:
            unlink(self.lockfile)
        except OSError, error:
            if error.errno != ENOENT:
                raise

    @property
    def locked(self):
        try:
            rmdir(self.lockdir)
        except OSError, error:
            if error.errno == ENOTEMPTY:
                return True
            elif error.errno == ENOENT:
                return False
            else:
                raise
        else:
            return False

    def setUp(self):
        super(ClusterFixture, self).setUp()
        if not self.leave:
            self.addCleanup(self.destroy)
        self.create()
        self.addCleanup(self.stop)
        self.start()
        self.addCleanup(self.unlock)
        self.lock()

    def createdb(self, name):
        """Create the named database if it does not exist already.

        Arranges to drop the named database during clean-up, unless `leave`
        has been specified.
        """
        if name not in self.databases:
            super(ClusterFixture, self).createdb(name)
            if not self.leave:
                self.addCleanup(self.dropdb, name)

    def dropdb(self, name):
        """Drop the named database if it exists."""
        if name in self.databases:
            super(ClusterFixture, self).dropdb(name)

    def stop(self):
        if not self.locked:
            super(ClusterFixture, self).stop()

    def destroy(self):
        if not self.locked:
            super(ClusterFixture, self).destroy()


def setup():
    # Ensure stdout and stderr are line-bufferred.
    sys.stdout = fdopen(sys.stdout.fileno(), "ab", 1)
    sys.stderr = fdopen(sys.stderr.fileno(), "ab", 1)
    # Run the SIGINT handler on SIGTERM; `svc -d` sends SIGTERM.
    signal.signal(signal.SIGTERM, signal.default_int_handler)


def action_run(cluster):
    """Create and run a cluster."""
    with cluster:
        cluster.createdb("maas")
        while cluster.running:
            sleep(5.0)


def action_shell(cluster):
    """Spawn a ``psql`` shell for `maas` in the cluster."""
    with cluster:
        cluster.createdb("maas")
        cluster.execute("psql", "--", "maas")


def action_stop(cluster):
    """Stop a cluster."""
    cluster.stop()


actions = {
    "run": action_run,
    "shell": action_shell,
    "stop": action_stop,
    }


argument_parser = argparse.ArgumentParser(description=__doc__)
argument_parser.add_argument(
    "action", choices=sorted(actions), nargs="?", default="shell",
    help="the action to perform (default: %(default)s)")
argument_parser.add_argument(
    "-D", "--datadir", dest="datadir", action="store_true",
    default="db", help=(
        "the directory in which to place, or find, the cluster "
        "(default: %(default)s)"))
argument_parser.add_argument(
    "--leave", dest="leave", action="store_true",
    default=False, help=(
        "leave the cluster and its databases behind, even if it "
        "was necessary to create it (default: %(default)s)"))


def main(args=None):
    args = argument_parser.parse_args(args)
    try:
        setup()
        action = actions[args.action]
        cluster = ClusterFixture(
            datadir=args.datadir, leave=args.leave)
        action(cluster)
    except CalledProcessError, error:
        raise SystemExit(error.returncode)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
