# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Django command: Configure master DHCP.

The master DHCP settings apply to the DHCP server running on the MAAS server
itself.  They can be either disabled (if you don't want MAAS to manage DHCP)
or fully configured using this command.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'Command',
    ]

from optparse import make_option

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--clear', dest='clear', action='store_true',
            default=False,
            help="Clear settings.  Do only when MAAS DHCP is disabled."),
      )
    help = "Purpose of this command."

    def handle(self, *args, **options):
        pass
