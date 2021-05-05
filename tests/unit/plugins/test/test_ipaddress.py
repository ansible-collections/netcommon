# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
The test plugin file for netaddr tests
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import unittest  # TestCase, assertTrue
import ansible_collections.ansible.netcommon.plugins.test.ipaddress_tests as ipaddress
from ansible.template import Templar

TESTS = [
    "{{ '10.1.1.1' is ansible.netcommon.in_network '10.0.0.0/8' }}",
    "{{ '10.1.1.1' is not ansible.netcommon.in_network '192.168.1.0/24' }}",
    "{{ '2001:db8:a::123' is ansible.netcommon.in_network '2001:db8:a::/64' }}",
    "{{ '2001:db8:a::123' is not ansible.netcommon.in_network '10.0.0.0/8' }}",
    "{{ '2001:db8:a::123' is not ansible.netcommon.in_network 'string' }}",
    "{{ '10.1.1.1' is ansible.netcommon.in_one_network ['10.0.0.0/8', '192.168.1.0/24'] }}",
    "{{ '10.1.1.1' is not ansible.netcommon.in_one_network ['10.0.0.0/8', '10.1.1.0/24'] }}",
    "{{ '10.1.1.1' is ansible.netcommon.in_any_network ['10.0.0.0/8', '192.168.1.0/24'] }}",
    "{{ '8.8.8.8' is not ansible.netcommon.in_any_network ['10.0.0.0/8', '192.168.1.0/24', '172.16.0.0/16'] }}",
    "{{ '10.1.1.1' is ansible.netcommon.ip }}",
    "{{ 'string' is not ansible.netcommon.ip }}",
    "{{ '300.1.1.1' is not ansible.netcommon.ip }}",
    "{{ '10.1.1.1' is ansible.netcommon.ip_address }}",
    "{{ 'string' is not ansible.netcommon.ip_address }}",
    "{{ '10.0.0.0/8' is not ansible.netcommon.ip_address }}",
    "{{ '10.1.1.1' is ansible.netcommon.ipv4 }}",
    "{{ 'fe80::216:3eff:fee4:16f3' is not ansible.netcommon.ipv4 }}",
    "{{ '10.1.1.1' is ansible.netcommon.ipv4_address }}",
    "{{ '10.1.1.1/31' is not ansible.netcommon.ipv4_address }}",
    "{{ '0.1.255.255' is ansible.netcommon.ipv4_hostmask }}",
    "{{ '255.255.255.0' is not ansible.netcommon.ipv4_hostmask }}",
    "{{ '255.255.255.0' is ansible.netcommon.ipv4_netmask }}",
    "{{ '255.255.255.128' is ansible.netcommon.ipv4_netmask }}",
    "{{ '255.255.255.127' is not ansible.netcommon.ipv4_netmask }}",
    "{{ 'fe80::216:3eff:fee4:16f3' is ansible.netcommon.ipv6 }}",
    "{{ '2001:db8:a::/64' is ansible.netcommon.ipv6 }}",
    "{{ 'fe80::216:3eff:fee4:16f3' is ansible.netcommon.ipv6_address }}",
    "{{ '2001:db8:a::123/64' is not ansible.netcommon.ipv6_address }}",
    "{{ '::FFFF:10.1.1.1' is ansible.netcommon.ipv6_ipv4_mapped }}",
    "{{ '::AAAA:10.1.1.1' is not ansible.netcommon.ipv6_ipv4_mapped }}",
    "{{ 'string' is not ansible.netcommon.ipv6_ipv4_mapped }}",
    "{{ '2002:c0a8:6301:1::1' is ansible.netcommon.ipv6_sixtofour }}",
    "{{ '2001:c0a8:6301:1::1' is not ansible.netcommon.ipv6_sixtofour }}",
    "{{ 'string' is not ansible.netcommon.ipv6_sixtofour }}",
    "{{ '2001::c0a8:6301:1' is ansible.netcommon.ipv6_teredo }}",
    "{{ '2002::c0a8:6301:1' is not ansible.netcommon.ipv6_teredo }}",
    "{{ 'string' is not ansible.netcommon.ipv6_teredo }}",
    "{{ '127.10.10.10' is ansible.netcommon.loopback }}",
    "{{ '10.1.1.1' is not ansible.netcommon.loopback }}",
    "{{ '::1' is ansible.netcommon.loopback }}",
    "{{ '02:16:3e:e4:16:f3' is ansible.netcommon.mac }}",
    "{{ '02-16-3e-e4-16-f3' is ansible.netcommon.mac }}",
    "{{ '0216.3ee4.16f3' is ansible.netcommon.mac }}",
    "{{ '02163ee416f3' is ansible.netcommon.mac }}",
    "{{ 'string' is not ansible.netcommon.mac }}",
    "{{ '224.0.0.1' is ansible.netcommon.multicast }}",
    "{{ '127.0.0.1' is not ansible.netcommon.multicast }}",
    "{{ '10.1.1.1' is ansible.netcommon.private }}",
    "{{ '8.8.8.8' is not ansible.netcommon.private }}",
    "{{ '8.8.8.8' is ansible.netcommon.public }}",
    "{{ '10.1.1.1' is not ansible.netcommon.public }}",
    "{{ '253.0.0.1' is ansible.netcommon.reserved }}",
    "{{ '128.146.1.7' is not ansible.netcommon.reserved }}",
    "{{ '10.1.1.0/24' is ansible.netcommon.subnet_of '10.0.0.0/8' }}",
    "{{ '192.168.1.0/24' is not ansible.netcommon.subnet_of '10.0.0.0/8' }}",
    "{{ '10.0.0.0/8' is ansible.netcommon.supernet_of '10.1.1.0/24' }}",
    "{{ '0.0.0.0' is ansible.netcommon.unspecified }}",
    "{{ '0:0:0:0:0:0:0:0' is ansible.netcommon.unspecified }}",
    "{{ '::' is ansible.netcommon.unspecified }}",
    "{{ '::1' is not ansible.netcommon.unspecified }}",
]


class TestIpaddress(unittest.TestCase):
    def setUp(self):
        self._templar = Templar(loader=None, variables=vars)

    def test_simple(self):
        """ Confirm some simple jinja tests
        """
        for test in TESTS:
            self.assertTrue(self._templar.template(test), test)

    def test_no_lib(self):
        """ Confirm missing lib
        """
        ipaddress.HAS_IPADDRESS = False
        template_data = "{{ '10.1.1.1' is ansible.netcommon.ip }}"
        with self.assertRaises(Exception) as error:
            self._templar.template(template_data)
        self.assertIn("'ip' requires 'ipaddress'", str(error.exception))

    def test_fail_subnet(self):
        """ Confirm non ip obj passed to is_subnet_of
        """
        self.assertFalse(ipaddress._is_subnet_of("a", "b"))

    def fail_list_needed(self):
        """ Confirm graceful fail when list is requried but not provided
        """
        template_data = "{{ '10.1.1.1' is not ansible.netcommon.in_one_network '10.0.0.0/8' }}"
        with self.assertRaises(Exception) as error:
            self._templar.template(template_data)
        self.assertIn("'in_one_network' requires a list", str(error.exception))
