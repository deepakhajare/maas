# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `maasserver.preseed` and related bits and bobs."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import collections

from maastesting.testcase import TestCase


class TestConfiguration(TestCase):
    """Test for correct configuration of the preseed component."""

    def test_setting_defined(self):
        from django.conf import settings
        self.assertIsInstance(
            settings.PRESEED_TEMPLATE_LOCATIONS,
            collections.Sequence)
