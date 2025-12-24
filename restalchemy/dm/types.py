# Copyright 2014 Eugene Frolov <eugene@frolov.net.ru>
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

import abc
import copy
import ctypes
import datetime
import decimal
import json
import re
import sys
import time
import uuid

import email_validator


INFINITY = float("inf")
INFINITI = INFINITY  # TODO(d.burmistrov): remove this hack
UUID_RE_TEMPLATE = (
    r"[0-9a-fA-F]{8}"
    r"-"
    r"[0-9a-fA-F]{4}"
    r"-"
    r"[0-9a-fA-F]{4}"
    r"-"
    r"[0-9a-fA-F]{4}"
    r"-"
    r"[0-9a-fA-F]{12}"
)

TIMEDELTA_INFINITY = (1 << (ctypes.sizeof(ctypes.c_int()) * 8) - 1) - 1

# Copy-paste from validators library because RA must support python 2.7
# and support cyrillic domain names. The validators library is located:
# https://github.com/kvesteri/validators/blob/master/validators/domain.py#L5
# the regexp has issue https://github.com/kvesteri/validators/issues/185
HOSTNAME_RE_TEMPLATE = (
    # First character of the domain
    "^(?:[a-zA-Z0-9]"
    # Sub domain + hostname
    "(?:[a-zA-Z0-9-_]{0,61}[A-Za-z0-9])?\.)"  # noqa
    # First 61 characters of the gTLD
    "+[A-Za-z0-9][A-Za-z0-9-_]{0,61}"
    # Last character of the gTLD
    "[A-Za-z]$"
)
KWARGS_OPENAPI_MAP = {
    "read_only": "readOnly",
    "default": "default",
    "example": "example",
}
MYSQL_DATETIME_FMT = "%Y-%m-%d %H:%M:%S.%f"
DEFAULT_DATE = datetime.datetime.strptime(
    "2006-01-02 15:04:05.000576", MYSQL_DATETIME_FMT
)
DEFAULT_DATE_Z = DEFAULT_DATE.replace(tzinfo=datetime.timezone.utc)
# RFC3339
# python's datetime doesn't support nanosecond precision
# + now without timezone, example "2006-01-02T15:04:05.999999999Z07:00"
OPENAPI_DATETIME_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def build_prop_kwargs(kwargs, to_simple_type=None):
    result = {}
    for k, v in KWARGS_OPENAPI_MAP.items():
        if k in kwargs.keys():
            value = kwargs[k]() if callable(kwargs[k]) else kwargs[k]
            if isinstance(value, (UUID, uuid.UUID, bool)):
                # No default value for uuid and bool
                continue
            elif isinstance(value, datetime.datetime):
                value = DEFAULT_DATE.strftime(OPENAPI_DATETIME_FMT)
            elif hasattr(value, "__dict__"):
                value = {
                    name: prop.get_property_type().to_simple_type(value[name])
                    for name, prop in value.properties.properties.items()
                }
            elif to_simple_type is not None:
                value = to_simple_type(value)

            result[v] = value
    return result


class BaseType(metaclass=abc.ABCMeta):

    def __init__(self, openapi_type="object", openapi_format=None):
        super(BaseType, self).__init__()
        self._openapi_type = openapi_type
        self._openapi_format = openapi_format

    @abc.abstractmethod
    def validate(self, value):
        pass

    @abc.abstractmethod
    def to_simple_type(self, value):
        pass

    def dump_value(self, value):
        return self.to_simple_type(value)

    @abc.abstractmethod
    def from_simple_type(self, value):
        pass

    @abc.abstractmethod
    def from_unicode(self, value):
        pass

    def __repr__(self):
        return self.__class__.__name__

    @property
    def ra_type(self):
        return self.__class__

    @property
    def openapi_type(self):
        return self._openapi_type

    @property
    def openapi_format(self):
        return self._openapi_format

    def to_openapi_spec(self, prop_kwargs):
        spec = {"type": self._openapi_type}
        if self._openapi_format is not None:
            spec["format"] = self._openapi_format
        spec.update(
            build_prop_kwargs(
                kwargs=prop_kwargs, to_simple_type=self.to_simple_type
            )
        )
        return spec


