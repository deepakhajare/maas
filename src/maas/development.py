# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Django DEVELOPMENT settings for maas project."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type

import os
from socket import gethostname

from maas import (
    import_local_settings,
    import_settings,
    settings,
    )

# We expect the following settings to be overridden. They are mentioned here
# to silence lint warnings.
INSTALLED_APPS = None

# Extend base settings.
import_settings(settings)

# In development, django can be accessed directly on port 5240.
DEFAULT_MAAS_URL = "http://%s:5240/" % gethostname()

# Use our custom test runner, which makes sure that a local database
# cluster is running in the branch.
TEST_RUNNER = 'maastesting.runner.TestRunner'

# Invalid strings should be visible.
TEMPLATE_STRING_IF_INVALID = '#### INVALID STRING ####'

DEBUG = True
TEMPLATE_DEBUG = DEBUG
YUI_DEBUG = DEBUG
STATIC_LOCAL_SERVE = True

DATABASES = {
    'default': {
        # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' etc.
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'maas',
        # For PostgreSQL, a "hostname" starting with a slash indicates a
        # Unix socket directory.
        'HOST': '%s/db' % os.getcwd(),
    }
}

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(os.getcwd(), "media/development")

# The absolute path to the directory containing the Raphael JavaScript library.
RAPHAEL_ROOT = '/usr/share/javascript/raphael'

INSTALLED_APPS += (
    'django.contrib.admin',
    'maastesting',
    'debug_toolbar',
    'django_nose',
)

INTERNAL_IPS = ('127.0.0.1',)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    }

# Allow the user to override settings in maas_local_settings.
import_local_settings()
