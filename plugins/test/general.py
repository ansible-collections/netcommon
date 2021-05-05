# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Simple, dependancy free convenience tests
"""
from __future__ import absolute_import, division, print_function

__metaclass__ = type


import socket

from ansible.errors import AnsibleError
from ansible.module_utils.basic import missing_required_lib

try:
    import ipaddress

    HAS_IPADDRESS = True
except ImportError:
    HAS_IPADDRESS = False


def _need_ipaddress(func):
    def wrapper(*args, **kwargs):
        if not HAS_IPADDRESS:
            msg = "'{test}' requires 'ipaddress' {stnd}".format(
                test=func.__name__,
                stnd=missing_required_lib("ipaddress").replace(
                    "module", "plugin"
                ),
            )
            raise AnsibleError(msg)
        return func(*args, **kwargs)

    return wrapper


def disabled(str):
    """ Case insensitive test for `disabled`<br/>`interface.ip_redirects is ansible.netcommon.disabled`
    """
    try:
        return str.lower() == "disabled"
    except Exception:
        return False


def down(str):
    """ Case insensitive test for `down`<br/>`interface.oper_state is ansible.netcommon.down`
    """
    try:
        return str.lower() == "down"
    except Exception:
        return False


def enabled(str):
    """ Case insensitive test for `enabled`<br/>`interface.bpdu_guard is ansible.netcommon.enabled`
    """
    try:
        return str.lower() == "enabled"
    except Exception:
        return False


@_need_ipaddress
def resolvable(str):
    """ Test if an IP or name can be resolved via /etc/hosts or DNS<br/>`'docs.ansible.com' is ansible.netcommon.resolvable`
    """
    try:
        ipaddress.ip_address(str)
        ip = True
    except Exception:
        ip = False
    if ip:
        try:
            socket.gethostbyaddr(str)
            return True
        except Exception:
            return False
    else:
        try:
            socket.getaddrinfo(str, None)
            return True
        except Exception:
            return False


def up(str):
    """ Case insensitve test for `up`<br/>`interface.admin_state is ansible.netcommon.up`
    """
    try:
        return str.lower() == "up"
    except Exception:
        return False


class TestModule(object):
    """ network jinja tests
    """

    test_map = {
        "disabled": disabled,
        "down": down,
        "enabled": enabled,
        "resolvable": resolvable,
        "up": up,
    }

    def tests(self):
        return self.test_map
