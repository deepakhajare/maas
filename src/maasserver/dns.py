# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""DNS management module."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'add_zone',
    'change_dns_zones',
    'is_dns_enabled',
    'is_dns_managed',
    'next_zone_serial',
    'write_full_dns_config',
    ]


import collections
from itertools import groupby
import logging
import socket

from django.conf import settings
from maasserver.enum import (
    NODEGROUP_STATUS,
    NODEGROUPINTERFACE_MANAGEMENT,
    )
from maasserver.exceptions import MAASException
from maasserver.models import (
    DHCPLease,
    NodeGroup,
    )
from maasserver.sequence import (
    INT_MAX,
    Sequence,
    )
from maasserver.server_address import get_maas_facing_server_address
from netaddr import (
    IPAddress,
    IPNetwork,
    )
from provisioningserver import tasks
from provisioningserver.dns.config import (
    DNSForwardZoneConfig,
    DNSReverseZoneConfig,
    )

# A DNS zone's serial is a 32-bit integer.  Also, we start with the
# value 1 because 0 has special meaning for some DNS servers.  Even if
# we control the DNS server we use, better safe than sorry.
zone_serial = Sequence(
    'maasserver_zone_serial_seq', incr=1, minvalue=1, maxvalue=INT_MAX)


def next_zone_serial():
    return '%0.10d' % zone_serial.nextval()


def is_dns_enabled():
    """Is MAAS configured to manage DNS?"""
    return settings.DNS_CONNECT


class DNSException(MAASException):
    """An error occured when setting up MAAS's DNS server."""


def is_dns_managed(nodegroup):
    """Does MAAS manage a DNS zone for this Nodegroup?"""
    interface = nodegroup.get_managed_interface()
    return (
        nodegroup.status == NODEGROUP_STATUS.ACCEPTED and
        interface is not None and
        interface.management == NODEGROUPINTERFACE_MANAGEMENT.DHCP_AND_DNS)


def warn_loopback(ip):
    """Warn if the given IP address is in the loopback network."""
    if IPAddress(ip) in IPNetwork('127.0.0.1/8'):
        logging.getLogger('maas').warn(
            "The DNS server will use the address '%s',  which is inside the "
            "loopback network.  This may not be a problem if you're not using "
            "MAAS's DNS features or if you don't rely on this information.  "
            "Be sure to configure the DEFAULT_MAAS_URL setting in MAAS's "
            "settings.py (or demo.py/development.py if you are running a "
            "development system)."
            % ip)


def get_dns_server_address():
    """Return the DNS server's IP address.

    That address is derived from DEFAULT_MAAS_URL in order to get a sensible
    default and at the same time give a possibility to the user to change this.
    """
    try:
        ip = get_maas_facing_server_address()
    except socket.error as e:
        raise DNSException(
            "Unable to find MAAS server IP address: %s.  "
            "MAAS's DNS server requires this IP address for the NS records "
            "in its zone files.  Make sure that the DEFAULT_MAAS_URL setting "
            "has the correct hostname."
            % e.strerror)

    warn_loopback(ip)
    return ip


def gen_zones(nodegroups, serial=None):
    """Create ...

    This method also accepts a serial to reuse the same serial when
    we are creating config objects in bulk.
    """
    # Narrow down to the managed nodegroups.
    nodegroups = {
        nodegroup for nodegroup in nodegroups
        if is_dns_managed(nodegroup)
        }
    if len(nodegroups) == 0:
        return
    # Handy stuff for later.
    if serial is None:
        serial = next_zone_serial()
    dns_ip = get_dns_server_address()
    # Functions on nodegroups.
    get_domain = lambda nodegroup: nodegroup.name
    get_interface = lambda nodegroup: nodegroup.get_managed_interface()
    get_mapping = DHCPLease.objects.get_hostname_ip_mapping
    # Sort then collate by domain name.
    nodegroups = sorted(nodegroups, key=get_domain)
    for domain, nodegroups in groupby(nodegroups, get_domain):
        nodegroups = list(nodegroups)
        mappings = {
            nodegroup: get_mapping(nodegroup)
            for nodegroup in nodegroups
            }
        interfaces = {
            nodegroup: get_interface(nodegroup)
            for nodegroup in nodegroups
            }
        assert len(interfaces) == 1, "Too many managed interfaces."
        # A forward zone encompassing all nodes in the same domain.
        yield DNSForwardZoneConfig(
            domain, serial=serial, dns_ip=dns_ip,
            mapping={
                hostname: ip
                for mapping in mappings.values()
                for hostname, ip in mapping.items()
                },
            networks={
                interface.network
                for interface in interfaces.values()
                },
            )
        # A reverse zone for each managed interface.
        for nodegroup, interface in interfaces.items():
            yield DNSReverseZoneConfig(
                domain, serial=serial, dns_ip=dns_ip,
                mapping=mappings[nodegroup],
                network=interface.network)


def change_dns_zones(nodegroups):
    """Update the zone configuration for the given list of Nodegroups.

    :param nodegroups: The list of nodegroups (or the nodegroup) for which the
        zone should be updated.
    :type nodegroups: list (or :class:`NodeGroup`)
    """
    if not is_dns_enabled():
        return
    if not isinstance(nodegroups, collections.Iterable):
        nodegroups = [nodegroups]
    serial = next_zone_serial()
    zones = gen_zones(nodegroups, serial)
    for zone in zones:
        zone_reload_subtask = tasks.rndc_command.subtask(
            args=[['reload', zone.zone_name]])
        tasks.write_dns_zone_config.delay(
            zones=[zone], callback=zone_reload_subtask)


def add_zone(nodegroup):
    """Add to the DNS server a new zone for the given `nodegroup`.

    To do this we have to write a new configuration file for the zone
    and update the master config to include this new configuration.
    These are done in turn by chaining Celery subtasks.

    :param nodegroup: The nodegroup for which the zone should be added.
    :type nodegroup: :class:`NodeGroup`
    """
    if not is_dns_enabled():
        return
    zones_to_add = list(gen_zones([nodegroup]))
    if len(zones_to_add) == 0:
        return None
    serial = next_zone_serial()
    # Compute non-None zones.
    zones = list(gen_zones(NodeGroup.objects.all(), serial))
    reconfig_subtask = tasks.rndc_command.subtask(args=[['reconfig']])
    write_dns_config_subtask = tasks.write_dns_config.subtask(
        zones=zones, callback=reconfig_subtask)
    tasks.write_dns_zone_config.delay(
        zones=zones_to_add, callback=write_dns_config_subtask)


def write_full_dns_config(active=True, reload_retry=False):
    """Write the DNS configuration.

    :param active: If True, write the DNS config for all the nodegroups.
        Otherwise write an empty DNS config (with no zones).  Defaults
        to `True`.
    :type active: bool
    :param reload_retry: Should the reload rndc command be retried in case
        of failure?  Defaults to `False`.
    :type reload_retry: bool
    """
    if not is_dns_enabled():
        return
    if active:
        zones = list(gen_zones(NodeGroup.objects.all()))
    else:
        zones = []
    tasks.write_full_dns_config.delay(
        zones=zones,
        callback=tasks.rndc_command.subtask(
            args=[['reload'], reload_retry]))