class BasePythonType(BaseType):

    def __init__(self, python_type, **kwargs):
        super(BasePythonType, self).__init__(**kwargs)
        self._python_type = python_type

    def validate(self, value):
        return isinstance(value, self._python_type)

    def to_simple_type(self, value):
        return value

    def from_simple_type(self, value):
        return value

    def from_unicode(self, value):
        return self._python_type(value)


class Boolean(BasePythonType):

    def __init__(self):
        super(Boolean, self).__init__(bool, openapi_type="boolean")

    def from_simple_type(self, value):
        return bool(value)

    def from_unicode(self, value):
        return value.lower() in ["yes", "true", "1"]


class String(BasePythonType):

    def __init__(self, min_length=0, max_length=sys.maxsize, **kwargs):
        openapi_type = kwargs.pop("openapi_type", "string")
        super(String, self).__init__(str, openapi_type=openapi_type, **kwargs)
        self.min_length = int(min_length)
        self.max_length = int(max_length)

    def validate(self, value):
        result = super(String, self).validate(value)
        return result and self.min_length <= len(str(value)) <= self.max_length

    def from_unicode(self, value):
        return str(value)

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self.openapi_type,
            "minLength": self.min_length,
            "maxLength": self.max_length,
        }
        spec.update(build_prop_kwargs(kwargs=prop_kwargs))
        return spec


class Email(String):

    def __init__(
        self,
        min_length=5,
        max_length=254,
        check_deliverability=False,
        **kwargs
    ):
        """
        Email type.

        :param min_length: Minimum length of email
        :param max_length: Maximum length of email
        :param check_deliverability: check email deliverability, default: False
        :param \\*\\*kwargs: Additional keyword arguments
        """
        openapi_type = kwargs.pop("openapi_type", "string")
        openapi_format = kwargs.pop("openapi_format", "email")
        super(Email, self).__init__(
            min_length=min_length,
            max_length=max_length,
            openapi_type=openapi_type,
            openapi_format=openapi_format,
            **kwargs
        )
        self._check_deliverability = check_deliverability

    def validate(self, value):
        """
        Validates given value as an email address.

        :param value: Value to validate
        :return: True if value is valid, False otherwise
        """
        result = super(Email, self).validate(value)
        try:
            email_validator.validate_email(
                value,
                check_deliverability=self._check_deliverability,
            )
        except email_validator.EmailNotValidError:
            return False
        return result


class Integer(BasePythonType):

    def __init__(self, min_value=-INFINITY, max_value=INFINITY):
        super(Integer, self).__init__(int, openapi_type="integer")
        self.min_value = (
            min_value if min_value == -INFINITY else int(min_value)
        )
        self.max_value = max_value if max_value == INFINITY else int(max_value)

    def validate(self, value):
        result = super(Integer, self).validate(value)
        return result and self.min_value <= value <= self.max_value

    def from_unicode(self, value):
        return int(value)

    @property
    def max_openapi_value(self):
        if self.max_value == INFINITI:
            return sys.maxsize
        else:
            return self.max_value

    @property
    def min_openapi_value(self):
        if self.min_value == -INFINITI:
            return -sys.maxsize
        else:
            return self.min_value

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self.openapi_type,
            "minimum": self.min_openapi_value,
            "maximum": self.max_openapi_value,
        }
        spec.update(build_prop_kwargs(kwargs=prop_kwargs))
        return spec


class Int8(Integer):
    def __init__(self):
        super(Int8, self).__init__(min_value=0, max_value=2**8 - 1)


class Float(BasePythonType):

    def __init__(self, min_value=-INFINITY, max_value=INFINITY):
        super(Float, self).__init__(
            float, openapi_type="number", openapi_format="float"
        )
        self.min_value = (
            min_value if min_value == -INFINITY else float(min_value)
        )
        self.max_value = (
            max_value if max_value == INFINITY else float(max_value)
        )

    def validate(self, value):
        result = super(Float, self).validate(value)
        return result and self.min_value <= value <= self.max_value

    @property
    def max_openapi_value(self):
        if self.max_value == INFINITI:
            return sys.float_info.max
        else:
            return self.max_value

    @property
    def min_openapi_value(self):
        if self.min_value == -INFINITI:
            return -sys.float_info.max
        else:
            return self.min_value

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self.openapi_type,
            "format": self.openapi_format,
            "minimum": self.min_openapi_value,
            "maximum": self.max_openapi_value,
        }
        spec.update(build_prop_kwargs(kwargs=prop_kwargs))
        return spec


