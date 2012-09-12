# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Commands relating to the MAAS API."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "cmd_api_describe",
    ]

import json
import os
import urllib2
from urlparse import urljoin

from apiclient.utils import ascii_url
from commandant.commands import Command
import yaml


def ensure_trailing_slash(string):
    """Ensure that `string` has a trailing forward-slash."""
    slash = b"/" if isinstance(string, bytes) else u"/"
    return (string + slash) if not string.endswith(slash) else string


# TODO: Change default; this one's for development.
MAAS_API_URL = os.environ.get(
    "MAAS_API_URL", "http://localhost:5243/api/1.0/")
MAAS_API_URL = ensure_trailing_slash(MAAS_API_URL)
MAAS_API_URL = ascii_url(MAAS_API_URL)

# This is dumber than a bag of wet mice, but it's a start.
MAAS_API_DESCRIPTION_URL = urljoin(MAAS_API_URL, "describe")
MAAS_API_DESCRIPTION_URL = ascii_url(MAAS_API_DESCRIPTION_URL)
MAAS_API_DESCRIPTION = json.loads(
    urllib2.urlopen(MAAS_API_DESCRIPTION_URL).read())


class cmd_api_describe(Command):
    """Describe the MAAS API referred to by `MAAS_API_URL`."""

    def run(self):
        yaml.safe_dump(MAAS_API_DESCRIPTION, stream=self.outf)
