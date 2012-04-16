# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Django command: access the development database directly in SQL."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = ['Command']

from subprocess import check_call

from django.core.management.base import (
    BaseCommand,
    CommandError,
    )


class Command(BaseCommand):
    """Custom django command: access the local development database directly.

    Executes an SQL statement given on the command line, or opens an SQL
    shell if no statement was given.
    """

    args = "[SQL statement]"
    help = "Access the database directly in SQL."

    def handle(self, *args, **kwargs):
        if len(args) > 1:
            raise CommandError("Too many arguments.")
        elif len(args) == 1:
            subcommand = 'query'
        else:
            subcommand = 'shell'
        check_call(
            ['utilities/maasdb', subcommand, 'db'] + list(args))
