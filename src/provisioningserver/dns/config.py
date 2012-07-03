# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""DNS configuration."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'BlankDNSConfig',
    'DNSConfig',
    'DNSZoneConfig',
    'setup_rndc',
    ]


import os.path
from subprocess import check_output

from celery.conf import conf
import tempita


class DNSConfigFail(Exception):
    """Raised if there's a problem with a DNS config."""


def generate_rndc():
    """Use `rndc-confgen` (from bind9utils) to generate a rndc+named
    configuration.

    `rndc-confgen` generates the rndc configuration which also contains (that
    part is commented out) the named configuration.
    """
    # Generate the configuration:
    # - 256 bits is the recommanded size for the key nowadays;
    # - Use the unlocked random source to make the executing
    # non-blocking.
    rndc_content = check_output(
        ['rndc-confgen', '-b', '256', '-r', '/dev/urandom',
         '-k', 'rndc-maas-key'])
    # Extract from the result the part which corresponds to the named
    # configuration.
    start_marker = (
        "# Use with the following in named.conf, adjusting the "
        "allow list as needed:")
    end_marker = '# End of named.conf'
    named_start = rndc_content.index(start_marker) + len(start_marker)
    named_end = rndc_content.index(end_marker)
    named_conf = rndc_content[named_start:named_end].replace('\n# ', '\n')
    # Return a tuple of the two configurations.
    return rndc_content, named_conf


def setup_rndc():
    """Writes out the two files needed to enable MAAS to use rndc commands:
    rndc.conf and named.conf.rndc, both stored in conf.DNS_CONFIG_DIR.
    """
    rndc_content, named_content = generate_rndc()

    target_file = os.path.join(conf.DNS_CONFIG_DIR, 'rndc.conf')
    with open(target_file, "w") as f:
        f.write(rndc_content)

    target_file = os.path.join(conf.DNS_CONFIG_DIR, 'named.conf.rndc')
    with open(target_file, "w") as f:
        f.write(named_content)


TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), 'templates')


class DNSConfig:
    """
    A DNS configuration file.

    Encapsulation of DNS config templates and parameter substitution.

    :param path: The directory where the template can be found.
    :type path: string
    :param target_path: The directory where the configuration will be written.
    :type target_path: string
    :param filename: The name of the template file.
    :type filename: string
    :param target_filename: The name of the configuration file to be written.
    :type target_filename: string
    :raises DNSConfigFail: if there's a problem with template parameters.
    """

    def __init__(self, path=TEMPLATES_PATH, target_path=conf.DNS_CONFIG_DIR,
                 filename='named.conf.template',
                 target_filename='named.conf'):
        self.template_name = os.path.join(path, filename)
        self.target_file = os.path.join(target_path, target_filename)

    def get_template(self):
        with open(self.template_name, "r") as f:
            return tempita.Template(f.read(), name=self.template_name)

    def render_template(self, template, **kwargs):
        try:
            return template.substitute(kwargs)
        except NameError as error:
            raise DNSConfigFail(*error.args)

    def write_config(self, **kwargs):
        """Write out this DNS config file."""
        template = self.get_template()
        rendered = self.render_template(template, **kwargs)
        with open(self.target_file, "w") as f:
            f.write(rendered)


class BlankDNSConfig(DNSConfig):
    """A specialized version of DNSConfig that simply writes a blank/empty
    configuration file.
    """

    def write_config(self, **kwargs):
        """Write out an empty DNS config file."""
        with open(self.target_file, "w") as f:
            f.write('')


class DNSZoneConfig(DNSConfig):
    """A specialized version of DNSConfig that writes zone files."""

    def __init__(self, zone_id):
        self.template_name = os.path.join(TEMPLATES_PATH, 'zone.template')
        self.target_file = os.path.join(
            conf.DNS_CONFIG_DIR, 'zone.%d' % zone_id)
