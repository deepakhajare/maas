# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Django settings for maas project."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type

from getpass import getuser
import os
from urlparse import urljoin

# Use new style url tag:
# https://docs.djangoproject.com/en/dev/releases/1.3/#changes-to-url-and-ssi
import django.template
from maas import import_local_settings
from metadataserver.address import guess_server_address


django.template.add_to_builtins('django.templatetags.future')

DEBUG = False

# Used to set a prefix in front of every URL.
FORCE_SCRIPT_NAME = None

# Allow the user to override settings in maas_local_settings. Later settings
# depend on the values of DEBUG and FORCE_SCRIPT_NAME, so we must import local
# settings now in case those settings have been overridden.
import_local_settings()

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# Location where python-oops should store errors.
OOPS_REPOSITORY = 'logs/oops'

LOGOUT_URL = '/'
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'

# The MAAS CLI.
MAAS_CLI = 'sudo maas'

# The relative path where a proxy to the Longpoll server can be
# reached.  Longpolling will be disabled in the UI if this is None.
LONGPOLL_PATH = '/longpoll/'

# Default URL specifying protocol, host, and (if necessary) port where
# this MAAS can be found.  Configuration can, and probably should,
# override this.
DEFAULT_MAAS_URL = "http://%s/" % guess_server_address()

if FORCE_SCRIPT_NAME is not None:
    LOGOUT_URL = FORCE_SCRIPT_NAME + LOGOUT_URL
    LOGIN_REDIRECT_URL = FORCE_SCRIPT_NAME + LOGIN_REDIRECT_URL
    LOGIN_URL = FORCE_SCRIPT_NAME + LOGIN_URL
    LONGPOLL_PATH = FORCE_SCRIPT_NAME + LONGPOLL_PATH
    DEFAULT_MAAS_URL = urljoin(DEFAULT_MAAS_URL, FORCE_SCRIPT_NAME)
    # ADMIN_MEDIA_PREFIX will be deprecated in Django 1.4.
    # Admin's media will be served using staticfiles instead.
    ADMIN_MEDIA_PREFIX = FORCE_SCRIPT_NAME

API_URL_REGEXP = '^/api/1[.]0/'
METADATA_URL_REGEXP = '^/metadata/'

YUI_COMBO_URL = "combo/"
# We handle exceptions ourselves (in
# maasserver.middleware.APIErrorsMiddleware)
PISTON_DISPLAY_ERRORS = False

TEMPLATE_DEBUG = DEBUG
YUI_DEBUG = DEBUG
YUI_VERSION = '3.4.1'
STATIC_LOCAL_SERVE = DEBUG

AUTH_PROFILE_MODULE = 'maasserver.UserProfile'

AUTHENTICATION_BACKENDS = (
    'maasserver.models.MAASAuthorizationBackend',
    )

# Rabbit MQ Configuration.
RABBITMQ_HOST = 'localhost'
RABBITMQ_USERID = 'guest'
RABBITMQ_PASSWORD = 'guest'
RABBITMQ_VIRTUAL_HOST = '/'

RABBITMQ_PUBLISH = True


DATABASES = {
    'default': {
        # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' etc.
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'maas',
        'USER': '',
        'PASSWORD': '',
        # For PostgreSQL, a "hostname" starting with a slash indicates a
        # Unix socket directory.
        'HOST': '',
        'PORT': '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'
if FORCE_SCRIPT_NAME is not None:
    STATIC_URL = FORCE_SCRIPT_NAME + STATIC_URL

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'
if FORCE_SCRIPT_NAME is not None:
    ADMIN_MEDIA_PREFIX = FORCE_SCRIPT_NAME + ADMIN_MEDIA_PREFIX

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'zk@qw+fdhu_b4ljx+pmb*8sju4lpx!5zkez%&4hep_(o6y1nf0'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.request",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    #"django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "maasserver.context_processors.yui",
    "maasserver.context_processors.global_options",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ErrorsMiddleware catches ExternalComponentException and redirects.
    # Specialised error handling middleware (like APIErrorsMiddleware)
    # should be placed after it.
    'maasserver.middleware.ErrorsMiddleware',
    'maasserver.middleware.APIErrorsMiddleware',
    'maasserver.middleware.ExternalComponentsMiddleware',
    'metadataserver.middleware.MetadataErrorsMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.csrf.CsrfResponseMiddleware',
    'maasserver.middleware.ExceptionLoggerMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'maasserver.middleware.AccessMiddleware',
)

ROOT_URLCONF = 'maas.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates"
    # or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(__file__), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'maasserver',
    'metadataserver',
    'piston',
    'south',
)

if DEBUG:
    INSTALLED_APPS += (
        'django.contrib.admin',
    )

# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize the logging configuration.
LOGGING = {
    'version': 1,
}

# The location of the Provisioning API XML-RPC endpoint.  This should
# match the setting in etc/pserv.yaml.
PSERV_URL = "http://%s:test@localhost:5241/api" % getuser()

# Time-out for socket operations against the Provisioning API.
PSERV_TIMEOUT = 7.0  # seconds.

# Use a real provisioning server?  If yes, the URL for the provisioning
# server's API should be set in PSERV_URL.  If this is set to False, for
# testing or demo purposes, MAAS will use an internal fake service.
USE_REAL_PSERV = True

# The location of the commissioning script that is executed on nodes as
# part of commissioning.  Only override this if you know what you are
# doing.
COMMISSIONING_SCRIPT = 'etc/maas/commissioning-user-data'

# The duration, in minutes, after which we consider a commissioning node
# to have failed and mark it as FAILED_TESTS.
COMMISSIONING_TIMEOUT = 60

# Location of power action templates. Use an absolute path.
POWER_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "provisioningserver", "power", "templates")

# Allow the user to override settings in maas_local_settings.
import_local_settings()
