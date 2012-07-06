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
    'reload_dns_config',
    'reload_zone_config',
    'write_dns_config',
    'write_dns_zone_config',
    'setup_rndc_configuration',
    ]


from celery.task import task
from celery.task.sets import subtask
from provisioningserver.dns.config import (
    BlankDNSConfig,
    DNSConfig,
    DNSZoneConfig,
    execute_rndc_command,
    setup_rndc,
    )
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
def write_tftp_config_for_node(arch, macs, subarch="generic",
                               tftproot=None, **kwargs):
    """Write out the TFTP MAC-based config for a node.

    A config file is written for each MAC associated with the node.

    :param arch: Architecture name
    :type arch: string
    :param macs: An iterable of mac addresses
    :type macs: Iterable of strings
    :param subarch: The subarchitecture of the node, defaults to "generic" for
        architectures without sub-architectures.
    :param tftproot: Root TFTP directory.
    :param **kwargs: Keyword args passed to PXEConfig.write_config()
    """
    # TODO: fix subarch when node.py starts modelling sub-architecture for ARM
    for mac in macs:
        pxeconfig = PXEConfig(arch, subarch, mac, tftproot)
        pxeconfig.write_config(**kwargs)


@task
def reload_dns_config():
    """Use rndc to reload the DNS configuration."""
    execute_rndc_command('reload')


@task
def reload_zone_config(zone_id):
    """Use rndc to reload the DNS configuration for a zone."""
    execute_rndc_command('reload', zone_id)


@task
def write_dns_config(blank=False, zone_ids=(), reverse_zone_ids=(),
                     reload_config=True, **kwargs):
    """Write out the DNS configuration file.

    :param blank: Whether or not a blank configuration should be written.
        False by default.
    :type blank: boolean
    :param zone_ids: List of zone ids to include as part of the main config.
    :type zone_ids: list
    :param reverse_zone_ids: List of reverse zone ids to include as part of
        the main config.
    :type reverse_zone_ids: list
    :param reload_config: Whether or not to reload the configuration after it
        has been written.  True by default.
    :type reload_config: boolean
    :param **kwargs: Keyword args passed to DNSConfig.write_config()
    """
    if blank:
        BlankDNSConfig().write_config()
    else:
        config = DNSConfig(
            zone_ids=zone_ids,
            reverse_zone_ids=reverse_zone_ids)
        config.write_config(**kwargs)
    if reload_config:
        subtask(reload_dns_config.subtask()).delay()


@task
def write_dns_zone_config(zone_id, reload_config=True, **kwargs):
    """Write out a DNS zone configuration file.

    :param zone_id: The identifier of the zone to write the configuration for.
    :type zone_id: int
    :param hosts: The list of hosts in this zone. Each element in this list
        must be a dict (or provide dict-like access) containing an 'ip' and a
        'hostname'.
    :type hosts: list
    :param reload_config: Whether or not to reload the configuration after it
        has been written.  True by default.
    :type reload_config: boolean
    :param **kwargs: Keyword args passed to DNSZoneConfig.write_config()
    """
    DNSZoneConfig(zone_id).write_config(**kwargs)
    if reload_config:
        subtask(reload_zone_config.subtask(args=[zone_id])).delay()


@task
def setup_rndc_configuration(reload_config=True):
    """Write out the two rndc configuration files (rndc.conf and
    named.conf.rndc).

    :param reload_config: Whether or not to reload the configuration after it
        has been written.  True by default.
    :type reload_config: boolean
    """
    setup_rndc()
    if reload_config:
        subtask(reload_dns_config.subtask()).delay()