class Decimal(BasePythonType):
    def __init__(
        self, min_value=-INFINITY, max_value=INFINITY, max_decimal_places=None
    ):
        super().__init__(
            python_type=decimal.Decimal,
            openapi_type="string",
            openapi_format="decimal",
        )
        self.min_value = decimal.Decimal(min_value)
        self.max_value = decimal.Decimal(max_value)
        self.max_decimal_places = max_decimal_places

    def validate(self, value):
        return (
            isinstance(value, decimal.Decimal)
            and self.min_value <= value <= self.max_value
            and (
                (self.max_decimal_places is None)
                or -value.as_tuple().exponent <= self.max_decimal_places
            )
        )

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        return decimal.Decimal(str(value))

    def from_unicode(self, value):
        return self.from_simple_type(value)

    @property
    def max_openapi_value(self):
        if self.max_value == INFINITY:
            return sys.maxsize
        else:
            return int(self.max_value)

    @property
    def min_openapi_value(self):
        if self.min_value == -INFINITY:
            return -sys.maxsize
        else:
            return int(self.min_value)

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self.openapi_type,
            "minimum": self.min_openapi_value,
            "maximum": self.max_openapi_value,
        }
        if self._openapi_format is not None:
            spec["format"] = self._openapi_format
        spec.update(
            build_prop_kwargs(
                kwargs=prop_kwargs, to_simple_type=self.to_simple_type
            )
        )
        return spec


class UUID(BaseType):

    def __init__(self):
        super(UUID, self).__init__(
            openapi_type="string", openapi_format="uuid"
        )

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)

    def validate(self, value):
        return isinstance(value, uuid.UUID)

    def from_unicode(self, value):
        return uuid.UUID(value)


class ComplexPythonType(BasePythonType):

    _TYPE_ERROR_MSG = "Can't convert '%s' with type '%s' into %s"

    def _raise_on_invalid_type(self, value):
        if not isinstance(value, self._python_type):
            raise TypeError(
                self._TYPE_ERROR_MSG % (value, type(value), self._python_type)
            )

    def from_simple_type(self, value):
        self._raise_on_invalid_type(value)
        return value

    def from_unicode(self, value):
        result = None
        try:
            result = json.loads(value)
        except (TypeError, ValueError):
            pass
        self._raise_on_invalid_type(value)
        return self.from_simple_type(result)


class List(ComplexPythonType):

    def __init__(self):
        super(List, self).__init__(
            list, openapi_type="array", openapi_format="string"
        )

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self.openapi_type,
            "format": self.openapi_format,
            "items": {"type": "string"},
        }
        spec.update(build_prop_kwargs(kwargs=prop_kwargs))
        return spec


class TypedList(List):

    def __init__(self, nested_type):
        super(TypedList, self).__init__()
        if not isinstance(nested_type, BaseType):
            raise TypeError(
                "Nested type '%s' is not inherited from %s"
                % (nested_type, BaseType)
            )
        self._nested_type = nested_type

    def validate(self, value):
        return super(TypedList, self).validate(value) and all(
            self._nested_type.validate(item) for item in value
        )

    def to_simple_type(self, value):
        return [self._nested_type.to_simple_type(e) for e in value]

    def from_simple_type(self, value):
        return [self._nested_type.from_simple_type(e) for e in value]

    def from_unicode(self, value):
        if not isinstance(value, str):
            raise TypeError("Value must be str, not %s", type(value))

        value = self._nested_type.from_unicode(value)
        return [value]

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self.openapi_type,
            "items": self._nested_type.to_openapi_spec({}),
        }
        spec.update(
            build_prop_kwargs(
                kwargs=prop_kwargs, to_simple_type=self.to_simple_type
            )
        )
        return spec


class Dict(ComplexPythonType):

    def __init__(self):
        super(Dict, self).__init__(dict)

    def validate(self, value):
        return super(Dict, self).validate(value) and all(
            isinstance(k, str) for k in value
        )

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": "object",
            "additionalProperties": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "integer"},
                    {"type": "boolean"},
                    {"type": "object"},
                    {"type": "array", "items": {}},
                ]
            },
        }
        spec.update(build_prop_kwargs(kwargs=prop_kwargs))
        return spec


