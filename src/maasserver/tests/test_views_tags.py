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

    pass
