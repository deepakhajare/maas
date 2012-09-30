# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver nodes views."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django.core.urlresolvers import reverse
from lxml.html import fromstring
# from maasserver.models import (
#     MACAddress,
#     Node,
#     Tag,
#     )
from maasserver.testing import (
    extract_redirect,
    get_content_links,
    reload_object,
    )
from maasserver.testing.factory import factory
from maasserver.testing.rabbit import uses_rabbit_fixture
from maasserver.testing.testcase import (
    AdminLoggedInTestCase,
    LoggedInTestCase,
    TestCase,
    )


class TagViewsTest(LoggedInTestCase):

    def test_view_tag_displays_tag_info(self):
        # The tag page features the basic information about the tag.
        tag = factory.make_tag(name='the-named-tag',
                               comment='Human description of the tag',
                               definition='//xpath')
        tag_link = reverse('tag-view', args=[tag.name])
        response = self.client.get(tag_link)
        doc = fromstring(response.content)
        content_text = doc.cssselect('#content')[0].text_content()
        self.assertIn(tag.name, content_text)
        self.assertIn(tag.comment, content_text)
        self.assertIn(tag.definition, content_text)

    def test_view_tag_includes_node_links(self):
        tag = factory.make_tag()
        node = factory.make_node(set_hostname=True)
        node.tags.add(tag)
        tag_link = reverse('tag-view', args=[tag.name])
        node_link = reverse('node-view', args=[node.system_id])
        response = self.client.get(tag_link)
        doc = fromstring(response.content)
        content_text = doc.cssselect('#content')[0].text_content()
        self.assertIn(node.hostname, content_text)
