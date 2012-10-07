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
    "register_api_commands",
    "register_cli_commands",
    ]

from email.message import Message
from getpass import getpass
import httplib
from itertools import chain
import json
import sys
from urlparse import (
    urljoin,
    urlparse,
    )

from apiclient.creds import (
    convert_string_to_tuple,
    convert_tuple_to_string,
    )
from apiclient.maas_client import MAASOAuth
from apiclient.multipart import encode_multipart_data
from apiclient.utils import ascii_url
import httplib2
from maascli.command import (
    Command,
    CommandError,
    )
from maascli.config import ProfileConfig
from maascli.utils import (
    ensure_trailing_slash,
    handler_command_name,
    parse_docstring,
    safe_name,
    urlencode,
    )


def try_getpass(prompt):
    """Call `getpass`, ignoring EOF errors."""
    try:
        return getpass(prompt)
    except EOFError:
        return None


def obtain_credentials(credentials):
    """Prompt for credentials if possible.

    If the credentials are "-" then read from stdin without interactive
    prompting.
    """
    if credentials == "-":
        credentials = sys.stdin.readline().strip()
    elif credentials is None:
        credentials = try_getpass(
            "API key (leave empty for anonymous access): ")
    # Ensure that the credentials have a valid form.
    if credentials and not credentials.isspace():
        return convert_string_to_tuple(credentials)
    else:
        return None


def http_request(url, method, body=None, headers=None,
                 disable_cert_check=False):
    """Issue an http request"""
    http = httplib2.Http(
        disable_ssl_certificate_validation=disable_cert_check)
    try:
        return http.request(ascii_url(url), "GET")
    except httplib2.SSLHandshakeError:
        raise CommandError(
            "Certificate verify failed, use --disable-cert-check to disable "
            "the certificate check.")


def fetch_api_description(url, disable_cert_check=False):
    """Obtain the description of remote API given its base URL."""
    url_describe = urljoin(url, "describe/")
    response, content = http_request(
        ascii_url(url_describe), "GET", disable_cert_check=disable_cert_check)
    if response.status != httplib.OK:
        raise CommandError(
            "{0.status} {0.reason}:\n{1}".format(response, content))
    if response["content-type"] != "application/json":
        raise CommandError(
            "Expected application/json, got: %(content-type)s" % response)
    return json.loads(content)


def get_response_content_type(response):
    """Returns the response's content-type, without parameters.

    If the content-type was not set in the response, returns `None`.

    :type response: :class:`httplib2.Response`
    """
    try:
        content_type = response["content-type"]
    except KeyError:
        return None
    else:
        # It seems odd to create a Message instance here, but at the time of
        # writing it's the only place that has the smarts to correctly deal
        # with a Content-Type that contains a charset (or other parameters).
        message = Message()
        message.set_type(content_type)
        return message.get_content_type()


def is_response_textual(response):
    """Is the response body text?"""
    content_type = get_response_content_type(response)
    return (
        content_type.endswith("/json") or
        content_type.startswith("text/"))


def print_headers(headers, file=sys.stdout):
    """Show an HTTP response in a human-friendly way.

    :type headers: :class:`httplib2.Response`, or :class:`dict`
    """
    # Function to change headers like "transfer-encoding" into
    # "Transfer-Encoding".
    cap = lambda header: "-".join(
        part.capitalize() for part in header.split("-"))
    # Format string to prettify reporting of response headers.
    form = "%%%ds: %%s" % (
        max(len(header) for header in headers) + 2)
    # Print the response.
    for header in sorted(headers):
        print(form % (cap(header), headers[header]), file=file)


class cmd_login(Command):
    """Log-in to a remote API, storing its description and credentials.

    If credentials are not provided on the command-line, they will be prompted
    for interactively.
    """

    def __init__(self, parser):
        super(cmd_login, self).__init__(parser)
        parser.add_argument(
            "profile_name", metavar="profile-name", help=(
                "The name with which you will later refer to this remote "
                "server and credentials within this tool."
                ))
        parser.add_argument(
            "url", help=(
                "The URL of the remote API, e.g. "
                "http://example.com/MAAS/api/1.0/"))
        parser.add_argument(
            "credentials", nargs="?", default=None, help=(
                "The credentials, also known as the API key, for the "
                "remote MAAS server. These can be found in the user "
                "preferences page in the web UI; they take the form of "
                "a long random-looking string composed of three parts, "
                "separated by colons."
                ))
        parser.add_argument(
            '--disable-cert-check', action='store_true', help=(
                "Disable SSL certificate check"), default=False)
        parser.set_defaults(credentials=None)

    def __call__(self, options):
        # Try and obtain credentials interactively if they're not given, or
        # read them from stdin if they're specified as "-".
        credentials = obtain_credentials(options.credentials)
        # Normalise the remote service's URL.
        url = ensure_trailing_slash(options.url)
        # Get description of remote API.
        disable_cert_check = options.disable_cert_check
        description = fetch_api_description(url, disable_cert_check)
        # Save the config.
        profile_name = options.profile_name
        with ProfileConfig.open() as config:
            config[profile_name] = {
                "credentials": credentials,
                "description": description,
                "name": profile_name,
                "url": url,
                }


