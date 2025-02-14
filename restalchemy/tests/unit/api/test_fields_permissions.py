# Copyright 2022 George Melikov
#
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

import unittest
import webob

from restalchemy.api import constants
from restalchemy.api import contexts
from restalchemy.api import field_permissions as fp
from restalchemy.api import resources
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types


class FakeModel(models.CustomPropertiesMixin, models.ModelWithUUID):
    _private_field = properties.property(types.Integer())
    standard_field1 = properties.property(types.Integer(), required=True)
    standard_field2 = properties.property(types.Integer())
    standard_field3 = properties.property(types.Integer())
    standard_field4 = properties.property(types.Integer(), required=True)
    standard_field5 = properties.property(types.Integer())


class FakeMemberContext(object):
    roles = ["_member_"]


class FakeAdminContext(object):
    roles = ["admin"]


class FakeEmptyContext(object):
    roles = []


class ResourceByRAModelFieldsPermissions(unittest.TestCase):

    def setUp(self):
        super(ResourceByRAModelFieldsPermissions, self).setUp()

        self.resource = resources.ResourceByRAModel(
            FakeModel,
            fields_permissions=fp.FieldsPermissionsByRole(
                default=fp.UniversalPermissions(
                    permission=fp.Permissions.HIDDEN
                ),
                admin=fp.FieldsPermissions(
                    {
                        "standard_field1": {
                            constants.ALL: fp.Permissions.HIDDEN
                        },
                        "standard_field2": {
                            constants.CREATE: (fp.Permissions.HIDDEN)
                        },
                        "standard_field3": {
                            constants.GET: fp.Permissions.HIDDEN
                        },
                        "standard_field5": {
                            constants.FILTER: (fp.Permissions.HIDDEN),
                            constants.DELETE: (fp.Permissions.HIDDEN),
                        },
                    }
                ),
                _member_=fp.FieldsPermissions(
                    {
                        "standard_field1": {
                            constants.CREATE: (fp.Permissions.HIDDEN),
                            constants.ALL: fp.Permissions.RO,
                        },
                        "standard_field2": {
                            constants.GET: fp.Permissions.RO,
                            constants.FILTER: fp.Permissions.RO,
                            constants.ALL: fp.Permissions.HIDDEN,
                        },
                        "standard_field4": {
                            constants.GET: fp.Permissions.RO,
                            constants.UPDATE: fp.Permissions.RO,
                            constants.ALL: fp.Permissions.HIDDEN,
                        },
                        "standard_field5": {
                            constants.UPDATE: (fp.Permissions.HIDDEN),
                            constants.DELETE: (fp.Permissions.HIDDEN),
                        },
                    }
                ),
            ),
        )

        self._request = webob.Request.blank("/some-uri")
        self._request.api_context = contexts.RequestContext(self._request)

    def tearDown(self):
        super(ResourceByRAModelFieldsPermissions, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._request

    def _test_fields_is_shown(self, expected_fields):
        result = [
            name
            for name, prop in self.resource.get_fields_by_request(
                self._request
            )
            if prop.is_public()
            and not self.resource._fields_permissions.is_hidden(
                name, self._request
            )
        ]

        self.assertEqual(sorted(expected_fields), sorted(result))

    def _test_fields_is_hidden(self, expected_fields):
        result = [
            name
            for name, prop in self.resource.get_fields_by_request(
                self._request
            )
            if prop.is_public()
            and self.resource._fields_permissions.is_hidden(
                name, self._request
            )
        ]

        self.assertEqual(sorted(expected_fields), sorted(result))

    def _test_fields_is_readonly(self, expected_fields):
        result = [
            name
            for name, prop in self.resource.get_fields_by_request(
                self._request
            )
            if prop.is_public()
            and self.resource._fields_permissions.is_readonly(
                name, self._request
            )
        ]

        self.assertEqual(sorted(expected_fields), sorted(result))

    def _test_default(self):
        resource = resources.ResourceByRAModel(
            FakeModel,
            fields_permissions=fp.FieldsPermissionsByRole(
                default=fp.UniversalPermissions(
                    permission=fp.Permissions.HIDDEN
                ),
                admin=fp.FieldsPermissions(
                    {
                        "standard_field1": {
                            constants.ALL: fp.Permissions.HIDDEN
                        },
                    },
                ),
            ),
        )

        self.assertFalse(
            resource._fields_permissions.is_readonly(
                "standard_field2", self._request
            )
        )

    def _test_default_custom_value(self):
        resource = resources.ResourceByRAModel(
            FakeModel,
            fields_permissions=fp.FieldsPermissionsByRole(
                default=fp.UniversalPermissions(
                    permission=fp.Permissions.HIDDEN
                ),
                admin=fp.FieldsPermissions(
                    {
                        "standard_field1": {
                            constants.ALL: fp.Permissions.HIDDEN
                        },
                    },
                    default=fp.Permissions.RO,
                ),
            ),
        )

        self.assertTrue(
            resource._fields_permissions.is_readonly(
                "standard_field2", self._request
            )
        )


class ResourceByRAModelFieldsPermissionsRoleAdmin(
    ResourceByRAModelFieldsPermissions
):

    def setUp(self):
        super(ResourceByRAModelFieldsPermissionsRoleAdmin, self).setUp()
        admin_context = FakeAdminContext()
        self._request.context = admin_context

    def test_fields_permission_role_admin_method_get(self):
        self._request.api_context.set_active_method(constants.GET)

        expected_shown_fields = [
            "standard_field2",
            "standard_field4",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field1", "standard_field3"]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_hidden_fields)

    def test_fields_permission_role_admin_method_filter(self):
        self._request.api_context.set_active_method(constants.FILTER)

        expected_shown_fields = [
            "standard_field2",
            "standard_field3",
            "standard_field4",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field1", "standard_field5"]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_hidden_fields)

    def test_fields_permission_role_admin_method_create(self):
        self._request.api_context.set_active_method(constants.CREATE)

        expected_shown_fields = [
            "standard_field3",
            "standard_field4",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = [
            "standard_field1",
            "standard_field2",
        ]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_hidden_fields)

    def test_fields_permission_role_admin_method_update(self):
        self._request.api_context.set_active_method(constants.UPDATE)

        expected_shown_fields = [
            "standard_field2",
            "standard_field3",
            "standard_field4",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field1"]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_hidden_fields)

    def test_fields_permission_role_admin_method_delete(self):
        self._request.api_context.set_active_method(constants.DELETE)

        expected_shown_fields = [
            "standard_field2",
            "standard_field3",
            "standard_field4",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field1", "standard_field5"]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_hidden_fields)

    def test_fields_permission_role_admin_action_get(self):
        self._request.api_context.set_active_method(constants.ACTION_GET)

        expected_shown_fields = [
            "standard_field2",
            "standard_field3",
            "standard_field4",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field1"]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_hidden_fields)

    def test_fields_permission_role_admin_action_post(self):
        self._request.api_context.set_active_method(constants.ACTION_POST)

        expected_shown_fields = [
            "standard_field2",
            "standard_field3",
            "standard_field4",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field1"]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_hidden_fields)

    def test_fields_permission_role_admin_action_put(self):
        self._request.api_context.set_active_method(constants.ACTION_PUT)

        expected_shown_fields = [
            "standard_field2",
            "standard_field3",
            "standard_field4",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field1"]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_hidden_fields)


class ResourceByRAModelFieldsPermissionsNoRole(
    ResourceByRAModelFieldsPermissions
):

    def setUp(self):
        super(ResourceByRAModelFieldsPermissionsNoRole, self).setUp()
        empty_context = FakeEmptyContext()
        self._request.context = empty_context

        self.expected_shown_fields = []
        self.expected_hidden_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field3",
            "standard_field4",
            "standard_field5",
            "uuid",
        ]

    def test_fields_permission_no_role_method_get(self):
        self._request.api_context.set_active_method(constants.GET)

        self._test_fields_is_shown(self.expected_shown_fields)
        self._test_fields_is_hidden(self.expected_hidden_fields)
        self._test_fields_is_readonly(self.expected_hidden_fields)

    def test_fields_permission_no_role_method_filter(self):
        self._request.api_context.set_active_method(constants.FILTER)

        self._test_fields_is_shown(self.expected_shown_fields)
        self._test_fields_is_hidden(self.expected_hidden_fields)
        self._test_fields_is_readonly(self.expected_hidden_fields)

    def test_fields_permission_no_role_method_create(self):
        self._request.api_context.set_active_method(constants.CREATE)

        self._test_fields_is_shown(self.expected_shown_fields)
        self._test_fields_is_hidden(self.expected_hidden_fields)
        self._test_fields_is_readonly(self.expected_hidden_fields)

    def test_fields_permission_no_role_method_update(self):
        self._request.api_context.set_active_method(constants.UPDATE)

        self._test_fields_is_shown(self.expected_shown_fields)
        self._test_fields_is_hidden(self.expected_hidden_fields)
        self._test_fields_is_readonly(self.expected_hidden_fields)

    def test_fields_permission_no_role_method_delete(self):
        self._request.api_context.set_active_method(constants.DELETE)

        self._test_fields_is_shown(self.expected_shown_fields)
        self._test_fields_is_hidden(self.expected_hidden_fields)
        self._test_fields_is_readonly(self.expected_hidden_fields)

    def test_fields_permission_no_role_action_get(self):
        self._request.api_context.set_active_method(constants.ACTION_GET)

        self._test_fields_is_shown(self.expected_shown_fields)
        self._test_fields_is_hidden(self.expected_hidden_fields)
        self._test_fields_is_readonly(self.expected_hidden_fields)

    def test_fields_permission_no_role_action_post(self):
        self._request.api_context.set_active_method(constants.ACTION_POST)

        self._test_fields_is_shown(self.expected_shown_fields)
        self._test_fields_is_hidden(self.expected_hidden_fields)
        self._test_fields_is_readonly(self.expected_hidden_fields)

    def test_fields_permission_no_role_action_put(self):
        self._request.api_context.set_active_method(constants.ACTION_PUT)

        self._test_fields_is_shown(self.expected_shown_fields)
        self._test_fields_is_hidden(self.expected_hidden_fields)
        self._test_fields_is_readonly(self.expected_hidden_fields)


class ResourceByRAModelFieldsPermissionsRoleMember(
    ResourceByRAModelFieldsPermissions
):

    def setUp(self):
        super(ResourceByRAModelFieldsPermissionsRoleMember, self).setUp()
        member_context = FakeMemberContext()
        self._request.context = member_context

    def test_fields_permission_role_member_method_get(self):
        self._request.api_context.set_active_method(constants.GET)
        expected_shown_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field3",
            "standard_field4",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = []
        expected_ro_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field4",
        ]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_ro_fields)

    def test_fields_permission_role_member_method_update(self):
        self._request.api_context.set_active_method(constants.UPDATE)
        expected_shown_fields = [
            "standard_field1",
            "standard_field3",
            "standard_field4",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field2", "standard_field5"]
        expected_ro_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field4",
            "standard_field5",
        ]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_ro_fields)

    def test_fields_permission_role_member_method_create(self):
        self._request.api_context.set_active_method(constants.CREATE)
        expected_shown_fields = ["standard_field3", "standard_field5", "uuid"]
        expected_hidden_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field4",
        ]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_hidden_fields)

    def test_fields_permission_role_member_method_delete(self):
        self._request.api_context.set_active_method(constants.DELETE)
        expected_shown_fields = ["standard_field1", "standard_field3", "uuid"]
        expected_hidden_fields = [
            "standard_field2",
            "standard_field4",
            "standard_field5",
        ]
        expected_ro_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field4",
            "standard_field5",
        ]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_ro_fields)

    def test_fields_permission_role_member_method_filter(self):
        self._request.api_context.set_active_method(constants.FILTER)
        expected_shown_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field3",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field4"]
        expected_ro_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field4",
        ]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_ro_fields)

    def test_fields_permission_role_member_action_get(self):
        self._request.api_context.set_active_method(constants.ACTION_GET)
        expected_shown_fields = [
            "standard_field1",
            "standard_field3",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field2", "standard_field4"]
        expected_ro_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field4",
        ]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_ro_fields)

    def test_fields_permission_role_member_action_post(self):
        self._request.api_context.set_active_method(constants.ACTION_POST)
        expected_shown_fields = [
            "standard_field1",
            "standard_field3",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field2", "standard_field4"]
        expected_ro_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field4",
        ]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_ro_fields)

    def test_fields_permission_role_member_action_put(self):
        self._request.api_context.set_active_method(constants.ACTION_PUT)
        expected_shown_fields = [
            "standard_field1",
            "standard_field3",
            "standard_field5",
            "uuid",
        ]
        expected_hidden_fields = ["standard_field2", "standard_field4"]
        expected_ro_fields = [
            "standard_field1",
            "standard_field2",
            "standard_field4",
        ]

        self._test_fields_is_shown(expected_shown_fields)
        self._test_fields_is_hidden(expected_hidden_fields)
        self._test_fields_is_readonly(expected_ro_fields)
