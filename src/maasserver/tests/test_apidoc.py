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

from maasserver.api import (
    api_exported,
    api_operations,
    )
from maasserver.apidoc import (
    describe_args,
    describe_handler,
    find_api_handlers,
    generate_api_docs,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from piston.doc import HandlerDocumentation
from piston.handler import BaseHandler


class TestFindingHandlers(TestCase):
    """Tests for API inspection support: finding handlers."""

    @staticmethod
    def make_module():
        """Return a new module with a fabricated name."""
        name = factory.make_name("module").encode("ascii")
        return new.module(name)

    def test_empty_module(self):
        # No handlers are found in empty modules.
        module = self.make_module()
        module.__all__ = []
        self.assertSequenceEqual(
            [], list(find_api_handlers(module)))

    def test_empty_module_without_all(self):
        # The absence of __all__ does not matter.
        module = self.make_module()
        self.assertSequenceEqual(
            [], list(find_api_handlers(module)))

    def test_ignore_non_handlers(self):
        # Module properties that are not handlers are ignored.
        module = self.make_module()
        module.something = 123
        self.assertSequenceEqual(
            [], list(find_api_handlers(module)))

    def test_module_with_handler(self):
        # Handlers are discovered in a module and returned.
        module = self.make_module()
        module.handler = BaseHandler
        self.assertSequenceEqual(
            [BaseHandler], list(find_api_handlers(module)))

    def test_module_with_handler_not_in_all(self):
        # When __all__ is defined, only the names it defines are searched for
        # handlers.
        module = self.make_module()
        module.handler = BaseHandler
        module.something = "abc"
        module.__all__ = ["something"]
        self.assertSequenceEqual(
            [], list(find_api_handlers(module)))


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

    def test_describe_args(self):
        self.assertEqual(
            [{"name": "alice"}],
            list(describe_args(("alice",), ())))
        self.assertEqual(
            [{"name": "alice"}, {"name": "bob"}],
            list(describe_args(("alice", "bob"), ())))
        self.assertEqual(
            [{"name": "alice"}, {"name": "bob", "default": "carol"}],
            list(describe_args(("alice", "bob"), ("carol",))))

    def test_describe_handler(self):
        # describe_handler() returns a description of a handler that can be
        # readily serialised into JSON, for example.

        @api_operations
        class MegadethHandler(BaseHandler):
            """The mighty 'deth."""

            allowed_methods = "GET", "POST", "PUT"

            @api_exported("POST")
            def peace_sells(but, whos, buying):
                """Released 1986."""

            @api_exported("GET")
            def so_far(so_good, so_what):
                """Released 1988."""

            @classmethod
            def resource_uri(self):
                return ("megadeth_view", ["vic", "rattlehead"])

        expected_actions = [
            {"args": [
                    {"name": "so_good"},
                    {"name": "so_what"},
                    ],
             "doc": "Released 1988.",
             "method": "GET",
             "op": "so_far",
             "uri": "?op=so_far",
             "uri_params": ["vic", "rattlehead"]},
            {"args": [
                    {"name": "but"},
                    {"name": "whos"},
                    {"name": "buying"},
                    ],
             "doc": "Released 1986.",
             "method": "POST",
             "op": "peace_sells",
             "uri": "?op=peace_sells",
             "uri_params": ["vic", "rattlehead"]},
            {"doc": None,
             "method": "PUT",
             "uri": "",
             "uri_params": ["vic", "rattlehead"]},
            ]

        observed = describe_handler(MegadethHandler)
        # The description contains `uri` and `actions` entries.
        self.assertSetEqual({"actions", "doc", "name"}, set(observed))
        self.assertEqual(MegadethHandler.__name__, observed["name"])
        self.assertEqual(MegadethHandler.__doc__, observed["doc"])
        self.assertSequenceEqual(expected_actions, observed["actions"])

    def test_describe_handler_with_maas_handler(self):
        # Ensure that describe_handler() yields something sensible with a
        # "real" MAAS API handler.
        from maasserver.api import NodeHandler as handler
        description = describe_handler(handler)
        # The RUD of CRUD actions are still available, but the C(reate) action
        # has been overridden with custom operations. Not entirely sure how
        # this makes sense, but there we go :)
        expected_actions = {
            "DELETE /api/1.0/nodes/{system_id}/",
            "GET /api/1.0/nodes/{system_id}/",
            "POST /api/1.0/nodes/{system_id}/?op=release",
            "POST /api/1.0/nodes/{system_id}/?op=start",
            "POST /api/1.0/nodes/{system_id}/?op=stop",
            "PUT /api/1.0/nodes/{system_id}/",
            }
        observed_actions = {
            "%(method)s %(uri)s" % action
            for action in description["actions"]
            }
        self.assertSetEqual(expected_actions, observed_actions)
