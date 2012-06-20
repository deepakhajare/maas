# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

""":class:`TimestampedModel` tests."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django.db import transaction
from maasserver.models.timestampedmodel import now
from maasserver.testing.testcase import TestModelTestCase
from maasserver.tests.models import TimestampedModelTestModel
from maastesting.djangotestcase import TestModelTransactionalTestCase


class TimestampedModelTest(TestModelTestCase):
    """Testing for the class `TimestampedModel`."""

    app = 'maasserver.tests'

    def test_created_populated_when_object_saved(self):
        obj = TimestampedModelTestModel()
        obj.save()
        self.assertIsNotNone(obj.created)

    def test_updated_populated_when_object_saved(self):
        obj = TimestampedModelTestModel()
        obj.save()
        self.assertIsNotNone(obj.updated)

    def test_updated_and_created_are_the_same_after_first_save(self):
        obj = TimestampedModelTestModel()
        obj.save()
        self.assertEqual(obj.created, obj.updated)

    def test_created_not_modified_by_subsequent_calls_to_save(self):
        obj = TimestampedModelTestModel()
        obj.save()
        old_created = obj.created
        obj.save()
        self.assertEqual(old_created, obj.created)


class TimestampedModelTransactionalTest(TestModelTransactionalTestCase):

    app = 'maasserver.tests'

    def test_created_bracketed_by_before_and_after_time(self):
        before = now()
        obj = TimestampedModelTestModel()
        obj.save()
        transaction.commit()
        after = now()
        self.assertLessEqual(before, obj.created)
        self.assertGreaterEqual(after, obj.created)

    def test_updated_is_updated_when_object_saved(self):
        obj = TimestampedModelTestModel()
        obj.save()
        old_updated = obj.updated
        transaction.commit()
        obj.save()
        self.assertLessEqual(old_updated, obj.updated)
