# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test combo view."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os

from django.conf import settings
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maasserver.views.combo import get_yui_location


class TestUtilities(TestCase):

    def test_get_yui_location_if_static_root_is_none(self):
        self.patch(settings, 'STATIC_ROOT', None)
        yui_location = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static', 'jslibs', 'yui')
        self.assertEqual(yui_location, get_yui_location())

    def test_get_yui_location(self):
        static_root = factory.getRandomString()
        self.patch(settings, 'STATIC_ROOT', static_root)
        yui_location = os.path.join(static_root, 'jslibs', 'yui')
        self.assertEqual(yui_location, get_yui_location())
