# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `zeroconfservice`."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import random
import select
import subprocess
import time

from maasserver.zeroconfservice import ZeroconfService
from maastesting.testcase import TestCase


class TestZeroconfService(TestCase):
    """Test :class:`ZeroconfService`.

    These tests will actually inject data in the system Avahi service. It
    would be nice to isolate it from the system Avahi service, but there's a
    lot of work involved in writing a private DBus session with a mock Avahi
    service on it, probably more than it's worth.
    """

    STYPE = '_maas_zeroconftest._tcp'

    count = 0

    def avahi_browse(self, service_type, timeout=3):
        """Return the list of published Avahi service through avahi-browse."""
        # Doing this from pure python would be a pain, as it would involve
        # running a glib mainloop. And stopping one is hard. Much easier to
        # kill an external process. This slows test, and could be fragile,
        # but it's the best I've come with.
        browser = subprocess.Popen(
            ['avahi-browse', '-k', '-p', service_type],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        until = time.time() + timeout
        while time.time() < until:
            # Busy loop until there is some input on stdout,
            # or we give up.
            ready = select.select([browser.stdout], [], [], 0.10)
            if ready[0] or browser.poll():
                break
        browser.terminate()
        names = []
        for record in browser.stdout.readlines():
            fields = record.split(';')
            names.append(fields[3])
        return names

    @classmethod
    def getUniqueServiceNameAndPort(cls):
        # getUniqueString() generates an invalid service name
        name = 'My-Test-Service-%d' % cls.count
        cls.count += 1
        port = random.randint(30000, 40000)
        return name, port

    def test_publish(self):
        # Calling publish() should make the service name available
        # over Avahi.
        name, port = self.getUniqueServiceNameAndPort()
        service = ZeroconfService(name, port, self.STYPE)
        service.publish()
        # This will unregister the published name from Avahi.
        self.addCleanup(service.group.Reset)
        services = self.avahi_browse(self.STYPE)
        self.assertIn(name, services)

    def test_unpublish(self):
        # Calling unpublish() should remove the published
        # service name from Avahi.
        name, port = self.getUniqueServiceNameAndPort()
        service = ZeroconfService(name, port, self.STYPE)
        service.publish()
        service.unpublish()
        services = self.avahi_browse(self.STYPE)
        self.assertNotIn(name, services)
