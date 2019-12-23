# vim: tabstop=4 shiftwidth=4 softtabstop=4
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


INFINITY = float("inf")
INFINITI = INFINITY  # TODO(d.burmistrov): remove this hack
UUID_RE_TEMPLATE = r"[a-f0-9]{8,8}-([a-f0-9]{4,4}-){3,3}[a-f0-9]{12,12}"


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

    _TYPE_ERROR_MSG = "Can't convert '%s' to %s"

    def _raise_on_invalid_type(self, value):
        if not isinstance(value, self._python_type):
            raise TypeError(self._TYPE_ERROR_MSG % (value, self._python_type))

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


class TypedList(ComplexPythonType):

    def __init__(self, nested_type):
        super(TypedList, self).__init__(list)
        if not isinstance(nested_type, BaseType):
            raise TypeError("Nested type '%s' is not inherited from %s"
                            % (nested_type, BaseType))
        self._nested_type = nested_type

    def validate(self, value):
        result = super(TypedList, self).validate(value)
        for element in value:
            if result:
                result &= self._nested_type.validate(element)
            else:
                break
        return result

    def to_simple_type(self, value):
        return [self._nested_type.to_simple_type(e) for e in value]

    def from_simple_type(self, value):
        return [self._nested_type.from_simple_type(e) for e in value]


class Dict(ComplexPythonType):

    def __init__(self):
        super(Dict, self).__init__(dict)


class TypedDict(ComplexPythonType):

    def __init__(self, scheme):
        super(TypedDict, self).__init__(dict)
        non_string_keys = [key for key in scheme.keys()
                           if not isinstance(key, six.string_types)]
        if non_string_keys:
            raise ValueError("Keys '%s' are not strings" % non_string_keys)
        invalid_types = [value for value in scheme.values()
                         if not isinstance(value, BaseType)]
        if invalid_types:
            raise ValueError("Values '%s' are not %s"
                             % (non_string_keys, BaseType))
        self._scheme = scheme

    def validate(self, value):
        result = super(TypedDict, self).validate(value)
        result &= (set(value.keys()) == set(self._scheme.keys()))
        for key, scheme in six.iteritems(self._scheme):
            if result:
                result &= scheme.validate(value[key])
            else:
                break
        return result

    def to_simple_type(self, value):
        return {value[key]: scheme.to_simple_type(value[key])
                for key, scheme in self._scheme.items()}

    def from_simple_type(self, value):
        value = super(TypedDict, self).from_simple_type(value)
        return {k: self._scheme[k].from_simple_type(v)
                for k, v in value.items()}


class UTCDateTime(BasePythonType):

    def __init__(self):
        super(UTCDateTime, self).__init__(python_type=datetime.datetime)

    def validate(self, value):
        return isinstance(value, datetime.datetime) and value.tzinfo is None

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        if isinstance(value, datetime.datetime):
            return value
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')

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


class Uri(BaseRegExpType):

    def __init__(self):
        super(Uri, self).__init__(pattern=r"^(/[A-Za-z0-9\-_]*)*/%s$" %
                                  UUID_RE_TEMPLATE)


class Mac(BaseRegExpType):

    def __init__(self):
        super(Mac, self).__init__("^([0-9a-fA-F]{2,2}:){5,5}[0-9a-fA-F]{2,2}$")


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
