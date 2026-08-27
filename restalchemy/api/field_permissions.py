# Copyright 2022 George Melikov
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

from restalchemy.api import constants
from restalchemy.common import utils


class Permissions(object):
    __slots__ = ()
    HIDDEN = 1
    RO = 2
    RW = 3

    ALL_PERMISSIONS = (
        HIDDEN,
        RO,
        RW,
    )


class BasePermissions(object):
    """What a request may do with each of a resource's fields.

    `resolve` is the one method a container of your own writes. It is
    asked once per request for every field at once, rather than once per
    field, so whatever the answers turn on -- the RA method, a role, a
    rule an enforcer answers -- is read once.

    Asking for all of them together is also what lets a resource resolve
    its fields once and hand the answer to every request told the same:
    the mapping `resolve` returns is what the answer is kept by. That is
    not a promise a container makes and has to keep in step with its own
    logic -- there is nothing to keep in step, because the mapping is the
    logic's own output.
    """

    _REMOVED = {
        "meets_field_permission": "resolve",
        "visibility_key": "resolve",
    }

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        utils.refuse_removed_overrides(cls, BasePermissions._REMOVED)

    def __init__(self, permission=Permissions.RW):
        self._permission = permission

    def resolve(self, req, field_names):
        """What this request may do with each of `field_names`.

        A mapping of field name to `Permissions`, covering every name
        given.
        """
        raise NotImplementedError()

    def permission_of(self, model_field_name, req):
        """What this request may do with one field.

        Spelled out of `resolve`, so a container answers one way and one
        way only. Reading a single field is the cold path -- a resource
        being packed asks for all of them at once.
        """
        return self.resolve(req, (model_field_name,))[model_field_name]

    def is_readonly(self, model_field_name, req):
        return self.permission_of(model_field_name, req) <= Permissions.RO

    def is_hidden(self, model_field_name, req):
        return self.permission_of(model_field_name, req) <= Permissions.HIDDEN


class UniversalPermissions(BasePermissions):
    def __init__(self, permission=Permissions.RW):
        """General fields permissions container for resource

        This class describes a dict of fields with one permission
        for all fields.

        Example of usage:

        ```
        UniversalPermissions(
                permission=Permissions.RW
            )
        ```
        This code set to all fields READWRITE permissions.
        """
        super(UniversalPermissions, self).__init__(permission)

    def resolve(self, req, field_names):
        # One permission for every field of every request.
        permission = self._permission
        return {name: permission for name in field_names}


class FieldsPermissions(BasePermissions):
    def __init__(self, fields, default=Permissions.RW):
        """Field permissions container for resource

        This class describes a dict of fields with permissions for
        various RestAlchemy API methods. All permissions are decrared
        in class Permissions. The methods supported by RA are declared
        in the `restalchemy.api.constants` module.
        For example, the code below shows how to set:
        > HIDDEN permissions to the `one_field` for the FILTER method
          and RW for all others RA methods, except FILTER;
        > RO permissions for the `two_field` for all RA methods;
        > HIDDEN permissions for the `three_field` for GET method and
          RO permissions for all others RA methods, except GET.

        ```
        FieldsPermissions(
            default=Permissions.RW,
            fields={
                'one_field':{
                    constants.FILTER: Permissions.HIDDEN},
                'two_field': {
                    constants.ALL: Permissions.RO},
                'three_field': {
                    constants.GET: Permissions.HIDDEN,
                    constants.ALL: Permissions.RO},
            }
        )
        ```

        Pay attention: if you wouldn't set permission for field and RA method
        by default it would be RW (READWRITE) permission.

        :param fields: dict of field model name and permissions
        :param default: default permission for non-described fields
        """
        for field, method_permission in fields.items():
            for method, permission in method_permission.items():
                if method.upper() not in constants.ALL_RA_METHODS:
                    raise ValueError(
                        "Unknown RA method %r for field %r" % (method, field)
                    )
                if permission not in Permissions.ALL_PERMISSIONS:
                    raise ValueError(
                        "Unknown permission %r for field %r" % (permission, field)
                    )
        super(FieldsPermissions, self).__init__(permission=default)
        self.fields = fields

    def _permission_for(self, model_field_name, method):
        field_permission = self.fields.get(model_field_name)
        if not field_permission:
            return self._permission
        permission = field_permission.get(method)
        if permission is None:
            permission = field_permission.get(constants.ALL)
        # NOTE(g.melikov): By DEFAULT permission is Permissions.RW
        return self._permission if permission is None else permission

    def resolve(self, req, field_names):
        # The method is what every field's answer turns on, so it is read
        # once rather than once per field.
        method = req.api_context.get_active_method()
        return {name: self._permission_for(name, method) for name in field_names}


class FieldsPermissionsByRole(BasePermissions):
    def __init__(self, default, **kwargs):
        """Role based fields permissions

        This class describes a dict of roles with FieldsPermissions.
        Note: default will be used for all roles which are not specified.

        Example of usage:

        ```
        FieldsPermissionsByRole(
        some_role=FieldsPermissions(
            default=Permissions.RW,
            fields={
                'status':
                {
                    constants.ALL: Permissions.RO
                }
            }
        ),
        admin=FieldsPermissions(
            default=Permissions.RW,
            fields={
                'namespace':
                {
                    constants.ALL: Permissions.HIDDEN
                }
            }
        ),
        default=UniversalPermissions(
            permission=Permissions.RW
            )
        )
        ```

        :param default: default permission for non-described roles
        :param kwargs: dict of roles with FieldsPermissions.
        """
        for role, permissions in dict(kwargs, default=default).items():
            if not isinstance(permissions, BasePermissions):
                raise TypeError(
                    "Permissions for %s must be inherited BasePermissions class" % role
                )
        self.default = default
        self.role_fields = kwargs

        super(FieldsPermissionsByRole, self).__init__()

    @staticmethod
    def _get_roles(req):
        return (
            req.context.roles
            if hasattr(req, "context") and hasattr(req.context, "roles")
            else []
        )

    def _deciding(self, req):
        """The container that answers for this request.

        The first role the request carries that this was told about, so
        the order they arrive in is part of the answer -- and it needs no
        saying anywhere else, because what comes back is the answer.
        """
        for role in self._get_roles(req):
            if role in self.role_fields:
                return self.role_fields[role]
        return self.default

    def resolve(self, req, field_names):
        return self._deciding(req).resolve(req, field_names)
