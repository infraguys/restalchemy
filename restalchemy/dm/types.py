# coding=utf-8
#
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
import datetime
import json
import re
import uuid

import six

if six.PY2:
    # http://bugs.python.org/issue7980
    datetime.datetime.strptime('', '')


INFINITY = float("inf")
INFINITI = INFINITY  # TODO(d.burmistrov): remove this hack
UUID_RE_TEMPLATE = r"[a-f0-9]{8,8}-([a-f0-9]{4,4}-){3,3}[a-f0-9]{12,12}"

# Copy-paste from validators library because RA must support python 2.7
# and support cyrillic domain names. The validators library is located:
# https://github.com/kvesteri/validators/blob/master/validators/domain.py#L5
# the regexp has issue https://github.com/kvesteri/validators/issues/185
HOSTNAME_RE_TEMPLATE = (
    # First character of the domain
    u'^(?:[a-zA-Z0-9]'
    # Sub domain + hostname
    u'(?:[a-zA-Z0-9-_]{0,61}[A-Za-z0-9])?\.)'  # noqa
    # First 61 characters of the gTLD
    u'+[A-Za-z0-9][A-Za-z0-9-_]{0,61}'
    # Last character of the gTLD
    u'[A-Za-z]$'
)


@six.add_metaclass(abc.ABCMeta)
class BaseType(object):

    @abc.abstractmethod
    def validate(self, value):
        pass

    @abc.abstractmethod
    def to_simple_type(self, value):
        pass

    @abc.abstractmethod
    def from_simple_type(self, value):
        pass

    @abc.abstractmethod
    def from_unicode(self, value):
        pass

    def __repr__(self):
        return self.__class__.__name__


class BasePythonType(BaseType):

    def __init__(self, python_type):
        super(BasePythonType, self).__init__()
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
        super(Boolean, self).__init__(bool)

    def from_simple_type(self, value):
        return bool(value)

    def from_unicode(self, value):
        return value.lower() in ['yes', 'true', '1']


class String(BasePythonType):

    def __init__(self, min_length=0, max_length=six.MAXSIZE):
        super(String, self).__init__(six.string_types)
        self.min_length = int(min_length)
        self.max_length = int(max_length)

    def validate(self, value):
        result = super(String, self).validate(value)
        return result and self.min_length <= len(str(value)) <= self.max_length

    def from_unicode(self, value):
        return six.text_type(value)


class Integer(BasePythonType):

    def __init__(self, min_value=-INFINITY, max_value=INFINITY):
        super(Integer, self).__init__(six.integer_types)
        self.min_value = (
            min_value if min_value == -INFINITY else int(min_value))
        self.max_value = max_value if max_value == INFINITY else int(max_value)

    def validate(self, value):
        result = super(Integer, self).validate(value)
        return result and self.min_value <= value <= self.max_value

    def from_unicode(self, value):
        return int(value)


class Float(BasePythonType):

    def __init__(self, min_value=-INFINITY, max_value=INFINITY):
        super(Float, self).__init__(float)
        self.min_value = (
            min_value if min_value == -INFINITY else float(min_value))
        self.max_value = max_value if max_value == INFINITY else float(
            max_value)

    def validate(self, value):
        result = super(Float, self).validate(value)
        return result and self.min_value <= value <= self.max_value


class UUID(BaseType):

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        return uuid.UUID(value)

    def validate(self, value):
        return isinstance(value, uuid.UUID)

    def from_unicode(self, value):
        return uuid.UUID(value)


class ComplexPythonType(BasePythonType):

    _TYPE_ERROR_MSG = "Can't convert '%s' with type '%s' into %s"

    def _raise_on_invalid_type(self, value):
        if not isinstance(value, self._python_type):
            raise TypeError(self._TYPE_ERROR_MSG
                            % (value, type(value), self._python_type))

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
        super(List, self).__init__(list)


class TypedList(List):

    def __init__(self, nested_type):
        super(TypedList, self).__init__()
        if not isinstance(nested_type, BaseType):
            raise TypeError("Nested type '%s' is not inherited from %s"
                            % (nested_type, BaseType))
        self._nested_type = nested_type

    def validate(self, value):
        return (super(TypedList, self).validate(value)
                and all(self._nested_type.validate(item) for item in value))

    def to_simple_type(self, value):
        return [self._nested_type.to_simple_type(e) for e in value]

    def from_simple_type(self, value):
        return [self._nested_type.from_simple_type(e) for e in value]

    def from_unicode(self, value):
        if not isinstance(value, six.string_types):
            raise TypeError("Value must be six.string_types, not %s",
                            type(value))

        value = self._nested_type.from_unicode(value)
        return [value]


class Dict(ComplexPythonType):

    def __init__(self):
        super(Dict, self).__init__(dict)

    def validate(self, value):
        return (super(Dict, self).validate(value)
                and all(isinstance(k, six.string_types) for k in value))


