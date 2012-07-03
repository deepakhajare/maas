# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test cases for dns.config"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os.path
import random

from celery.conf import conf
from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver.dns.config import (
    BlankDNSConfig,
    DNSConfig,
    DNSConfigFail,
    DNSZoneConfig,
    generate_rndc,
    setup_rndc,
    TEMPLATES_PATH,
    )
import tempita
from testtools.matchers import FileContains


class TestRNDCGeneration(TestCase):

    def test_generate_rndc_returns_configurations(self):
        rndc_content, named_content = generate_rndc()
        # rndc_content and named_content look right.
        self.assertIn('# Start of rndc.conf', rndc_content)
        self.assertIn('controls {', named_content)
        # named_content does not include any comment.
        self.assertNotIn('\n#', named_content)

    def test_setup_rndc_writes_configurations(self):
        dns_conf_dir = self.make_dir()
        self.patch(conf, 'DNS_CONFIG_DIR', dns_conf_dir)
        setup_rndc()
        expected = (
            ('rndc.conf', '# Start of rndc.conf'),
            ('named.conf.rndc', 'controls {'))
        for filename, content in expected:
            with open(os.path.join(dns_conf_dir, filename), "rb") as stream:
                conf_content = stream.read()
                self.assertIn(content, conf_content)


class TestDNSConfig(TestCase):
    """Tests for DNSConfig."""

    def test_DNSConfig_defaults(self):
        dnsconfig = DNSConfig()
        self.assertEqual(
            (
                os.path.join(TEMPLATES_PATH, 'named.conf.template'),
                os.path.join(conf.DNS_CONFIG_DIR, 'named.conf')
            ),
            (dnsconfig.template_name, dnsconfig.target_file))

    def test_get_template_retrieves_template(self):
        dnsconfig = DNSConfig()
        template = dnsconfig.get_template()
        self.assertIsInstance(template, tempita.Template)
        self.assertThat(
            dnsconfig.template_name, FileContains(template.content))

    def test_render_template(self):
        dnsconfig = DNSConfig()
        random_content = factory.getRandomString()
        template = tempita.Template("{{test}}")
        rendered = dnsconfig.render_template(template, test=random_content)
        self.assertEqual(random_content, rendered)

    def test_render_template_raises_PXEConfigFail(self):
        dnsconfig = DNSConfig()
        template = tempita.Template("template: {{test}}")
        exception = self.assertRaises(
            DNSConfigFail, dnsconfig.render_template, template)
        self.assertIn("'test' is not defined", exception.message)

    def test_write_config_writes_config(self):
        target_file = self.make_file()
        target_file_name = os.path.basename(target_file)
        target_dir = os.path.dirname(target_file)
        template_file = self.make_file(contents="{{test}}")
        template_file_name = os.path.basename(template_file)
        template_dir = os.path.dirname(template_file)
        dnsconfig = DNSConfig(
            path=template_dir, target_path=target_dir,
            filename=template_file_name, target_filename=target_file_name)
        random_content = factory.getRandomString()
        dnsconfig.write_config(test=random_content)
        self.assertThat(target_file, FileContains(random_content))


class TestBlankDNSConfig(TestCase):
    """Tests for BlankDNSConfig."""

    def test_write_config_writes_empty_config(self):
        target_file = self.make_file()
        target_file_name = os.path.basename(target_file)
        target_dir = os.path.dirname(target_file)
        dnsconfig = BlankDNSConfig(
            target_path=target_dir, target_filename=target_file_name)
        dnsconfig.write_config()
        self.assertThat(target_file, FileContains(''))


class TestDNSZoneConfig(TestCase):
    """Tests for DNSZoneConfig."""

    def test_DNSZoneConfig_fields(self):
        zone_id = random.randint(0, 100)
        dnszoneconfig = DNSZoneConfig(zone_id)
        self.assertEqual(
            (
                os.path.join(TEMPLATES_PATH, 'zone.template'),
                os.path.join(conf.DNS_CONFIG_DIR, 'zone.%d' % zone_id)
            ),
            (dnszoneconfig.template_name, dnszoneconfig.target_file))
