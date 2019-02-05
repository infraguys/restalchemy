# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2018 Mail.ru Group
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

import six

from restalchemy.dm import relationships
from restalchemy.storage import base
from restalchemy.storage.rest import engines
from restalchemy.storage.rest import utils


class RESTPath(object):

    def __init__(self, *args):
        super(RESTPath, self).__init__()
        self._rest_path = args

    def _get_parent_name(self, model_cls):
        if hasattr(model_cls, 'get_parent_name'):
            return model_cls.get_parent_name()
        raise NotImplementedError(
            "Please implement `get_parent_name` classmethod for class %s" %
            model_cls)

    def has_parent(self):
        for pice in reversed(self._rest_path):
            if not isinstance(pice, six.string_types):
                return True
        return False

    def get_parent_uri(self, resource_uri):
        for pice in reversed(self._rest_path):
            if not isinstance(pice, six.string_types):
                return '/'.join(
                    resource_uri.split('/')[:self._rest_path.index(pice) + 2])

    def get_collection_uri(self, model_cls, obj):
        rest_path = []
        curr_model_cls = model_cls
        curr_obj = obj
        for pice in reversed(self._rest_path):
            if isinstance(pice, six.string_types):
                rest_path.insert(0, pice)
            else:
                parent_prop_name = self._get_parent_name(curr_model_cls)
                parent = curr_obj[parent_prop_name]
                curr_model_cls = type(parent)
                curr_obj = parent
                rest_path.insert(0, parent.get_resource_id())
        return '/' + utils.force_last_slash('/'.join(rest_path))

    def get_resource_uri(self, model_cls, obj, obj_id):
        return self.get_collection_uri(model_cls, obj) + obj_id


class ObjectCollection(base.AbstractObjectCollection):

    @property
    def _engine(self):
        return engines.engine_factory.get_engine()

    def _filters_to_storage_view(self, context, filters):
        # TODO(efrolov): Move this code from class to utils or another
        #                location.
        result = {}
        for name, value in (filters or {}).items():
            prop = self.model_cls.properties.properties[name]
            if prop.get_property_class() == relationships.Relationship:
                result[name] = (self.model_cls.properties.properties[name]
                                .get_property_type().to_simple_type(context,
                                                                    value))
            else:
                result[name] = (self.model_cls.properties.properties[name]
                                .get_property_type().to_simple_type(value))
        return result

    def _get_id_property_name(self):
        id_property_names = []
        for name, prop in self.model_cls.properties.properties.items():
            if prop.get_property_class().is_id_property():
                id_property_names.append(name)
        if len(id_property_names) != 1:
            raise ValueError(("Model %s should have only one property mark as "
                              "`id_property`. Curently: %d") % (
                self.model_cls, len(id_property_names)))
        return id_property_names[0]

    def _value_to_simple_type(self, prop_name, prop_value):
        return (self.model_cls
                .properties
                .properties[prop_name]
                .get_property_type()
                .to_simple_type(prop_value))

    def get_all(self, context, filters=None):
        models_uri = self.model_cls.get_path_ctrl().get_collection_uri(
            model_cls=self.model_cls, obj=filters)
        resp = self._engine.list(uri=models_uri,
                                 params=self._filters_to_storage_view(context,
                                                                      filters),
                                 context=context)
        for result in resp:
            yield self.model_cls.restore_from_storage(context, **result)

    def get_one(self, context, filters=None):
        filters = filters.copy()
        id_prop_name = self._get_id_property_name()
        obj_id = self._value_to_simple_type(id_prop_name,
                                            filters.pop(id_prop_name))
        model_uri = self.model_cls.get_path_ctrl().get_resource_uri(
            model_cls=self.model_cls, obj=filters, obj_id=obj_id)
        result = self._engine.get(
            uri=model_uri,
            params=self._filters_to_storage_view(context, filters),
            context=context)
        return self.model_cls.restore_from_storage(context, **result)


