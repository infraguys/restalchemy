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

from restalchemy.api import constants
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
        """Get any resource from service using request and custom uri

        This method allows to get any resource, if there is a controller with
        a get method for it. In this case, the request will be the same as the
        call through the API, with the exception of the passage of
        middlewares.

        :param request: The user request
        :param uri: The custom URI for desired resource

        :return: The resource which controller returns
        """
        resource_locator = cls.get_locator(uri)
        uri_stack = uri.split('/')

        # has parent resource?
        pstack = resource_locator.path_stack
        parent_resource = None

        # NOTE(efrolov): Get all resources except the last
        for num in range(len(pstack[:-1])):
            if not isinstance(pstack[num], six.string_types):
                # NOTE(efrolov): pstack is shorter than uri_stack by 1
                #                element. And I have to grab the ID, so +2.
                parent_uri = '/'.join(uri_stack[0:num + 2])
                parent_locator = cls.get_locator(parent_uri)
                parent_resource = parent_locator.get_resource(
                    request, parent_uri, parent_resource=parent_resource)

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

    def get_type(self,):
        return self._resource.get_property_type(
            property_name=self._model_property_name,
        )

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


class BaseHiddenFieldsMap(object):

    def __init__(self, hidden_fields=None):
        super(BaseHiddenFieldsMap, self).__init__()
        self._hidden_fields = set(hidden_fields or [])

    def is_hidden_field(self, model_field_name, req):
        return model_field_name in self

    def __contains__(self, item):
        # NOTE(efrolov): backward compatibility
        return item in self._hidden_fields


class HiddenFieldsCompatibleClass(BaseHiddenFieldsMap):
    pass


class HiddenFieldMap(BaseHiddenFieldsMap):

    def __init__(self, **kwargs):
        """Hidden fields mapper for resource

        This class describes a list of fields that should be hidden for
        various RestAlchemy API methods. The methods supported by RA are
        declared in the `restalchemy.api.constants` module. To hide the
        `my_hidden_field` field for the FILTER method, the code will look
        like this:

        ```
        HiddenFieldMap(filter=['my_hidden_field'])
        ```

        For all other RA API methods, `my_hidden_field` field will not be
        hidden.

        :param filter: HTTP method GET for :func:`Controller.filter` method
        :param get: HTTP method GET for :func:`Controller.get` method
        :param create: HTTP method POST for :func:`Controller.create` method
        :param update: HTTP method PUT for :func:`Controller.update` method
        :param delete: HTTP method PUT for :func:`Controller.delete` method
        :param action_get: HTTP method GET for :func:`Action.get` method
        :param action_post: HTTP method POST for :func:`Action.post` method
        :param action_put: HTTP method PUT for :func:`Action.put` method
        """
        params = {}
        all_values = []
        for method in constants.ALL_RA_METHODS:
            value_arg = kwargs.pop(method.lower(), [])
            params[method] = value_arg
            all_values += value_arg
        if kwargs:
            raise TypeError('Got an unexpected keyword arguments %r' % kwargs)
        super(HiddenFieldMap, self).__init__(hidden_fields=all_values)
        self._method_map = {m: set(v) for m, v in params.items()}

    def is_hidden_field(self, model_field_name, req):
        """Checks that a field is in the list of hidden list

        :param model_field_name: The field name
        :param req: The webob request
        :return: True or False
        """
        try:
            method = req.api_context.get_active_method()
            return model_field_name in self._method_map[method]
        except KeyError:
            raise NotImplementedError("Unsupported RA method `%s`" % req)


