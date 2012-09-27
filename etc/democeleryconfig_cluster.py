# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Celery demo settings for the maas project: cluster settings."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
)

__metaclass__ = type


import celeryconfig_cluster
import democeleryconfig_common
from maas import import_settings

# Extend base settings.
import_settings(celeryconfig_cluster)

import_settings(democeleryconfig_common)

# This can be removed once the call to
# ./bin/maas-provision start-cluster-controller is in place.
# Right now, it is simply used to override CELERYBEAT_SCHEDULE
# so that the proper queue ('demo-UUID') is used.
from datetime import timedelta
CELERYBEAT_SCHEDULE = {
    'unconditional-dhcp-lease-upload': {
        'task': 'provisioningserver.tasks.upload_dhcp_leases',
        'schedule': timedelta(minutes=1),
        'options': {'queue': 'demo-UUID'},
    },
}
