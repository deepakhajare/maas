# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SQL Sequence."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'Sequence',
    'INT_MAX',
    ]


from django.db import (
    connection,
    transaction,
    )


BIBINT_MAX = 2 ** 63 - 1

INT_MAX = 2 ** 32 - 1


class Sequence:
    """SQL sequence."""

    def __init__(self, name, incr=1, minvalue=1, maxvalue=BIBINT_MAX):
        self.name = name
        self.incr = incr
        self.minvalue = minvalue
        self.maxvalue = maxvalue

    def create(self):
        cursor = connection.cursor()
        query = "CREATE SEQUENCE %s" % self.sequence_name
        cursor.execute(
            query + " INCREMENT BY %s MINVALUE %s MAXVALUE %s CYCLE",
            [self.incr, self.minvalue, self.maxvalue])
        transaction.commit_unless_managed()

    def nextval(self):
        cursor = connection.cursor()
        cursor.execute(
            "SELECT nextval(%s)", [self.sequence_name])
        return cursor.fetchone()[0]

    def delete(self):
        cursor = connection.cursor()
        cursor.execute(
            "DROP SEQUENCE %s" % self.sequence_name)
        transaction.commit_unless_managed()

    @property
    def sequence_name(self):
        return 'maasserver_%s_custom_seq' % self.name
