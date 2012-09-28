# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Celery settings for the region controller.

Do not edit this file.  Instead, put custom settings in a module named
maas_local_celeryconfig.py somewhere on the PYTHONPATH.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
)

__metaclass__ = type

from datetime import timedelta

import celeryconfig_common
from maas import import_settings

WORKER_QUEUE_BOOT_IMAGES = None

import_settings(celeryconfig_common)

try:
    import maas_local_celeryconfig
except ImportError:
    pass
else:
    import_settings(maas_local_celeryconfig)


CELERYBEAT_SCHEDULE = {
    'report-boot-images': {
        'task': 'provisioningserver.tasks.report_boot_images',
        'schedule': timedelta(minutes=5),
        'options': {'queue': WORKER_QUEUE_BOOT_IMAGES},
    },
}
