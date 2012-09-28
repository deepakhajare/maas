# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Celery demo settings for the maas project: region settings."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
)

__metaclass__ = type


import celeryconfig
import democeleryconfig_common
from maas import import_settings

# Extend base settings.
import_settings(celeryconfig)

import_settings(democeleryconfig_common)



