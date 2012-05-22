# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""MAAS OAuth API connection library."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from abc import (
    ABCMeta,
    abstractmethod,
    )
import oauth.oauth as oauth
from twisted.internet import reactor
from twisted.web.client import HTTPClientFactory
from urllib import urlencode
import urllib2
from urlparse import (
    urljoin,
    urlparse,
    )

from apiclient.multipart import encode_multipart_data

DEFAULT_FACTORY = HTTPClientFactory
DEFAULT_CONNECT = reactor.connectTCP


def _ascii_url(url):
    """Ensure that the given URL is ASCII, encoding if necessary."""
    if isinstance(url, unicode):
        urlparts = urlparse(url)
        urlparts = urlparts._replace(
            netloc=urlparts.netloc.encode("idna"))
        url = urlparts.geturl()
    return url.encode("ascii")


class MAASOAuthConnection:
    """Helper class to OAuth sign a HTTP request."""

    __metaclass__ = ABCMeta

    def __init__(self, oauth_info):
        consumer_key, resource_token, resource_secret = oauth_info
        resource_tok_string = "oauth_token_secret=%s&oauth_token=%s" % (
            resource_secret, resource_token)
        self.resource_token = oauth.OAuthToken.from_string(resource_tok_string)
        self.consumer_token = oauth.OAuthConsumer(consumer_key, "")

    def oauth_sign_request(self, url, headers):
        """Sign a request.

        @param url: The URL to which the request is to be sent.
        @param headers: The headers in the request.
        """
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer_token, token=self.resource_token, http_url=url)
        oauth_request.sign_request(
            oauth.OAuthSignatureMethod_PLAINTEXT(), self.consumer_token,
            self.resource_token)
        headers.update(oauth_request.to_header())

    @abstractmethod
    def dispatch_query(self, request_url, method="GET", data=None,
                       headers=None):
        """Add an OAuth header to the request and dispatch it."""


class MAASTwistedDispatcher(MAASOAuthConnection):
    """Helper class to connect to a MAAS server using Twisted."""

    # Static methods that can be patched in tests.
    factory = staticmethod(DEFAULT_FACTORY)
    connect = staticmethod(DEFAULT_CONNECT)

    def dispatch_query(self, request_url, method="GET",
                       data=None, headers=None):
        """Dispatch an OAuth-signed request to L{request_url}.

        :param request_url: The URL to which the request is to be sent.
        :param method: The HTTP method, e.g. C{GET}, C{POST}, etc.
        :param data: The data to send, if any.
        :type data: A byte string.
        :param headers: Headers to include in the request.
        :type headers: A dict.

        :return: A Deferred that fires when the request completes.  Its
            value is the response contents.
        """
        if headers is None:
            headers = {}
        self.oauth_sign_request(request_url, headers)
        self.client = self.factory(
            url=_ascii_url(request_url), method=method,
            headers=headers, postdata=data)
        urlparts = urlparse(request_url)
        self.connect(urlparts.hostname, urlparts.port, self.client)
        return self.client.deferred


class MAASDispatcher(MAASOAuthConnection):
    """Helper class to connect to a MAAS server using blocking requests."""

    def dispatch_query(self, request_url, method="GET", data=None,
                       headers=None):
        """Synchronously dispatch an OAuth-signed request to L{request_url}.

        :param request_url: The URL to which the request is to be sent.
        :param method: The HTTP method, e.g. C{GET}, C{POST}, etc.
            An AssertionError is raised if trying to pass data for a GET.
        :param data: The data to send, if any.
        :type data: A byte string.
        :param headers: Headers to include in the request.
        :type headers: A dict.

        :return: A open file-like object that contains the response.
        """
        if data is not None and method == "GET":
            raise AssertionError(
                "data can't be passed if using GET.")
        if headers is None:
            headers = {}
        self.oauth_sign_request(request_url, headers)
        req = urllib2.Request(request_url, data, headers)
        return urllib2.urlopen(req)


class MAASClient:
    """Base class for connecting to MAAS servers."""

    def __init__(self, dispatcher, base_url):
        """Intialise the client.

        :param dispatcher: An object implementing the MAASOAuthConnection
            base class.
        :param base_url: The base URL for the MAAS server, e.g.
            http://my.maas.com:5240/
        """
        self.dispatcher = dispatcher
        self.url = base_url

    def get(self, path, params):
        """Dispatch a C{GET} call to a MAAS server.

        :param path: The MAAS path for the endpoint to call.
        :param params: A C{dict} of parameters - or sequence of 2-tuples - to
            encode into the request.
        :return: The result of the dispatch_query call on the dispatcher.
        """
        url = "%s?%s" % (urljoin(self.url, path), urlencode(params))
        return self.dispatch_query(url)

    def post(self, path, params):
        """Dispatch a C{POST} call to a MAAS server.

        :param path: The MAAS path for the endpoint to call.
        :param params: A C{dict} of parameters to encode into the request.
        :return: The result of the dispatch_query call on the dispatcher.
        """
        url = urljoin(self.url, path)
        body, headers = encode_multipart_data(params, {})
        return self.dispatch_query(url, "POST", headers=headers, data=body)

