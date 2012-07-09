# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Setup configuration files required to run `named` in etc/named.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import os
import shutil

from maastesting.bindfixture import set_up_named


PROJECT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)


NAMED_HOMEDIR = os.path.join(
    PROJECT_DIR, 'etc', 'named')


if __name__ == "__main__":
    # Cleanup the old configuration.
    shutil.rmtree(NAMED_HOMEDIR)
    # Create the directory.
    os.makedirs(NAMED_HOMEDIR)
    # Write the config.
    set_up_named(
        homedir=NAMED_HOMEDIR,
        port=5244,
        rndc_port=5245,
        log_file=os.path.join(PROJECT_DIR, 'logs', 'dns', 'current'),
        named_file=os.path.join(NAMED_HOMEDIR, 'named'),
        conf_file=os.path.join(NAMED_HOMEDIR, 'named.conf'),
        rndcconf_file=os.path.join(NAMED_HOMEDIR, 'rndc.conf')
        )
