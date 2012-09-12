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
import re
from urllib2 import urlopen
from urlparse import urljoin

from apiclient.maas_client import MAASOAuth
from apiclient.utils import ascii_url
from commandant.commands import Command
import httplib2
import yaml


def ensure_trailing_slash(string):
    """Ensure that `string` has a trailing forward-slash."""
    slash = b"/" if isinstance(string, bytes) else u"/"
    return (string + slash) if not string.endswith(slash) else string


re_camelcase = re.compile(
    r"([A-Z]*[a-z0-9]+)(?:(?=[^a-z0-9])|\Z)")


def handler_command_name(string):
    string = string if isinstance(string, bytes) else string.encode("ascii")
    parts = re_camelcase.findall(string)
    parts = (part.lower() for part in parts)
    parts = (part for part in parts if part != b"handler")
    return b"_".join(parts)


# TODO: Change default; this one's for development.
MAAS_API_URL = os.environ.get(
    "MAAS_API_URL", "http://localhost:5243/api/1.0/")
MAAS_API_URL = ensure_trailing_slash(MAAS_API_URL)
MAAS_API_URL = ascii_url(MAAS_API_URL)

# This is dumber than a bag of wet mice, but it's a start.
MAAS_API_DESCRIPTION_URL = urljoin(MAAS_API_URL, "describe/")
MAAS_API_DESCRIPTION_URL = ascii_url(MAAS_API_DESCRIPTION_URL)
MAAS_API_DESCRIPTION = json.load(urlopen(MAAS_API_DESCRIPTION_URL))


class cmd_api_describe(Command):
    """Describe the MAAS API referred to by `MAAS_API_URL`."""

    def run(self):
        yaml.safe_dump(MAAS_API_DESCRIPTION, stream=self.outf)


class APICommand(Command):

    actions = []
    takes_args = ["action"]

    def run(self, action, **params):
        try:
            # TODO: this does not find CRUD actions because they don't
            # currently have an "op" parameter.
            action = next(
                act for act in self.actions
                if act.get("op") == action)
        except StopIteration:
            raise LookupError(
                "%s: cannot '%s'" % (self.name(), action))

        # TODO: get rid of this.
        #yaml.safe_dump(action, stream=self.outf)

        method = action["method"]
        uri = action["uri"].format(**params)
        headers = {}

        auth = MAASOAuth("key", "token", "secret")
        auth.sign_request(uri, headers)

        print(method, uri, headers)

        http = httplib2.Http()
        response, content = http.request(uri, method, headers=headers)

        print(headers, response, content)


def gen_api_commands(api):
    for handler in api["handlers"]:
        actions = handler["actions"]
        # TODO: all uri_params for a handler are the same, so the description
        # ought not to specify them for every action.
        params = actions[0]["uri_params"]
        name = handler["name"]
        command = type(
            b"cmd_api_" + handler_command_name(name), (APICommand,), {
                "__doc__": handler["doc"],
                "actions": APICommand.actions + actions,
                "takes_args": APICommand.takes_args + params,
                }
            )
        yield command.__name__, command


globals().update(gen_api_commands(MAAS_API_DESCRIPTION))
