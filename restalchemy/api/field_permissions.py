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
from restalchemy.api import contexts


def active_method(req):
    """The RA method this request is being answered as, or `None`."""
    try:
        return req.api_context.get_active_method()
    except (AttributeError, contexts.CanNotGetActiveMethod):
        return None


class Permissions:
    __slots__ = ()
    HIDDEN = 1
    RO = READONLY = 2
    RW = READWRITE = 3

    ALL_PERMISSIONS = (
        HIDDEN,
        RO,
        RW,
    )


class BasePermissions:
    def __init__(self, permission=Permissions.RW):
        self._permission = permission

    def meets_field_permission(self, model_field_name, req, current_permission):
        raise NotImplementedError()

    def visibility_key(self, req):
        """What this request makes the answers depend on.

        A hashable value that stands for every answer this object will
        give about this request: two requests with equal keys are told the
        same about every field, so a resource may resolve its fields once
        and hand the same answer to both.

        `None` means the answers cannot be summarised, and then nothing is
        reused between requests. That is the default, and what a class
        deciding permissions its own way is left with -- see
        `visibility_key_of`, which does not take a subclass's word for it.
        """
        return None

    def is_readonly(self, model_field_name, req):
        return self.meets_field_permission(
            model_field_name=model_field_name,
            req=req,
            current_permission=Permissions.RO,
        )

    def is_hidden(self, model_field_name, req):
        return self.meets_field_permission(
            model_field_name=model_field_name,
            req=req,
            current_permission=Permissions.HIDDEN,
        )


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
        super().__init__(permission)

    def meets_field_permission(self, model_field_name, req, current_permission):
        return self._permission <= current_permission

    def visibility_key(self, req):
        # One permission for every field of every request.
        return ()


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
        for method_permission in fields.values():
            for method, permission in method_permission.items():
                assert (
                    method.upper() in constants.ALL_RA_METHODS
                    and permission in Permissions.ALL_PERMISSIONS
                )
        super().__init__(permission=default)
        self.fields = fields

    def meets_field_permission(self, model_field_name, req, current_permission):

        method = req.api_context.get_active_method()
        field_permission = self.fields.get(model_field_name, {})

        # NOTE(g.melikov): By DEFAULT permission is Permissions.RW
        permission = (
            field_permission.get(method)
            or field_permission.get(constants.ALL)
            or self._permission
        )

        return permission <= current_permission

    def visibility_key(self, req):
        method = active_method(req)
        return None if method is None else (method,)


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
        for role, permissions in kwargs.items():
            if not isinstance(permissions, BasePermissions):
                raise NotImplementedError(
                    f"Permissions for {role} must be inherited BasePermissions class"
                )
        self.default = default
        self.role_fields = kwargs

        super().__init__()

    @staticmethod
    def _get_roles(req):
        return (
            req.context.roles
            if hasattr(req, "context") and hasattr(req.context, "roles")
            else []
        )

    def meets_field_permission(self, model_field_name, req, current_permission):

        for current_role in self._get_roles(req):
            if current_role in self.role_fields:
                fields = self.role_fields[current_role]
                return fields.meets_field_permission(
                    model_field_name, req, current_permission
                )

        return self.default.meets_field_permission(
            model_field_name, req, current_permission
        )

    def visibility_key(self, req):
        # Which role answers depends on the roles the request carries;
        # what that role then answers is its own container's business, so
        # every one of them has to be able to say.
        keys = [visibility_key_of(self.default, req)]
        for role, permissions in self.role_fields.items():
            keys.append(role)
            keys.append(visibility_key_of(permissions, req))
        if any(key is None for key in keys):
            return None
        return (self._deciding_role(req), tuple(keys))

    def _deciding_role(self, req):
        """The role that answers for this request, or `None` for the default.

        `meets_field_permission` takes the first role the request carries
        that this was told about, so the order those roles arrive in is
        part of the answer: a request carrying `["hide", "show"]` and one
        carrying `["show", "hide"]` are not told the same thing. What the
        answer turns on is which of them wins, so that is what the key
        says -- not the set of them, which loses the order, and not the
        whole list, which says more than the answer depends on.
        """
        for role in self._get_roles(req):
            if role in self.role_fields:
                return role
        return None


# The implementations shipped here, which `visibility_key` describes. A
# class deciding permissions its own way inherits a key that does not
# describe it, so the key is only trusted from these.
_SHIPPED_PERMISSIONS = frozenset(
    (
        UniversalPermissions.meets_field_permission,
        FieldsPermissions.meets_field_permission,
        FieldsPermissionsByRole.meets_field_permission,
    )
)


def visibility_key_of(permissions, req):
    """`permissions`' key for this request, or `None` to reuse nothing."""
    if getattr(type(permissions), "meets_field_permission", None) not in (
        _SHIPPED_PERMISSIONS
    ):
        return None
    return permissions.visibility_key(req)
