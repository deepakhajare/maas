# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `network` module."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from random import (
    choice,
    randint,
    )

from maastesting.factory import factory
from maastesting.testcase import TestCase
from provisioningserver import network


class FakeCheckCall:
    """Test double for `check_call`."""

    def __init__(self, output_text):
        self.output_text = output_text
        self.calls = []

    def __call__(self, command, stdout=None, env=None):
        stdout.write(self.output_text.encode('ascii'))
        self.calls.append(dict(command=command, env=env))
        return 0


def make_address_line(**kwargs):
    """Create an inet address line."""
    # First word on this line is inet or inet6.
    kwargs.setdefault('inet', 'inet')
    kwargs.setdefault('broadcast', '10.255.255.255')
    kwargs.setdefault('mask', '255.0.0.0')
    items = [
        kwargs['inet'],
        ]
    if len(kwargs['broadcast']) > 0:
        items.append("Bcast:%(broadcast)s")
    items.append("Mask:%(mask)s")
    return '  '.join(items) % kwargs


def make_stats_line(direction, **kwargs):
    """Create one of the incoming/outcoming packet-count lines."""
    assert direction in {'RX', 'TX'}
    if direction == 'RX':
        variable_field = 'frame'
    else:
        variable_field = 'carrier'
    kwargs.setdefault('variable_field', variable_field)
    kwargs.setdefault('packets', randint(0, 100000))
    kwargs.setdefault('errors', randint(0, 100))
    kwargs.setdefault('dropped', randint(0, 100))
    kwargs.setdefault('overruns', randint(0, 100))
    kwargs.setdefault('variable', randint(0, 100))

    return " ".join([
        direction,
        "packets:%(packets)d",
        "errors:%(errors)d",
        "dropped:%(dropped)d",
        "overruns:%(overruns)d",
        "%(variable_field)s:%(variable)d"
        ]) % kwargs


def make_payload_stats(direction, **kwargs):
    assert direction in {'RX', 'TX'}
    kwargs.setdefault('bytes', randint(0, 1000000))
    kwargs.setdefault('bigger_unit', randint(10, 10240) / 10.0)
    kwargs.setdefault('unit', choice(['B', 'KB', 'GB']))
    return " ".join([
        direction,
        "bytes:%(bytes)s",
        "(%(bigger_unit)d %(unit)s)",
        ]) % kwargs


def make_stanza(**kwargs):
    """Create an ifconfig output stanza.

    Variable values can be specified, but will be given random values by
    default.  Values that interfaces may not have, such as broadcast
    address or allocated interrupt, may be set to the empty string to
    indicate that they should be left out of the output.
    """
    kwargs.setdefault('interface', factory.make_name('eth'))
    kwargs.setdefault('encapsulation', 'Ethernet')
    kwargs.setdefault('mac', factory.getRandomMACAddress())
    kwargs.setdefault('ip', factory.getRandomIPAddress())
    kwargs.setdefault('broadcast', factory.getRandomIPAddress())
    kwargs.setdefault('mtu', randint(100, 10000))
    kwargs.setdefault('rxline', make_stats_line('RX', **kwargs))
    kwargs.setdefault('txline', make_stats_line('TX', **kwargs))
    kwargs.setdefault('collisions', randint(0, 100))
    kwargs.setdefault('txqueuelen', randint(0, 100))
    kwargs.setdefault('rxbytes', make_payload_stats('RX', **kwargs))
    kwargs.setdefault('txbytes', make_payload_stats('TX', **kwargs))
    kwargs.setdefault('interrupt', randint(1, 30))

    header = "%(interface)s Link encap:%(encapsulation)s  HWaddr %(mac)s"
    body_lines = [
        "UP BROADCAST MULTICAST  MTU:%(mtu)d  Metric:1",
        ]
    if len(kwargs['ip']) > 0:
        body_lines.append(make_address_line(inet='inet', **kwargs))
    body_lines += [
        "%(rxline)s",
        "%(txline)s",
        "collisions:%(collisions)d txqueuelen:%(txqueuelen)d",
        "%(rxbytes)s  %(txbytes)s",
        ]
    if kwargs['interrupt'] != '':
        body_lines.append("Interrupt:%(interrupt)d")

    text = '\n'.join(
        [header] +
        [(10 * " ") + line for line in body_lines])
    return (text + "\n") % kwargs


def join_stanzas(stanzas):
    """Format a sequence of interface stanzas like ifconfig does."""
    return '\n'.join(stanzas) + '\n'


class TestNetworks(TestCase):

    def test_run_ifconfig_returns_ifconfig_output(self):
        text = join_stanzas([make_stanza()])
        self.patch(network, 'check_call', FakeCheckCall(text))
        self.assertEqual(text, network.run_ifconfig())

    def test_parse_ifconfig_produces_interface_info(self):
        num_interfaces = randint(1, 3)
        text = join_stanzas([
            make_stanza()
            for counter in range(num_interfaces)])
        info = network.parse_ifconfig(text)
        self.assertEqual(num_interfaces, len(info))
        self.assertIsInstance(info[0], network.InterfaceInfo)

    def test_parse_stanza_reads_interface_with_ip_and_interrupt(self):
        parms = {
            'interface': factory.make_name('eth'),
            'ip': factory.getRandomIPAddress(),
            'mask': '255.255.255.128',
        }
        info = network.parse_stanza(make_stanza(**parms))
        self.assertEqual(parms, info.as_dict())

    def test_parse_stanza_reads_interface_without_interrupt(self):
        parms = {
            'interface': factory.make_name('eth'),
            'ip': factory.getRandomIPAddress(),
            'mask': '255.255.255.128',
            'interrupt': '',
        }
        info = network.parse_stanza(make_stanza(**parms))
        expected = parms.copy()
        del expected['interrupt']
        self.assertEqual(expected, info.as_dict())

    def test_parse_stanza_reads_interface_without_ip(self):
        parms = {
            'interface': factory.make_name('eth'),
            'ip': '',
            'mask': '255.255.255.128',
        }
        info = network.parse_stanza(make_stanza(**parms))
        expected = parms.copy()
        expected['ip'] = None
        self.assertEqual(expected, info.as_dict())

    def test_parse_stanza_reads_loopback(self):
        parms = {
            'interface': 'lo',
            'ip': '127.1.2.3',
            'mask': '255.0.0.0',
            'broadcast': '',
            'interrupt': '',
        }
        info = network.parse_stanza(make_stanza(**parms))
        expected = parms.copy()
        del expected['broadcast']
        del expected['interrupt']
        self.assertEqual(parms, info.as_dict())

    def test_discover_networks_returns_suitable_interfaces(self):
        eth = factory.make_name('eth')
        regular_interface = make_stanza(interface=eth)
        loopback = make_stanza(
            interface='lo', encapsulation='Local loopback', broadcast='',
            interrupt='')
        disabled_interface = make_stanza(ip='', broadcast='', mask='')

        text = join_stanzas([regular_interface, loopback, disabled_interface])
        info = network.parse_ifconfig(text)
        self.assertEqual(1, len(info))
        self.assertEqual(eth, info[0].interface)
