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
    "command_module",
    ]

from glob import iglob
import httplib
import json
import new
import os
from os.path import (
    exists,
    expanduser,
    isdir,
    join,
    )
import re
from urllib import urlencode
from urlparse import (
    urljoin,
    urlparse,
    )

from apiclient.creds import convert_string_to_tuple
from apiclient.maas_client import MAASOAuth
from apiclient.multipart import encode_multipart_data
from apiclient.utils import ascii_url
from bzrlib.errors import BzrCommandError
from bzrlib.option import Option
from commandant.commands import Command
import httplib2
import lockfile
import yaml


dotdir = expanduser("~/.maascli")
dotlock = lockfile.FileLock("%s.lock" % dotdir)


re_camelcase = re.compile(
    r"([A-Z]*[a-z0-9]+)(?:(?=[^a-z0-9])|\Z)")


def safe_name(string):
    """Return a munged version of string, suitable as an ASCII filename."""
    return "-".join(re_camelcase.findall(string))


def ensure_trailing_slash(string):
    """Ensure that `string` has a trailing forward-slash."""
    slash = b"/" if isinstance(string, bytes) else u"/"
    return (string + slash) if not string.endswith(slash) else string


class cmd_login(Command):
    """Log-in to a remote API, storing its description and credentials."""

    takes_args = ("profile_name", "url")
    takes_options = (
        Option("credentials", type=unicode, short_name="c"),
        )

    def run(self, profile_name, url, credentials=None):
        profile_path = join(
            dotdir, "%s.profile" % safe_name(profile_name))
        # Ensure that the credentials have a valid form.
        if credentials is not None:
            credentials = convert_string_to_tuple(credentials)
        # Don't allow any concurrency beyond this point.
        with dotlock:
            if exists(profile_path):
                raise BzrCommandError(
                    "Already logged-in to %s." % profile_name)
            if not isdir(dotdir):
                os.mkdir(dotdir, 0700)

            url = ensure_trailing_slash(url)
            url_describe = urljoin(url, "describe/")

            http = httplib2.Http()
            response, content = http.request(
                ascii_url(url_describe), "GET")

            if response.status != httplib.OK:
                raise BzrCommandError(
                    "{0.status} {0.reason}:\n{1}".format(response, content))

            profile = {
                "credentials": credentials,
                "description": json.loads(content),
                "name": profile_name,
                "url": url,
                }

            with open(profile_path, "wb") as stream:
                yaml.safe_dump(profile, stream=stream)


class cmd_logout(Command):
    """Log-out of a remote API, purging any stored credentials."""

    takes_args = ["profile_name"]

    def run(self, profile_name):
        profile_path = join(
            dotdir, "%s.profile" % safe_name(profile_name))
        with dotlock:
            if exists(profile_path):
                os.remove(profile_path)


class APICommand(Command):
    """A generic MAAS API command.

    This is used as a base for creating more specific commands; see
    `gen_profile_commands`.
    """

    # See `cmd_login` and `cmd_logout`.
    profile = None

    # Override these in subclasses; see `gen_profile_commands`.
    actions = []
    takes_args = ["action", "...", "data*"]

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
            # TODO: make encode_multipart_data work with arbitrarily encoded
            # strings; atm, it blows up when encountering a non-ASCII string.
        else:
            # TODO: deal with state information, i.e. where to stuff CRUD
            # data, content types, etc.
            body, headers = None, {}
            # TODO: smarter merging of data with query.
            uri = urlparse(uri)._replace(query=urlencode(data)).geturl()

        # Sign request if credentials have been provided.
        credentials = self.profile["credentials"]
        if credentials is not None:
            auth = MAASOAuth(*credentials)
            auth.sign_request(uri, headers)

        # Use httplib2 instead of urllib2 (or MAASDispatcher, which is based
        # on urllib2) so that we get full control over HTTP method. TODO:
        # create custom MAASDispatcher to use httplib2 so that MAASClient can
        # be used.
        http = httplib2.Http()
        response, content = http.request(
            uri, method, body=body, headers=headers)

        # TODO: parse the content type with a little more elegance.
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


def handler_command_name(string):
    """Create a handler command name from an arbitrary string.

    Camel-case parts of string will be extracted, converted to lowercase,
    joined with underscores, and the rest discarded. The term "handler" will
    also be removed if discovered amongst the aforementioned parts.
    """
    parts = re_camelcase.findall(string)
    parts = (part.lower().encode("ascii") for part in parts)
    parts = (part for part in parts if part != b"handler")
    return b"_".join(parts)


def gen_profile_commands(profile):
    """Manufacture command classes based on an API profile."""
    prefix = profile["name"].encode("ascii")
    description = profile["description"]
    for handler in description["handlers"]:
        command_name = b"cmd_%s_%s" % (
            prefix, handler_command_name(handler["name"]))
        command_bases = (APICommand,)
        command_ns = {
            "__doc__": handler["doc"],
            "actions": handler["actions"],
            "profile": profile,
            "takes_args": ["action"] + handler["params"] + ["data*"],
            "uri": handler["uri"],
            }
        yield command_name, type(
            command_name, command_bases, command_ns)


def gen_profiles():
    """Load all profiles that we're logged-in to."""
    with dotlock:
        for profile_path in iglob(join(dotdir, "*.profile")):
            with open(profile_path, "rb") as stream:
                yield yaml.safe_load(stream)


def command_module():
    """Return a module populated with command classes.

    This is then ready to be passed to `CommandController.load_module`.
    """
    module = new.module(b"%s.commands" % __name__)
    for profile in gen_profiles():
        commands = gen_profile_commands(profile)
        vars(module).update(commands)
    return module