def _validate_scheme(scheme):
    non_string_keys = []
    invalid_types = []

    for key, val in scheme.items():
        if not isinstance(key, str):
            non_string_keys.append(key)
        if not isinstance(val, BaseType):
            invalid_types.append(val)

    if non_string_keys:
        raise ValueError("Scheme keys %r are not strings" % non_string_keys)
    if invalid_types:
        raise ValueError(
            "Scheme values %r are not %s instances" % (invalid_types, BaseType)
        )


# TODO(d.burmistrov): we have to make this group of Dict Schemers:
#   - ExactSchemaDict - data must follow schema in every detail
#   - PartialSchemaDict - data must be within schema definition (some keys
#                         may be missing)
#   - ExtraSchemaDict - data must follow schema but may have extra keys
#   - not sure about this option: there may be extra keys (not defined
#     in schema) and some schema keys may be missing, but all defined keys
#     matching schema must be valid due to schema


class SoftSchemeDict(Dict):

    def __init__(self, scheme):
        super(SoftSchemeDict, self).__init__()
        _validate_scheme(scheme)
        self._scheme = scheme

    def validate(self, value):
        return (
            super(SoftSchemeDict, self).validate(value)
            and set(value.keys()).issubset(set(self._scheme.keys()))
            and all(self._scheme[k].validate(v) for k, v in value.items())
        )

    def to_simple_type(self, value):
        return {k: self._scheme[k].to_simple_type(v) for k, v in value.items()}

    def from_simple_type(self, value):
        value = super(SoftSchemeDict, self).from_simple_type(value)
        return {
            k: self._scheme[k].from_simple_type(v) for k, v in value.items()
        }

    def to_openapi_spec(self, prop_kwargs):
        spec = {"type": "object", "properties": {}}
        for k, v in self._scheme.items():
            spec["properties"][k] = v.to_openapi_spec(prop_kwargs)
        return spec


class SchemeDict(Dict):

    def __init__(self, scheme):
        super(SchemeDict, self).__init__()
        _validate_scheme(scheme)
        self._scheme = scheme

    def validate(self, value):
        return (
            super(SchemeDict, self).validate(value)
            and set(value.keys()) == set(self._scheme.keys())
            and all(
                scheme.validate(value[key])
                for key, scheme in self._scheme.items()
            )
        )

    def to_simple_type(self, value):
        return {
            key: scheme.to_simple_type(value[key])
            for key, scheme in self._scheme.items()
        }

    def from_simple_type(self, value):
        value = super(SchemeDict, self).from_simple_type(value)
        return {
            key: scheme.from_simple_type(value.get(key, None))
            for key, scheme in self._scheme.items()
        }

    def to_openapi_spec(self, prop_kwargs):
        spec = {"type": "object", "properties": {}}
        for k, v in self._scheme.items():
            spec["properties"][k] = v.to_openapi_spec(prop_kwargs)
        return spec


class TypedDict(Dict):

    def __init__(self, nested_type):
        super(TypedDict, self).__init__()
        if not isinstance(nested_type, BaseType):
            raise TypeError(
                "Nested type '%s' is not inherited from %s"
                % (nested_type, BaseType)
            )
        self._nested_type = nested_type

    def validate(self, value):
        return super(TypedDict, self).validate(value) and all(
            self._nested_type.validate(element) for element in value.values()
        )

    def to_simple_type(self, value):
        return {
            k: self._nested_type.to_simple_type(v) for k, v in value.items()
        }

    def from_simple_type(self, value):
        value = super(TypedDict, self).from_simple_type(value)
        return {
            k: self._nested_type.from_simple_type(v) for k, v in value.items()
        }

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self._openapi_type,
            "additionalProperties": self._nested_type.to_openapi_spec({}),
        }
        if self._openapi_format is not None:
            spec["format"] = self._openapi_format
        spec.update(
            build_prop_kwargs(
                kwargs=prop_kwargs, to_simple_type=self.to_simple_type
            )
        )
        return spec


