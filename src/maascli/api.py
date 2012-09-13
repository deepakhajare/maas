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

import httplib
import json
import os
import re
from urllib import urlencode
from urllib2 import urlopen
from urlparse import (
    urljoin,
    urlparse,
    )

from apiclient.creds import convert_string_to_tuple
from apiclient.maas_client import MAASOAuth
from apiclient.multipart import encode_multipart_data
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

MAAS_API_CREDENTIALS = os.environ.get("MAAS_API_CREDENTIALS")

# This is dumber than a bag of wet mice, but it's a start.
MAAS_API_DESCRIPTION_URL = urljoin(MAAS_API_URL, "describe/")
MAAS_API_DESCRIPTION_URL = ascii_url(MAAS_API_DESCRIPTION_URL)
MAAS_API_DESCRIPTION = json.load(urlopen(MAAS_API_DESCRIPTION_URL))


class cmd_api_describe(Command):
    """Describe the MAAS API referred to by `MAAS_API_URL`."""

    def run(self):
        yaml.safe_dump(MAAS_API_DESCRIPTION, stream=self.outf)


class APICommand(Command):
    """A generic MAAS API command.

    This is used as a base for creating more specific commands; see
    `gen_api_commands`.
    """

    actions = []
    takes_args = ["action", "data*"]

    def get_action(self, action):
        """Return the action specification for the given name.

        :raises LookupError: if the named action is not found.
        """
        try:
            return next(
                act for act in self.actions
                if act.get("name") == action)
        except StopIteration:
            raise LookupError(
                "%s: cannot '%s'" % (self.name(), action))

    def run(self, action, data_list, **params):
        # Look for the action first.
        action = self.get_action(action)

        # TODO: this is el-cheapo URI Template
        # <http://tools.ietf.org/html/rfc6570> support; use uritemplate-py
        # <https://github.com/uri-templates/uritemplate-py> here?
        uri = self.uri.format(**params)

        if data_list is None:
            data = dict()
        else:
            data = dict(item.split("=", 1) for item in data_list)

        op = action["op"]
        if op is not None:
            data["op"] = op

        method = action["method"]
        restful = action["restful"]

        if method == "POST" and not restful:
            # Encode the data as multipart for non-ReSTful POST requests; all
            # others should use query parameters. TODO: encode_multipart_data
            # insists on a dict for the data, which prevents specifying
            # multiple values for a field, like mac_addresses.  This needs to
            # be fixed.
            body, headers = encode_multipart_data(data, {})
        else:
            # TODO: deal with state information, i.e. where to stuff CRUD
            # data, content types, etc.
            body, headers = None, {}
            # TODO: smarter merging of data with query.
            uri = urlparse(uri)._replace(query=urlencode(data)).geturl()

        # Sign request if credentials have been provided.
        if MAAS_API_CREDENTIALS is not None:
            creds = convert_string_to_tuple(MAAS_API_CREDENTIALS)
            auth = MAASOAuth(*creds)
            auth.sign_request(uri, headers)

        # Use httplib2 instead of urllib2 (or MAASDispatcher, which is based
        # on urllib2) so that we get full control over HTTP method. TODO:
        # create custom MAASDispatcher to use httplib2 so that MAASClient can
        # be used.
        http = httplib2.Http()
        response, content = http.request(
            uri, method, body=body, headers=headers)

        if (response["content-type"] == "application/json" or
            response["content-type"].startswith("application/json;")):
            content = json.loads(content)

        self.report(
            {"response": vars(response),
             "headers": dict(response),
             "content": content})

        if response.status != httplib.OK:
            raise SystemExit(2)

    def report(self, contents):
        yaml.safe_dump(contents, stream=self.outf)


def gen_api_commands(api):
    """Manufacture command classes based on an API description document."""
    for handler in api["handlers"]:
        actions = handler["actions"]
        params = handler["params"]
        name = handler["name"]
        command = type(
            b"cmd_api_" + handler_command_name(name), (APICommand,), {
                "__doc__": handler["doc"],
                "actions": APICommand.actions + actions,
                "takes_args": APICommand.takes_args + params,
                "uri": handler["uri"],
                }
            )
        yield command.__name__, command


# Generate command classes into the module's namespace, ready to be discovered
# by CommandController.load_module().
globals().update(gen_api_commands(MAAS_API_DESCRIPTION))
