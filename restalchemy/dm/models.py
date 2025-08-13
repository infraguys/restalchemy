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
from __future__ import annotations

import abc
import copy
import datetime
import uuid
import inspect
import typing as tp

from collections import abc as collections_abc

from restalchemy.common import exceptions as exc
from restalchemy.dm import properties
from restalchemy.dm import types


class DmOperationalStorage(object):

    def __init__(self):
        super(DmOperationalStorage, self).__init__()
        self._storage = {}

    def store(self, name, data):
        self._storage[name] = data

    def get(self, name):
        try:
            return self._storage[name]
        except KeyError:
            raise exc.NotFoundOperationalStorageError(name=name)


class MetaModel(abc.ABCMeta):

    def __new__(cls, name, bases, attrs):
        props = {}
        attrs["id_properties"] = {}

        for key, value in attrs.copy().items():
            if isinstance(
                value,
                (properties.PropertyCreator, properties.PropertyCollection),
            ):
                props[key] = value
                del attrs[key]
        all_base_properties = properties.PropertyCollection()
        for base in bases:
            base_properties = getattr(base, "properties", None)
            if isinstance(base_properties, properties.PropertyCollection):
                all_base_properties += base_properties
        attrs["properties"] = (
            attrs.pop("properties", properties.PropertyCollection())
            + all_base_properties
            + properties.PropertyCollection(**props)
        )
        for key, prop in attrs["properties"].items():
            if prop.is_id_property():
                attrs["id_properties"][key] = attrs["properties"].properties[
                    key
                ]
        dm_class = super(MetaModel, cls).__new__(cls, name, bases, attrs)
        dm_class.__operational_storage__ = DmOperationalStorage()
        return dm_class

    def __getattr__(cls, name):
        try:
            return cls.properties[name]
        except KeyError:
            raise AttributeError(
                "%s object has no attribute %s" % (cls.__name__, name)
            )

    def to_openapi_spec(self, prop_kwargs):
        spec = {
            "type": "string",
        }
        spec.update(types.build_prop_kwargs(kwargs=prop_kwargs))
        return spec


class Model(collections_abc.Mapping, metaclass=MetaModel):
    _python_simple_types = (type(None), str, int, float, complex, bool)

    def __init__(self, **kwargs):
        super(Model, self).__init__()
        self.pour(**kwargs)

    def __getattr__(self, name):
        try:
            return self.properties[name].value
        except KeyError:
            raise AttributeError(
                "%s object has no attribute %s" % (type(self).__name__, name)
            )

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
                property_type=e.get_property_type(),
            )
        except exc.ReadOnlyProperty:
            raise exc.ReadOnlyProperty(name=name, model=type(self))

    def pour(self, **kwargs):
        try:
            self.properties = properties.PropertyManager(
                self.properties, **kwargs
            )
            self.validate()
        except exc.PropertyRequired as e:
            raise exc.PropertyRequired(name=e.name, model=self.__class__)

        self.id_properties = {}
        for name, prop in self.properties.items():
            if prop.is_id_property():
                self.id_properties[name] = prop

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
        for name, value in values.items():
            setattr(self, name, value)

    @classmethod
    def get_id_property(cls):
        if len(cls.id_properties) == 1:
            return cls.id_properties.copy()

        raise TypeError(
            "Model %s has %s properties which marked as "
            "id_property. Please implement get_id_property "
            "method on your model."
            % (type(cls), "many" if cls.id_properties else "no")
        )

    @classmethod
    def get_id_property_name(cls):
        for key in cls.get_id_property():
            return key

    def get_id_properties(self):
        return self.id_properties.copy()

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

    def as_plain_dict(self):
        plain_dict = {}
        props = self.properties

        for name in props:
            val = props[name].value
            if isinstance(val, Model):
                plain_dict[name] = val.get_id()
            elif isinstance(val, self._python_simple_types):
                plain_dict[name] = val
            else:
                plain_dict[name] = copy.deepcopy(val)

        return plain_dict

    def __getitem__(self, name):
        return self.properties[name].value

    def __iter__(self):
        return iter(self.properties)

    def __len__(self):
        return len(self.properties)

    def __str__(self):
        if len(self.id_properties) == 0:
            return self.__repr__()

        return "<%s %s>" % (self.__class__.__name__, self.get_id())

    def __repr__(self):
        result = []
        for k, v in self.items():
            result.append("%s: %s" % (k, v))
        result = ", ".join(result)
        return "<%s {%s}>" % (self.__class__.__name__, result)


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

    uuid = properties.property(
        types.UUID(),
        read_only=True,
        id_property=True,
        default=lambda: uuid.uuid4(),
    )


