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

from django.conf import settings
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    )
from maasserver.enum import (
    NODE_PERMISSION,
    NODE_STATUS,
    NODE_STATUS_CHOICES,
    NODE_STATUS_CHOICES_DICT,
    )
from maasserver.exceptions import NodeStateViolation
from maasserver.models import (
    Config,
    MACAddress,
    Node,
    )
from maasserver.models.node import NODE_TRANSITIONS
from maasserver.models.user import create_auth_token
from maasserver.testing import reload_object
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from maasserver.utils import map_enum
from metadataserver.models import (
    NodeCommissionResult,
    NodeUserData,
    )
from provisioningserver.enum import POWER_TYPE
from provisioningserver.power.poweraction import PowerAction
from testtools.matchers import FileContains


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
