# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Celery settings for the maas project.

Do not edit this file.  Instead, put custom settings in a module named
user_maasceleryconfig.py somewhere on the PYTHONPATH.
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
DHCP_LEASES_FILE = '/var/lib/dhcp/dhcpd.leases'

# ISC dhcpd configuration file.
DHCP_CONFIG_FILE = '/etc/dhcp/dhcpd.conf'


try:
    import user_maasceleryconfig
except ImportError:
    pass
else:
    import_settings(user_maasceleryconfig)


CELERY_IMPORTS = (
    "provisioningserver.tasks",
)

CELERY_ACKS_LATE = True

# Do not store the tasks' return values (aka tombstones);
# This improves performance.
CELERY_IGNORE_RESULT = True


CELERYBEAT_SCHEDULE = {
    # XXX JeroenVermeulen 2012-08-24, bug=1039366: once we have multiple
    # workers, make sure each worker gets one of these.
    'unconditional-dhcp-lease-upload': {
        'task': 'provisioningserver.tasks.upload_dhcp_leases',
        'schedule': timedelta(minutes=1),
    },
}
