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

import builtins
from collections import abc as collections_abc

from restalchemy.common import exceptions as exc
from restalchemy.common import utils
from restalchemy.dm import types


class AbstractProperty(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def value(self):
        pass

    @abc.abstractmethod
    def set_value_force(self, value):
        pass

    @abc.abstractmethod
    def is_dirty(self):
        pass

    @classmethod
    def is_prefetch(cls):
        return False


class BaseProperty(AbstractProperty):
    pass


class Property(BaseProperty):

    def __init__(
        self,
        property_type,
        default=None,
        required=False,
        read_only=False,
        value=None,
        mutable=False,
        example=None,
    ):
        if not isinstance(property_type, types.BaseType):
            raise TypeError(
                "Property type must be instance of %s" % types.BaseType
            )
        self._type = property_type
        self._required = bool(required)
        self._read_only = bool(read_only)
        if value is not None:
            self.set_value_force(value)
        elif callable(default):
            self.set_value_force(default())
        else:
            self.set_value_force(default)
        self.__first_value = (
            copy.deepcopy(self.value) if mutable else self.value
        )
        self._example = example

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

    @builtins.property
    def old_value(self):
        return self.__first_value

    @builtins.property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.is_read_only() or self.is_id_property():
            if value != self._value:
                raise exc.ReadOnlyProperty()
        self._value = self._safe_value(value)

    def set_value_force(self, value):
        self._value = self._safe_value(value)

    @builtins.property
    def property_type(self):
        return self._type

    def get_property_type(self):
        return self._type

    def example(self):
        return self._example


class IDProperty(Property):

    @classmethod
    def is_id_property(cls):
        return True


class PropertyCreator(object):

    def __init__(self, prop_class, prop_type, args, kwargs):
        self._property = prop_class
        self._property_type = prop_type
        self._args = args
        self._kwargs = kwargs
        self._prefetch = kwargs.pop("prefetch", False)

    def __call__(self, value):
        return self._property(
            value=value,
            property_type=self._property_type,
            *self._args,
            **self._kwargs
        )

    def get_property_class(self):
        return self._property

    def get_property_type(self):
        return self._property_type

    def get_kwargs(self):
        return self._kwargs

    def is_prefetch(self):
        return self._prefetch


class PropertyMapping(collections_abc.Mapping, metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def properties(self):
        pass

    def __getitem__(self, name):
        return self.properties[name]

    def __iter__(self):
        return iter(self.properties)

    def __len__(self):
        return len(self.properties)


class PropertyCollection(PropertyMapping):

    def __init__(self, **kwargs):
        self._properties = kwargs
        super(PropertyCollection, self).__init__()

    def sort_properties(self):
        """Switch the model to sorted properties

        After call this method all requests to Model.properties will return
        sorted values. For example:

        ```
        class Model(Model):
            b = properties.property(type.B())
            a = properties.property(type.A())

        Model.properties.keys()  #-> ['b', 'a']
        Model.properties.sort_properties()
        Model.properties.keys()  #-> ['a', 'b']
        ```

        Most often, this functionality is needed for tests.
        """
        result = collections.OrderedDict()
        for key in sorted(self._properties):
            result[key] = self._properties[key]
        self._properties = result

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
        raise TypeError(
            "Cannot concatenate %s and %s objects"
            % (type(self).__name__, type(other).__name__)
        )

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
        for k, v in self.properties.items():
            result[k] = v.value
        return result

    @value.setter
    def value(self, values):
        for k, v in values.items():
            self._properties[k].value = v


def property(property_type, *args, **kwargs):
    id_property = kwargs.pop("id_property", False)
    property_class = kwargs.pop(
        "property_class", IDProperty if id_property else Property
    )
    if inspect.isclass(property_class) and issubclass(
        property_class, AbstractProperty
    ):
        return PropertyCreator(
            prop_class=property_class,
            prop_type=property_type,
            args=args,
            kwargs=kwargs,
        )
    else:
        raise ValueError(
            "Value of property class argument (%s) must be"
            " inherited on AbstractProperty class"
            "" % str(property_class)
        )


def container(**kwargs):
    kwargs = copy.deepcopy(kwargs)
    for prop in kwargs.values():
        if not isinstance(prop, (PropertyCreator, PropertyCollection)):
            raise Exception(
                "Only property, relationship " "and container are allowed."
            )
    return PropertyCollection(**kwargs)


def required_property(property_type, *args, **kwargs):
    kwargs["required"] = True
    return property(property_type, *args, **kwargs)


def readonly_property(property_type, *args, **kwargs):
    kwargs["read_only"] = True
    return required_property(property_type, *args, **kwargs)
