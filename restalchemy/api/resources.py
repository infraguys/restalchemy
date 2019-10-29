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
import inspect

import six
from sqlalchemy.orm import attributes
from sqlalchemy.orm import properties
from sqlalchemy.orm import relationships

from restalchemy.common import exceptions as exc
from restalchemy.dm import properties as ra_properties
from restalchemy.dm import relationships as ra_relationsips


class ResourceMap(object):

    resource_map = {}
    model_type_to_resource = {}

    @classmethod
    def get_location(cls, model):
        resource = cls.get_resource_by_model(model)
        if resource not in cls.resource_map:
            raise exc.UnknownResourceLocation(resource=resource)
        return cls.resource_map[resource].get_uri(model)

    @classmethod
    def get_locator(cls, uri):
        for resource, locator in cls.resource_map.items():
            if locator.is_your_uri(uri):
                return locator
        raise exc.LocatorNotFound(uri=uri)

    @classmethod
    def get_resource(cls, request, uri):
        resource_locator = cls.get_locator(uri)

        # has parent resource?
        pstack = resource_locator.path_stack
        parent_resource = None

        for pice in reversed(pstack[:-1]):
            if not isinstance(pice, six.string_types):
                parent_uri = '/'.join(uri.split('/')[:pstack.index(pice) + 2])
                parent_locator = cls.get_locator(parent_uri)
                parent_resource = parent_locator.get_resource(
                    request, parent_uri)
                break

        return resource_locator.get_resource(request, uri, parent_resource)

    @classmethod
    def set_resource_map(cls, resource_map):
        cls.resource_map = resource_map

    @classmethod
    def add_model_to_resource_mapping(cls, model_class, resource):
        if model_class in cls.model_type_to_resource:
            raise ValueError(
                "model (%s) for resource (%s) already added. %s" % (
                    model_class, resource, cls.model_type_to_resource))
        cls.model_type_to_resource[model_class] = resource

    @classmethod
    def get_resource_by_model(cls, model):
        model_type = model.get_model_type()
        try:
            return cls.model_type_to_resource[model_type]
        except KeyError:
            raise exc.CanNotFindResourceByModel(model=model)


@six.add_metaclass(abc.ABCMeta)
class AbstractResourceProperty(object):

    def __init__(self, resource, model_property_name, public=True):
        super(AbstractResourceProperty, self).__init__()
        self._resource = resource
        self._model_property_name = model_property_name
        self._hidden = False
        self._public = public

    def is_public(self):
        return self._public

    @property
    def api_name(self):
        return self._resource.get_resource_field_name(
            self._model_property_name)

    @property
    def name(self):
        return self._model_property_name

    @abc.abstractmethod
    def parse_value(self, req, value):
        raise NotImplementedError()

    @abc.abstractmethod
    def parse_value_from_unicode(self, req, value):
        raise NotImplementedError()

    @abc.abstractmethod
    def dump_value(self, value):
        return NotImplementedError()


class ResourceProperty(AbstractResourceProperty):
    pass


class ResourceSAProperty(ResourceProperty):

    def parse_value(self, req, value):
        return value

    def parse_value_from_unicode(self, req, value):
        return value

    def dump_value(self, value):
        return value


class ResourceRAProperty(ResourceProperty):

    def __init__(self, resource, prop_type, model_property_name, public=True):
        super(ResourceRAProperty, self).__init__(
            resource=resource,
            model_property_name=model_property_name,
            public=public)
        self._prop_type = (
            prop_type() if inspect.isclass(prop_type) else prop_type)

    def parse_value(self, req, value):
        return self._prop_type.from_simple_type(value)

    def parse_value_from_unicode(self, req, value):
        return self._prop_type.from_unicode(value)

    def dump_value(self, value):
        return self._prop_type.to_simple_type(value)


class ResourceRelationship(AbstractResourceProperty):

    def parse_value(self, req, value):
        return ResourceMap.get_resource(req, value)

    def parse_value_from_unicode(self, req, value):
        return self.parse_value(req, value)

    def dump_value(self, value):
        return ResourceMap.get_location(value)


