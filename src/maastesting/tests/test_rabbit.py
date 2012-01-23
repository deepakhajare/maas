# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import (
    print_function,
    unicode_literals,
    )

"""Tests for `maastesting.rabbit`."""

__metaclass__ = type
__all__ = []

from maastesting import TestCase
from maastesting.rabbit import RabbitServerResource

from rabbitfixture.server import RabbitServer


class TestRabbitServerResource(TestCase):

    def test_cycle(self):
        """
        A RabbitMQ server can be successfully brought up and shut-down.
        """
        resource = RabbitServerResource()
        server = resource.make({})
        try:
            self.assertIsInstance(server, RabbitServer)
        finally:
            resource.clean(server)
