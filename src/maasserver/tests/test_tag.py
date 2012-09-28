# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver models."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import DatabaseError
from maastesting.djangotestcase import TransactionTestCase
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase


class TagTest(TestCase):

    def test_factory_make_tag(self):
        """
        The generated system_id looks good.

        """
        tag = factory.make_tag('tag-name', '//node[@id=display]')
        self.assertEqual('tag-name', tag.name)
        self.assertEqual('//node[@id=display]', tag.definition)
        self.assertEqual('', tag.comment)
        self.assertIsNot(None, tag.updated)
        self.assertIsNot(None, tag.created)

    def test_add_tag_to_node(self):
        node = factory.make_node()
        tag = factory.make_tag()
        tag.save()
        node.tags.add(tag)
        self.assertEqual([tag.id], [t.id for t in node.tags.all()])
        self.assertEqual([node.id], [n.id for n in tag.node_set.all()])

    def test_valid_tag_names(self):
        for valid in ['valid-dash', 'under_score', 'long'*50]:
            tag = factory.make_tag(name=valid)
            self.assertEqual(valid, tag.name)

    def test_validate_traps_invalid_tag_name(self):
        for invalid in ['invalid:name', 'no spaces', 'no\ttabs',
                        'no&ampersand', 'no!shouting', '',
                        'too-long'*33, '\xb5']:
            self.assertRaises(ValidationError, factory.make_tag, name=invalid)

    def test_populate_nodes_applies_tags_to_nodes(self):
        node1 = factory.make_node()
        node1.set_hardware_details('<node><child /></node>')
        node2 = factory.make_node()
        node2.set_hardware_details('<node />')
        tag = factory.make_tag(definition='/node/child')
        tag.populate_nodes()
        self.assertItemsEqual([tag.name], node1.tag_names())
        self.assertItemsEqual([], node2.tag_names())

    def test_populate_nodes_removes_old_values(self):
        node1 = factory.make_node()
        node1.set_hardware_details('<node><foo /></node>')
        node2 = factory.make_node()
        node2.set_hardware_details('<node><bar /></node>')
        tag = factory.make_tag(definition='/node/foo')
        tag.populate_nodes()
        self.assertItemsEqual([tag.name], node1.tag_names())
        self.assertItemsEqual([], node2.tag_names())
        tag.definition = '/node/bar'
        tag.populate_nodes()
        self.assertItemsEqual([], node1.tag_names())
        self.assertItemsEqual([tag.name], node2.tag_names())

    def test_populate_nodes_doesnt_touch_other_tags(self):
        node1 = factory.make_node()
        node1.set_hardware_details('<node><foo /></node>')
        node2 = factory.make_node()
        node2.set_hardware_details('<node><bar /></node>')
        tag1 = factory.make_tag(definition='/node/foo')
        tag1.populate_nodes()
        self.assertItemsEqual([tag1.name], node1.tag_names())
        self.assertItemsEqual([], node2.tag_names())
        tag2 = factory.make_tag(definition='/node/bar')
        tag2.populate_nodes()
        self.assertItemsEqual([tag1.name], node1.tag_names())
        self.assertItemsEqual([tag2.name], node2.tag_names())


class TestTagTransactions(TransactionTestCase):

    def test_populate_nodes_rollsback_invalid_xpath(self):
        @transaction.commit_manually
        def setup():
            node = factory.make_node()
            node.set_hardware_details('<node><foo /></node>')
            tag = factory.make_tag(definition='/node/foo')
            tag.populate_nodes()
            self.assertItemsEqual([tag.name], node.tag_names())
            transaction.commit()
            return tag, node
        tag, node = setup()
        @transaction.commit_manually
        def trigger_invalid():
            tag.definition = 'invalid::tag'
            self.assertRaises(DatabaseError, tag.populate_nodes)
            transaction.rollback()
        # Because the definition is invalid, the db should not have been
        # updated
        trigger_invalid()
        self.assertItemsEqual([tag.name], node.tag_names())
