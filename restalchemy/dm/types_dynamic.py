#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
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
import logging
import uuid

from restalchemy.common import exceptions as ra_exc
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types

LOG = logging.getLogger(__name__)


def build_prop_kwargs(kwargs):
    """
    Build the openapi schema properties from the given ``kwargs``.

    The main purpose of this function is to map the ``kwargs`` to the
    corresponding openapi property name and handle the special cases for
    values that are not serializable to json (like UUIDs).

    :param kwargs: dictionary of keyword arguments
    :return: dictionary of openapi properties
    """
    result = {}
    for k, v in types.KWARGS_OPENAPI_MAP.items():
        if k in kwargs.keys():
            value = kwargs[k]() if callable(kwargs[k]) else kwargs[k]
            if isinstance(value, (types.UUID, uuid.UUID)):
                value = "uuid"
            elif isinstance(value, datetime.datetime):
                value = value.strftime(types.OPENAPI_FMT)
            if hasattr(value, "__dict__"):
                value = {
                    name: prop.get_property_type().to_simple_type(value[name])
                    for name, prop in value.properties.properties.items()
                }
            result[v] = value
    return result


class UnknownType(Exception):
    pass


class AbstractKindType(types.BasePythonType):
    def from_unicode(self, value):
        """
        Deserialize the given value into a python object.

        This method is used by the ``from_unicode`` method of the
        ``BaseType`` class. It takes a unicode string as an argument and
        returns a python object.

        The default implementation of this method simply calls the
        ``from_unicode`` method of the ``BaseType`` class with the
        deserialized value from the given ``value``.

        :param value: unicode string to be deserialized
        :return: python object
        """
        return super().from_unicode(self.from_simple_type(json.loads(value)))


class AbstractKindModel(models.Model, metaclass=abc.ABCMeta):
    DOMAIN = uuid.UUID("0188bbae-7e1b-11ee-a337-047c160cda6f")

    @classmethod
    @abc.abstractmethod
    def KIND(cls):
        """
        The kind of the object.

        This abstract property should be overridden by subclasses to return
        a string that uniquely identifies the kind of the object.

        :return: string
        :raises NotImplementedError: If the method is not implemented by a
            subclass.
        """
        raise NotImplementedError()

    kind = properties.property(
        types.String(min_length=1, max_length=128),
        required=True,
        read_only=True,
    )

    def __init__(self, kind=None, **kwargs):
        """
        Initialize the object.

        :param kind: the kind of the object. If not given, the class' KIND
            property is used.
        :param kwargs: keyword arguments to be passed to the parent class'
            constructor.
        """
        kind = kind or self.KIND
        super().__init__(kind=kind, **kwargs)


class KindModelType(types.BasePythonType):
    def __init__(self, model):
        """
        Initialize the type.

        :param model: the model class to be represented by this type.
        :type model: type
        """
        super(KindModelType, self).__init__(
            python_type=model,
            openapi_type="object",
        )

    @property
    def kind(self):
        """
        Return the kind of the object.

        This property is read-only and returns the kind of the object as given
        by the KIND property of the class.

        :return: string
        """
        return self._python_type.KIND

    def from_simple_type(self, value):
        """
        Convert a simple type representation into an instance of the model
        type.

        This function takes a dictionary representation of the model and
        converts it into an instance of the associated model type. Each field
        in the input dictionary is processed using the corresponding
        property's `from_simple_type` method. If there are any extra fields
        in the input dictionary that do not correspond to the model's
        properties, a `ValueError` is raised.

        :param value: A dictionary where keys are field names and values are
            the simple type representations of the model's properties.
        :return: An instance of the model type with fields populated from the
            input dictionary.
        :raises ValueError: If the input dictionary contains unknown fields.
        """

        copied_value = copy.deepcopy(value)
        parsed_value = {}
        for name, prop in self._python_type.properties.properties.items():
            if name in copied_value:
                property_type = prop.get_property_type()
                try:
                    val = copied_value.pop(name)
                    parsed_value[name] = property_type.from_simple_type(val)
                except (ValueError, TypeError):
                    raise ra_exc.ParseError(value="%s=%s" % (name, val))
                except ra_exc.ParseError as e:
                    raise ra_exc.ParseError(value="%s=%s" % (name, e.value))
        if copied_value:
            raise ra_exc.ParseError(
                value="(Unknown fields: %s)" % (copied_value)
            )
        return self._python_type(**parsed_value)

    def to_simple_type(self, value):
        """
        Convert an instance of the model type to a simple type representation.

        This function takes an instance of the model type and converts it into
        a dictionary representation. Each field in the model is processed
        using the corresponding property's `to_simple_type` method to obtain
        its simple type representation.

        :param value: An instance of the model type with fields to be
            converted.
        :return: A dictionary where keys are field names and values are the
            simple type representations of the model's properties.
        """
        return {
            name: prop.get_property_type().to_simple_type(value[name])
            for name, prop in value.properties.properties.items()
        }

    def to_openapi_spec(self, prop_kwargs):
        """
        Return an OpenAPI specification for this type.

        :param prop_kwargs: additional keyword arguments to be passed to
            `build_prop_kwargs`.
        :return: an OpenAPI specification for this type.
        """
        props = {
            name: prop.get_property_type().to_openapi_spec(prop.get_kwargs())
            for name, prop in self._python_type.properties.properties.items()
        }
        props["kind"] = {"type": "string", "enum": [self.kind]}
        spec = {"type": self.openapi_type, "properties": props}
        spec.update(build_prop_kwargs(kwargs=prop_kwargs))
        return spec