def _validate_scheme(scheme):
    non_string_keys = [key for key in scheme.keys()
                       if not isinstance(key, six.string_types)]
    if non_string_keys:
        raise ValueError("Keys '%s' are not strings" % non_string_keys)

    invalid_types = [value for value in scheme.values()
                     if not isinstance(value, BaseType)]
    if invalid_types:
        raise ValueError("Values '%s' are not %s"
                         % (non_string_keys, BaseType))


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
        return (super(SoftSchemeDict, self).validate(value)
                and set(value.keys()).issubset(set(self._scheme.keys()))
                and all(self._scheme[k].validate(v)
                        for k, v in six.iteritems(value)))

    def to_simple_type(self, value):
        return {k: self._scheme[k].to_simple_type(v)
                for k, v in six.iteritems(value)}

    def from_simple_type(self, value):
        value = super(SoftSchemeDict, self).from_simple_type(value)
        return {k: self._scheme[k].from_simple_type(v)
                for k, v in six.iteritems(value)}


class SchemeDict(Dict):

    def __init__(self, scheme):
        super(SchemeDict, self).__init__()
        _validate_scheme(scheme)
        self._scheme = scheme

    def validate(self, value):
        return (super(SchemeDict, self).validate(value)
                and set(value.keys()) == set(self._scheme.keys())
                and all(scheme.validate(value[key])
                        for key, scheme in six.iteritems(self._scheme)))

    def to_simple_type(self, value):
        return {value[key]: scheme.to_simple_type(value[key])
                for key, scheme in self._scheme.items()}

    def from_simple_type(self, value):
        value = super(SchemeDict, self).from_simple_type(value)
        return {key: scheme.from_simple_type(value[key])
                for key, scheme in six.iteritems(self._scheme)}


class TypedDict(Dict):

    def __init__(self, nested_type):
        super(TypedDict, self).__init__()
        if not isinstance(nested_type, BaseType):
            raise TypeError("Nested type '%s' is not inherited from %s"
                            % (nested_type, BaseType))
        self._nested_type = nested_type

    def validate(self, value):
        return (super(TypedDict, self).validate(value)
                and all(self._nested_type.validate(element)
                        for element in six.itervalues(value)))

    def to_simple_type(self, value):
        return {k: self._nested_type.to_simple_type(v)
                for k, v in six.iteritems(value)}

    def from_simple_type(self, value):
        value = super(TypedDict, self).from_simple_type(value)
        return {k: self._nested_type.from_simple_type(v)
                for k, v in six.iteritems(value)}


class UTCDateTime(BasePythonType):

    _FORMAT = '%Y-%m-%d %H:%M:%S.%f'

    def __init__(self):
        super(UTCDateTime, self).__init__(python_type=datetime.datetime)

    def validate(self, value):
        return isinstance(value, datetime.datetime) and value.tzinfo is None

    def to_simple_type(self, value):
        return value.strftime(self._FORMAT)

    def from_simple_type(self, value):
        if isinstance(value, datetime.datetime):
            return value
        return datetime.datetime.strptime(value, self._FORMAT)

    def from_unicode(self, value):
        return self.from_simple_type(value)


class Enum(BaseType):

    def __init__(self, enum_values):
        super(Enum, self).__init__()
        self._enums_values = copy.deepcopy(enum_values)

    def validate(self, value):
        return value in self._enums_values

    def to_simple_type(self, value):
        return value

    def from_simple_type(self, value):
        return value

    def from_unicode(self, value):
        for enum_value in self._enums_values:
            if value == six.text_type(enum_value):
                return enum_value
        raise TypeError("Can't convert '%s' to enum type."
                        " Allowed values are %s"
                        % (value, self._enums_values))


class BaseRegExpType(BaseType):
    '''BaseCompiledRegExpTypeFromAttr is preferred to be used'''

    def __init__(self, pattern):
        super(BaseType, self).__init__()
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


class BaseCompiledRegExpType(BaseRegExpType):
    def __init__(self, pattern):
        super(BaseRegExpType, self).__init__()
        self._pattern = pattern


class BaseCompiledRegExpTypeFromAttr(BaseCompiledRegExpType):
    def __init__(self):
        super(BaseCompiledRegExpTypeFromAttr, self).__init__(
            pattern=self.pattern)


class Uri(BaseCompiledRegExpTypeFromAttr):
    pattern = re.compile(r"^(/[A-Za-z0-9\-_]*)*/%s$" % UUID_RE_TEMPLATE)


class Mac(BaseCompiledRegExpTypeFromAttr):
    pattern = re.compile(r"^([0-9a-fA-F]{2,2}:){5,5}[0-9a-fA-F]{2,2}$")


class Hostname(BaseCompiledRegExpTypeFromAttr):
    '''DEPRECATED! Use types from types_network module'''
    pattern = re.compile(HOSTNAME_RE_TEMPLATE)


class AllowNone(BaseType):

    def __init__(self, nested_type):
        super(AllowNone, self).__init__()
        self._nested_type = nested_type

    @property
    def nested_type(self):
        return self._nested_type

    def validate(self, value):
        return value is None or self._nested_type.validate(value)

    def to_simple_type(self, value):
        return None if value is None else self._nested_type.to_simple_type(
            value)

    def from_simple_type(self, value):
        return None if value is None else self._nested_type.from_simple_type(
            value)

    def from_unicode(self, value):
        return None if value is None else self._nested_type.from_unicode(
            value)
