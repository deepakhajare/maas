# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provisioning server tasks that are run in Celery workers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'power_off',
    'power_on',
    ]


from celery.decorators import task
from maasserver.models import MACAddress
from provisioningserver.power.poweraction import (
    PowerAction,
    PowerActionFail,
    )
from provisioningserver.pxe.pxeconfig import PXEConfig


def issue_power_action(power_type, power_change, **kwargs):
    """Issue a power action to a node.

    :param power_type: The node's power type.  Must have a corresponding
        power template.
    :param power_change: The change to request: 'on' or 'off'.
    :param **kwargs: Keyword arguments are passed on to :class:`PowerAction`.
    """
    assert power_change in ('on', 'off'), (
        "Unknown power change keyword: %s" % power_change)
    kwargs['power_change'] = power_change
    try:
        pa = PowerAction(power_type)
        pa.execute(**kwargs)
    except PowerActionFail:
        # TODO: signal to webapp that it failed

        # Re-raise, so the job is marked as failed.  Only currently
        # useful for tests.
        raise

    # TODO: signal to webapp that it worked.


@task
def power_on(power_type, **kwargs):
    """Turn a node on."""
    issue_power_action(power_type, 'on', **kwargs)


@task
def power_off(power_type, **kwargs):
    """Turn a node off."""
    issue_power_action(power_type, 'off', **kwargs)


@task
def write_tftp_config_for_node(node, pxe_target_dir=None, **kwargs):
    """Write out the TFTP MAC-based config for `node`.

    A config file is written for each MAC associated with the node.

    :param node: A models.Node.
    :param **kwargs: Keyword args passed to PXEConfig.write_config()
    """
    arch = node.architecture
    # TODO: fix subarch when node.py starts modelling sub-architecture for ARM
    subarch = "generic"
    macs = MACAddress.objects.filter(node=node)
    for mac in macs:
        pxeconfig = PXEConfig(arch, subarch, mac.mac_address, pxe_target_dir)
        pxeconfig.write_config(**kwargs)
