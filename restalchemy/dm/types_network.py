# coding=utf-8
#
# Copyright 2021 George Melikov
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import netaddr
import re

from restalchemy.dm import types

DNS_LABEL_MAX_LEN = 63
FQDN_MAX_LEN = 254
HOSTNAME_MAX_LEN = FQDN_MAX_LEN - 1


class IPAddress(types.BaseType):

    def validate(self, value):
        return isinstance(value, netaddr.IPAddress)

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        return netaddr.IPAddress(value)

    def from_unicode(self, value):
        return self.from_simple_type(value)


class Network(types.BaseType):

    def validate(self, value):
        return isinstance(value, netaddr.IPNetwork)

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        return netaddr.IPNetwork(value).cidr

    def from_unicode(self, value):
        return self.from_simple_type(value)


class IpWithMask(types.BaseType):

    def validate(self, value):
        return isinstance(value, netaddr.IPNetwork)

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        return netaddr.IPNetwork(value)

    def from_unicode(self, value):
        return self.from_simple_type(value)


class OUI(types.BaseCompiledRegExpTypeFromAttr):
    pattern = re.compile(r"^([0-9a-fA-F]{2,2}:){2,2}[0-9a-fA-F]{2,2}$")


class RecordName(types.BaseCompiledRegExpTypeFromAttr):
    pattern = re.compile(r"^([a-zA-Z0-9-_]{1,61}\.{0,1}){0,30}$")

    def from_simple_type(self, value):
        converted_value = super(RecordName, self).from_simple_type(value)
        return converted_value.rstrip('.').rstrip('@')

    def to_simple_type(self, value):
        converted_value = super(RecordName, self).to_simple_type(value)
        return converted_value if len(converted_value) > 0 else '@'


class SrvName(RecordName):
    def validate(self, value):
        parts = value.split(".")
        if len(parts) < 2:
            return False

        if not parts[0].startswith("_"):
            return False

        if not parts[1].startswith("_"):
            return False

        record_name = ".".join(parts[2:])

        if record_name and not super(SrvName, self).validate(record_name):
            return False

        return True


class FQDN(types.BaseCompiledRegExpTypeFromAttr):
    '''FQDN type. Allows 1 level too. Root only is prohibited.

    See https://github.com/powerdns/pdns/blob/master/pdns/dnsname.cc#L44
    and https://github.com/powerdns/pdns/blob/master/pdns/ws-api.cc#L387
    '''
    pattern = re.compile(
        r"(?=^.{2,%i}$)(^((?!-)[a-zA-Z0-9-_]{1,%i}(?<!-)\.){1,}$)" %
        (FQDN_MAX_LEN, DNS_LABEL_MAX_LEN))


class Hostname(types.BaseCompiledRegExpTypeFromAttr):
    '''Same as FQDN but without root dot. Allows 1 level too. '''
    pattern = re.compile(
        r"(?=^.{1,%i}$)(^((?!-)[a-zA-Z0-9-_]{1,%i}(?<!-)\.)*"
        r"((?!-)[a-zA-Z0-9-_]{1,%i}(?<!-))$)" %
        (HOSTNAME_MAX_LEN, DNS_LABEL_MAX_LEN, DNS_LABEL_MAX_LEN)
    )
