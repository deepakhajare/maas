# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A fixture to make Celery run tasks in a synchronous fashion."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'CeleryFixture',
    ]

from celery import current_app
from fixtures import Fixture
from testtools.monkey import MonkeyPatcher


class CeleryFixture(Fixture):
    """This fixture will make Celery run tasks in a synchronous fashion.

    This fixture can be used directly::

    >>> class CeleryTest1(TestCase):
    >>>
    >>>     def setUp(self):
    >>>         super(CeleryTest1, self).setUp()
    >>>         self.useFixture(CeleryFixture())

    It can also be converted into a FixtureResource::

    >>> from testresources import FixtureResource
    >>>
    >>> class CeleryTest2(TestCase):
    >>>
    >>>     resources = (
    >>>         ("celery", FixtureResource(CeleryFixture())),
    >>>         )
    >>>
    """

    def setUp(self):
        super(CeleryFixture, self).setUp()
        patcher = MonkeyPatcher()
        patcher.add_patch(current_app.conf, 'CELERY_ALWAYS_EAGER', True)
        patcher.add_patch(
            current_app.conf, 'CELERY_EAGER_PROPAGATES_EXCEPTIONS', True)
        self.addCleanup(patcher.restore)
        patcher.patch()

