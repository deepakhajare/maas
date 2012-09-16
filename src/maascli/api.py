# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interact with a remote MAAS server."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "register",
    ]

from abc import (
    ABCMeta,
    abstractmethod,
    )
from contextlib import (
    closing,
    contextmanager,
    )
from getpass import getpass
import httplib
import json
import os
from os.path import expanduser
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
import httplib2
from maascli import CommandError
from maascli.utils import (
    ensure_trailing_slash,
    handler_command_name,
    parse_docstring,
    safe_name,
    )
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


class Command:

    __metaclass__ = ABCMeta

    def __init__(self, parser):
        super(Command, self).__init__()
        self.parser = parser

    @abstractmethod
    def __call__(self, options):
        """Execute this command."""


class cmd_login(Command):
    """Log-in to a remote API, storing its description and credentials.

    If credentials are not provided on the command-line, they will be prompted
    for interactively.
    """

    def __init__(self, parser):
        super(cmd_login, self).__init__(parser)
        parser.add_argument("profile_name")
        parser.add_argument("url")
        parser.add_argument("credentials", nargs="?", default=None)
        parser.set_defaults(credentials=None)

    def __call__(self, options):
        # Try and obtain credentials interactively if they're not given, or
        # read them from stdin if they're specified as "-".
        credentials = options.credentials
        if credentials is None and sys.stdin.isatty():
            prompt = "API key (leave empty for anonymous access): "
            try:
                credentials = getpass(prompt, stream=sys.stdout)
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
        url = ensure_trailing_slash(options.url)
        # Get description of remote API.
        url_describe = urljoin(url, "describe/")
        http = httplib2.Http()
        response, content = http.request(
            ascii_url(url_describe), "GET")
        if response.status != httplib.OK:
            raise CommandError(
                "{0.status} {0.reason}:\n{1}".format(response, content))
        if response["content-type"] != "application/json":
            raise CommandError(
                "Expected application/json, got: %(content-type)s" % response)
        description = json.loads(content)
        # Save the config.
        profile_name = options.profile_name
        with ProfileConfig.open() as config:
            config[profile_name] = {
                "credentials": credentials,
                "description": description,
                "name": profile_name,
                "url": url,
                }


class cmd_logout(Command):
    """Log-out of a remote API, purging any stored credentials."""

    def __init__(self, parser):
        super(cmd_logout, self).__init__(parser)
        parser.add_argument("profile_name")

    def __call__(self, options):
        with ProfileConfig.open() as config:
            del config[options.profile_name]


class cmd_list(Command):
    """List remote APIs that have been logged-in to."""

    def __call__(self, options):
        with ProfileConfig.open() as config:
            for profile_name in config:
                print(profile_name)


class Action(Command):
    """A generic MAAS API action.

    This is used as a base for creating more specific commands; see
    `register_actions`.

    **Note** that this class conflates two things: CLI exposure and API
    client. The client in apiclient.maas_client is not quite suitable yet, but
    it should be iterated upon to make it suitable.
    """

    # Override these in subclasses; see `register_actions`.
    profile = handler = action = None

    def __init__(self, parser):
        super(Action, self).__init__(parser)
        # Register command-line arguments.
        for param in self.handler["params"]:
            parser.add_argument(param)
        parser.add_argument("data", nargs="*")

    def __call__(self, options):
        # TODO: this is el-cheapo URI Template
        # <http://tools.ietf.org/html/rfc6570> support; use uritemplate-py
        # <https://github.com/uri-templates/uritemplate-py> here?
        uri = self.handler["uri"].format(**vars(options))
        data = dict(item.split("=", 1) for item in options.data)

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
        yaml.safe_dump(contents, stream=sys.stdout)


def register_actions(profile, handler, parser):
    """Register a handler's actions."""
    for action in handler["actions"]:
        help_title, help_body = parse_docstring(action["doc"])
        action_name = safe_name(action["name"]).encode("ascii")
        action_bases = (Action,)
        action_ns = {
            "action": action,
            "handler": handler,
            "profile": profile,
            }
        action_class = type(action_name, action_bases, action_ns)
        action_parser = parser.subparsers.add_parser(
            action_name, help=help_title, description=help_body)
        action_parser.set_defaults(
            execute=action_class(action_parser))


def register_handlers(profile, parser):
    """Register a profile's handlers."""
    description = profile["description"]
    for handler in description["handlers"]:
        help_title, help_body = parse_docstring(handler["doc"])
        handler_name = handler_command_name(handler["name"])
        handler_parser = parser.subparsers.add_parser(
            handler_name, help=help_title, description=help_body)
        register_actions(profile, handler, handler_parser)


def register(module, parser):
    """Register profiles."""
    with ProfileConfig.open() as config:
        for profile_name in config:
            profile = config[profile_name]
            profile_parser = parser.subparsers.add_parser(
                profile["name"], help="Interact with %(url)s" % profile)
            register_handlers(profile, profile_parser)