@six.add_metaclass(abc.ABCMeta)
class AbstractResource(object):

    def __init__(self, model_class, name_map=None, hidden_fields=None,
                 convert_underscore=True, process_filters=False,
                 model_subclasses=None):
        """Resource constructor

        :param model_class: The model class that is the source of the fields
                            for the resource
        :param name_map: The dictionary whose key is the name of the field in
                         the model and the value is the name of the field in
                         the resource. All model fields that match the names
                         from the passed keys in dictionary will be renamed to
                         values in passed dictionary.
        :param hidden_fields: The list of field names or instance of
                              :class:`HiddenFieldMap` class to hide from the
                              API user. The user will also not be able to set
                              these fields using API. All fields starting with
                              _ are already hidden from the user.
        :param convert_underscore: The boolean value. Should a resource
                                   convert _ to -
        :param process_filters: The boolean value. If the value is True then RA
                                will try to automatically parse the filters and
                                convert the filter values to the field type of
                                the model (resource).
        :param model_subclasses: The list of subclasses that can be represented
                                 by this resource, most often these are the
                                 children of the model specified in the
                                 model_class argument.
        """
        super(AbstractResource, self).__init__()
        self._model_class = model_class
        self._name_map = name_map or {}
        # NOTE(efrolov): to support the old resource interface
        if not isinstance(hidden_fields, BaseHiddenFieldsMap):
            hidden_fields = HiddenFieldsCompatibleClass(
                hidden_fields=hidden_fields,
            )
        self._hidden_fields = hidden_fields
        self._convert_underscore = convert_underscore
        self._process_filters = process_filters
        self._model_subclasses = model_subclasses or []
        ResourceMap.add_model_to_resource_mapping(model_class, self)
        for model_subclass in self._model_subclasses:
            ResourceMap.add_model_to_resource_mapping(model_subclass, self)

    def is_process_filters(self):
        return self._process_filters

    @abc.abstractmethod
    def get_fields(self, override_is_public_field_func=None):
        raise NotImplementedError()

    def get_fields_by_request(self, req):
        """Get fields

        :param req: the webob request
        :return: A dict of fields for specific method
        """
        def is_public_field(model_field_name):
            return self.is_public_field_by_request(
                req=req,
                model_field_name=model_field_name,
            ) and req.api_context.can_be_shown_field(
                self.get_resource_field_name(
                    model_field_name=model_field_name,
                )
            )

        return self.get_fields(override_is_public_field_func=is_public_field)

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
        return not (model_field_name.startswith('_')
                    or model_field_name in self._hidden_model_fields)

    def is_public_field_by_request(self, req, model_field_name):
        return not (
            model_field_name.startswith('_')
            or self._hidden_fields.is_hidden_field(
                model_field_name=model_field_name,
                req=req,
            )
        )

    def get_property_type(self, property_name):
        model = self.get_model()
        return model.properties.properties[property_name].get_property_type()

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

    def get_fields(self, override_is_public_field_func=None):
        """Get resource fields

        :return: The dict of resource fields.
        """
        is_public_field = (
            override_is_public_field_func or self.is_public_field
        )
        for name, prop in self._model_class.properties.items():
            if issubclass(prop, ra_properties.BaseProperty):
                prop = ResourceRAProperty(
                    resource=self,
                    prop_type=(self._model_class.properties.properties[name]
                               .get_property_type()),
                    model_property_name=name,
                    public=is_public_field(name),
                )
            elif issubclass(prop, ra_relationsips.BaseRelationship):
                prop = ResourceRelationship(
                    self, model_property_name=name,
                    public=is_public_field(name),
                )
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

    def get_id_type(self):
        id_property = self._model_class.get_id_property()
        if len(id_property) != 1:
            raise TypeError("Model %s returns %s properties which marked as "
                            "id_property. Please implement get_id_type "
                            "method on your resource %r."
                            % (self._model_class,
                               'many' if id_property else 'no',
                               type(self)))
        return id_property.popitem()[-1].get_property_type()


class ResourceByModelWithCustomProps(ResourceByRAModel):

    def get_fields(self, override_is_public_field_func=None):
        """Get resource fields

        :return: The dict of resource fields.
        """
        is_public_field = (
            override_is_public_field_func or self.is_public_field
        )

        fields = super(ResourceByModelWithCustomProps, self).get_fields(
            override_is_public_field_func=override_is_public_field_func,
        )

        for name, prop in fields:
            yield name, prop
        for name, prop_type in self._model_class.get_custom_properties():
            yield name, ResourceRAProperty(
                resource=self,
                prop_type=prop_type,
                model_property_name=name,
                public=is_public_field(name),
            )

    def get_property_type(self, property_name):
        try:
            property_type = super(
                ResourceByModelWithCustomProps,
                self,
            ).get_property_type(property_name=property_name)
        except KeyError:
            model = self.get_model()
            property_type = model.get_custom_property_type(
                property_name=property_name,
            )
        return property_type

    def get_resource_id(self, model):
        return str(model.get_id())
