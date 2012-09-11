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

from maasserver.apidoc import (
    describe_args,
    describe_method,
    find_api_handlers,
    generate_api_docs,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from piston.doc import (
    HandlerDocumentation,
    HandlerMethod,
    )
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

    def test_describe_method(self):
        method = lambda a, b=1, c=2: a + b + c
        method.__doc__ = factory.make_name("doc")
        method.__name__ = factory.make_name("name").encode("ascii")
        method_doc = HandlerMethod(method)
        expected = {
            "name": method.__name__,
            "documentation": method.__doc__,
            "signature": "a, b=1, c=2",
            "arguments": [
                {"name": "a"},
                {"default": 1, "name": "b"},
                {"default": 2, "name": "c"},
                ],
            }
        observed = describe_method(method_doc)
        self.assertEqual(expected, observed)
