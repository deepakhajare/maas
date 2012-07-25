# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""PXE configuration file."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'PXEConfig',
    'PXEConfigFail',
    ]


import os

from celeryconfig import PXE_TEMPLATES_DIR
import tempita


class PXEConfigFail(Exception):
    """Raised if there's a problem with a PXE config."""


class PXEConfig:
    """A PXE configuration file.

    Encapsulation of PXE config templates and parameter substitution.

    :param arch: The architecture of the context node.
    :type arch: string
    :param subarch: The sub-architecture of the context node. This is
        optional because some architectures such as i386 don't have a
        sub-architecture.  If not passed, a directory name of "generic"
        is used in the subarch part of the path to the target file.
    :type subarch: string
    :param mac: If specified will write out a mac-specific pxe file.
        If not specified will write out a "default" file.
        Note: Ensure the mac is passed in a colon-separated format like
        aa:bb:cc:dd:ee:ff.  This is the default for MAC addresses coming
        from the database fields in MAAS, so it's not heavily checked here.
    :type mac: string

    :raises PXEConfigFail: if there's a problem with template parameters
        or the MAC address looks incorrectly formatted.

    Use this class by instantiating with parameters that define its location:

    >>> pxeconfig = PXEConfig("armhf", "armadaxp", mac="00:a1:b2:c3:e4:d5")

    and then produce a configuration file with:

    >>> pxeconfig.get_config(
    ...     menutitle="menutitle", kernelimage="/my/kernel",
            append="initrd=blah url=blah")
    """

    def __init__(self, arch, subarch='generic', mac=None):
        self._validate_mac(mac)
        self.template = os.path.join(self.template_basedir, "maas.template")

    @property
    def template_basedir(self):
        """Directory where PXE templates are stored."""
        if PXE_TEMPLATES_DIR is None:
            # The PXE templates are installed into the same location as this
            # file, and also live in the same directory as this file in the
            # source tree.
            return os.path.join(os.path.dirname(__file__), 'templates')
        else:
            return PXE_TEMPLATES_DIR

    def _validate_mac(self, mac):
        # A MAC address should be of the form aa:bb:cc:dd:ee:ff with
        # precisely five colons in it.  We do a cursory check since most
        # MACs will come from the DB which are already checked and
        # formatted.
        if mac is None:
            return
        colon_count = mac.count(":")
        if colon_count != 5:
            raise PXEConfigFail(
                "Expecting exactly five ':' chars, found %s" % colon_count)

    def get_template(self):
        with open(self.template, "r") as f:
            return tempita.Template(f.read(), name=self.template)

    def render_template(self, template, **kwargs):
        try:
            return template.substitute(kwargs)
        except NameError as error:
            raise PXEConfigFail(*error.args)

    def get_config(self, **kwargs):
        """Return this PXE config file as a unicode string.

        :param menutitle: The PXE menu title shown.
        :param kernelimage: The path to the kernel in the TFTP server
        :param append: Kernel parameters to append.
        """
        template = self.get_template()
        return self.render_template(template, **kwargs)
