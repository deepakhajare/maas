# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import (
    print_function,
    unicode_literals,
    )

"""Tests for `maas.testing.rabbit`."""

__metaclass__ = type
__all__ = []

from maas.testing import TestCase
from maas.testing.rabbit import RabbitServerResource


class TestRabbitServerResource(TestCase):

    def test_cycle(self):
        resource = RabbitServerResource()
        print(resource)
        0/0
