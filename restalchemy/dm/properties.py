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
import collections
import copy
import inspect

from restalchemy.common import exceptions as exc
from restalchemy.common import utils
from restalchemy.dm import types

import six
from six.moves import builtins


@six.add_metaclass(abc.ABCMeta)
class AbstractProperty(object):

    @abc.abstractproperty
    def value(self):
        pass

    @abc.abstractmethod
    def set_value_force(self, value):
        pass

    @abc.abstractmethod
    def is_dirty(self):
        pass


class BaseProperty(AbstractProperty):
    pass


class Property(BaseProperty):

    def __init__(self, property_type, default=None, required=False,
                 read_only=False, value=None):
        if not isinstance(property_type, types.BaseType):
            raise TypeError("Property type must be instance of %s" %
                            types.BaseType)
        self._type = property_type
        self._required = bool(required)
        self._read_only = bool(read_only)
        default = default() if callable(default) else default
        self.set_value_force(value if value is not None else default)
        self.__first_value = self.value

    def is_dirty(self):
        return not self.__first_value == self.value

    def _safe_value(self, value):
        if value is None or self._type.validate(value):
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
    def is_id_property(cls):
        return False

    @property
    def old_value(self):
        return self.__first_value

    @builtins.property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if (self.is_read_only() or self.is_id_property()):
            raise exc.ReadOnlyProperty()
        self._value = self._safe_value(value)

    def set_value_force(self, value):
        self._value = self._safe_value(value)

    @property
    def property_type(self):
        return self._type


class IDProperty(Property):

    @classmethod
    def is_id_property(self):
        return True


class PropertyCreator(object):

    def __init__(self, prop_class, prop_type, args, kwargs):
        self._property = prop_class
        self._property_type = prop_type
        self._args = args
        self._kwargs = kwargs

    def __call__(self, value):
        return self._property(value=value, property_type=self._property_type,
                              *self._args, **self._kwargs)

    def get_property_class(self):
        return self._property

    def get_property_type(self):
        return self._property_type


@six.add_metaclass(abc.ABCMeta)
class PropertyMapping(collections.Mapping):

    @abc.abstractproperty
    def properties(self):
        pass

    def __getitem__(self, name):
        return self.properties[name]

    def __iter__(self):
        return six.iterkeys(self.properties)

    def __len__(self):
        return len(self.properties)


class PropertyCollection(PropertyMapping):

    def __init__(self, **kwargs):
        self._properties = kwargs
        super(PropertyCollection, self).__init__()

    def __getitem__(self, name):
        return self.properties[name].get_property_class()

    @builtins.property
    def properties(self):
        return utils.ReadOnlyDictProxy(self._properties)

    def __add__(self, other):
        if isinstance(other, PropertyCollection):
            props = dict(self.properties)
            props.update(other.properties)
            return type(self)(**props)
        raise TypeError("Cannot concatenate %s and %s objects" %
                        (type(self).__name__, type(other).__name__))

    def instantiate_property(self, name, value=None):
        return self._properties[name](value)

    def get_property_class(self):
        return type(self)


class PropertyManager(PropertyMapping):

    def __init__(self, property_collection, **kwargs):
        self._properties = {}
        for name, item in property_collection.properties.items():
            if isinstance(item, PropertyCollection):
                prop = PropertyManager(item, **kwargs.pop(name, {}))
            else:
                try:
                    prop = property_collection.instantiate_property(
                        name, kwargs.pop(name, None)
                    )
                except exc.PropertyRequired:
                    raise exc.PropertyRequired(name=name)
            self._properties[name] = prop

        # commented because kwargs can contain 'context' etc. Figure out
#        if len(kwargs) > 0:
#            raise TypeError("Unknown parameters: %s" % str(kwargs))
        super(PropertyManager, self).__init__()

    @builtins.property
    def properties(self):
        return utils.ReadOnlyDictProxy(self._properties)

    @builtins.property
    def value(self):
        result = {}
        for k, v in self.properties.iteritems():
            result[k] = v.value
        return result

    @value.setter
    def value(self, values):
        for k, v in values.iteritems():
            self._properties[k].value = v


def property(property_type, *args, **kwargs):
    id_property = kwargs.pop('id_property', False)
    property_class = kwargs.pop('property_class',
                                IDProperty if id_property else Property)
    if (inspect.isclass(property_class) and
            issubclass(property_class, AbstractProperty)):
        return PropertyCreator(prop_class=property_class,
                               prop_type=property_type,
                               args=args,
                               kwargs=kwargs)
    else:
        raise ValueError("Value of property class argument (%s) must be"
                         " inherited on AbstractProperty class"
                         "" % str(property_class))


def container(**kwargs):
    kwargs = copy.deepcopy(kwargs)
    for prop in kwargs.values():
        if not isinstance(prop, (PropertyCreator, PropertyCollection)):
            raise Exception("Only property, relationship "
                            "and container are allowed.")
    return PropertyCollection(**kwargs)
