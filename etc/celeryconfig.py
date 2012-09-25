# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Celery settings for the maas project.

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

from maas import import_settings

# Location of power action templates.  Use an absolute path, or leave as
# None to use the templates installed with the running version of MAAS.
POWER_TEMPLATES_DIR = None

# Location of PXE config templates.  Use an absolute path, or leave as
# None to use the templates installed with the running version of MAAS.
PXE_TEMPLATES_DIR = None

# Location of MAAS' bind configuration files.
DNS_CONFIG_DIR = '/etc/bind/maas'

# RNDC port to be configured by MAAS to communicate with the BIND
# server.
DNS_RNDC_PORT = 954

# DHCP leases file, as maintained by ISC dhcpd.
DHCP_LEASES_FILE = '/var/lib/maas/dhcpd.leases'

# ISC dhcpd configuration file.
DHCP_CONFIG_FILE = '/etc/maas/dhcpd.conf'

# List of interfaces that the dhcpd should service (if managed by MAAS).
DHCP_INTERFACES_FILE = '/var/lib/maas/dhcpd-interfaces'

# Broker connection information.  This is read by the region controller
# and sent to connecting cluster controllers.
# The cluster controllers currently read this same configuration file,
# but the broker URL they receive from the region controller overrides
# this setting.
BROKER_URL = 'amqp://guest:guest@localhost:5672//'


WORKER_QUEUE_DNS = 'celery'
WORKER_QUEUE_BOOT_IMAGES = 'celery'
WORKER_QUEUE_CLUSTER = 'celery'

try:
    import maas_local_celeryconfig
except ImportError:
    pass
else:
    import_settings(maas_local_celeryconfig)


# Each cluster should have its own queue created automatically by Celery.
CELERY_CREATE_MISSING_QUEUES = True


CELERY_IMPORTS = (
    # Tasks.
    "provisioningserver.tasks",

    # This import is needed for its side effect: it initializes the
    # cache that allows workers to share data.
    "provisioningserver.initialize_cache",
    )

CELERY_ACKS_LATE = True

# Do not store the tasks' return values (aka tombstones);
# This improves performance.
CELERY_IGNORE_RESULT = True


CELERYBEAT_SCHEDULE = {
    'unconditional-dhcp-lease-upload': {
        'task': 'provisioningserver.tasks.upload_dhcp_leases',
        'schedule': timedelta(minutes=1),
        'options': {'queue': WORKER_QUEUE_CLUSTER},
    },

    'report-boot-images': {
        'task': 'provisioningserver.tasks.report_boot_images',
        'schedule': timedelta(minutes=5),
        'options': {'queue': WORKER_QUEUE_BOOT_IMAGES},
    },
}