@six.add_metaclass(abc.ABCMeta)
class RESTStorableMixin(base.AbstractStorableMixin):

    _saved = False

    _ObjectCollection = ObjectCollection

    @abc.abstractproperty
    def __restpath__(self):
        raise NotImplementedError()

    @classmethod
    def get_path_ctrl(self):
        return self.__restpath__

    @property
    def _engine(self):
        return engines.engine_factory.get_engine()

    @classmethod
    def restore_from_storage(cls, context, **kwargs):
        model_format = {}
        for name, value in kwargs.items():
            name = name.replace('-', '_')
            prop = cls.properties.properties[name]
            if prop.get_property_class() == relationships.Relationship:
                model_format[name] = (
                    prop.get_property_type().from_simple_type(context,
                                                              value))
            else:
                model_format[name] = (
                    prop.get_property_type().from_simple_type(value))
        obj = cls(**model_format)
        obj._saved = True
        return obj

    def _update_model_from_storage(self, context, **kwargs):
        model_format = {}
        for name, value in kwargs.items():
            model_name = name.replace('-', '_')
            model_format[model_name] = (
                self.properties[model_name].property_type
                .from_simple_type(context, value) if isinstance(
                    self.properties[model_name],
                    relationships.Relationship) else
                self.properties[model_name].property_type
                .from_simple_type(value))
        for name, prop in self.properties.items():
            prop.set_value_force(model_format.get(name, None))

    def _get_prepared_data(self, context, properties=None):
        res = {}
        props = properties or self.properties
        for name, prop in props.items():
            if isinstance(prop, relationships.Relationship):
                res[name] = prop.property_type.to_simple_type(context,
                                                              prop.value)
            else:
                res[name] = prop.property_type.to_simple_type(prop.value)
        return {name.replace('_', '-'): value for name, value in res.items()}

    def insert(self, context):
        models_uri = self.get_path_ctrl().get_collection_uri(
            model_cls=type(self), obj=self)
        resp = self._engine.post(uri=models_uri,
                                 params=self._get_prepared_data(context),
                                 context=context)
        self._saved = True
        self._update_model_from_storage(context, **resp)

    def save(self, context):
        self.update(context) if self._saved else self.insert(context)

    def update(self, context):
        model_uri = self.get_path_ctrl().get_resource_uri(
            model_cls=type(self), obj=self, obj_id=self.get_resource_id())
        dirty_props = {name: prop for name, prop in self.properties.items()
                       if prop.is_dirty()}
        result = self._engine.put(
            uri=model_uri,
            params=self._get_prepared_data(context, properties=dirty_props),
            context=context)
        return self.restore_from_storage(context, **result)

    def delete(self, context):
        model_uri = self.get_path_ctrl().get_resource_uri(
            model_cls=type(self), obj=self, obj_id=self.get_resource_id())
        self._engine.delete(uri=model_uri, context=context)
        self._saved = False

    def _get_resource_id_prop(self):
        for prop in self.properties.values():
            if prop.is_id_property():
                return prop
        raise ValueError("Model (%s) should contain a property of IdProperty "
                         "type" % self)

    def get_resource_id(self):
        prop = self._get_resource_id_prop()
        return prop.property_type.to_simple_type(self.get_id())

    def get_resource_uri(self):
        prop = self._get_resource_id_prop()
        return self.get_path_ctrl().get_resource_uri(
            model_cls=type(self),
            obj=self,
            obj_id=prop.property_type.to_simple_type(self.get_id()))

    @classmethod
    def to_simple_type(cls, context, value):
        return value.get_resource_uri() if value is not None else None

    @classmethod
    def from_simple_type(cls, context, value):
        if value is None:
            return None
        raw_value = value.split('/')[-1]
        path_ctrl = cls.get_path_ctrl()
        filters = {}
        for name, prop in cls.properties.items():
            if prop.is_id_property():
                if path_ctrl.has_parent():
                    parent_name = cls.get_parent_name()
                    parent_prop = (cls.properties.properties[parent_name]
                                   .get_property_type())
                    parent = parent_prop.from_simple_type(
                        context, path_ctrl.get_parent_uri(value))
                    filters[parent_name] = parent
                value = (cls.properties.properties[name].get_property_type()
                         .from_simple_type(raw_value))
                filters[name] = value
                return cls.objects.get_one(context, filters=filters)
        raise NotImplementedError("Id property for %s not found!!!" % cls)
