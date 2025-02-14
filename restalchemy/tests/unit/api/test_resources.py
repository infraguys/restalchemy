#    Copyright 2021 Eugene Frolov.
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
from restalchemy.api import resources
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types


class FakeModel(models.CustomPropertiesMixin, models.ModelWithUUID):
    _private_field = properties.property(types.Integer())
    standard_field1 = properties.property(types.Integer())
    standard_field2 = properties.property(types.Integer())
    standard_field3 = properties.property(types.Integer())
    standard_field4 = properties.property(types.Integer())
    standard_field5 = properties.property(types.Integer())


class FakeMemberContext(object):
    roles = ["member", "some-role"]


class FakeAdminContext(object):
    roles = ["member", "admin"]


class FakeEmptyContext(object):
    roles = []


class FakeIncorrectFieldsRoleContext(object):
    roles = ["incorrect_fields"]


class FakeEmptyFieldsRoleContext(object):
    roles = ["empty_fields"]


# NOTE(efrolov): Interface tests
class ResourceByRAModelHiddenFieldsInterfacesTestCase(unittest.TestCase):

    def tearDown(self):
        super(ResourceByRAModelHiddenFieldsInterfacesTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}

    def test_hide_some_fields(self):
        resource = resources.ResourceByRAModel(
            FakeModel,
            hidden_fields=[
                "standard_field1",
                "standard_field4",
                "standard_field5",
            ],
        )

        result = [
            name for name, prop in resource.get_fields() if prop.is_public()
        ]

        self.assertEqual(
            ["standard_field2", "standard_field3", "uuid"], sorted(result)
        )

    def test_hide_renamed_fields(self):
        resource = resources.ResourceByRAModel(
            FakeModel,
            hidden_fields=[
                "standard_field1",
                "standard_field4",
                "standard_field5",
            ],
            name_map={"standard_field1": "new_standard_field1"},
        )

        result = [
            name for name, prop in resource.get_fields() if prop.is_public()
        ]

        self.assertEqual(
            ["standard_field2", "standard_field3", "uuid"], sorted(result)
        )


class ResourceByRAModelHiddenFieldsNewInterfacesTestCase(unittest.TestCase):

    def setUp(self):
        super(ResourceByRAModelHiddenFieldsNewInterfacesTestCase, self).setUp()
        self.target = resources.ResourceByRAModel(
            FakeModel,
            hidden_fields=resources.HiddenFieldMap(
                filter=["standard_field1", "standard_field2", "uuid"],
                get=["standard_field1", "standard_field3", "uuid"],
                create=["standard_field1", "standard_field4", "uuid"],
                update=["standard_field1", "standard_field5", "uuid"],
                delete=["standard_field2", "standard_field3", "uuid"],
                action_get=["standard_field2", "standard_field4", "uuid"],
                action_post=["standard_field2", "standard_field5", "uuid"],
                action_put=["standard_field3", "standard_field4", "uuid"],
            ),
        )
        self._request = webob.Request.blank("/some-uri")
        self._request.api_context = contexts.RequestContext(self._request)

    def tearDown(self):
        super(
            ResourceByRAModelHiddenFieldsNewInterfacesTestCase, self
        ).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._request

    def _test_hide_some_fields_for_request(self, req, fields):

        result = [
            name
            for name, prop in self.target.get_fields_by_request(req)
            if prop.is_public()
        ]

        self.assertEqual(sorted(fields), sorted(result))

    def test_hide_some_fields_for_filter_method(self):
        self._request.api_context.set_active_method(constants.FILTER)

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=["standard_field3", "standard_field4", "standard_field5"],
        )

    def test_hide_some_fields_for_get_method(self):
        self._request.api_context.set_active_method(constants.GET)

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=["standard_field2", "standard_field4", "standard_field5"],
        )

    def test_hide_some_fields_for_create_method(self):
        self._request.api_context.set_active_method(constants.CREATE)

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=["standard_field2", "standard_field3", "standard_field5"],
        )

    def test_hide_some_fields_for_update_method(self):
        self._request.api_context.set_active_method(constants.UPDATE)

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=["standard_field2", "standard_field3", "standard_field4"],
        )

    def test_hide_some_fields_for_delete_method(self):
        self._request.api_context.set_active_method(constants.DELETE)

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=["standard_field1", "standard_field4", "standard_field5"],
        )

    def test_hide_some_fields_for_action_get_method(self):
        self._request.api_context.set_active_method(constants.ACTION_GET)

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=["standard_field1", "standard_field3", "standard_field5"],
        )

    def test_hide_some_fields_for_action_post_method(self):
        self._request.api_context.set_active_method(constants.ACTION_POST)

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=["standard_field1", "standard_field3", "standard_field4"],
        )

    def test_hide_some_fields_for_action_put_method(self):
        self._request.api_context.set_active_method(constants.ACTION_PUT)

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=["standard_field1", "standard_field2", "standard_field5"],
        )

    def test_get_fields_with_custom_is_public_field_func(self):
        def always_true(name):
            return True

        result = self.target.get_fields(
            override_is_public_field_func=always_true,
        )

        for name, prop in result:
            self.assertTrue(prop.is_public())


