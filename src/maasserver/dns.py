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
    'change_dns_zone',
    'next_zone_serial',
    'write_full_dns_config',
    ]


from maasserver.models import (
    DHCPLease,
    NodeGroup,
    )
from maasserver.sequence import (
    INT_MAX,
    Sequence,
    )
from provisioningserver import tasks

# A DNS zone's serial is a 32-bit integer.  Also, we start with the
# value 1 because 0 has special meaning for some DNS servers.  Even if
# we control the DNS server we use, better safe than sorry.
zone_serial = Sequence(
    'maasserver_zone_serial_seq', incr=1, minvalue=1, maxvalue=INT_MAX)


def next_zone_serial():
    return '%0.10d' % zone_serial.nextval()


def change_dns_zone(nodegroup):
    mapping = DHCPLease.objects.get_hostname_ip_mapping(nodegroup)
    zone_name = nodegroup.name
    tasks.write_dns_zone_config.delay(
        zone_name=zone_name, domain=zone_name,
        serial=next_zone_serial(), hostname_ip_mapping=mapping,
        callback=tasks.rndc_command.subtask(args=['reload', zone_name]))


def add_zone(nodegroup):
    zone_names = [
        result[0]
        for result in NodeGroup.objects.all().values_list('name')]
    tasks.write_dns_config(zone_names=zone_names)
    mapping = DHCPLease.objects.get_hostname_ip_mapping(nodegroup)
    zone_name = nodegroup.name
    tasks.write_dns_zone_config.delay(
        zone_name=zone_name, domain=zone_name,
        serial=next_zone_serial(), hostname_ip_mapping=mapping,
        callback=tasks.write_dns_config.subtask(
            zone_names=zone_names,
            callback=tasks.rndc_command.subtask(args=['reconfig'])))


def write_full_dns_config():
    groups = NodeGroup.objects.all()
    serial = next_zone_serial()
    zones = {
        group.name: {
            'serial': serial,
            'zone_name': group.name,
            'domain': group.name,
            'hostname_ip_mapping': (
                DHCPLease.objects.get_hostname_ip_mapping(
                    group))
            }
        for group in groups
        }
    tasks.write_full_dns_config(
        zones,  callback=tasks.rndc_command.subtask(args=['reload']))