class KindModelSelectorType(types.BaseType):
    def __init__(self, *args):
        """
        Initialize the type.

        :param args: A variable number of arguments
            of :py:class:`KindModelType` instances.
        """
        super(KindModelSelectorType, self).__init__(openapi_type="object")
        self._kind_type_map = {model.kind: model for model in args}

    def validate(self, value):
        """
        Check if the given value is valid according to the type definition.

        This function takes a value and checks if it is valid according to the
        definition of this type. This is done by looking up the type of the
        value in the map of types and checking if the value is valid according
        to that type.

        :param value: The value to be validated.
        :return: ``True`` if the value is valid, ``False`` otherwise.
        """
        try:
            value_type_name = value.kind
            value_type = self._kind_type_map[value_type_name]
            return value_type.validate(value)
        except (AttributeError, KeyError):
            return False

    def to_simple_type(self, value):
        """
        Convert an instance of the model type to a simple type representation.

        This function takes an instance of the model type and converts it into
        a dictionary representation. The dictionary representation is obtained
        by calling the `to_simple_type` method of the type corresponding to
        the kind of the model instance.

        :param value: An instance of the model type with fields to be
            converted.
        :return: A dictionary where keys are field names and values are the
            simple type representations of the model's properties.
        """
        value_type_name = value.kind
        value_type = self._kind_type_map[value_type_name]
        return value_type.to_simple_type(value)

    def from_simple_type(self, value):
        """
        Convert a simple type representation into an instance of the model
        type.

        This function takes a dictionary representation of the model and
        determines the appropriate model class to use based on the 'kind'
        field. It then uses the `from_simple_type` method of the identified
        model class to instantiate an instance of the model type. If the
        'kind' is not found or is invalid, an `UnknownType` error is raised.

        :param value: A dictionary with a 'kind' field indicating the model
            type and additional fields representing the simple type data.
        :return: An instance of the model type corresponding to the 'kind'
            field.
        :raises UnknownType: If the 'kind' field does not correspond to any
            known model type.
        """
        try:
            value_type_name = value["kind"]
            value_class = self._kind_type_map[value_type_name]
            return value_class.from_simple_type(value)
        except (AttributeError, KeyError):
            raise UnknownType("Unknown kind for value: %s" % value)

    def from_unicode(self, value):
        """
        Deserialize the given Unicode string into an instance of the model
        type.

        This method parses the input Unicode string as JSON and converts the
        resulting dictionary into an instance of the corresponding model type
        using the `from_simple_type` method.

        :param value: A Unicode string representing the JSON-encoded simple
            type data.
        :return: An instance of the model type.
        :raises json.JSONDecodeError: If the input string is not valid JSON.
        :raises UnknownType: If the 'kind' field in the decoded JSON does not
            correspond to any known model type.
        """

        return self.from_simple_type(json.loads(value))

    def to_openapi_spec(self, prop_kwargs):
        """
        Generate an OpenAPI specification for the model type.

        This method creates a dictionary representing the OpenAPI
        specification for the model type. The specification includes the
        OpenAPI type of the model and incorporates additional properties
        from `prop_kwargs` if provided.

        :param prop_kwargs: Additional keyword arguments for building the
            OpenAPI specification.
        :return: A dictionary representing the OpenAPI specification.
        """

        spec = {
            "type": self.openapi_type,
            "oneOf": [
                subtype.to_openapi_spec({})
                for subtype in self._kind_type_map.values()
            ],
        }

        spec.update(build_prop_kwargs(kwargs=prop_kwargs))
        return spec
