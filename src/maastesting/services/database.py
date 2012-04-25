# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Manage a PostgreSQL database service."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type

from contextlib import contextmanager
from os import (
    environ,
    path,
    symlink,
    unlink,
    )
import signal
from time import (
    sleep,
    time,
    )

import psycopg2
from van.pg import Cluster


PG_VERSION = "9.1"
PG_BIN = "/usr/lib/postgresql/%s/bin" % PG_VERSION


@contextmanager
def timing(message="%.1f seconds."):
    start = time()
    yield lambda: time() - start
    print(message % (time() - start))


def setup_environment():
    """Ensure that `PG_BIN` is in `PATH`, and catch `SIGTERM`."""
    pg_bin = PG_BIN
    exe_path = environ.get("PATH", "").split(path.pathsep)
    if pg_bin not in exe_path:
        exe_path.insert(0, pg_bin)
        environ["PATH"] = path.pathsep.join(exe_path)
    # Run the SIGINT handler on SIGTERM.
    signal.signal(signal.SIGTERM, signal.default_int_handler)


@contextmanager
def cluster(dbdir):
    with timing("Database cluster created in %.1f seconds."):
        cluster = Cluster()
        cluster.initdb()
        cluster.start()
        cluster.pidfile = path.join(
            cluster.dbdir, "postmaster.pid")
    try:
        yield cluster
    finally:
        with timing("Database cluster destroyed in %.1f seconds."):
            cluster.stop()
            cluster.cleanup()


@contextmanager
def symlinked(src, dst):
    symlink(src, dst)
    try:
        yield
    finally:
        unlink(dst)


def execute(cluster, query, parameters=None):
    conn = psycopg2.connect(database="template1", host=cluster.dbdir)
    try:
        conn.autocommit = True
        conn.cursor().execute(query, parameters)
    finally:
        conn.close()


@contextmanager
def database(cluster, name):
    with timing("Database '%s' created in %%.1f seconds." % name):
        execute(cluster, "CREATE DATABASE %s" % name)
        marker = path.join(cluster.dbdir, "%s-created" % name)
        with open(marker, "wb") as fd:
            fd.write(path.abspath(__file__))
    try:
        yield
    finally:
        with timing("Database '%s' dropped in %%.1f seconds." % name):
            execute(cluster, "DROP DATABASE %s" % name)
            unlink(marker)


def main():
    dbdir = path.abspath("db")

    if path.exists(dbdir):
        raise SystemExit(
            "Database cluster already exists at %s." % dbdir)
    elif path.islink(dbdir):
        # Get rid of dangling symlink.
        unlink(dbdir)

    setup_environment()

    with cluster(dbdir) as c:
        with database(c, "maas"):
            with symlinked(c.dbdir, dbdir):
                while path.exists(c.pidfile):
                    sleep(5.0)


if __name__ == "__main__":
    # Run the bloomin' thing.
    try:
        main()
    except KeyboardInterrupt:
        pass
