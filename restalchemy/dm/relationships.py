# Copyright (c) 2014 Eugene Frolov <eugene@frolov.net.ru>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import abc

from restalchemy.common import exceptions as exc
from restalchemy.dm import models
from restalchemy.dm import properties


def relationship(property_type, *args, **kwargs):
    prefetch = kwargs.get("prefetch", False)
    for arg in args:
        if not issubclass(arg, models.Model):
            raise exc.RelationshipModelError(model=arg)
    kwargs["property_class"] = kwargs.get(
        "property_class",
        PrefetchRelationship if prefetch else Relationship,
    )
    return properties.property(property_type=property_type, *args, **kwargs)


def required_relationship(property_type, *args, **kwargs):
    kwargs["required"] = True
    return relationship(property_type, *args, **kwargs)


def readonly_relationship(property_type, *args, **kwargs):
    kwargs["read_only"] = True
    return required_relationship(property_type, *args, **kwargs)


class BaseRelationship(properties.AbstractProperty, metaclass=abc.ABCMeta):
    pass


class Relationship(BaseRelationship):

    def __init__(
        self,
        property_type,
        default=None,
        required=False,
        read_only=False,
        value=None,
    ):
        if value and not isinstance(value, property_type):
            raise TypeError(
                "Expected '%s' type; value: %r" % (property_type, value)
            )
        self._type = property_type
        self._required = bool(required)
        self._read_only = bool(read_only)
        self._default = None
        if default:
            default = default() if callable(default) else default
            self._default = (
                (default()) if callable(default) else self._safe_value(default)
            )
        self._value = value
        self.__first_value = self.value

    def is_dirty(self):
        return not self.__first_value == self.value

    def _safe_value(self, value):
        if value is None or isinstance(value, self._type):
            if value is None and self.is_required():
                raise exc.PropertyRequired()
            return value
        else:
            raise exc.TypeError(value=value, property_type=self._type)

    def is_read_only(self):
        return self._read_only

    def is_required(self):
        return self._required

    @classmethod
    def is_prefetch(cls):
        return False

    @property
    def value(self):
        return self._value or self._default

    @value.setter
    def value(self, value):
        if self.is_read_only():
            raise exc.ReadOnlyProperty()
        self._value = self._safe_value(value)

    def set_value_force(self, value):
        self._value = self._safe_value(value)

    @property
    def property_type(self):
        return self._type

    def get_property_type(self):
        return self._type

    @classmethod
    def is_id_property(cls):
        return False


class PrefetchRelationship(Relationship):

    @classmethod
    def is_prefetch(cls):
        return True
