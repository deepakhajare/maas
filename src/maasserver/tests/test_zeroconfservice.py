# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the ZeroconfService class"""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import random
import subprocess
import time

from maastesting.testcase import TestCase
from maasserver.zeroconfservice import ZeroconfService

# These tests will actually inject data in the system Avahi system.
# Would be nice to isolate it from the system Avahi service, but I didn't
# feel like writing a private DBus session with a mock Avahi service on it.
class TestZeroconfService(TestCase):

    STYPE = '_zeroconftest._tcp'

    def avahi_browse(self, service_type, timeout=0.5):
        """Return the list of published Avahi service through avahi-browse."""
        # Doing this from pure python would be a pain, as it would involve
        # running a glib mainloop. And stopping one is hard. Much easier to
        # kill an external process. This slows test, and could be fragile,
        # but it's the best I've come with.
        browser = subprocess.Popen(
            ['avahi-browse', '-k', '-p', service_type],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(timeout)
        browser.terminate()
        names = []
        for record in browser.stdout.readlines():
            fields = record.split(';')
            names.append(fields[3])
        return names

    def test_publish(self):
        # getUniqueString() generates an invalid service name
        name = 'My Test Service-%d' % random.randint(1, 1000)
        port = random.randint(30000, 40000)
        service = ZeroconfService(name, port, self.STYPE)
        service.publish()
        self.addCleanup(service.group.Reset)
        services = self.avahi_browse(self.STYPE)
        self.assertIn(name, services)