class cmd_refresh(Command):
    """Refresh the API descriptions of all profiles."""

    def __call__(self, options):
        with ProfileConfig.open() as config:
            for profile_name in config:
                profile = config[profile_name]
                url = profile["url"]
                profile["description"] = fetch_api_description(url)
                config[profile_name] = profile


class cmd_logout(Command):
    """Log-out of a remote API, purging any stored credentials."""

    def __init__(self, parser):
        super(cmd_logout, self).__init__(parser)
        parser.add_argument(
            "profile_name", metavar="profile-name", help=(
                "The name with which a remote server and its credentials "
                "are referred to within this tool."
                ))

    def __call__(self, options):
        with ProfileConfig.open() as config:
            del config[options.profile_name]


class cmd_list(Command):
    """List remote APIs that have been logged-in to."""

    def __call__(self, options):
        with ProfileConfig.open() as config:
            for profile_name in config:
                profile = config[profile_name]
                url = profile["url"]
                creds = profile["credentials"]
                if creds is None:
                    print(profile_name, url)
                else:
                    creds = convert_tuple_to_string(creds)
                    print(profile_name, url, creds)


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

    uri = property(lambda self: self.handler["uri"])
    method = property(lambda self: self.action["method"])
    credentials = property(lambda self: self.profile["credentials"])
    op = property(lambda self: self.action["op"])

    def __init__(self, parser):
        super(Action, self).__init__(parser)
        for param in self.handler["params"]:
            parser.add_argument(param)
        parser.add_argument(
            "data", type=self.name_value_pair, nargs="*")
        parser.add_argument(
            "-d", "--debug", action="store_true", default=False,
            help="Display more information about API responses.")
        parser.add_argument(
            '--disable-cert-check', action='store_true', help=(
                "Disable SSL certificate check"), default=False)

    def __call__(self, options):
        # TODO: this is el-cheapo URI Template
        # <http://tools.ietf.org/html/rfc6570> support; use uritemplate-py
        # <https://github.com/uri-templates/uritemplate-py> here?
        uri = self.uri.format(**vars(options))

        # Bundle things up ready to throw over the wire.
        uri, body, headers = self.prepare_payload(
            self.op, self.method, uri, options.data)

        # Sign request if credentials have been provided.
        if self.credentials is not None:
            self.sign(uri, headers, self.credentials)

        # Use httplib2 instead of urllib2 (or MAASDispatcher, which is based
        # on urllib2) so that we get full control over HTTP method. TODO:
        # create custom MAASDispatcher to use httplib2 so that MAASClient can
        # be used.
        disable_cert_check = options.disable_cert_check
        response, content = http_request(
             uri, self.method, body=body, headers=headers,
             disable_cert_check=disable_cert_check)

        # Output.
        if options.debug:
            self.print_debug(response)
        self.print_response(response, content)

        # 2xx status codes are all okay.
        if response.status // 100 != 2:
            raise CommandError(2)

    @staticmethod
    def name_value_pair(string):
        parts = string.split("=", 1)
        if len(parts) == 2:
            return tuple(parts)
        else:
            raise CommandError(
                "%r is not a name=value pair" % string)

    @staticmethod
    def prepare_payload(op, method, uri, data):
        """Return the URI (modified perhaps) and body and headers.

        - For GET requests, encode parameters in the query string.

        - Otherwise always encode parameters in the request body.

        - Except op; this can always go in the query string.

        :param method: The HTTP method.
        :param uri: The URI of the action.
        :param data: A dict or iterable of name=value pairs to pack into the
            body or headers, depending on the type of request.
        """
        if method == "GET":
            query = data if op is None else chain([("op", op)], data)
            body, headers = None, {}
        else:
            query = [] if op is None else [("op", op)]
            if data:
                body, headers = encode_multipart_data(data)
            else:
                body, headers = None, {}

        uri = urlparse(uri)._replace(query=urlencode(query)).geturl()
        return uri, body, headers

    @staticmethod
    def sign(uri, headers, credentials):
        """Sign the URI and headers."""
        auth = MAASOAuth(*credentials)
        auth.sign_request(uri, headers)

    @staticmethod
    def print_debug(response):
        """Dump the response line and headers to stderr."""
        print(response.status, response.reason, file=sys.stderr)
        print(file=sys.stderr)
        print_headers(response, file=sys.stderr)
        print(file=sys.stderr)

    @classmethod
    def print_response(cls, response, content):
        """Print the response body if it's textual.

        Otherwise write it raw to stdout.
        """
        if is_response_textual(response):
            print(content)  # Trailing newline, might encode.
        else:
            sys.stdout.write(content)  # Raw, binary.


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


commands = {
    'login': cmd_login,
    'logout': cmd_logout,
    'list': cmd_list,
    'refresh': cmd_refresh,
}


def register_cli_commands(parser):
    """Register the CLI's meta-subcommands on `parser`."""
    for name, command in commands.items():
        help_title, help_body = parse_docstring(command)
        command_parser = parser.subparsers.add_parser(
            safe_name(name), help=help_title, description=help_body)
        command_parser.set_defaults(execute=command(command_parser))


def register_api_commands(parser):
    """Register all profiles as subcommands on `parser`."""
    with ProfileConfig.open() as config:
        for profile_name in config:
            profile = config[profile_name]
            profile_parser = parser.subparsers.add_parser(
                profile["name"], help="Interact with %(url)s" % profile)
            register_handlers(profile, profile_parser)
