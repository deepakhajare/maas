# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Django command: start a database shell.

Overrides the default implementation.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = ['Command']

from django.core.management.commands import dbshell
from django.db import connections, DEFAULT_DB_ALIAS

from maastesting.services.database import ClusterFixture


class Command(dbshell.Command):
    """Customized "dbshell" command."""

    def handle(self, **options):
        connection = connections[options.get('database', DEFAULT_DB_ALIAS)]
        #import pdb; pdb.set_trace()
        cluster = ClusterFixture(
            datadir=connection.settings_dict["host"], preserve=True)
        with cluster:
            cluster.createdb(connection.settings_dict["name"])
            super(Command, self).handle(**options)
