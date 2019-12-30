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
import uuid

from restalchemy.common import exceptions as exc
from restalchemy.dm import properties
from restalchemy.dm import types

import six


class MetaModel(abc.ABCMeta):

    def __new__(cls, name, bases, attrs):
        props = {}
        for key, value in attrs.copy().items():
            if isinstance(value, (properties.PropertyCreator,
                                  properties.PropertyCollection)):
                props[key] = value
                del attrs[key]
        all_base_properties = properties.PropertyCollection()
        for base in bases:
            base_properties = getattr(base, 'properties', None)
            if isinstance(base_properties, properties.PropertyCollection):
                all_base_properties += base_properties
        attrs['properties'] = (
            attrs.pop('properties', properties.PropertyCollection()) +
            all_base_properties + properties.PropertyCollection(**props))
        return super(MetaModel, cls).__new__(cls, name, bases, attrs)

    def __getattr__(cls, name):
        try:
            return cls.properties[name]
        except KeyError:
            raise AttributeError("%s object has no attribute %s" % (
                cls.__name__, name))


@six.add_metaclass(MetaModel)
class Model(collections.Mapping):

    def __init__(self, **kwargs):
        super(Model, self).__init__()
        self.pour(**kwargs)

    def __getattr__(self, name):
        try:
            return self.properties[name].value
        except KeyError:
            raise AttributeError("%s object has no attribute %s" % (
                type(self).__name__, name))

    def __setattr__(self, name, value):
        try:
            self.properties[name].value = value
        except KeyError:
            super(Model, self).__setattr__(name, value)
        except exc.TypeError as e:
            raise exc.ModelTypeError(
                property_name=name,
                value=value,
                model=self,
                property_type=e.get_property_type())
        except exc.ReadOnlyProperty as e:
            raise exc.ReadOnlyProperty(
                name=name,
                model=type(self)
            )

    def pour(self, **kwargs):
        try:
            self.properties = properties.PropertyManager(
                self.properties,
                **kwargs
            )
            self.validate()
        except exc.PropertyRequired as e:
            raise exc.PropertyRequired(
                name=e.name,
                model=self.__class__
            )

    @classmethod
    def restore(cls, **kwargs):
        obj = cls.__new__(cls)

        # NOTE(aostapenko): We can't invoke 'pour' from __new__ because of
        #                   copy.copy of object becomes imposible
        obj.pour(**kwargs)
        return obj

    def validate(self):
        pass

    def update_dm(self, values):
        for name, value in values.iteritems():
            setattr(self, name, value)

    @classmethod
    def get_id_property(cls):
        result = {}
        for name, prop in cls.properties.items():
            if prop.is_id_property():
                result[name] = cls.properties.properties[name]
        if len(result) == 1:
            return result
        raise TypeError("Model %s has %s properties which marked as "
                        "id_property. Please implement get_id_prop "
                        "method on your model."
                        % (type(cls), 'many' if result else 'no'))

    @classmethod
    def get_id_property_name(cls):
        for key in cls.get_id_property():
            return key

    def get_id_properties(self):
        result = {}
        for name, prop in self.properties.items():
            if prop.is_id_property():
                result[name] = prop
        return result

    def get_data_properties(self):
        result = {}
        for name, prop in self.properties.items():
            if not prop.is_id_property():
                result[name] = prop
        return result

    def is_dirty(self):
        for prop in self.properties.values():
            if prop.is_dirty():
                return True
        return False

    @classmethod
    def get_model_type(cls):
        return cls

    def __getitem__(self, name):
        return self.properties[name].value

    def __iter__(self):
        return six.iterkeys(self.properties)

    def __len__(self):
        return len(self.properties)

    def __str__(self):
        return '<%s %s>' % (self.__class__.__name__,
                            self.get_id())

    def __repr__(self):
        result = []
        for k, v in self.items():
            result.append('%s: %s' % (k, v))
        result = ', '.join(result)
        return '<%s {%s}>' % (self.__class__.__name__, result)


class ModelWithID(Model):

    def get_id(self):
        return getattr(self, self.get_id_property_name())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.get_id() == other.get_id()
        return False

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(str(self.get_id()))


class ModelWithUUID(ModelWithID):

    uuid = properties.property(types.UUID(), read_only=True, id_property=True,
                               default=lambda: uuid.uuid4())


class ModelWithRequiredUUID(ModelWithUUID):

    uuid = properties.property(types.UUID(), read_only=True, id_property=True,
                               required=True)
