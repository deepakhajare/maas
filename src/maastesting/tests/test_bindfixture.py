# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Bind fixture."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


from subprocess import (
    CalledProcessError,
    check_output,
    )

from maastesting.bindfixture import (
    BindServer,
    BindServerResources,
    )
from maastesting.testcase import TestCase
import os
from testtools.matchers import (
    Contains,
    Equals,
    FileContains,
    FileExists,
    MatchesListwise,
    )
from testtools.testcase import gather_details


def dig_call(port=53, server='127.0.0.1', command=''):
    try:
        cmd = [
            'dig', '+time=1', '+tries=1', '@%s' % server, '-p',
            '%d' % port]
        if command != '':
            cmd.append(command)
        return check_output(cmd), 0
    except CalledProcessError, e:
        return '', e.returncode


class TestBindFixture(TestCase):

    def test_start_check_shutdown(self):
        # The fixture correctly starts and stops Bind.
        with BindServer() as fixture:
            try:
                result, retcode = dig_call(fixture.config.port)
                self.assertThat(
                    (result, retcode),
                    MatchesListwise(
                        [Contains("Got answer"), Equals(0)]))
            except Exception:
                # self.useFixture() is not being used because we want to
                # handle the fixture's lifecycle, so we must also be
                # responsible for propagating fixture details.
                gather_details(fixture.getDetails(), self.getDetails())
                raise
        result, retcode = dig_call(fixture.config.port)
        self.assertEqual(9, retcode)  # return code 9 means timeout.

    def test_config(self):
        # The configuration can be passed in.
        config = BindServerResources()
        fixture = self.useFixture(BindServer(config))
        self.assertIs(config, fixture.config)


class TestBindServerResources(TestCase):

    def test_defaults(self):
        with BindServerResources() as resources:
            self.assertIsInstance(resources.port, int)
            self.assertIsInstance(resources.rndc_port, int)
            self.assertIsInstance(resources.homedir, basestring)
            self.assertIsInstance(resources.log_file, basestring)
            self.assertIsInstance(resources.named_file, basestring)
            self.assertIsInstance(resources.conf_file, basestring)
            self.assertIsInstance(
                resources.rndcconf_file, basestring)

    def test_setUp_copies_executable(self):
        with BindServerResources() as resources:
            self.assertThat(resources.named_file, FileExists())

    def test_setUp_creates_config_files(self):
        with BindServerResources() as resources:
            self.assertThat(
                resources.conf_file,
                FileContains(matcher=Contains(
                    b'listen-on port %s' % resources.port)))
            self.assertThat(
                resources.rndcconf_file,
                FileContains(matcher=Contains(
                    b'default-port %s' % (
                        resources.rndc_port))))

    def test_defaults_reallocated_after_teardown(self):
        seen_homedirs = set()
        resources = BindServerResources()
        for i in range(2):
            with resources:
                self.assertTrue(os.path.exists(resources.homedir))
                self.assertNotIn(resources.homedir, seen_homedirs)
                seen_homedirs.add(resources.homedir)
