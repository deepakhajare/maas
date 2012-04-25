# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Manage a PostgreSQL database service."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type

from contextlib import (
    closing,
    contextmanager,
    )
from os import (
    devnull,
    environ,
    fdopen,
    makedirs,
    path,
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
from time import (
    sleep,
    time,
    )

import psycopg2


PG_VERSION = "9.1"
PG_BIN = "/usr/lib/postgresql/%s/bin" % PG_VERSION


def path_with_pg_bin(exe_path):
    """Ensure that `PG_BIN` is in `PATH`."""
    exe_path = exe_path.split(path.pathsep)
    if PG_BIN not in exe_path:
        exe_path.insert(0, PG_BIN)
    return path.pathsep.join(exe_path)


@contextmanager
def timing(message="%.1f seconds."):
    assert isinstance(message % 1.0, (str, unicode))
    start = time()
    yield lambda: time() - start
    print(message % (time() - start))


class Cluster:

    def __init__(self, datadir):
        self.datadir = path.abspath(datadir)

    def execute(self, *command, **options):
        env = options.pop("env", environ).copy()
        env["PATH"] = path_with_pg_bin(env.get("PATH", ""))
        env["PGDATA"] = self.datadir
        check_call(command, env=env, **options)

    @property
    def exists(self):
        version_file = path.join(self.datadir, "PG_VERSION")
        return path.exists(version_file)

    @property
    def pidfile(self):
        return path.join(self.datadir, "postmaster.pid")

    @property
    def logfile(self):
        return path.join(self.datadir, "backend.log")

    @property
    def running(self):
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
        if not self.exists:
            if not path.isdir(self.datadir):
                makedirs(self.datadir)
            self.execute("pg_ctl", "init", "-s", "-o", "-E utf8 -A trust")

    def start(self):
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
        self.start()
        connection = psycopg2.connect(
            database=database, host=self.datadir)
        connection.autocommit = autocommit
        return connection

    @property
    def databases(self):
        with closing(self.connect("postgres")) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("SELECT datname FROM pg_catalog.pg_database")
                return {name for (name,) in cur.fetchall()}

    def createdb(self, name):
        with closing(self.connect()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("CREATE DATABASE %s" % name)

    def dropdb(self, name):
        with closing(self.connect()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("DROP DATABASE %s" % name)

    def stop(self):
        if self.running:
            # pg_ctl options:
            #  -w -- wait for shutdown to complete.
            #  -m <mode> -- shutdown mode.
            self.execute("pg_ctl", "stop", "-s", "-w", "-m", "fast")

    def destroy(self):
        if self.exists:
            self.stop()
            rmtree(self.datadir)

    @classmethod
    @contextmanager
    def use(cls, datadir):
        cluster = cls(datadir)
        exists = cluster.exists
        running = cluster.running

        if not exists:
            with timing("Cluster created in %.1f seconds."):
                cluster.create()
        if not running:
            with timing("Cluster started in %.1f seconds."):
                cluster.start()
        try:
            yield cluster
        finally:
            if not running:
                with timing("Cluster stopped in %.1f seconds."):
                    cluster.stop()
            if not exists:
                with timing("Cluster destroyed in %.1f seconds."):
                    cluster.destroy()


def touch(filename):
    with open(filename, "ab"):
        pass  # Opening it is enough.


@contextmanager
def database(cluster, name):
    databases = cluster.databases
    marker = path.join(cluster.datadir, "%s-created" % name)
    if name not in databases:
        cluster.createdb(name)
        touch(marker)
    try:
        yield
    finally:
        if name not in databases:
            cluster.dropdb(name)
            unlink(marker)


def setup():
    # Ensure stdout and stderr are line-bufferred.
    sys.stdout = fdopen(sys.stdout.fileno(), "ab", 1)
    sys.stderr = fdopen(sys.stderr.fileno(), "ab", 1)
    # Run the SIGINT handler on SIGTERM; `svc -d` sends SIGTERM.
    signal.signal(signal.SIGTERM, signal.default_int_handler)


def main():
    datadir = path.abspath("db")
    with Cluster.use(datadir) as cluster:
        with database(cluster, "maas"):
            while cluster.running:
                sleep(5.0)


if __name__ == "__main__":
    try:
        setup()
        main()
    except KeyboardInterrupt:
        pass
