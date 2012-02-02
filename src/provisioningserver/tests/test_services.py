# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.services`."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os

from fixtures import TempDir
from oops_twisted import OOPSObserver
from provisioningserver.services import (
    LogService,
    OOPSService,
    )
from testtools import TestCase
from testtools.content import content_from_file
from testtools.deferredruntest import AsynchronousDeferredRunTest
from twisted.application.service import MultiService
from twisted.python.log import theLogPublisher


class TestOOPSService(TestCase):
    """Tests for `provisioningserver.services.OOPSService`."""

    run_tests_with = AsynchronousDeferredRunTest

    def setUp(self):
        super(TestOOPSService, self).setUp()
        self.observers = theLogPublisher.observers[:]
        self.services = MultiService()
        self.services.privilegedStartService()
        self.services.startService()
        # OOPSService relies upon LogService.
        self.tempdir = self.useFixture(TempDir()).path
        self.log_filename = os.path.join(self.tempdir, "test.log")
        self.log_service = LogService(self.log_filename)
        self.log_service.setServiceParent(self.services)

    def tearDown(self):
        super(TestOOPSService, self).tearDown()
        d = self.services.stopService()
        # The log file must be read in right after services have stopped,
        # before the temporary directory where the log lives is removed.
        d.addBoth(lambda ignore: self.addDetailFromLog())
        return d

    def addDetailFromLog(self):
        content = content_from_file(self.log_filename, buffer_now=True)
        self.addDetail("log", content)

    def test_minimal(self):
        oops_service = OOPSService(self.log_service, None, None)
        oops_service.setServiceParent(self.services)
        observer = oops_service.observer
        self.assertIsInstance(observer, OOPSObserver)
        self.assertEqual([], observer.config.publishers)
        self.assertEqual({}, observer.config.template)

    def test_with_all_params(self):
        oops_dir = os.path.join(self.tempdir, "oops")
        oops_service = OOPSService(self.log_service, oops_dir, "Sidebottom")
        oops_service.setServiceParent(self.services)
        observer = oops_service.observer
        self.assertIsInstance(observer, OOPSObserver)
        self.assertEqual(1, len(observer.config.publishers))
        self.assertEqual(
            {"reporter": "Sidebottom"},
            observer.config.template)
