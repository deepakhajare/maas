# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Actions for power-related operations."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "PowerAction",
    "PowerActionFail",
    "UnknownPowerType",
    ]


import os
import subprocess

from django.conf import settings


class UnknownPowerType(Exception):
    """Raised when trying to process an unknown power type."""

class PowerActionFail(Exception):
    """Raised when there's a problem execting a power script."""


class PowerAction:
    """Actions for power-related operations."""

    def __init__(self, power_type):
        basedir = settings.POWER_TEMPLATES_DIR
        self.path = os.path.join(basedir, power_type + ".template")
        if not os.path.exists(self.path):
            raise UnknownPowerType

        self.power_type = power_type
        
    def get_template(self):
        with open(self.path, "r") as f:
            template = f.read()
        return template

    def render_template(self, template, **kwargs):
        rendered = template % kwargs
        # TODO: how can we check for unused variables?
        return rendered

    def execute(self, **kwargs):
        template = self.get_template()
        rendered = self.render_template(template, **kwargs)
        cmd = ['/bin/sh','-c', rendered]

        # This might need retrying but it could be better to leave that
        # to the individual scripts.
        try:
            proc = subprocess.Popen(
                cmd, shell=False, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, close_fds=True)
        except OSError, e:
            raise PowerActionFail(e)

        stdout, stderr = proc.communicate()
        code = proc.returncode
        if code != 0:
            raise PowerActionFail("%s failed with return code %s" % (
                self.power_type, code))