class UTCDateTime(BasePythonType):
    """Deprecated utc datetime type. Use UTCDateTimeZ instead.

    UTCDateTime should be used only for compatibility,
    when you use naive datetime objects without datetimes.
    It's strongly recommended to use UTCDateTimeZ.
    """

    def __init__(self):
        super(UTCDateTime, self).__init__(
            python_type=datetime.datetime,
            openapi_type="string",
            openapi_format="date-time",
        )

    def validate(self, value):
        return isinstance(value, datetime.datetime) and (
            value.tzinfo == datetime.timezone.utc or value.tzinfo is None
        )

    def to_simple_type(self, value):
        return value.strftime(MYSQL_DATETIME_FMT)

    def dump_value(self, value):
        # Converting value in api response
        return value.strftime(OPENAPI_DATETIME_FMT)

    def from_simple_type(self, value):
        if isinstance(value, datetime.datetime):
            return value
        try:
            return datetime.datetime.strptime(value, MYSQL_DATETIME_FMT)
        except ValueError:
            # Used in cases, than we manually convert openapi string in
            # http response to ra type in model
            return datetime.datetime.strptime(value, OPENAPI_DATETIME_FMT)

    def from_unicode(self, value):
        return self.from_simple_type(value)

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self._openapi_type,
            # https://github.com/ogen-go/ogen/blob/main/_testdata/positive/time_extension.yml#L29
            "x-ogen-time-format": self.dump_value(DEFAULT_DATE),
        }
        if self._openapi_format is not None:
            spec["format"] = self._openapi_format
        spec.update(
            build_prop_kwargs(
                kwargs=prop_kwargs, to_simple_type=self.dump_value
            )
        )
        return spec


class UTCDateTimeZ(UTCDateTime):
    """Appropriate datetime UTC type with guarantees for tzinfo existence."""

    def validate(self, value):
        return isinstance(value, datetime.datetime) and (
            value.tzinfo == datetime.timezone.utc
        )

    def from_simple_type(self, value):
        result = super(UTCDateTimeZ, self).from_simple_type(value)
        if result.tzinfo is not None:
            return result.astimezone(datetime.timezone.utc)
        # If datetime is naive, it's assumed that timezone is UTC, add it
        return result.replace(tzinfo=datetime.timezone.utc)


class TimeDelta(BasePythonType):
    """Appropriate timedelta type."""

    def __init__(
        self, min_value=-TIMEDELTA_INFINITY, max_value=TIMEDELTA_INFINITY
    ):
        self._min_value = min_value
        self._max_value = max_value
        super().__init__(
            python_type=datetime.timedelta,
            openapi_type="number",
            openapi_format="float",
        )

    @property
    def min_value(self):
        return self._min_value

    @property
    def max_value(self):
        return self._max_value

    def validate(self, value):
        result = super().validate(value)
        return (
            result
            and self.min_value <= self.to_simple_type(value) <= self.max_value
        )

    def to_simple_type(self, value):
        return value.total_seconds()

    def from_simple_type(self, value):
        if isinstance(value, datetime.timedelta):
            return value
        return datetime.timedelta(seconds=value)

    def from_unicode(self, value):
        return self.from_simple_type(value)

    @property
    def max_openapi_value(self):
        if self.max_value == INFINITI:
            return sys.float_info.max
        else:
            return self.max_value

    @property
    def min_openapi_value(self):
        if self.min_value == -INFINITI:
            return -sys.float_info.max
        else:
            return self.min_value

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self.openapi_type,
            "format": self.openapi_format,
            "minimum": self.min_openapi_value,
            "maximum": self.max_openapi_value,
        }
        spec.update(
            build_prop_kwargs(
                kwargs=prop_kwargs, to_simple_type=self.to_simple_type
            )
        )
        return spec


class DateTime(BasePythonType):

    def __init__(self, min_value=None, max_value=None):
        super(DateTime, self).__init__(python_type=datetime.datetime)

    def to_simple_type(self, value):
        return int(time.mktime(value.utctimetuple()))

    def from_simple_type(self, value):
        return datetime.datetime.utcfromtimestamp(value)

    def from_unicode(self, value):
        return self.from_simple_type(value)


