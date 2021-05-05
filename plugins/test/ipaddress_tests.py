# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
The test plugin file for netaddr tests
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type


import json
import re

from ansible.errors import AnsibleError
from ansible.module_utils.basic import missing_required_lib
from ansible.module_utils.six import ensure_text
from functools import wraps


try:
    import ipaddress

    HAS_IPADDRESS = True
except ImportError:
    HAS_IPADDRESS = False


def ip_network(ip):
    """ PY2 compat shim, PY2 requires unicode
    """
    return ipaddress.ip_network(ensure_text(ip))


def ip_address(ip):
    """ PY2 compat shim, PY2 requires unicode
    """
    return ipaddress.ip_address(ensure_text(ip))


def _need_ipaddress(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not HAS_IPADDRESS:
            test = func.__name__.lstrip("_")
            msg = "'{test}' requires 'ipaddress' {stnd}".format(
                test=test,
                stnd=missing_required_lib("ipaddress").replace(
                    "module", "plugin"
                ),
            )
            raise AnsibleError(msg)
        return func(*args, **kwargs)

    return wrapper


def _is_subnet_of(network_a, network_b):
    try:
        if network_a._version != network_b._version:
            return False
        return (
            network_b.network_address <= network_a.network_address
            and network_b.broadcast_address >= network_a.broadcast_address
        )
    except Exception:
        return False


def _to_well_known_type(obj):
    """ Convert an ansible internal type to a well-known type
    ie AnsibleUnicode => str

    :param obj: the obj to convert
    :type obj: unknown
    """
    return json.loads(json.dumps(obj))


def _error_not_list(test, obj):
    tipe = _to_well_known_type(obj)
    if not isinstance(tipe, list):
        msg = "The test '{test}' requires a list, but {obj} was a '{type}'".format(
            test=test, obj=obj, type=type(tipe).__name__
        )
        raise AnsibleError(msg)


@_need_ipaddress
def _in_network(ip, network):
    """Test if an address or network is in a network<br/>`'10.1.1.1' is ansible.netcommon.in_network '10.0.0.0/8'`
    """
    try:
        return _is_subnet_of(ip_network(ip), ip_network(network))
    except Exception:
        return False


def _in_one_network(ip, networks):
    """Test if an IP or network is in one network<br/>`'10.1.1.1' is ansible.netcommon.in_one_network ['10.0.0.0/8', '192.168.1.0/24']`
    """

    _error_not_list("in_one_network", networks)
    bools = [_in_network(ip, network) for network in networks]
    if bools.count(True) == 1:
        return True
    return False


def _in_any_network(ip, networks):
    """Test if an IP or network is in any network<br/>`'10.1.1.1' is ansible.netcommon.in_any_network ['10.0.0.0/8', '192.168.1.0/24']`
    """
    _error_not_list("in_networks", networks)
    bools = [_in_network(ip, network) for network in networks]
    if True in bools:
        return True
    return False


@_need_ipaddress
def _ip(ip):
    """Test if something in an IP address or network<br/>`'10.1.1.1' is ansible.netcommon.ip`
    """
    try:
        ip_network(ip)
        return True
    except Exception:
        return False


@_need_ipaddress
def _ip_address(ip):
    """Test if something in an IP address<br/>`'10.1.1.1' is ansible.netcommon.ip_address`
    """
    try:
        ip_address(ip)
        return True
    except Exception:
        return False


@_need_ipaddress
def _ipv4(ip):
    """Test if something in an IPv4 address or network<br/>`'10.0.0.0/8' is ansible.netcommon.ipv4`
    """
    try:
        return ip_network(ip).version == 4
    except Exception:
        return False


@_need_ipaddress
def _ipv4_address(ip):
    """Test if something in an IPv4 address<br/>`'10.1.1.1' is ansible.netcommon.ipv4_address`
    """
    try:
        return ip_address(ip).version == 4
    except Exception:
        return False


@_need_ipaddress
def _ipv4_hostmask(ip):
    """Test if an address is a hostmask<br/>`'0.0.0.255' is ansible.netcommon.ipv4_hostmask`
    """
    try:
        ipaddr = ip_network("10.0.0.0/{ip}".format(ip=ip))
        return str(ipaddr.hostmask) == ip
    except Exception:
        return False


@_need_ipaddress
def _ipv4_netmask(mask):
    """ Test for a valid IPv4 netmask<br/>`'255.255.255.0' is ansible.netcommon.ipv4_netmask`
    """
    try:
        network = ip_network("10.0.0.0/{mask}".format(mask=mask))
        return str(network.netmask) == mask
    except Exception:
        return False


@_need_ipaddress
def _ipv6(ip):
    """ Test if something is an IPv6 address or network<br/>`'2001:db8:a::123/64' is ansible.netcommon.ipv6`
    """
    try:
        return ip_network(ip).version == 6
    except Exception:
        return False


@_need_ipaddress
def _ipv6_address(ip):
    """ Test if something is an IPv6 address<br/>`'fe80::216:3eff:fee4:16f3' is ansible.netcommon.ipv6_address`
    """
    try:
        return ip_address(ip).version == 6
    except Exception:
        return False


@_need_ipaddress
def _ipv6_ipv4_mapped(ip):
    """ Test if something appears to be a mapped IPv6 to IPv4 mapped address<br/>`'::FFFF:10.1.1.1'' is ansible.netcommon.ipv4_ipv4_mapped`
    """
    try:
        if ip_address(ip).ipv4_mapped is None:
            return False
        return True
    except Exception:
        return False


@_need_ipaddress
def _ipv6_sixtofour(ip):
    """ Test if something appears to be a 6to4 address<br/>`'2002:c0a8:6301:1::1' is ansible.netcommon.ipv6_sixtofour`
    """
    try:
        if ip_address(ip).sixtofour is None:
            return False
        return True
    except Exception:
        return False


@_need_ipaddress
def _ipv6_teredo(ip):
    """ Test if something is an IPv6 teredo address<br/>`'2001::c0a8:6301:1' is ansible.netcommon.ipv6_teredo`
    """
    try:
        if ip_address(ip).teredo is None:
            return False
        return True
    except Exception:
        return False


@_need_ipaddress
def _loopback(ip):
    """ Test if an IP address is a loopback<br/>`'127.10.10.10' is ansible.netcommon.loopback`
    """
    try:
        return ip_address(ip).is_loopback
    except Exception:
        return False


def _mac(mac):
    """ Test if something appears to be a valid mac address<br/>`'02:16:3e:e4:16:f3' is ansible.netcommon.mac`'
    """
    # IEEE EUI-48 upper and lower, commom unix
    re1 = r"^(?i)([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$"
    # Cisco triple hextex
    re2 = r"^(?i)([0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4})$"
    # Bare
    re3 = r"^(?i)[0-9a-f]{12}$"
    regex = "{re1}|{re2}|{re3}".format(re1=re1, re2=re2, re3=re3)
    return bool(re.match(regex, mac))


@_need_ipaddress
def _multicast(ip):
    """ Test for a multicast IP address<br/>`'224.0.0.1' is ansible.netcommon.multicast`
    """
    try:
        return ip_address(ip).is_multicast
    except Exception:
        return False


@_need_ipaddress
def _private(ip):
    """ Test if an IP address is private<br/>`'10.1.1.1' is ansible.netcommon.private`
    """
    try:
        return ip_address(ip).is_private
    except Exception:
        return False


@_need_ipaddress
def _public(ip):
    """ Test if an IP address is public<br/>`'8.8.8.8' is ansible.netcommon.public`
    """
    try:
        return ip_address(ip).is_global
    except Exception:
        return False


@_need_ipaddress
def _reserved(ip):
    """ Test for a reserved IP address<br/>`'253.0.0.1' is ansible.netcommon.reserved`
    """
    try:
        return ip_address(ip).is_reserved
    except Exception:
        return False


@_need_ipaddress
def _subnet_of(network_a, network_b):
    """Test if a network is a subnet of another network<br/>`'10.1.1.0/24' is ansible.netcommon.subnet_of '10.0.0.0/8'`
    """
    try:
        return _is_subnet_of(ip_network(network_a), ip_network(network_b))
    except Exception:
        return False


@_need_ipaddress
def _supernet_of(network_a, network_b):
    """Test if an network is a supernet of another network<br/>`'10.0.0.0/8' is ansible.netcommon.supernet_of '10.1.1.0/24'`
    """
    try:
        return _is_subnet_of(ip_network(network_b), ip_network(network_a))
    except Exception:
        return False


@_need_ipaddress
def _unspecified(ip):
    """ Test for a unicast IP address<br/>`'0.0.0.0' is ansible.netcommon.unspecifed`
    """
    try:
        return ip_address(ip).is_unspecified
    except Exception:
        return False


class TestModule(object):
    """ network jinja tests
    """

    test_map = {
        "in_any_network": _in_any_network,
        "in_network": _in_network,
        "in_one_network": _in_one_network,
        "ip_address": _ip_address,
        "ip": _ip,
        "ipv4": _ipv4,
        "ipv4_address": _ipv4_address,
        "ipv4_hostmask": _ipv4_hostmask,
        "ipv4_netmask": _ipv4_netmask,
        "ipv6": _ipv6,
        "ipv6_address": _ipv6_address,
        "ipv6_ipv4_mapped": _ipv6_ipv4_mapped,
        "ipv6_sixtofour": _ipv6_sixtofour,
        "ipv6_teredo": _ipv6_teredo,
        "loopback": _loopback,
        "mac": _mac,
        "multicast": _multicast,
        "private": _private,
        "public": _public,
        "reserved": _reserved,
        "subnet_of": _subnet_of,
        "supernet_of": _supernet_of,
        "unspecified": _unspecified,
    }

    def tests(self):
        return self.test_map
