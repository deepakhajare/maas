# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Django DEMO settings for maas project."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type

import os

from maas import (
    development,
    import_settings,
    settings,
    )

# We expect the following settings to be overridden. They are mentioned here
# to silence lint warnings.
MIDDLEWARE_CLASSES = None

# Extend base and development settings.
import_settings(settings)
import_settings(development)

MEDIA_ROOT = os.path.join(os.getcwd(), "media/demo")

MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

# In dev mode: Django should act as a proxy to txlongpoll.
LONGPOLL_SERVER_URL = "http://localhost:5242/"

# Enable longpoll. Set LONGPOLL_PATH to None to disable it.
LONGPOLL_PATH = '/longpoll/'

# For demo purposes, use a real provisioning server.
USE_REAL_PSERV = True

MAAS_CLI = os.path.join(os.getcwd(), 'bin', 'maas')

RABBITMQ_PUBLISH = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'maas': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'propagate': True,
        },
     }
}