class Enum(BaseType):

    def __init__(self, enum_values):
        super(Enum, self).__init__(openapi_type="string")
        self._enums_values = copy.deepcopy(enum_values)

    @property
    def values(self):
        return self._enums_values

    def validate(self, value):
        return value in self._enums_values

    def to_simple_type(self, value):
        return value

    def from_simple_type(self, value):
        return value

    def from_unicode(self, value):
        for enum_value in self._enums_values:
            if value == str(enum_value):
                return enum_value
        raise TypeError(
            "Can't convert '%s' to enum type."
            " Allowed values are %s" % (value, self._enums_values)
        )

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": self.openapi_type,
            "enum": sorted(list(self.values)),
        }
        spec.update(build_prop_kwargs(kwargs=prop_kwargs))
        return spec


class BaseRegExpType(BaseType):
    """BaseCompiledRegExpTypeFromAttr is preferred to be used"""

    def __init__(self, pattern, openapi_type="string", **kwargs):
        super(BaseRegExpType, self).__init__(openapi_type, **kwargs)
        self._pattern = re.compile(pattern)

    def validate(self, value):
        try:
            return self._pattern.match(value) is not None
        except TypeError:
            return False

    def to_simple_type(self, value):
        return value

    def from_simple_type(self, value):
        return value

    def from_unicode(self, value):
        return value

    @property
    def pattern_openapi(self):
        return self._pattern.pattern

    def to_openapi_spec(self, prop_kwargs):
        spec = {"type": self.openapi_type, "pattern": self.pattern_openapi}
        spec.update(build_prop_kwargs(kwargs=prop_kwargs))
        return spec


class BaseCompiledRegExpType(BaseRegExpType):
    def __init__(self, pattern, **kwargs):
        if "openapi_type" not in kwargs:
            kwargs["openapi_type"] = "string"
        super(BaseRegExpType, self).__init__(**kwargs)
        self._pattern = pattern


class BaseCompiledRegExpTypeFromAttr(BaseCompiledRegExpType):
    def __init__(self, **kwargs):
        super(BaseCompiledRegExpTypeFromAttr, self).__init__(
            pattern=self.pattern, **kwargs
        )


class Uri(BaseCompiledRegExpTypeFromAttr):
    pattern = re.compile(r"^(/[A-Za-z0-9\-_]*)*/%s$" % UUID_RE_TEMPLATE)

    def __init__(self):
        super(Uri, self).__init__(
            openapi_type="string",
            openapi_format="uri",
        )


class Mac(BaseCompiledRegExpTypeFromAttr):
    pattern = re.compile(r"^([0-9a-fA-F]{2,2}:){5,5}[0-9a-fA-F]{2,2}$")

    def __init__(self):
        super(Mac, self).__init__(
            openapi_type="string",
            openapi_format="mac",
        )


class Hostname(BaseCompiledRegExpTypeFromAttr):
    """DEPRECATED! Use types from types_network module"""

    pattern = re.compile(HOSTNAME_RE_TEMPLATE)

    def __init__(self):
        super(Hostname, self).__init__(
            openapi_type="hostname",
        )


class Url(BaseCompiledRegExpTypeFromAttr):
    """

    django url validation regex
    (https://github.com/django/django/blob/stable/1.3.x/django/core/validators.py#L45):
    """

    pattern = re.compile(
        r"^(?:http|ftp)s?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # noqa
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )


class AllowNone(BaseType):

    def __init__(self, nested_type):
        super(AllowNone, self).__init__(openapi_type="string")
        self._nested_type = nested_type

    @property
    def nested_type(self):
        return self._nested_type

    def validate(self, value):
        return value is None or self._nested_type.validate(value)

    def to_simple_type(self, value):
        return (
            None if value is None else self._nested_type.to_simple_type(value)
        )

    def from_simple_type(self, value):
        return (
            None
            if value is None
            else self._nested_type.from_simple_type(value)
        )

    def from_unicode(self, value):
        if value == "null":
            return None
        else:
            return self._nested_type.from_unicode(value)

    def to_openapi_spec(self, prop_kwargs):
        if "default" in prop_kwargs and prop_kwargs["default"] is None:
            del prop_kwargs["default"]
        spec = self._nested_type.to_openapi_spec(prop_kwargs)
        spec["nullable"] = True
        return spec