@six.add_metaclass(abc.ABCMeta)
class AbstractResource(object):

    def __init__(self, model_class, name_map=None, hidden_fields=None,
                 convert_underscore=True, process_filters=False,
                 model_subclasses=None):
        super(AbstractResource, self).__init__()
        self._model_class = model_class
        self._name_map = name_map or {}
        self._hidden_fields = hidden_fields or []
        self._convert_underscore = convert_underscore
        self._process_filters = process_filters
        self._model_subclasses = model_subclasses or []
        ResourceMap.add_model_to_resource_mapping(model_class, self)
        for model_subclass in self._model_subclasses:
            ResourceMap.add_model_to_resource_mapping(model_subclass, self)

    def is_process_filters(self):
        return self._process_filters

    @abc.abstractmethod
    def get_fields(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_resource_id(self, model):
        raise NotImplementedError()

    @property
    def _m2r_name_map(self):
        return self._name_map

    @property
    def _hidden_model_fields(self):
        return self._hidden_fields

    def get_resource_field_name(self, model_field_name):
        name = self._m2r_name_map.get(
            model_field_name, model_field_name)
        return name.replace('_', '-') if self._convert_underscore else name

    def is_public_field(self, model_field_name):
        return not (model_field_name.startswith('_') or
                    model_field_name in self._hidden_model_fields)

    def get_model(self):
        return self._model_class

    def __repr__(self):
        return ("<%s[model=%r], name_map=%r, convert_underscore=%s, "
                "process_filters=%s, fields=%r>" % (
                    self.__class__.__name__,
                    self._model_class,
                    self._name_map,
                    self._convert_underscore,
                    self._process_filters,
                    self._model_class.properties.properties.keys()))


class ResourceByRAModel(AbstractResource):

    def get_fields(self):
        for name, prop in self._model_class.properties.items():
            if issubclass(prop, ra_properties.BaseProperty):
                prop = ResourceRAProperty(
                    resource=self,
                    prop_type=(self._model_class.properties.properties[name]
                               .get_property_type()),
                    model_property_name=name,
                    public=self.is_public_field(name))
            elif issubclass(prop, ra_relationsips.BaseRelationship):
                prop = ResourceRelationship(
                    self, model_property_name=name,
                    public=self.is_public_field(name))
            else:
                raise TypeError("Unknown property type %s" % type(prop))
            yield name, prop

    def get_resource_id(self, model):
        # TODO(efrolov): Write code to convert value to simple value.
        if hasattr(model, 'get_id'):
            return str(model.get_id())
        else:
            # TODO(efrolov): Add autosearch resource id by model
            raise ValueError("Can't find resource ID for %s. Please implement "
                             "get_id method in your model (%s)" % (
                                 model, self._model_class))


class ResourceBySAModel(AbstractResource):

    def get_fields(self):
        for name in dir(self._model_class):
            attr = getattr(self._model_class, name)
            if isinstance(attr, attributes.InstrumentedAttribute):
                if isinstance(
                        attr.comparator,
                        properties.ColumnProperty.Comparator):
                    prop = ResourceSAProperty(
                        self, model_property_name=name,
                        public=self.is_public_field(name))
                elif isinstance(
                        attr.comparator,
                        relationships.RelationshipProperty.Comparator):
                    prop = ResourceRelationship(
                        self, model_property_name=name,
                        public=self.is_public_field(name))
                else:
                    raise TypeError("Unknown property type %s" % type(attr))
                yield name, prop

    def get_resource_id(self, model):
        if not isinstance(model, self._model_class):
            raise TypeError('Model instance must be %s (not %s)' % (
                self._model_class, type(model)))
        if hasattr(model, "get_id"):
            return model.get_id()
        primary_keys = []
        for name, column in self._model_class.__table__.columns.items():
            if column.primary_key == True:
                primary_keys.append(name)
        if len(primary_keys) == 1:
            return getattr(model, primary_keys[0])
        raise ValueError("Can't find resource ID for %s. Please implement "
                         "get_id method in your model (%s)" % (
                             model, self._model_class))
