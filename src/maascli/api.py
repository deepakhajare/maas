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

from contextlib import (
    closing,
    contextmanager,
    )
from getpass import getpass
import httplib
import json
import new
import os
from os.path import expanduser
import re
import sqlite3
import sys
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
from commandant.commands import Command
import httplib2
import yaml


class ProfileConfig:
    """Store profile configurations in an sqlite3 database."""

    def __init__(self, database):
        self.database = database
        with self.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS profiles "
                "(id INTEGER PRIMARY KEY,"
                " name TEXT NOT NULL UNIQUE,"
                " data BLOB)")

    def cursor(self):
        return closing(self.database.cursor())

    def __iter__(self):
        with self.cursor() as cursor:
            results = cursor.execute(
                "SELECT name FROM profiles").fetchall()
        return (name for (name,) in results)

    def __getitem__(self, name):
        with self.cursor() as cursor:
            [data] = cursor.execute(
                "SELECT data FROM profiles"
                " WHERE name = ?", (name,)).fetchone()
        return json.loads(data)

    def __setitem__(self, name, data):
        with self.cursor() as cursor:
            cursor.execute(
                "INSERT INTO profiles (name, data) "
                "VALUES (?, ?)", (name, json.dumps(data)))

    def __delitem__(self, name):
        with self.cursor() as cursor:
            cursor.execute(
                "DELETE FROM profiles"
                " WHERE name = ?", (name,))

    @classmethod
    @contextmanager
    def open(cls, dbpath=expanduser("~/.maascli.db")):
        """Load a profiles database.

        Called without arguments this will open (and create) a database in the
        user's home directory.

        **Note** that this returns a context manager which will close the
        database on exit, saving if the exit is clean.
        """
        # Initialise filename with restrictive permissions...
        os.close(os.open(dbpath, os.O_CREAT | os.O_APPEND, 0600))
        # before opening it with sqlite.
        database = sqlite3.connect(dbpath)
        try:
            yield cls(database)
        except:
            raise
        else:
            database.commit()
        finally:
            database.close()


re_camelcase = re.compile(
    r"([A-Z]*[a-z0-9]+|[A-Z]+)(?:(?=[^a-z0-9])|\Z)")


def safe_name(string):
    """Return a munged version of string, suitable as an ASCII filename."""
    return "-".join(re_camelcase.findall(string))


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


def ensure_trailing_slash(string):
    """Ensure that `string` has a trailing forward-slash."""
    slash = b"/" if isinstance(string, bytes) else u"/"
    return (string + slash) if not string.endswith(slash) else string


class cmd_login(Command):
    """Log-in to a remote API, storing its description and credentials.

    If credentials are not provided on the command-line, they will be prompted
    for interactively.
    """

    # TODO: rename credentials api_key or something.
    takes_args = ("profile_name", "url", "credentials?")

    def run(self, profile_name, url, credentials=None):
        # Try and obtain credentials interactively if they're not given, or
        # read them from stdin if they're specified as "-".
        if credentials is None and sys.stdin.isatty():
            prompt = "API key (leave empty for anonymous access): "
            try:
                credentials = getpass(prompt, stream=self.outf)
            except EOFError:
                credentials = None
        elif credentials == "-":
            credentials = sys.stdin.readline()
        # Ensure that the credentials have a valid form.
        if credentials and not credentials.isspace():
            credentials = convert_string_to_tuple(credentials)
        else:
            credentials = None
        # Normalise the remote service's URL.
        url = ensure_trailing_slash(url)
        # Get description of remote API.
        url_describe = urljoin(url, "describe/")
        http = httplib2.Http()
        response, content = http.request(
            ascii_url(url_describe), "GET")
        if response.status != httplib.OK:
            raise BzrCommandError(
                "{0.status} {0.reason}:\n{1}".format(response, content))
        if response["content-type"] != "application/json":
            raise BzrCommandError(
                "Expected application/json, got: %(content-type)s" % response)
        description = json.loads(content)
        # Save the config.
        with ProfileConfig.open() as config:
            config[profile_name] = {
                "credentials": credentials,
                "description": description,
                "name": profile_name,
                "url": url,
                }


class cmd_logout(Command):
    """Log-out of a remote API, purging any stored credentials."""

    takes_args = ["profile_name"]

    def run(self, profile_name):
        with ProfileConfig.open() as config:
            del config[profile_name]


class APICommand(Command):
    """A generic MAAS API command.

    This is used as a base for creating more specific commands; see
    `gen_profile_commands`.

    **Note** that this class conflates two things: CLI exposure and API
    client. The client in apiclient.maas_client is not quite suitable yet, but
    it should be iterated upon to make it suitable.
    """

    # Override these in subclasses; see `gen_profile_commands`.
    action = None
    profile = None
    takes_args = ["...", "data*"]

    def run(self, data_list, **params):
        # TODO: this is el-cheapo URI Template
        # <http://tools.ietf.org/html/rfc6570> support; use uritemplate-py
        # <https://github.com/uri-templates/uritemplate-py> here?
        uri = self.uri.format(**params)

        if data_list is None:
            data = dict()
        else:
            data = dict(item.split("=", 1) for item in data_list)

        op = self.action["op"]
        if op is not None:
            data["op"] = op

        method = self.action["method"]
        restful = self.action["restful"]

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


def gen_profile_commands(profile):
    """Manufacture command classes based on an API profile."""
    prefix = profile["name"].encode("ascii")
    description = profile["description"]
    for handler in description["handlers"]:
        command_name = b"cmd_%s_%s" % (
            prefix, handler_command_name(handler["name"]))
        command_bases = (APICommand,)
        for action in handler["actions"]:
            command_ns = {
                "__doc__": action["doc"],
                "action": action,
                "profile": profile,
                "takes_args": handler["params"] + ["data*"],
                "uri": handler["uri"],
                }
            command_action_name = b"%s_%s" % (
                command_name, action["name"].encode("ascii"))
            yield command_action_name, type(
                command_action_name, command_bases, command_ns)


def command_module():
    """Return a module populated with command classes.

    This is then ready to be passed to `CommandController.load_module`.
    """
    module = new.module(b"%s.commands" % __name__)
    with ProfileConfig.open() as config:
        for profile_name in config:
            profile = config[profile_name]
            commands = gen_profile_commands(profile)
            vars(module).update(commands)
    return module
