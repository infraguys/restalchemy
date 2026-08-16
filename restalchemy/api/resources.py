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

from webob.request import Request

from restalchemy.api import constants
from restalchemy.api import contexts
from restalchemy.api import field_permissions
from restalchemy.common import exceptions as exc
from restalchemy.dm import properties as ra_properties
from restalchemy.dm import relationships as ra_relationsips
from restalchemy.dm import types as ra_types


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
        uri_stack = uri.split("/")

        # has parent resource?
        pstack = resource_locator.path_stack
        parent_resource = None

        # NOTE(efrolov): Get all resources except the last
        for num in range(len(pstack[:-1])):
            if not isinstance(pstack[num], str):
                # NOTE(efrolov): pstack is shorter than uri_stack by 1
                #                element. And I have to grab the ID, so +2.
                parent_uri = "/".join(uri_stack[0 : num + 2])
                parent_locator = cls.get_locator(parent_uri)
                parent_resource = parent_locator.get_resource(
                    request, parent_uri, parent_resource=parent_resource
                )

        return resource_locator.get_resource(request, uri, parent_resource)

    @classmethod
    def set_resource_map(cls, resource_map):
        cls.resource_map = resource_map

    @classmethod
    def add_model_to_resource_mapping(cls, model_class, resource):
        if model_class in cls.model_type_to_resource:
            if (
                cls.model_type_to_resource[model_class].get_model()
                is not resource.get_model()
            ):
                raise ValueError(
                    "model (%s) is already mapped to a different resource (%s)."
                    % (model_class, cls.model_type_to_resource[model_class])
                )
        cls.model_type_to_resource[model_class] = resource

    @classmethod
    def get_resource_by_model(cls, model):
        model_type = model.get_model_type()
        try:
            return cls.model_type_to_resource[model_type]
        except KeyError:
            raise exc.CanNotFindResourceByModel(model=model)


class AbstractResourceProperty(metaclass=abc.ABCMeta):
    def __init__(self, resource, model_property_name, public=True):
        super(AbstractResourceProperty, self).__init__()
        self._resource = resource
        self._model_property_name = model_property_name
        self._hidden = False
        self._public = public

    def is_public(self):
        return self._public

    def get_type(
        self,
    ):
        return self._resource.get_property_type(
            property_name=self._model_property_name,
        )

    def is_id_property(self):
        return self._resource.is_id_property(
            property_name=self._model_property_name,
        )

    @property
    def api_name(self):
        return self._resource.get_resource_field_name(self._model_property_name)

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

    def get_dump_callable(self):
        """What turns a model value into the value the API writes out.

        `None` says the value goes out as it stands, which lets a packer
        leave the call out altogether rather than reach the identity two
        frames down. A field that does not know either way says so by
        handing back its own `dump_value`.
        """
        return self.dump_value


class ResourceProperty(AbstractResourceProperty):
    pass


# The `to_simple_type` implementations that hand the value back unchanged.
_IDENTITY_TO_SIMPLE_TYPES = frozenset(
    (
        ra_types.BasePythonType.to_simple_type,
        ra_types.BaseRegExpType.to_simple_type,
        ra_types.Enum.to_simple_type,
    )
)


class ResourceRAProperty(ResourceProperty):
    def __init__(self, resource, prop_type, model_property_name, public=True):
        super(ResourceRAProperty, self).__init__(
            resource=resource,
            model_property_name=model_property_name,
            public=public,
        )
        self._prop_type = prop_type() if inspect.isclass(prop_type) else prop_type

    def parse_value(self, req, value):
        return self._prop_type.from_simple_type(value)

    def parse_value_from_unicode(self, req, value):
        return self._prop_type.from_unicode(value)

    def dump_value(self, value):
        return self._prop_type.dump_value(value)

    def get_dump_callable(self):
        prop_type_class = type(self._prop_type)
        if (
            prop_type_class.dump_value is ra_types.BaseType.dump_value
            and prop_type_class.to_simple_type in _IDENTITY_TO_SIMPLE_TYPES
        ):
            # A string, an integer, an enum: the simple form is the value.
            # Say so, instead of calling two methods to be handed it back.
            # Which implementation the type resolved to is what is
            # checked, so a subclass that converts (`Decimal`) is not
            # mistaken for the base it inherits from.
            return None
        return self._prop_type.dump_value


