# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test cases for dhcp.config"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from textwrap import dedent

from provisioningserver.dhcp import config
from provisioningserver.pxe.tftppath import (
    compose_bootloader_path,
    locate_tftp_path,
    )
import tempita
from testtools import TestCase
from testtools.matchers import (
    Contains,
    MatchesAll,
    MatchesRegex,
    Not,
    )


# Simple test version of the DHCP template.  Contains parameter
# substitutions, but none that aren't also in the real template.
sample_template = dedent("""\
    {{subnet}}
    {{subnet_mask}}
    {{next_server}}
    {{broadcast_address}}
    {{dns_servers}}
    {{gateway}}
    {{low_range}}
    {{high_range}}
""")


def make_sample_params():
    """Produce a dict of sample parameters.

    The sample provides all parameters used by the DHCP template.
    """
    return dict(
        subnet="10.0.0.0",
        subnet_mask="255.0.0.0",
        next_server="10.0.0.1",
        broadcast_address="10.255.255.255",
        dns_servers="10.1.0.1 10.1.0.2",
        gateway="10.0.0.2",
        low_range="10.0.0.3",
        high_range="10.0.0.254",
        )


class TestDHCPConfig(TestCase):

    def patch_template(self, template_content=sample_template):
        """Patch the DHCP config template with the given contents."""
        name = "%s.template" % self.__class__.__name__
        template = tempita.Template(content=template_content, name=name)
        self.patch(config, "template", template)
        return template

    def test_param_substitution(self):
        template = self.patch_template()
        params = make_sample_params()

        output = config.get_config(**params)

        expected = template.substitute(params)
        self.assertEqual(expected, output)

    def test_get_config_with_too_few_parameters(self):
        template = self.patch_template()
        params = make_sample_params()
        del params['subnet']

        e = self.assertRaises(
            config.DHCPConfigError, config.get_config, **params)

        self.assertThat(
            e.message, MatchesRegex(
                "name 'subnet' is not defined at line \d+ column \d+ "
                "in file %s" % template.name))

    def test_config_refers_to_PXE_for_supported_architectures(self):
        params = make_sample_params()
        # Architectures that we have bootloaders for.  (We also have one
        # for amd64, but the same systems can use the i386 one so the
        # amd46 bootloader may not actually be used).
        bootloader_archs = [
            ('i386', 'generic'),
            ('arm', 'highbank'),
            ]
        # Bootloaders' locations on TFTP.  These are the loaders we tell
        # nodes to netboot from.
        bootloader_tftp_paths = [
            compose_bootloader_path(*arch)
            for arch in bootloader_archs]
        # Bootloaders' locations on the TFTP server's filesystem.  The
        # nodes are not to hear about these.  We test that they don't
        # because the correct (TFTP) paths are embedded in the strings
        # and the two kinds of path may be easily confused.
        bootloader_fs_paths = [
            locate_tftp_path(compose_bootloader_path(*arch))
            for arch in bootloader_archs]

        output = config.get_config(**params)
        # The DHCP config mentions all of the bootloaders' TFTP paths...
        self.assertThat(
            output,
            MatchesAll(*[Contains(path) for path in bootloader_tftp_paths]))
        # ...but none of their filesystem paths on the TFTP server.
        self.assertThat(
            output,
            MatchesAll(
                *[Not(Contains(path)) for path in bootloader_fs_paths]))
