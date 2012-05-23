# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provisioning server tasks that are run in Celery workers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


from celery.decorators import task

from provisioningserver.enum import POWER_TYPE
from provisioningserver.power.poweraction import (
    PowerAction,
    PowerActionFail,
    )


@task
def power_on_ether_wake(**kwargs):
    try:
        pa = PowerAction(POWER_TYPE.WAKE_ON_LAN)
        pa.execute(**kwargs)
    except PowerActionFail:
        # TODO: signal to webapp that it failed

        # Re-raise, so the job is marked as failed.  Only currently
        # useful for tests.
        raise

    # TODO: signal to webapp that it worked.