class ResourceRelationship(AbstractResourceProperty):
    def parse_value(self, req, value):
        return ResourceMap.get_resource(req, value)

    def parse_value_from_unicode(self, req, value):
        return self.parse_value(req, value)

    def dump_value(self, value):
        return ResourceMap.get_location(value)

    def is_id_property(self):
        return False


class BaseHiddenFieldsMap(object):
    def __init__(self, hidden_fields=None):
        super(BaseHiddenFieldsMap, self).__init__()
        self._hidden_fields = set(hidden_fields or [])

    @property
    def hidden_fields(self):
        return self._hidden_fields

    def is_hidden_field(self, model_field_name, req):
        return model_field_name in self

    def is_hidden_field_by_method(self, model_field_name, method):
        return model_field_name in self

    def visibility_key(self, req):
        """What this request makes `is_hidden_field` depend on.

        A hashable value standing for every answer this map will give
        about this request; `None` when they cannot be summarised, and
        then a resource resolves its fields per request as it always did.
        See `_hidden_fields_key`, which does not take a subclass's word
        for it.
        """
        # One set of hidden fields, whoever is asking.
        return ()

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
            raise TypeError("Got an unexpected keyword arguments %r" % kwargs)
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

    def is_hidden_field_by_method(self, model_field_name, method):
        try:
            return model_field_name in self._method_map[method]
        except KeyError:
            raise NotImplementedError("Unsupported RA method `%s`" % method)

    def visibility_key(self, req):
        method = field_permissions.active_method(req)
        return None if method is None else (method,)


class RoleBasedHiddenFieldContainer(BaseHiddenFieldsMap):
    def __init__(self, default, **kwargs):
        """The role based hidden field container

        The container of hidden fields. The class calculates the hidden fields
        using the roles from the oslo context.

        This class describes a list of fields that should be hidden for
        various oslo context roles. An object of the HiddenFieldMap class is
        used to specify lists of hidden fields for a role. The example below
        describes a different set of hidden fields for a user with the admin
        role and for users without the admin role:

        ```
        RoleBasedHiddenFieldContainer(
            default=HiddenFieldMap(get=['only_for_admin', 'hidden_field']),
            admin=HiddenFieldMap(get=['hidden_field']),
        )
        ```

        The example shows that the resource fields `only_for_admin` and
        `hidden_field` will be hidden by default for all roles. For the admin
        role, only `hidden_field` field is hidden.

        :param default: The instance of :class:`HiddenFieldMap` class. Hidden
                        fields for any role that has no other rules defined.
        :type default: HiddenFieldMap
        :param **kwargs: An optional parameter. The parameter name is the name
                         of the role name and parameter value is an instance
                         of :class:`HiddenFieldMap` class.
        :type default: HiddenFieldMap
        """
        self._default_hidden_fields = default
        self._hidden_fields_by_role = kwargs
        super(RoleBasedHiddenFieldContainer, self).__init__(
            hidden_fields=default.hidden_fields,
        )

    @staticmethod
    def _get_roles(req):
        """Returns the roles

        Returns the roles from the oslo context or an empty list if the
        context does not exist in the request from the user. Oslo context may
        be missing in the request if keystone middleware is not included to
        wsgi pipeline.

        :param req: The webob request that can contain oslo context
        :return: The list of roles from context or empty list if context is
                 missing.

        """
        roles = []

        if hasattr(req, "context") and hasattr(req.context, "roles"):
            roles = req.context.roles

        return roles

    def is_hidden_field(self, model_field_name, req):
        """Checks that a field is in the list of hidden list

        The field is considered hidden if the field is included to all hidden
        fields lists    for the specified roles.

        :param model_field_name: The field name
        :param req: The webob request that can contain oslo context
        :return: True or False
        """
        context_roles = self._get_roles(req)

        for rname, h_fields in self._hidden_fields_by_role.items():
            if rname in context_roles and not h_fields.is_hidden_field(
                model_field_name,
                req,
            ):
                return False
        return self._default_hidden_fields.is_hidden_field(model_field_name, req)

    def is_hidden_field_by_method(self, model_field_name, method):
        return True

    def visibility_key(self, req):
        # Which role answers depends on the roles the request carries;
        # what that role then answers is its own map's business. Every
        # role the request carries is asked and any one of them can
        # unhide a field, so the order they arrive in decides nothing and
        # the set of them is the whole of what this depends on.
        keys = [_hidden_fields_key(self._default_hidden_fields, req)]
        for role, hidden_fields in self._hidden_fields_by_role.items():
            keys.append(role)
            keys.append(_hidden_fields_key(hidden_fields, req))
        if any(key is None for key in keys):
            return None
        return (frozenset(self._get_roles(req)), tuple(keys))


