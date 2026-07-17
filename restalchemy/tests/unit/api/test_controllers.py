# Copyright 2022 Eugene Frolov <eugene@frolov.net.ru>
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

import tempfile
import unittest

import mock

from restalchemy.api import controllers
from restalchemy.api import packers
from restalchemy.dm import filters as dm_filters

FAKE_LOCATION_PATH = "fake location path"


class TestLocationHeaderLogic(unittest.TestCase):
    def setUp(self):
        super(TestLocationHeaderLogic, self).setUp()
        self._controller = controllers.Controller(None)

    def test_location_for_result(self):
        result = self._controller.process_result("")

        self.assertEqual(result.headers.get("Location", None), None)

    @mock.patch("restalchemy.api.resources.ResourceMap")
    def test_location_for_result_and_add_location(self, resource_map):
        resource_map.get_location.return_value = FAKE_LOCATION_PATH

        result = self._controller.process_result("", add_location=True)

        self.assertEqual(result.headers.get("Location", None), FAKE_LOCATION_PATH)

    def test_location_for_result_and_location_and_tuple_location_false(self):
        result = self._controller.process_result(
            ("", 200, None, False), add_location=True
        )

        self.assertEqual(result.headers.get("Location", None), None)

    @mock.patch("restalchemy.api.resources.ResourceMap")
    def test_location_for_result_and_location_and_tuple_location_true(
        self, resource_map
    ):
        resource_map.get_location.return_value = FAKE_LOCATION_PATH

        result = self._controller.process_result(
            ("", 200, None, True), add_location=True
        )

        self.assertEqual(result.headers.get("Location", None), FAKE_LOCATION_PATH)

    def test_location_for_result_and_tuple_location_false(self):
        result = self._controller.process_result(("", 200, None, False))

        self.assertEqual(result.headers.get("Location", None), None)

    @mock.patch("restalchemy.api.resources.ResourceMap")
    def test_location_for_result_and_tuple_location_true(self, resource_map):
        resource_map.get_location.return_value = FAKE_LOCATION_PATH

        result = self._controller.process_result(("", 200, None, True))

        self.assertEqual(result.headers.get("Location", None), FAKE_LOCATION_PATH)


class BytePacker(packers.JSONPacker):
    def pack(self, obj):
        if isinstance(obj, bytes):
            return obj
        return super().pack(obj)


class ByteController(controllers.Controller):
    __packer__ = BytePacker


class TestRawResponses(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._controller = ByteController(None)

    def test_binary_result(self):
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": 'attachment; filename="test.txt"',
        }

        result = self._controller.process_result((b"1", 200, headers))

        self.assertEqual(result.body, b"1")
        self.assertEqual(result.status, "200 OK")
        self.assertEqual(result.headers["Content-Type"], headers["Content-Type"])
        self.assertEqual(
            result.headers["Content-Disposition"],
            headers["Content-Disposition"],
        )


class TestOpenApiSpecificationCache(unittest.TestCase):
    def setUp(self):
        super(TestOpenApiSpecificationCache, self).setUp()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._engine = mock.Mock()
        self._engine.build_openapi_specification.return_value = {
            "openapi": "3.0.3",
        }
        request = mock.Mock()
        request.application.openapi_engine = self._engine
        self._controller = controllers.OpenApiSpecificationController(request)

    @mock.patch("restalchemy.api.controllers.tempfile.gettempdir")
    def test_get_caches_openapi_specification(self, gettempdir):
        gettempdir.return_value = self._tmpdir.name

        first = self._controller.get("3.0.3")
        second = self._controller.get("3.0.3")

        self.assertEqual({"openapi": "3.0.3"}, first)
        self.assertEqual(first, second)
        self._engine.build_openapi_specification.assert_called_once_with(
            version="3.0.3",
            request=self._controller._req,
        )

    @mock.patch("restalchemy.api.controllers.tempfile.gettempdir")
    def test_update_recalculates_openapi_specification(self, gettempdir):
        gettempdir.return_value = self._tmpdir.name
        self._controller.get("3.0.3")
        self._engine.build_openapi_specification.return_value = {
            "openapi": "3.0.3",
            "info": {"version": "updated"},
        }

        result = self._controller.update("3.0.3")

        self.assertEqual({"openapi": "3.0.3", "info": {"version": "updated"}}, result)
        self.assertEqual(result, self._controller.get("3.0.3"))
        self.assertEqual(2, self._engine.build_openapi_specification.call_count)


class FakeResource(object):
    def __init__(self, model):
        self._model = model

    def get_model(self):
        return self._model


class FakeModel(object):
    objects = mock.Mock()

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.insert = mock.Mock()

    @classmethod
    def get_id_property_name(cls):
        return "uuid"


class FakeItem(object):
    uuid = "resource-id"


class AutoBaseController(controllers.BaseResourceController):
    __resource__ = FakeResource(FakeModel)

    def get_autofilters(self):
        return {"project_id": dm_filters.EQ("project-id")}

    def get_autovalues(self):
        return {
            "project_id": "project-id",
            "updated_by": "user-id",
        }


class AutoNestedController(controllers.BaseNestedResourceController):
    __resource__ = FakeResource(FakeModel)
    __pr_name__ = "parent"

    def get_autofilters(self):
        return {"project_id": dm_filters.EQ("project-id")}

    def get_autovalues(self):
        return {
            "project_id": "project-id",
            "updated_by": "user-id",
        }