class ModelWithRequiredUUID(ModelWithUUID):

    uuid = properties.property(
        types.UUID(), read_only=True, id_property=True, required=True
    )


class CustomPropertiesMixin(object):

    __custom_properties__ = {}

    @classmethod
    def get_custom_properties(cls):
        for name, prop_type in cls.__custom_properties__.items():
            yield name, prop_type

    @classmethod
    def get_custom_property_type(cls, property_name):
        return cls.__custom_properties__[property_name]

    def _check_custom_property_value(
        self, name, value, static=False, should_be=None
    ):
        prop_type = self.__custom_properties__[name]
        prop_type.validate(value)
        if static and should_be != value:
            raise ValueError(
                (
                    "The value for property `%s` should be `%s` "
                    "but actual value is `%s`"
                )
                % (name, should_be, value)
            )


class ModelWithTimestamp(Model):

    created_at = properties.property(
        types.UTCDateTimeZ(),
        required=True,
        read_only=True,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = properties.property(
        types.UTCDateTimeZ(),
        required=True,
        read_only=True,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    def update(self, session=None, force=False, *args, **kwargs):
        if self.is_dirty() or force:
            self.properties["updated_at"].set_value_force(
                datetime.datetime.now(datetime.timezone.utc)
            )
        super().update(session=session, force=force, *args, **kwargs)


class ModelWithProject(Model):

    project_id = properties.property(
        types.UUID(), required=True, read_only=True
    )


class ModelWithNameDesc(Model):

    name = properties.property(types.String(max_length=255), default="")
    description = properties.property(types.String(max_length=255), default="")


class ModelWithRequiredNameDesc(ModelWithNameDesc):

    name = properties.property(
        types.String(max_length=255),
        required=True,
    )


class DumpToSimpleViewMixin:
    def dump_to_simple_view(
        self,
        skip: tp.Iterable[str] | None = None,
        save_uuid: bool = False,
        custom_properties: bool = False,
    ):
        skip = skip or []
        result = {}
        for name, prop in self.properties.properties.items():
            if name in skip:
                continue
            prop_type = prop.get_property_type()
            if save_uuid and (
                isinstance(prop_type, types.UUID)
                or (
                    isinstance(prop_type, types.AllowNone)
                    and isinstance(prop_type.nested_type, types.UUID)
                )
            ):
                result[name] = getattr(self, name)
                continue

            result[name] = prop_type.to_simple_type(getattr(self, name))

        # Convert the custom properties.
        if not custom_properties and not hasattr(
            self, "__custom_properties__"
        ):
            return result

        for name, prop_type in self.get_custom_properties():
            result[name] = prop_type.to_simple_type(getattr(self, name))

        return result


class RestoreFromSimpleViewMixin:
    @classmethod
    def restore_from_simple_view(
        cls, skip_unknown_fields: bool = False, **kwargs
    ):
        model_format = {}
        for name, value in kwargs.items():
            name = name.replace("-", "_")

            # Ignore unknown fields
            if skip_unknown_fields and name not in cls.properties.properties:
                continue

            try:
                prop_type = cls.properties.properties[name].get_property_type()
            except KeyError:
                prop_type = cls.get_custom_property_type(name)
            prop_type = (
                type(prop_type)
                if not inspect.isclass(prop_type)
                else prop_type
            )
            if not isinstance(value, prop_type):
                try:
                    model_format[name] = (
                        cls.properties.properties[name]
                        .get_property_type()
                        .from_simple_type(value)
                    )
                except KeyError:
                    model_format[name] = cls.get_custom_property_type(
                        name
                    ).from_simple_type(value)
            else:
                model_format[name] = value
        return cls(**model_format)


class SimpleViewMixin(DumpToSimpleViewMixin, RestoreFromSimpleViewMixin):
    pass
