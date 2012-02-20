# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Context processors."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "yui",
    ]

from django.conf import settings
from django.contrib.sites.models import Site


def yui(context):
    return {
        'YUI_DEBUG': settings.YUI_DEBUG,
        'YUI_VERSION': settings.YUI_VERSION,
    }

def site(context):
    return {'site': Site.objects.get_current()}
