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
import inspect

from webob.request import Request

from restalchemy.api import constants
from restalchemy.api import contexts
from restalchemy.api import field_permissions
from restalchemy.common import exceptions as exc
from restalchemy.common import utils
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
    _REMOVED = {
        "is_hidden_field": "hidden_for",
        "is_hidden_field_by_method": "hidden_for_method",
        "visibility_key": "hidden_for",
    }

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        utils.refuse_removed_overrides(cls, BaseHiddenFieldsMap._REMOVED)

    def __init__(self, hidden_fields=None):
        super(BaseHiddenFieldsMap, self).__init__()
        self._hidden_fields = set(hidden_fields or [])

    @property
    def hidden_fields(self):
        return self._hidden_fields

    def hidden_for(self, req, field_names):
        """Which of `field_names` this request does not see, as one set.

        The one method a map of your own writes. It is asked once per
        request for every field at once, so whatever the answer turns on
        is read once -- and the set it returns is what a resource keeps
        its resolved fields by, so there is no separate summary to write
        and none to keep in step.
        """
        return frozenset(self._hidden_fields.intersection(field_names))

    def hidden_for_method(self, method, field_names):
        """Which of `field_names` are hidden from `method` alone.

        There is no request here: this is what the OpenAPI spec is built
        from, where a method is all there is to go on.
        """
        return frozenset(self._hidden_fields.intersection(field_names))

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

    def hidden_for(self, req, field_names):
        """Which of `field_names` this request does not see.

        The method is what the answer turns on, so it is read once
        rather than once per field.
        """
        method = req.api_context.get_active_method()
        return self.hidden_for_method(method, field_names)

    def hidden_for_method(self, method, field_names):
        try:
            hidden = self._method_map[method]
        except KeyError:
            raise NotImplementedError("Unsupported RA method `%s`" % method)
        return frozenset(hidden.intersection(field_names))


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

    def hidden_for(self, req, field_names):
        """Which of `field_names` this request does not see.

        A field is hidden when every role the request carries that this
        was told about hides it, and the default map hides it too. The
        roles are read once and each map is asked once.
        """
        context_roles = self._get_roles(req)
        hidden = self._default_hidden_fields.hidden_for(req, field_names)
        for rname, h_fields in self._hidden_fields_by_role.items():
            if rname in context_roles:
                hidden &= h_fields.hidden_for(req, field_names)
        return hidden

    def hidden_for_method(self, method, field_names):
        """Which of `field_names` the OpenAPI spec does not carry.

        There is no request here and so no roles, and the spec is built
        for a request carrying none -- which is the request the default
        map answers for, and the one the permissions are asked about in
        the same place. A field only a role may see stays out of a spec
        anyone may read.
        """
        return self._default_hidden_fields.hidden_for_method(method, field_names)


