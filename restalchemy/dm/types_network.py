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
FQDN_MIN_LEVELS = 1
FQDN_TEMPLATE = r"(?=^.{2,%i}$)(^((?!-)[a-zA-Z0-9-_]{1,%i}(?<!-)\.){%i,}$)"
HOSTNAME_MIN_LEVELS = 1
LEADING_UNDERSCORE_GROUP = "(_?)"
UNDERSCORE = "_"
HOSTNAME_TEMPLATE = (
    r"(?=^.{1,%i}$)(^%s((?![-%s])[a-zA-Z0-9-%s]{1,%i}"
    r"(?<![-%s])\.){%i,}((?!-)[a-zA-Z0-9-]{1,%i}(?<!-))$)"
)


class IPAddress(types.BaseType):

    def __init__(self, **kwargs):
        super(IPAddress, self).__init__(openapi_type="string", **kwargs)

    def validate(self, value):
        return isinstance(value, netaddr.IPAddress)

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        return netaddr.IPAddress(value)

    def from_unicode(self, value):
        return self.from_simple_type(value)

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self.openapi_type,
            "anyOf": [{"format": "ipv4"}, {"format": "ipv6"}],
        }
        spec.update(
            types.build_prop_kwargs(
                kwargs=prop_kwargs, to_simple_type=self.to_simple_type
            )
        )
        return spec


class Network(types.BaseType):

    def __init__(self, **kwargs):
        super(Network, self).__init__(openapi_type="string", **kwargs)

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
        return converted_value.rstrip(".").rstrip("@")

    def to_simple_type(self, value):
        converted_value = super(RecordName, self).to_simple_type(value)
        return converted_value if len(converted_value) > 0 else "@"


class RecordNameWithWildcard(RecordName):
    # Difference - allow wildcard at the beginning of domain name.
    pattern = re.compile(r"^(\*\.){0,1}([a-zA-Z0-9-_]{1,61}\.{0,1}){0,30}$")


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
    """FQDN type. Allows 1 level too. Root only is prohibited.

    See https://github.com/powerdns/pdns/blob/master/pdns/dnsname.cc#L44
    and https://github.com/powerdns/pdns/blob/master/pdns/ws-api.cc#L387
    """

    pattern = re.compile(
        FQDN_TEMPLATE % (FQDN_MAX_LEN, DNS_LABEL_MAX_LEN, FQDN_MIN_LEVELS)
    )

    def __init__(self, min_levels=FQDN_MIN_LEVELS, **kwargs):
        if min_levels > FQDN_MIN_LEVELS:
            self.pattern = re.compile(
                FQDN_TEMPLATE % (FQDN_MAX_LEN, DNS_LABEL_MAX_LEN, min_levels)
            )
        super(FQDN, self).__init__(**kwargs)


class Hostname(types.BaseCompiledRegExpTypeFromAttr):
    """Same as FQDN but without root dot. Allows 1 level too."""

    def __init__(
        self,
        min_levels=HOSTNAME_MIN_LEVELS,
        allow_leading_underscore=False,
        allow_middle_underscore=False,
        **kwargs
    ):
        underscore_or_empty = UNDERSCORE if allow_middle_underscore else ""
        self.pattern = re.compile(
            HOSTNAME_TEMPLATE
            % (
                HOSTNAME_MAX_LEN,
                LEADING_UNDERSCORE_GROUP if allow_leading_underscore else "",
                underscore_or_empty,
                underscore_or_empty,
                DNS_LABEL_MAX_LEN,
                underscore_or_empty,
                max([min_levels, HOSTNAME_MIN_LEVELS]) - 1,
                DNS_LABEL_MAX_LEN,
            )
        )
        super(Hostname, self).__init__(**kwargs)


class IPRange(types.BaseType):
    """IPRange type.

    This type represents an IP range as a string. The string is expected
    to be in the format: <start_ip>-<end_ip>
    where <start_ip> and <end_ip> are valid IPv4 address.
    """

    SEPARATOR = "-"

    def __init__(self, **kwargs):
        super(IPRange, self).__init__(openapi_type="string", **kwargs)

    def validate(self, value):
        return isinstance(value, netaddr.IPRange)

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        return netaddr.IPRange(*value.split(self.SEPARATOR))

    def from_unicode(self, value):
        return self.from_simple_type(value)