# The implementations shipped here, which `visibility_key` describes. A
# map deciding visibility its own way inherits a key that does not
# describe it, so the key is only trusted from these.
_SHIPPED_HIDDEN_FIELDS = frozenset(
    (
        BaseHiddenFieldsMap.is_hidden_field,
        HiddenFieldMap.is_hidden_field,
        RoleBasedHiddenFieldContainer.is_hidden_field,
    )
)


def _hidden_fields_key(hidden_fields, req):
    """`hidden_fields`' key for this request, or `None` to reuse nothing."""
    if getattr(type(hidden_fields), "is_hidden_field", None) not in (
        _SHIPPED_HIDDEN_FIELDS
    ):
        return None
    return hidden_fields.visibility_key(req)


class AbstractResource(metaclass=abc.ABCMeta):
    def __init__(
        self,
        model_class,
        name_map=None,
        hidden_fields=None,
        convert_underscore=True,
        process_filters=False,
        model_subclasses=None,
        fields_permissions=None,
    ):
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
        :param fields_permissions: The dict of field and permissions, instance
                                 of `field_permissions.BasePermissions`.
                                 Use for setting field hidden or readonly by
                                 role from request context. if
                                 fields_permissionsis wouldn't set,
                                 it would be the object of UniversalPermissions
                                 with READWRITE permissions to all fields
        """
        super(AbstractResource, self).__init__()
        # Resource fields already built, by (model field name, public).
        self._field_cache = {}
        # API names already worked out, by model field name.
        self._api_names = {}
        # What was resolved for a request that may see what this one may,
        # by visibility key. See `request_cache`.
        self._visibility_caches = {}
        self._model_class = model_class
        self._name_map = name_map or {}
        self._inv_name_map = {v: k for k, v in self._name_map.items()}
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

        self._fields_permissions = (
            fields_permissions
            if fields_permissions is not None
            else field_permissions.UniversalPermissions(
                permission=field_permissions.Permissions.RW
            )
        )

        if not isinstance(self._fields_permissions, field_permissions.BasePermissions):
            raise ValueError(
                "Fields_permissions should inherit"
                "from BasePermissions, not {%s}" % (type(fields_permissions))
            )

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

    # How many visibilities to remember. The key carries the caller's
    # roles, and there is no reason to hold every combination that ever
    # arrived; past this, requests resolve their own.
    _MAX_VISIBILITY_CACHES = 64

    def request_cache(self, req):
        """Somewhere to keep what any request seeing the same fields sees.

        Resolving a resource's fields is a property object and three
        predicates per field, and the answer is the same for every request
        told the same about every field -- which is what the visibility
        key stands for. A caller may keep whatever it derives from those
        fields here too, as long as it does not change it afterwards.

        `None` when nothing may be shared: the request narrows the fields
        itself with `fields`, or something in the way visibility is
        decided cannot say what it depends on. Then the caller resolves
        its own, which is what always happened.
        """
        key = self._visibility_key(req)
        if key is None:
            return None
        cache = self._visibility_caches.get(key)
        if cache is None:
            if len(self._visibility_caches) >= self._MAX_VISIBILITY_CACHES:
                return None
            cache = {}
            self._visibility_caches[key] = cache
        return cache

    def _visibility_key(self, req):
        context = getattr(req, "api_context", None)
        if (
            getattr(type(context), "can_be_shown_field", None)
            is not contexts.RequestContext.can_be_shown_field
        ):
            return None
        if context.fields_to_show:
            # A projection this request asked for and the next one may
            # not: narrow enough that resolving it per request is right.
            return None
        hidden_key = _hidden_fields_key(self._hidden_fields, req)
        if hidden_key is None:
            return None
        permissions_key = field_permissions.visibility_key_of(
            self._fields_permissions, req
        )
        if permissions_key is None:
            return None
        return (hidden_key, permissions_key)

    def get_fields_by_method(self, method):
        def is_public_field(model_field_name):
            return self.is_public_field_by_method(
                model_field_name=model_field_name,
                method=method,
            )

        return self.get_fields(override_is_public_field_func=is_public_field)

    @abc.abstractmethod
    def get_resource_id(self, model):
        raise NotImplementedError()

    @property
    def _m2r_name_map(self):
        return self._name_map

    @property
    def _r2m_name_map(self):
        return self._inv_name_map

    @property
    def _hidden_model_fields(self):
        return self._hidden_fields

    def get_model_field_name(self, res_field_name):
        name = self._r2m_name_map.get(res_field_name, res_field_name)
        return name.replace("-", "_") if self._convert_underscore else name

    def get_resource_field_name(self, model_field_name):
        # Asked per field per request, twice over -- once to decide
        # visibility, once for the name to write out -- and the answer is
        # a property of the resource.
        try:
            return self._api_names[model_field_name]
        except KeyError:
            name = self._m2r_name_map.get(model_field_name, model_field_name)
            name = name.replace("_", "-") if self._convert_underscore else name
            self._api_names[model_field_name] = name
            return name

    def is_public_field(self, model_field_name):
        return not (
            model_field_name.startswith("_")
            or model_field_name in self._hidden_model_fields
        )

    @property
    def fields_permissions(self):
        return self._fields_permissions

    def is_public_field_by_request(self, req, model_field_name):
        return not (
            model_field_name.startswith("_")
            or self._hidden_fields.is_hidden_field(
                model_field_name=model_field_name,
                req=req,
            )
        )

    def is_public_field_by_method(self, method, model_field_name):
        return not (
            model_field_name.startswith("_")
            or self._hidden_fields.is_hidden_field_by_method(
                model_field_name=model_field_name,
                method=method,
            )
        )

    def get_property_type(self, property_name):
        model = self.get_model()
        return model.properties.properties[property_name].get_property_type()

    def is_id_property(self, property_name):
        model = self.get_model()
        return model.properties[property_name].is_id_property()

    def get_model(self):
        return self._model_class

    def __repr__(self):
        return (
            "<%s[model=%r], name_map=%r, convert_underscore=%s, "
            "process_filters=%s, fields=%r>"
            % (
                self.__class__.__name__,
                self._model_class,
                self._name_map,
                self._convert_underscore,
                self._process_filters,
                self._model_class.properties.properties.keys(),
            )
        )

    def get_prop_kwargs(self, name, openapi_version):
        try:
            kwargs = dict(self.get_model().properties.properties[name].get_kwargs())
        except KeyError:
            kwargs = {}
        kwargs["openapi"] = openapi_version
        return kwargs

    def generate_schema_object(self, method, openapi_version):
        properties = {}
        required = []

        req = Request(environ={})
        req.api_context = contexts.RequestContext(req)
        req.api_context.set_active_method(method)

        for name, prop in self.get_fields_by_method(method):
            prop_kwargs = self.get_prop_kwargs(name, openapi_version)

            is_readonly = self._fields_permissions.is_readonly(name, req)
            is_hidden = self._fields_permissions.is_hidden(name, req)
            if prop.is_public() and not is_hidden:
                if is_readonly:
                    prop_kwargs["read_only"] = True
                properties[prop.api_name] = prop.get_type().to_openapi_spec(prop_kwargs)
                if (
                    prop_kwargs.get("required")
                    and "default" not in prop_kwargs
                    and (
                        method not in [constants.CREATE, constants.UPDATE]
                        or not is_readonly
                    )
                ):
                    required.append(prop.api_name)
        spec = {
            "type": "object",
            "properties": properties,
        }
        if required:
            spec["required"] = required
        return spec


class ResourceByRAModel(AbstractResource):
    def _prep_field(self, name, prop, override_is_public_field_func=None):
        is_public_field = override_is_public_field_func or self.is_public_field
        public = is_public_field(name)

        # A resource field is what the model declared plus one bit the
        # request decides, so there are two of each at most, and both were
        # rebuilt per field per request -- for a collection that is a
        # `issubclass` against an abstract base and an object per field.
        cached = self._field_cache.get((name, public))
        if cached is not None:
            return cached

        if issubclass(prop, ra_properties.BaseProperty):
            field = ResourceRAProperty(
                resource=self,
                prop_type=(
                    self._model_class.properties.properties[name].get_property_type()
                ),
                model_property_name=name,
                public=public,
            )
        elif issubclass(prop, ra_relationsips.BaseRelationship):
            field = ResourceRelationship(
                self,
                model_property_name=name,
                public=public,
            )
        else:
            raise TypeError("Unknown property type %s" % type(prop))

        self._field_cache[(name, public)] = field
        return field

    def get_field(self, name, override_is_public_field_func=None):
        if not (prop := self._model_class.properties.get(name)):
            raise ValueError("Model doesn't have field %s" % name)
        return self._prep_field(
            name,
            prop,
            override_is_public_field_func,
        )

    def get_fields(self, override_is_public_field_func=None):
        """Get resource fields

        :return: The dict of resource fields.
        """

        for name, prop in self._model_class.properties.items():
            yield name, self._prep_field(name, prop, override_is_public_field_func)

    def get_resource_id(self, model):
        # TODO(efrolov): Write code to convert value to simple value.
        if hasattr(model, "get_id"):
            return str(model.get_id())
        else:
            # TODO(efrolov): Add autosearch resource id by model
            raise ValueError(
                "Can't find resource ID for %s. Please implement "
                "get_id method in your model (%s)" % (model, self._model_class)
            )

    def get_id_type(self):
        id_property = self._model_class.get_id_property()
        if len(id_property) != 1:
            raise TypeError(
                "Model %s returns %s properties which marked as "
                "id_property. Please implement get_id_type "
                "method on your resource %r."
                % (
                    self._model_class,
                    "many" if id_property else "no",
                    type(self),
                )
            )
        return id_property.popitem()[-1].get_property_type()


class ResourceByModelWithCustomProps(ResourceByRAModel):
    def get_field(self, name, override_is_public_field_func=None):
        try:
            return super(ResourceByModelWithCustomProps, self).get_field(
                name=name,
                override_is_public_field_func=override_is_public_field_func,
            )
        except ValueError:
            # native property doesn't exist, try custom property
            pass
        try:
            prop_type = self._model_class.get_custom_property_type(name)
        except KeyError:
            raise ValueError("Model doesn't have field %s" % name)
        is_public_field = override_is_public_field_func or self.is_public_field
        return self._prep_custom_field(name, prop_type, is_public_field(name))

    def get_fields(self, override_is_public_field_func=None):
        """Get resource fields

        :return: The dict of resource fields.
        """
        is_public_field = override_is_public_field_func or self.is_public_field

        fields = super(ResourceByModelWithCustomProps, self).get_fields(
            override_is_public_field_func=override_is_public_field_func,
        )

        for name, prop in fields:
            yield name, prop
        for name, prop_type in self._model_class.get_custom_properties():
            yield name, self._prep_custom_field(name, prop_type, is_public_field(name))

    def _prep_custom_field(self, name, prop_type, public):
        """A custom property's resource field, built once per visibility."""
        key = (name, public)
        field = self._field_cache.get(key)
        if field is None:
            field = ResourceRAProperty(
                resource=self,
                prop_type=prop_type,
                model_property_name=name,
                public=public,
            )
            self._field_cache[key] = field
        return field

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
