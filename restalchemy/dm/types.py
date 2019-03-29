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
import re
import uuid

import six


INFINITI = float("inf")
UUID_RE_TEMPLATE = "[a-f0-9]{8,8}-([a-f0-9]{4,4}-){3,3}[a-f0-9]{12,12}"


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


class BasePythonType(BaseType):

    def __init__(self, python_type):
        super(BasePythonType, self).__init__()
        self._python_type = python_type

    def validate(self, value):
        return isinstance(value, self._python_type)

    def to_simple_type(cls, value):
        return value

    def from_simple_type(cls, value):
        return value


class Boolean(BasePythonType):

    def __init__(self):
        super(Boolean, self).__init__(bool)

    def from_simple_type(cls, value):
        return bool(value)


class String(BasePythonType):

    def __init__(self, min_length=0, max_length=six.MAXSIZE):
        super(String, self).__init__(six.string_types)
        self.min_length = int(min_length)
        self.max_length = int(max_length)

    def validate(self, value):
        result = super(String, self).validate(value)
        l = len(str(value))
        return result and l >= self.min_length and l <= self.max_length


class Integer(BasePythonType):

    def __init__(self, min_value=-INFINITI, max_value=INFINITI):
        super(Integer, self).__init__(six.integer_types)
        self.min_value = (
            min_value if min_value == -INFINITI else int(min_value))
        self.max_value = max_value if max_value == INFINITI else int(max_value)

    def validate(self, value):
        result = super(Integer, self).validate(value)
        return result and value >= self.min_value and value <= self.max_value


class Float(BasePythonType):

    def __init__(self, min_value=-INFINITI, max_value=INFINITI):
        super(Float, self).__init__(float)
        self.min_value = (
            min_value if min_value == -INFINITI else float(min_value))
        self.max_value = max_value if max_value == INFINITI else float(
            max_value)

    def validate(self, value):
        result = super(Float, self).validate(value)
        return result and value >= self.min_value and value <= self.max_value


class UUID(BaseType):

    def to_simple_type(cls, value):
        return str(value)

    def from_simple_type(cls, value):
        return uuid.UUID(value)

    def validate(self, value):
        return isinstance(value, uuid.UUID)


# TODO(efrolov): Make converters to convert Dict type to storable type
class Dict(BasePythonType):

    def __init__(self):
        super(Dict, self).__init__(dict)


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


class BaseRegExpType(BaseType):

    def __init__(self, pattern):
        super(BaseType, self).__init__()
        self._pattern = re.compile(pattern)

    def validate(self, value):
        try:
            return self._pattern.match(value) is not None
        except TypeError:
            return False

    def to_simple_type(cls, value):
        return value

    def from_simple_type(cls, value):
        return value


class Uri(BaseRegExpType):

    def __init__(self):
        super(Uri, self).__init__(pattern="^(/[A-Za-z0-9\-_]*)*/%s$" %
                                  UUID_RE_TEMPLATE)


class Mac(BaseRegExpType):

    def __init__(self):
        super(Mac, self).__init__("^([0-9a-fA-F]{2,2}:){5,5}[0-9a-fA-F]{2,2}$")