class ResourceByRAModelWithCustomPropsHiddenFieldsNewInterfacesTestCase(
    ResourceByRAModelHiddenFieldsNewInterfacesTestCase
):
    def setUp(self):
        self.target = resources.ResourceByModelWithCustomProps(
            FakeModel,
            hidden_fields=resources.HiddenFieldMap(
                filter=["standard_field1", "standard_field2", "uuid"],
                get=["standard_field1", "standard_field3", "uuid"],
                create=["standard_field1", "standard_field4", "uuid"],
                update=["standard_field1", "standard_field5", "uuid"],
                delete=["standard_field2", "standard_field3", "uuid"],
                action_get=["standard_field2", "standard_field4", "uuid"],
                action_post=["standard_field2", "standard_field5", "uuid"],
                action_put=["standard_field3", "standard_field4", "uuid"],
            ),
        )
        self._request = webob.Request.blank("/some-uri")
        self._request.api_context = contexts.RequestContext(self._request)

    def tearDown(self):
        resources.ResourceMap.model_type_to_resource = {}
        del self._request


class ResourceByRAModelRoleBasedHiddenFieldsTestCase(unittest.TestCase):

    def setUp(self):
        super(ResourceByRAModelRoleBasedHiddenFieldsTestCase, self).setUp()
        self.target = resources.ResourceByRAModel(
            FakeModel,
            hidden_fields=resources.RoleBasedHiddenFieldContainer(
                default=resources.HiddenFieldMap(
                    get=[
                        "standard_field1",
                        "standard_field2",
                        "standard_field3",
                        "standard_field4",
                        "standard_field5",
                        "uuid",
                    ],
                ),
                member=resources.HiddenFieldMap(
                    get=["standard_field1", "standard_field3", "uuid"],
                ),
                admin=resources.HiddenFieldMap(
                    get=["standard_field1", "uuid"],
                ),
                incorrect_fields=resources.HiddenFieldMap(
                    get=["fake1", "fake2"],
                ),
                empty_fields=resources.HiddenFieldMap(get=[]),
            ),
        )
        self._request = webob.Request.blank("/some-uri")
        self._request.api_context = contexts.RequestContext(self._request)

    def tearDown(self):
        super(ResourceByRAModelRoleBasedHiddenFieldsTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._request

    def _test_hide_some_fields_for_request(self, req, fields):

        result = [
            name
            for name, prop in self.target.get_fields_by_request(req)
            if prop.is_public()
        ]

        self.assertEqual(sorted(fields), sorted(result))

    def test_hide_some_fields_for_admin_context_method(self):
        self._request.api_context.set_active_method(constants.GET)
        admin_context = FakeAdminContext()
        self._request.context = admin_context

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=[
                "standard_field2",
                "standard_field3",
                "standard_field4",
                "standard_field5",
            ],
        )

    def test_hide_some_fields_for_member_context_method(self):
        self._request.api_context.set_active_method(constants.GET)
        member_context = FakeMemberContext()
        self._request.context = member_context

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=["standard_field2", "standard_field4", "standard_field5"],
        )

    def test_hide_some_fields_for_empty_role_context_method(self):
        self._request.api_context.set_active_method(constants.GET)
        member_context = FakeEmptyContext()
        self._request.context = member_context

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=[],
        )

    def test_hide_some_fields_without_context(self):
        self._request.api_context.set_active_method(constants.GET)

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=[],
        )

    def test_no_hide_incorrect_fields(self):
        self._request.api_context.set_active_method(constants.GET)
        context = FakeIncorrectFieldsRoleContext()
        self._request.context = context

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=[
                "standard_field1",
                "standard_field2",
                "standard_field3",
                "standard_field4",
                "standard_field5",
                "uuid",
            ],
        )

    def test_no_hide_all_fields(self):
        self._request.api_context.set_active_method(constants.GET)
        context = FakeEmptyFieldsRoleContext()
        self._request.context = context

        self._test_hide_some_fields_for_request(
            req=self._request,
            fields=[
                "standard_field1",
                "standard_field2",
                "standard_field3",
                "standard_field4",
                "standard_field5",
                "uuid",
            ],
        )
