# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Additional services that compose the MaaS Provisioning Server."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "LogService",
    "OOPSService",
    ]

import signal
import sys

import oops
from oops_datedir_repo import DateDirRepo
from oops_twisted import (
    Config as oops_config,
    defer_publisher,
    OOPSObserver,
    )
from twisted.application.service import Service
from twisted.internet import reactor
from twisted.python.log import (
    addObserver,
    FileLogObserver,
    removeObserver,
    )
from twisted.python.logfile import LogFile


class LogService(Service):

    name = "log"

    def __init__(self, filename):
        self.filename = filename
        self.logfile = None
        self.observer = None

    def _signal_handler(self, sig, frame):
        reactor.callFromThread(self.logfile.reopen)

    def startService(self):
        Service.startService(self)
        if self.filename != '-':
            self.logfile = LogFile.fromFullPath(
                self.filename, rotateLength=None, defaultMode=0644)
            assert signal.getsignal(signal.SIGUSR1) is signal.SIG_DFL, (
                "A signal handler is already installed for SIGUSR1.")
            signal.signal(signal.SIGUSR1, self._signal_handler)
        else:
            self.logfile = sys.stdout
        self.observer = FileLogObserver(self.logfile)
        self.observer.start()

    def stopService(self):
        Service.stopService(self)
        # Must use == here; the handler returned from getsignal() is not the
        # same object as self._signal_handler, even though im_class, im_func,
        # and im_self *are* all identical. Don't know why this should be.
        if signal.getsignal(signal.SIGUSR1) == self._signal_handler:
            signal.signal(signal.SIGUSR1, signal.SIG_DFL)
        self.observer.stop()
        self.observer = None
        self.logfile.close()
        self.logfile = None


class OOPSService(Service):

    name = "oops"

    def __init__(self, log_service, oops_dir, oops_reporter):
        self.config = None
        self.log_service = log_service
        self.oops_dir = oops_dir
        self.oops_reporter = oops_reporter

    def startService(self):
        Service.startService(self)
        self.config = oops_config()
        # Add the oops publisher that writes files in the configured place if
        # the command line option was set.
        if self.oops_dir:
            repo = DateDirRepo(self.oops_dir)
            self.config.publishers.append(
                defer_publisher(oops.publish_new_only(repo.publish)))
        if self.oops_reporter:
            self.config.template['reporter'] = self.oops_reporter
        self.observer = OOPSObserver(
            self.config, self.log_service.observer.emit)
        addObserver(self.observer.emit)

    def stopService(self):
        Service.stopService(self)
        removeObserver(self.observer.emit)
        self.observer = None
        self.config = None