class Visibility(object):
    """What one request is told about a resource's fields.

    Hashable, and equal for two requests told the same thing -- which is
    what a resource keeps its resolved fields by. It is the answer as
    much as the key: there is no summary here that could come to
    describe something other than what the containers say.
    """

    __slots__ = ("_names", "_permissions", "hidden", "shown", "_key", "_by_name")

    def __init__(self, names, permissions, hidden, shown):
        # Held against the model's own order rather than sorted, so that
        # equal answers hash equal without a sort per request.
        self._names = names
        self._permissions = tuple(permissions[name] for name in names)
        self.hidden = hidden
        self.shown = shown
        self._key = (self._permissions, self.hidden, self.shown)
        self._by_name = None

    def permission_of(self, model_field_name):
        if self._by_name is None:
            self._by_name = dict(zip(self._names, self._permissions))
        return self._by_name[model_field_name]

    def is_hidden(self, model_field_name):
        return (
            model_field_name in self.hidden
            or self.permission_of(model_field_name)
            <= field_permissions.Permissions.HIDDEN
        )

    def is_readonly(self, model_field_name):
        return self.permission_of(model_field_name) <= field_permissions.Permissions.RO

    def __hash__(self):
        return hash(self._key)

    def __eq__(self, other):
        return isinstance(other, Visibility) and self._key == other._key


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
        # by visibility, least recently asked for first. See
        # `request_cache`.
        self._visibility_caches = collections.OrderedDict()
        # The model's field names and their API spelling, worked out once.
        self._declared = None
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
        return self.get_fields_by_visibility(self.resolve_visibility(req))

    def get_fields_by_visibility(self, visibility):
        """The fields a request resolving to `visibility` is answered from.

        Which fields there are is what the hidden-fields map and the
        caller's projection settled; what may be done with each of them
        is the permissions', and that is asked further down, where a
        field hidden by permission still has to be told apart from one
        the model does not have.
        """

        def is_public_field(model_field_name):
            return (
                not model_field_name.startswith("_")
                and model_field_name not in visibility.hidden
                and self.get_resource_field_name(model_field_name) in visibility.shown
            )

        return self.get_fields(override_is_public_field_func=is_public_field)

    # How many visibilities to remember. A resolution carries whatever
    # the caller's roles, permissions and projection made of the fields,
    # and there is no reason to hold every combination that ever arrived;
    # past this, the one longest unasked for is dropped.
    _MAX_VISIBILITY_CACHES = 64

    def resolve_visibility(self, req):
        """Everything this request is told about this resource's fields.

        The permission each field carries, which of them are hidden, and
        which the caller asked to be shown -- asked of each of the three
        once, for every field at once.

        This is both the answer and what the answer is kept by: two
        requests resolving to the same value are told the same about
        every field, because the value *is* what they were told. Nothing
        here is a summary that could describe the wrong thing.
        """
        kept = getattr(req.api_context, "resolved_visibilities", None)
        if isinstance(kept, dict):
            visibility = kept.get(self)
            if visibility is not None:
                return visibility
            visibility = self._resolve_visibility(req)
            kept[self] = visibility
            return visibility
        return self._resolve_visibility(req)

    def _resolve_visibility(self, req):
        names, api_names = self._declared_names()
        return Visibility(
            names=names,
            permissions=self._fields_permissions.resolve(req, names),
            hidden=self._hidden_fields.hidden_for(req, names),
            shown=req.api_context.shown_fields(api_names),
        )

    def _declared_names(self):
        """Every field this resource has, and how the API spells each.

        Asked of `get_fields` rather than of the model, because a
        resource may have fields the model does not declare -- a custom
        property is one. Neither answer turns on a request, so both are
        worked out once.
        """
        if self._declared is None:
            names = tuple(
                name for name, _ in self.get_fields(lambda model_field_name: True)
            )
            self._declared = (
                names,
                tuple(self.get_resource_field_name(name) for name in names),
            )
        return self._declared

    def request_cache(self, visibility):
        """Somewhere to keep what any request told the same thing sees.

        Resolving a resource's fields is a property object and three
        predicates per field, and the answer is the same for every
        request handed the same visibility. A caller may keep whatever it
        derives from those fields here too, as long as it does not change
        it afterwards.

        Only so many are held at once, and the one longest unasked for
        goes when the next arrives. A caller decides part of what it is
        told -- `fields` is its own to pick -- so a stream of visibilities
        nobody asks for twice has to cost the ones that are asked for
        again nothing more than being resolved afresh.
        """
        cache = self._visibility_caches.get(visibility)
        if cache is not None:
            self._visibility_caches.move_to_end(visibility)
            return cache
        cache = {}
        self._visibility_caches[visibility] = cache
        if len(self._visibility_caches) > self._MAX_VISIBILITY_CACHES:
            self._visibility_caches.popitem(last=False)
        return cache

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

    def is_public_field_by_method(self, method, model_field_name):
        return not (
            model_field_name.startswith("_")
            or model_field_name
            in self._hidden_fields.hidden_for_method(method, (model_field_name,))
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
