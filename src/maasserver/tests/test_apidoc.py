# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver API documentation functionality."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import new

from django.conf import settings
from django.conf.urls import (
    include,
    patterns,
    url,
    )
from django.core.exceptions import ImproperlyConfigured
from maasserver.api import (
    operation,
    OperationsHandler,
    )
from maasserver.apidoc import (
    describe_handler,
    find_api_resources,
    generate_api_docs,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from piston.doc import HandlerDocumentation
from piston.handler import BaseHandler
from piston.resource import Resource


class TestFindingResources(TestCase):
    """Tests for API inspection support: finding resources."""

    @staticmethod
    def make_module():
        """Return a new module with a fabricated name."""
        name = factory.make_name("module").encode("ascii")
        return new.module(name)

    def test_urlpatterns_empty(self):
        # No resources are found in empty modules.
        module = self.make_module()
        module.urlpatterns = patterns("")
        self.assertSetEqual(set(), find_api_resources(module))

    def test_urlpatterns_not_present(self):
        # The absence urlpatterns is an error.
        module = self.make_module()
        self.assertRaises(ImproperlyConfigured, find_api_resources, module)

    def test_urlpatterns_with_resource_for_incomplete_handler(self):
        # Resources for handlers that don't specify resource_uri are ignored.
        module = self.make_module()
        module.urlpatterns = patterns("", url("^foo", BaseHandler))
        self.assertSetEqual(set(), find_api_resources(module))

    def test_urlpatterns_with_resource(self):
        # Resources for handlers with resource_uri attributes are discovered
        # in a urlconf module and returned. The type of resource_uri is not
        # checked; it must only be present and not None.
        handler = type(b"\m/", (BaseHandler,), {"resource_uri": True})
        resource = Resource(handler)
        module = self.make_module()
        module.urlpatterns = patterns("", url("^metal", resource))
        self.assertSetEqual({resource}, find_api_resources(module))

    def test_nested_urlpatterns_with_handler(self):
        # Resources are found in nested urlconfs.
        handler = type(b"\m/", (BaseHandler,), {"resource_uri": True})
        resource = Resource(handler)
        module = self.make_module()
        submodule = self.make_module()
        submodule.urlpatterns = patterns("", url("^metal", resource))
        module.urlpatterns = patterns("", ("^genre/", include(submodule)))
        self.assertSetEqual({resource}, find_api_resources(module))

    def test_smoke(self):
        # Resources are found for the MAAS API.
        from maasserver import urls_api as urlconf
        self.assertNotEqual(set(), find_api_resources(urlconf))


class TestGeneratingDocs(TestCase):
    """Tests for API inspection support: generating docs."""

    @staticmethod
    def make_handler():
        """
        Return a new `BaseHandler` subclass with a fabricated name and a
        `resource_uri` class-method.
        """
        name = factory.make_name("handler").encode("ascii")
        resource_uri = lambda cls: factory.make_name("resource-uri")
        namespace = {"resource_uri": classmethod(resource_uri)}
        return type(name, (BaseHandler,), namespace)

    def test_generates_doc_for_handler(self):
        # generate_api_docs() yields HandlerDocumentation objects for the
        # handlers passed in.
        handler = self.make_handler()
        docs = list(generate_api_docs([handler]))
        self.assertEqual(1, len(docs))
        [doc] = docs
        self.assertIsInstance(doc, HandlerDocumentation)
        self.assertIs(handler, doc.handler)

    def test_generates_doc_for_multiple_handlers(self):
        # generate_api_docs() yields HandlerDocumentation objects for the
        # handlers passed in.
        handlers = [self.make_handler() for _ in range(5)]
        docs = list(generate_api_docs(handlers))
        self.assertEqual(len(handlers), len(docs))
        self.assertEqual(handlers, [doc.handler for doc in docs])

    def test_handler_without_resource_uri(self):
        # generate_api_docs() raises an exception if a handler does not have a
        # resource_uri attribute.
        handler = self.make_handler()
        del handler.resource_uri
        docs = generate_api_docs([handler])
        error = self.assertRaises(AssertionError, list, docs)
        self.assertEqual(
            "Missing resource_uri in %s" % handler.__name__,
            unicode(error))


class TestDescribingAPI(TestCase):
    """Tests for functions that describe a Piston API."""

    maxDiff = 10000

    def setUp(self):
        super(TestDescribingAPI, self).setUp()
        # Override DEFAULT_MAAS_URL so that it's stable for testing.
        self.patch(settings, "DEFAULT_MAAS_URL", "http://example.com/")

    def test_describe_handler(self):
        # describe_handler() returns a description of a handler that can be
        # readily serialised into JSON, for example.

        class MegadethHandler(OperationsHandler):
            """The mighty 'deth."""

            create = read = delete = None

            @operation(idempotent=False)
            def peace_sells_but_whos_buying(self, request, vic, rattlehead):
                """Released 1986."""

            @operation(idempotent=True)
            def so_far_so_good_so_what(self, request, vic, rattlehead):
                """Released 1988."""

            @classmethod
            def resource_uri(cls):
                # Note that the arguments, after request, to each of the ops
                # above matches the parameters (index 1) in the tuple below.
                return ("megadeth_view", ["vic", "rattlehead"])

        expected_actions = [
            {"doc": "Released 1988.",
             "method": "GET",
             "name": "so_far_so_good_so_what",
             "op": "so_far_so_good_so_what",
             "restful": False},
            {"doc": "Released 1986.",
             "method": "POST",
             "name": "peace_sells_but_whos_buying",
             "op": "peace_sells_but_whos_buying",
             "restful": False},
            {"doc": None,
             "method": "PUT",
             "name": "update",
             "op": None,
             "restful": True},
            ]

        observed = describe_handler(MegadethHandler)
        # The description contains several entries.
        self.assertSetEqual(
            {"actions", "doc", "name", "params", "uri"},
            set(observed))
        self.assertEqual(MegadethHandler.__doc__, observed["doc"])
        self.assertEqual(MegadethHandler.__name__, observed["name"])
        self.assertEqual(["vic", "rattlehead"], observed["params"])
        self.assertItemsEqual(expected_actions, observed["actions"])

    def test_describe_handler_with_maas_handler(self):
        # Ensure that describe_handler() yields something sensible with a
        # "real" MAAS API handler.
        from maasserver.api import NodeHandler as handler
        description = describe_handler(handler)
        # The RUD of CRUD actions are still available, but the C(reate) action
        # has been overridden with custom non-ReSTful operations.
        expected_actions = {
            "DELETE delete op=None restful=True",
            "GET read op=None restful=True",
            "POST start op=start restful=False",
            "POST stop op=stop restful=False",
            "POST release op=release restful=False",
            "PUT update op=None restful=True",
            }
        observed_actions = {
            "%(method)s %(name)s op=%(op)s restful=%(restful)s" % action
            for action in description["actions"]
            }
        self.assertSetEqual(expected_actions, observed_actions)
        self.assertSetEqual({"system_id"}, set(description["params"]))
        # The URI is a URI Template <http://tools.ietf.org/html/rfc6570>, the
        # components of which correspond to the parameters declared.
        self.assertEqual(
            "http://example.com/api/1.0/nodes/{system_id}/",
            description["uri"])