class AutoPaginatedController(
    controllers.BaseResourceControllerPaginated,
):
    __resource__ = FakeResource(FakeModel)

    def get_autofilters(self):
        return {"project_id": dm_filters.EQ("project-id")}


class TestAutoFiltersAndValues(unittest.TestCase):
    def setUp(self):
        super(TestAutoFiltersAndValues, self).setUp()
        FakeModel.objects = mock.Mock()

    def test_empty_autofilters_do_not_copy_filters(self):
        controller = controllers.Controller(None)
        filters = {"state": dm_filters.EQ("active")}

        result = controller._apply_autofilters(filters)

        self.assertIs(filters, result)

    def test_empty_autovalues_do_not_copy_values(self):
        controller = controllers.Controller(None)
        values = {"name": "server"}

        result = controller._apply_autovalues(values)

        self.assertIs(values, result)

    def test_base_create_applies_autovalues(self):
        controller = AutoBaseController(None)

        result = controller.create(name="server", project_id="request-project")

        self.assertEqual(
            {
                "name": "server",
                "project_id": "project-id",
                "updated_by": "user-id",
            },
            result.kwargs,
        )
        result.insert.assert_called_once_with()

    def test_base_get_applies_autofilters(self):
        controller = AutoBaseController(None)
        expected = mock.Mock()
        FakeModel.objects.get_one.return_value = expected

        result = controller.get(uuid="resource-id")

        self.assertIs(expected, result)
        filters = FakeModel.objects.get_one.call_args[1]["filters"]
        self.assertEqual(
            {
                "uuid": dm_filters.EQ("resource-id"),
                "project_id": dm_filters.EQ("project-id"),
            },
            filters,
        )

    def test_base_filter_applies_autofilters(self):
        controller = AutoBaseController(None)
        FakeModel.objects.get_all.return_value = []

        controller.filter(filters={"state": dm_filters.EQ("active")})

        filters = FakeModel.objects.get_all.call_args[1]["filters"]
        self.assertEqual(
            {
                "state": dm_filters.EQ("active"),
                "project_id": dm_filters.EQ("project-id"),
            },
            filters,
        )

    def test_base_update_applies_autovalues(self):
        controller = AutoBaseController(None)
        dm = mock.Mock()
        FakeModel.objects.get_one.return_value = dm

        controller.update(
            uuid="resource-id",
            name="server",
            project_id="request-project",
        )

        dm.update_dm.assert_called_once_with(
            values={
                "name": "server",
                "project_id": "project-id",
                "updated_by": "user-id",
            },
        )
        dm.update.assert_called_once_with()

    def test_nested_filter_applies_parent_and_autofilters(self):
        controller = AutoNestedController(None)
        FakeModel.objects.get_all.return_value = []

        controller.filter(
            parent_resource="parent-id",
            filters={"state": dm_filters.EQ("active")},
        )

        filters = FakeModel.objects.get_all.call_args[1]["filters"]
        self.assertEqual(
            {
                "state": dm_filters.EQ("active"),
                "parent": dm_filters.EQ("parent-id"),
                "project_id": dm_filters.EQ("project-id"),
            },
            filters,
        )

    def test_nested_update_applies_parent_autofilters_and_autovalues(self):
        controller = AutoNestedController(None)
        dm = mock.Mock()
        FakeModel.objects.get_one.return_value = dm

        controller.update(
            parent_resource="parent-id",
            uuid="resource-id",
            name="server",
        )

        filters = FakeModel.objects.get_one.call_args[1]["filters"]
        self.assertEqual(
            {
                "parent": "parent-id",
                "uuid": dm_filters.EQ("resource-id"),
                "project_id": dm_filters.EQ("project-id"),
            },
            filters,
        )
        dm.update_dm.assert_called_once_with(
            values={
                "name": "server",
                "project_id": "project-id",
                "updated_by": "user-id",
            },
        )
        dm.update.assert_called_once_with()

    def test_paginated_filter_applies_autofilters(self):
        controller = AutoPaginatedController(None)
        controller._pagination_limit = 1
        controller._pagination_marker = None
        FakeModel.objects.get_all.return_value = [FakeItem()]

        result = controller.filter(filters={"state": dm_filters.EQ("active")})

        self.assertEqual([FakeItem.uuid], [item.uuid for item in result])
        filters = FakeModel.objects.get_all.call_args[1]["filters"]
        self.assertEqual(
            {
                "state": dm_filters.EQ("active"),
                "project_id": dm_filters.EQ("project-id"),
            },
            filters,
        )

    def test_paginated_marker_lookup_applies_autofilters(self):
        controller = AutoPaginatedController(None)
        controller._pagination_limit = 1
        controller._pagination_marker = "marker-id"
        marker = mock.Mock()
        marker.name = "marker-name"
        FakeModel.objects.get_one.return_value = marker
        FakeModel.objects.get_all.return_value = []

        controller.filter(
            filters={"state": dm_filters.EQ("active")},
            order_by={"name": "asc"},
        )

        filters = FakeModel.objects.get_one.call_args[1]["filters"]
        self.assertEqual(
            {
                "state": dm_filters.EQ("active"),
                "project_id": dm_filters.EQ("project-id"),
                "uuid": dm_filters.EQ("marker-id"),
            },
            filters,
        )
