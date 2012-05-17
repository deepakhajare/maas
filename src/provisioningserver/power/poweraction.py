# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Actions for power-related operations."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "PowerAction",
    "UnknownPowerType",
    ]


import os

from django.conf import settings


class UnknownPowerType(Exception):
    """Raised when trying to process an unknown power type."""


class PowerAction:
    """Actions for power-related operations."""

    def __init__(self, power_type):
        basedir = settings.POWER_TEMPLATES_DIR
        path = os.path.join(basedir, power_type + ".template")
        if not os.path.exists(path):
            raise UnknownPowerType
        with open(path, "r") as f:
            pass

        self.power_type = power_type
        
