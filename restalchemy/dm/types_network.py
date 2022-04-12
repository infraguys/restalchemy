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
FQDN_MAX_LEN = 255

MATCH_DN = re.compile("[a-z0-9-]{1,%d}$" % DNS_LABEL_MAX_LEN)
# RFC 1123 hints that a TLD can't be all numeric. last is a TLD if
# it's an FQDN.
MATCH_TDL = re.compile("^[0-9]+$")


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
    pattern = re.compile(
        u"^([а-яА-ЯёЁa-zA-Z0-9-_]{1,61}\.{0,1}){0,30}$")  # noqa

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


class HostName(types.String):

    def __init__(self):
        super(HostName, self).__init__(min_length=1, max_length=FQDN_MAX_LEN)

    def validate(self, value):
        if not super(HostName, self).validate(value):
            return False

        names = value.split('.')

        for name in names:
            if (not name
                    or name[-1] == '-'
                    or name[0] == '-'
                    or not MATCH_DN.match(name)):
                return False

        return True


class AddressRecordName(HostName):

    def validate(self, value):
        names = value.split('.')

        if len(names) == 1 and names[0] in ['*', '@']:
            return True
        if len(names) >= 1 and names[0] == '*':
            value = '.'.join(names[1:])

        if not super(AddressRecordName, self).validate(value):
            return False

        return True


class FQDN(HostName):

    def validate(self, value):

        names = value.split('.')
        if names[-1]:
            return False
        value = '.'.join(names[:-1])

        if not super(FQDN, self).validate(value):
            return False

        if MATCH_TDL.match(names[-2]):
            return False

        return True
