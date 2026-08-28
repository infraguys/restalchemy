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

import json
import typing
import unittest
from unittest import mock
import uuid

import webob

from restalchemy.api import contexts as api_contexts
from restalchemy.api import controllers
from restalchemy.api import field_permissions
from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.common import exceptions as ra_exc
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models as dm_models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.openapi import cache as openapi_cache
from restalchemy.storage.sql import orm

FAKE_LOCATION_PATH = "fake location path"


class TestLocationHeaderLogic(unittest.TestCase):
    def setUp(self):
        super().setUp()
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


class FirstAppRoute:
    pass


class SecondAppRoute:
    pass


class TestOpenApiSpecificationCache(unittest.TestCase):
    def setUp(self):
        super().setUp()
        openapi_cache.clear()
        self.addCleanup(openapi_cache.clear)
        self._engine = self._build_engine({"openapi": "3.0.3"})
        self._controller = self._build_controller(FirstAppRoute)

    @staticmethod
    def _build_engine(specification):
        engine = mock.Mock()
        engine.build_openapi_specification.return_value = specification
        engine.build_openapi_servers.return_value = {
            "servers": [{"url": "http://example"}]
        }
        engine.list_supported_openapi_versions.return_value = ["3.0.3"]
        return engine

    def _build_controller(self, main_route, engine=None, host="http://one"):
        request = mock.Mock()
        request.application.openapi_engine = engine or self._engine
        request.application.main_route = main_route
        request.host_url = host
        return controllers.OpenApiSpecificationController(request)

    @staticmethod
    def _served(controller, version):
        body = controller.get(version)
        # The controller answers with the encoded document, not with a
        # structure to be encoded again per request.
        assert isinstance(body, bytes), body
        return json.loads(body)

    def test_get_builds_the_specification_once(self):
        first = self._served(self._controller, "3.0.3")
        second = self._served(self._controller, "3.0.3")

        self.assertEqual({"openapi": "3.0.3"}, first)
        self.assertEqual(first, second)
        self._engine.build_openapi_specification.assert_called_once_with(
            version="3.0.3",
            request=self._controller._req,
        )

    def test_get_encodes_the_specification_once_per_host(self):
        packer = controllers.packers.JSONPackerPreEncoded
        with mock.patch.object(packer, "pack", autospec=True) as pack:
            pack.side_effect = lambda self, obj: b"{}"
            self._controller.get("3.0.3")
            self._controller.get("3.0.3")
            self._controller.get("3.0.3")

        self.assertEqual(1, pack.call_count)

    def test_update_recalculates_the_specification(self):
        self._served(self._controller, "3.0.3")
        self._engine.build_openapi_specification.return_value = {
            "openapi": "3.0.3",
            "info": {"version": "updated"},
        }

        result = self._controller.update("3.0.3")

        self.assertEqual({"openapi": "3.0.3", "info": {"version": "updated"}}, result)
        served = self._served(self._controller, "3.0.3")
        self.assertEqual("updated", served["info"]["version"])
        self.assertEqual(2, self._engine.build_openapi_specification.call_count)

    def test_applications_do_not_share_an_entry(self):
        # Several RestAlchemy services may run in one interpreter.
        other_engine = self._build_engine(
            {"openapi": "3.0.3", "info": {"title": "the other service"}}
        )
        other = self._build_controller(SecondAppRoute, engine=other_engine)

        self.assertEqual({"openapi": "3.0.3"}, self._served(self._controller, "3.0.3"))
        self.assertEqual(
            {"openapi": "3.0.3", "info": {"title": "the other service"}},
            self._served(other, "3.0.3"),
        )

    def test_each_host_is_served_its_own_servers_block(self):
        # The servers url defaults to the host being addressed, so it is the
        # one part that must not be reused between callers.
        self._served(self._controller, "3.0.3")
        self._engine.build_openapi_servers.return_value = {
            "servers": [{"url": "http://another-host"}]
        }
        elsewhere = self._build_controller(FirstAppRoute, host="http://another-host")

        served = self._served(elsewhere, "3.0.3")

        self.assertEqual([{"url": "http://another-host"}], served["servers"])
        self._engine.build_openapi_specification.assert_called_once()

    def test_encoded_documents_are_bounded_by_host_count(self):
        # The host an encoded document is keyed by is the Host header of the
        # request, so a caller varying it must not be able to make the process
        # hold one copy of the document per value it sends.
        application = self._controller.request.application
        hosts = [
            f"http://host-{number}"
            for number in range(openapi_cache.ENCODED_MAX_ENTRIES * 4)
        ]

        for host in hosts:
            self._served(self._build_controller(FirstAppRoute, host=host), "3.0.3")

        retained = [
            host
            for host in hosts
            if openapi_cache.load_encoded(application, "3.0.3", host) is not None
        ]
        self.assertEqual(openapi_cache.ENCODED_MAX_ENTRIES, len(retained))

    def test_the_least_recently_served_host_loses_its_copy_first(self):
        # Which is what keeps the hosts a service actually answers on in the
        # cache while something else cycles through names.
        application = self._controller.request.application
        hosts = [
            f"http://host-{number}"
            for number in range(openapi_cache.ENCODED_MAX_ENTRIES)
        ]
        for host in hosts:
            self._served(self._build_controller(FirstAppRoute, host=host), "3.0.3")

        # Serving the oldest again leaves the second oldest least recent.
        self._served(self._build_controller(FirstAppRoute, host=hosts[0]), "3.0.3")
        self._served(self._build_controller(FirstAppRoute, host="http://new"), "3.0.3")

        self.assertIsNotNone(openapi_cache.load_encoded(application, "3.0.3", hosts[0]))
        self.assertIsNone(openapi_cache.load_encoded(application, "3.0.3", hosts[1]))

    def test_warm_up_serves_every_worker_of_a_forking_service(self):
        # A service builds one application per worker before forking, so the
        # first one to warm up must spare the rest the work.
        application = mock.Mock()
        application.main_route = FirstAppRoute
        application.openapi_engine = self._engine

        openapi_cache.warm_up(application, mock.Mock())
        openapi_cache.warm_up(application, mock.Mock())

        self.assertEqual(1, self._engine.build_openapi_specification.call_count)
        self.assertEqual({"openapi": "3.0.3"}, openapi_cache.load(application, "3.0.3"))

    def test_warm_up_failure_is_not_fatal(self):
        application = mock.Mock()
        application.main_route = FirstAppRoute
        application.openapi_engine = self._engine
        self._engine.build_openapi_specification.side_effect = RuntimeError("boom")

        openapi_cache.warm_up(application, mock.Mock())

        self.assertIsNone(openapi_cache.load(application, "3.0.3"))


class FakeResource:
    def __init__(self, model):
        self._model = model

    def get_model(self):
        return self._model


class FakeModel:
    objects = mock.Mock()

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.insert = mock.Mock()

    @classmethod
    def get_id_property_name(cls):
        return "uuid"


class FakeItem:
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
        super().setUp()
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


class StorableTaggedModel(
    dm_models.ModelWithUUID,
    dm_models.ModelWithTags,
    orm.SQLStorableMixin,
):
    __tablename__ = "tagged"

    name = properties.property(types.String(), default="")


class StorableTaggedController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        StorableTaggedModel,
        process_filters=True,
    )


class SecretModel(dm_models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "secret"

    name = properties.property(types.String(), default="")
    password_hash = properties.property(types.String(), default="")
    token = properties.property(types.String(), default="")


class HiddenFieldController(controllers.BaseResourceController):
    """Hides a field the old way: out of responses entirely."""

    __resource__ = resources.ResourceByRAModel(
        SecretModel,
        process_filters=True,
        hidden_fields=["password_hash"],
    )


class UnfilterableFieldController(controllers.BaseResourceController):
    """Hides a field for the FILTER method only."""

    __resource__ = resources.ResourceByRAModel(
        SecretModel,
        process_filters=True,
        fields_permissions=field_permissions.FieldsPermissions(
            fields={
                "token": {
                    controllers.constants.FILTER: field_permissions.Permissions.HIDDEN
                }
            },
        ),
    )


class RawHiddenFieldController(controllers.BaseResourceController):
    """Hides a field on a resource that does not process filters."""

    __resource__ = resources.ResourceByRAModel(
        SecretModel,
        hidden_fields=["password_hash"],
    )


class RawUnfilterableFieldController(controllers.BaseResourceController):
    """Hides a field for FILTER only, again without processing filters."""

    __resource__ = resources.ResourceByRAModel(
        SecretModel,
        fields_permissions=field_permissions.FieldsPermissions(
            fields={
                "token": {
                    controllers.constants.FILTER: field_permissions.Permissions.HIDDEN
                }
            },
        ),
    )


class UnderscoreController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        SecretModel,
        process_filters=True,
        convert_underscore=True,
    )


class CustomPropertyModel(
    dm_models.ModelWithUUID,
    dm_models.CustomPropertiesMixin,
    orm.SQLStorableMixin,
):
    __tablename__ = "custom"
    __custom_properties__: typing.ClassVar = {"computed": types.String()}

    name = properties.property(types.String(), default="")

    @property
    def computed(self):
        return "computed"


class CustomPropertyController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByModelWithCustomProps(
        CustomPropertyModel,
        process_filters=True,
    )


def _clauses_of(filters):
    """Every clause in a filter tree, whatever its shape."""
    if isinstance(filters, dict):
        return list(filters.values())
    found = []
    for clause in filters.clauses:
        found.extend(_clauses_of(clause))
    return found


def _request(query):
    request = webob.Request.blank(f"/?{query}")
    request.api_context = api_contexts.RequestContext(request)
    # do_collection sets this before parsing filters; FieldsPermissions
    # resolves its per-method rules against it.
    request.api_context.set_active_method(controllers.constants.FILTER)
    return request


class FilterLangControllerTestCase(unittest.TestCase):
    """`?q=<expression>` reaching the storage call."""

    def setUp(self):
        super().setUp()
        self._controller = StorableTaggedController(_request(""))

    def _parse(self, query):
        controller = StorableTaggedController(_request(query))
        return controller._prepare_query_filter(
            controller._req.api_context.params,
        )

    def _get_all_filters(self, query, controller_class=None):
        """Run a GET collection and return the filters storage was given."""
        controller = (controller_class or StorableTaggedController)(_request(query))
        with mock.patch.object(controller.model, "objects") as objects:
            objects.get_all.return_value = []
            controller.do_collection()
        return objects.get_all.call_args.kwargs["filters"]

    def test_no_parameter_no_expression(self):
        self.assertIsNone(self._parse("name=vm1"))

    def test_an_empty_parameter_is_not_an_expression(self):
        self.assertIsNone(self._parse("q="))

    def test_the_parameter_is_parsed(self):
        self.assertEqual(
            {"name": dm_filters.In(["a", "b"])},
            self._parse("q=name = a OR name = b"),
        )

    def test_the_parameter_is_not_also_a_field_filter(self):
        # It is taken out of the field namespace where it is enabled, or
        # it would resolve as a field and 400 as an unknown one.
        controller = StorableTaggedController(_request("q=name = a"))

        self.assertEqual(
            {},
            controller._prepare_filters(
                controller._req.api_context.get_params_filters(exclude=("q",)),
            ),
        )

    def test_two_expressions_are_refused(self):
        # Whether they should be ANDed or ORed is not in the request.
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._parse,
            "q=name = a&q=name = b",
        )

    def test_an_unknown_field_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError, self._parse, "q=nope = a"
        )

    def test_the_value_goes_through_the_field_type(self):
        # The same parse a field parameter gets, so `?name=x` and
        # `q=name = x` cannot drift apart.
        resource = StorableTaggedController.__resource__
        with mock.patch.object(
            resource,
            "get_field",
            wraps=resource.get_field,
        ) as get_field:
            self._parse('q=name = "vm1"')

        self.assertTrue(get_field.called)

    def test_an_expression_alone_reaches_storage(self):
        self.assertEqual(
            {"name": dm_filters.EQ("vm1")},
            self._get_all_filters("q=name = vm1"),
        )

    def test_field_parameters_and_the_expression_are_anded(self):
        filters = self._get_all_filters("name=vm1&q=tags:x")

        self.assertIsInstance(filters, dm_filters.AND)
        self.assertEqual({"name": dm_filters.EQ("vm1")}, filters.clauses[0])
        self.assertEqual({"tags": dm_filters.ContainsAll(["x"])}, filters.clauses[1])

    def test_no_expression_leaves_the_filters_a_plain_mapping(self):
        # The shape everything downstream of a filter has always seen.
        self.assertEqual(
            {"name": dm_filters.EQ("vm1")}, self._get_all_filters("name=vm1")
        )

    def test_a_custom_property_is_out_of_reach(self):
        # It is filtered in Python after the query, so an expression that
        # named it could not be evaluated in one place.
        controller = CustomPropertyController(_request("q=computed = x"))

        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            controller._prepare_query_filter,
            controller._req.api_context.params,
        )

    def test_a_custom_property_is_still_filterable_by_parameter(self):
        controller = CustomPropertyController(_request("computed=x"))

        self.assertEqual(
            {"computed": dm_filters.EQ("x")},
            controller._prepare_filters(
                controller._req.api_context.get_params_filters(exclude=("q",)),
            ),
        )

    def test_the_parameter_can_be_renamed(self):
        class RenamedController(StorableTaggedController):
            __filter_param__ = "filter"

        self.assertEqual(
            {"name": dm_filters.EQ("vm1")},
            self._get_all_filters("filter=name = vm1", RenamedController),
        )

    def test_the_language_can_be_turned_off(self):
        # With it off the parameter goes back to being an ordinary one,
        # which for a filtered resource means an unknown field.
        class PlainController(StorableTaggedController):
            __filter_param__ = None

        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._get_all_filters,
            "q=name = vm1",
            PlainController,
        )

    def test_a_controller_that_drops_the_expression_is_an_error(self):
        # Its own filter() never applied it; answering with unfiltered
        # rows would be a failure the caller cannot see.
        class OwnFilterController(StorableTaggedController):
            def filter(self, filters, order_by=None):
                return []

        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._get_all_filters,
            "q=name = vm1",
            OwnFilterController,
        )

    def test_a_controller_that_drops_the_expression_does_not_pack_a_body(self):
        # Packing is thrown away from there, so the check lands first.
        class OwnFilterController(StorableTaggedController):
            def filter(self, filters, order_by=None):
                return []

            def process_result(self, *args, **kwargs):
                raise AssertionError("packed a result that is about to 400")

        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._get_all_filters,
            "q=name = vm1",
            OwnFilterController,
        )

    def test_a_blank_expression_is_not_an_expression(self):
        # `?q=%20` has to read as `?q=`, or the check above fires on a
        # parameter that asked for nothing.
        class OwnFilterController(StorableTaggedController):
            def filter(self, filters, order_by=None):
                return []

        self.assertIsNone(self._parse("q=%20"))
        response = OwnFilterController(_request("q=%20")).do_collection()

        self.assertEqual(200, response.status_code)

    def test_too_complex_an_expression_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterTooComplexError,
            self._parse,
            "q=" + " AND ".join(["name = a"] * 40),
        )

    def test_too_long_an_expression_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterTooComplexError,
            self._parse,
            "q=" + "name = a " * controllers.Controller.__filter_max_length__,
        )


class PaginatedTaggedController(controllers.BaseResourceControllerPaginated):
    __resource__ = StorableTaggedController.__resource__


class FilterLangFieldVisibilityTestCase(unittest.TestCase):
    """A hidden field is not filterable through the expression.

    The response layer strips these fields; comparing against them would
    hand back, one bit per request, exactly what stripping them withholds.
    """

    def _parse(self, controller_class, query):
        controller = controller_class(_request(query))
        return controller._prepare_query_filter(
            controller._req.api_context.params,
        )

    def test_a_hidden_field_cannot_be_named(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._parse,
            HiddenFieldController,
            'q=password_hash = "x"',
        )

    def test_a_hidden_field_cannot_be_compared(self):
        # The comparison operators are what turn reach into extraction.
        for expression in (
            'password_hash > "m"',
            'password_hash >= "m"',
            'password_hash < "m"',
            'password_hash != "m"',
            "password_hash:*",
        ):
            self.assertRaises(
                ra_exc.ValidationFilterIncompatibleError,
                self._parse,
                HiddenFieldController,
                f"q={expression}",
            )

    def test_a_hidden_field_cannot_hide_inside_an_expression(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._parse,
            HiddenFieldController,
            'q=name = "victim" AND NOT (password_hash < "m")',
        )

    def test_a_visible_field_on_the_same_resource_still_works(self):
        self.assertEqual(
            {"name": dm_filters.EQ("victim")},
            self._parse(HiddenFieldController, 'q=name = "victim"'),
        )

    def test_a_field_hidden_for_filtering_only_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._parse,
            UnfilterableFieldController,
            'q=token > "m"',
        )

    def test_a_field_left_alone_by_the_permissions_still_works(self):
        self.assertEqual(
            {"name": dm_filters.EQ("victim")},
            self._parse(UnfilterableFieldController, 'q=name = "victim"'),
        )

    def test_hidden_and_unknown_are_indistinguishable(self):
        # Two different errors would answer "this field exists, you just
        # may not see it" -- half of what hiding it was meant to prevent.
        def error(query):
            try:
                self._parse(HiddenFieldController, query)
            except ra_exc.ValidationFilterIncompatibleError as e:
                return str(e)
            raise AssertionError(f"expected a refusal for {query}")

        self.assertEqual(
            error('q=no_such_field = "x"').replace("no_such_field", "F"),
            error('q=password_hash = "x"').replace("password_hash", "F"),
        )


class HiddenFieldParameterTestCase(unittest.TestCase):
    """A hidden field is not filterable by a plain parameter either."""

    def _filters(self, controller_class, query):
        controller = controller_class(_request(query))
        return controller._prepare_filters(
            controller._req.api_context.get_params_filters(exclude=("q",)),
        )

    def test_a_hidden_field_parameter_is_refused(self):
        # Weaker than the expression -- it only confirms a guess -- but it
        # is the same field and the same answer.
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._filters,
            HiddenFieldController,
            "password_hash=x",
        )

    def test_a_field_hidden_for_filtering_only_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._filters,
            UnfilterableFieldController,
            "token=x",
        )

    def test_a_visible_field_parameter_still_works(self):
        self.assertEqual(
            {"name": dm_filters.EQ("victim")},
            self._filters(HiddenFieldController, "name=victim"),
        )


class HiddenFieldParameterWithoutProcessingTestCase(unittest.TestCase):
    """The same question on a resource that does not process filters.

    `process_filters` turns on parsing a value into the field's type.
    Whether the field may be named at all is a different question, and the
    answer to it used to depend on the flag: without it the parameter went
    to `filter()` exactly as it arrived, hidden field or not.
    """

    def _filters(self, controller_class, query):
        controller = controller_class(_request(query))
        return controller._prepare_filters(
            controller._req.api_context.get_params_filters(),
        )

    def test_a_hidden_field_parameter_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._filters,
            RawHiddenFieldController,
            "password_hash=x",
        )

    def test_a_field_hidden_for_filtering_only_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._filters,
            RawUnfilterableFieldController,
            "token=x",
        )

    def test_a_hidden_field_is_refused_under_its_api_name(self):
        # The resource converts underscores, so this is the name the field
        # is addressed by from outside.
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._filters,
            RawHiddenFieldController,
            "password-hash=x",
        )

    def test_a_visible_field_parameter_arrives_unparsed(self):
        # Which is what not processing filters means, and is unchanged.
        self.assertEqual(
            {"name": dm_filters.EQ("victim")},
            self._filters(RawHiddenFieldController, "name=victim"),
        )

    def test_a_parameter_naming_no_field_is_left_alone(self):
        # A controller that does not process filters may take query
        # parameters of its own and read them in its own filter(); those
        # are not the resource's to judge.
        self.assertEqual(
            {"since": dm_filters.EQ("yesterday")},
            self._filters(RawHiddenFieldController, "since=yesterday"),
        )


class SortKeyVisibilityTestCase(unittest.TestCase):
    """Sorting reports on a field's value just as filtering does.

    `?sort_key=secret` orders the collection by a column the response
    never shows, and `page_marker` then makes the cursor compare against
    that column directly.
    """

    def _sorts(self, controller_class, query):
        controller = controller_class(_request(query))
        return controller._prepare_sorts(controller._req.api_context.params)

    def test_sorting_by_a_hidden_field_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationSortInvalidKeyError,
            self._sorts,
            HiddenFieldController,
            "sort_key=password_hash",
        )

    def test_sorting_by_a_field_hidden_for_filtering_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationSortInvalidKeyError,
            self._sorts,
            UnfilterableFieldController,
            "sort_key=token",
        )

    def test_sorting_by_an_unknown_field_is_refused(self):
        # It used to reach the database and come back a 500.
        self.assertRaises(
            ra_exc.ValidationSortInvalidKeyError,
            self._sorts,
            HiddenFieldController,
            "sort_key=no_such_field",
        )

    def test_hidden_and_unknown_sort_keys_are_indistinguishable(self):
        def error(query):
            try:
                self._sorts(HiddenFieldController, query)
            except ra_exc.ValidationSortInvalidKeyError as e:
                return str(e)
            raise AssertionError(f"expected a refusal for {query}")

        self.assertEqual(
            error("sort_key=no_such_field").replace("no_such_field", "F"),
            error("sort_key=password_hash").replace("password_hash", "F"),
        )

    def test_sorting_by_a_visible_field_still_works(self):
        self.assertEqual(
            {"name": "asc"}, self._sorts(HiddenFieldController, "sort_key=name")
        )

    def test_a_direction_still_applies(self):
        self.assertEqual(
            {"name": "desc"},
            self._sorts(HiddenFieldController, "sort_key=name&sort_dir=desc"),
        )

    def test_the_key_comes_back_as_the_model_name(self):
        # The parameter used to be passed through untouched, so an API
        # name that differs from the model's could filter but not sort.
        self.assertEqual(
            {"name": "asc"},
            self._sorts(UnderscoreController, "sort_key=name"),
        )

    def test_a_controller_without_a_resource_sorts_as_before(self):
        controller = controllers.Controller(_request("sort_key=whatever"))

        self.assertEqual(
            {"whatever": "asc"},
            controller._prepare_sorts(controller._req.api_context.params),
        )


class FilterLangPaginationTestCase(unittest.TestCase):
    """The cursor and the expression narrow the same page."""

    def _get_all_calls(self, query, pages=((),)):
        """Run a GET collection, return every get_all call it made."""
        controller = PaginatedTaggedController(_request(query))
        with mock.patch.object(controller.model, "objects") as objects:
            objects.get_all.side_effect = list(pages)
            controller.do_collection()
        return objects.get_all.call_args_list

    def _get_all_kwargs(self, query):
        return self._get_all_calls(query)[0].kwargs

    def test_the_expression_survives_pagination(self):
        kwargs = self._get_all_kwargs("q=name = vm1&page_limit=5")

        self.assertEqual(5, kwargs["limit"])
        self.assertEqual({"name": dm_filters.EQ("vm1")}, kwargs["filters"])

    def test_the_cursor_and_the_expression_are_both_applied(self):
        marker = str(uuid.uuid4())

        filters = self._get_all_kwargs(
            f"q=name = vm1&page_limit=5&page_marker={marker}"
        )["filters"]

        # AND(AND(cursor, {}), expression): the cursor is built against
        # the field filters, the expression joins straight after.
        self.assertIsInstance(filters, dm_filters.AND)
        self.assertEqual({"name": dm_filters.EQ("vm1")}, filters.clauses[-1])
        self.assertIn(
            # The marker went through the id type, as it does without an
            # expression in the request.
            {"uuid": dm_filters.GT(uuid.UUID(marker))},
            filters.clauses[0].clauses,
        )

    def test_the_marker_row_is_looked_up_by_the_field_filters(self):
        # The cursor resolves the marker's sort value with a mapping, so
        # the expression joins after it is built, not before. Sorting by
        # a column other than the id is what takes that lookup.
        marker = str(uuid.uuid4())
        controller = PaginatedTaggedController(
            _request(f"q=tags:x&sort_key=name&page_limit=5&page_marker={marker}")
        )
        with mock.patch.object(controller.model, "objects") as objects:
            objects.get_all.return_value = []
            objects.get_one.return_value = mock.Mock(name="row")
            controller.do_collection()

        self.assertEqual(
            {"uuid": dm_filters.EQ(uuid.UUID(marker))},
            objects.get_one.call_args.kwargs["filters"],
        )

    def test_every_page_of_the_top_up_loop_carries_the_expression(self):
        # paginated_filter calls storage again when custom properties
        # thinned the page out; the expression must ride every call.
        rows = [StorableTaggedModel(name="vm1") for _ in range(2)]

        calls = self._get_all_calls("q=name = vm1&page_limit=5", (rows, []))

        self.assertEqual(2, len(calls))
        for call in calls:
            self.assertIn(dm_filters.EQ("vm1"), _clauses_of(call.kwargs["filters"]))


class UnfilteredController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(StorableTaggedModel)


class FilterLangOpenApiTestCase(unittest.TestCase):
    """The expression parameter is described on the collection GET."""

    def _parameters(self, controller_class):
        class _Route(routes.Route):
            __controller__ = controller_class
            __allow_methods__: typing.ClassVar = [routes.FILTER]

        request = _request("")
        specification = _Route(request)._build_openapi_method_specification(
            routes.FILTER,
            parameters={"components": {"parameters": {}}},
            current_path="/{uuid}/",
        )
        return {param["name"]: param for param in specification["parameters"]}

    def test_the_parameter_is_described(self):
        parameter = self._parameters(StorableTaggedController)["q"]

        self.assertEqual("query", parameter["in"])
        self.assertEqual("string", parameter["schema"]["type"])
        self.assertFalse(parameter["required"])

    def test_it_carries_the_fields_it_may_name(self):
        # One opaque string is what a generated client gets; the fields
        # are listed so a generator has something better to work with.
        parameter = self._parameters(StorableTaggedController)["q"]

        self.assertIn("name", parameter["x-ra-filter-fields"])
        self.assertIn("tags", parameter["x-ra-filter-fields"])

    def test_a_renamed_parameter_is_described_under_its_name(self):
        class RenamedController(StorableTaggedController):
            __filter_param__ = "filter"

        parameters = self._parameters(RenamedController)

        self.assertIn("filter", parameters)
        self.assertNotIn("q", parameters)

    def test_nothing_is_described_where_the_language_is_off(self):
        class PlainController(StorableTaggedController):
            __filter_param__ = None

        self.assertNotIn("q", self._parameters(PlainController))

    def test_nothing_is_described_without_filter_processing(self):
        # The language needs fields to resolve against.
        self.assertNotIn("q", self._parameters(UnfilteredController))

    def test_a_field_of_the_same_name_is_not_described_twice(self):
        # Two parameters called `name` would collide.
        class NameFilterController(StorableTaggedController):
            __filter_param__ = "name"

        parameters = self._parameters(NameFilterController)

        self.assertIn("x-ra-filter-fields", parameters["name"])


class CustomFilterProcessingTestCase(unittest.TestCase):
    """The filters storage cannot run, applied over the rows it returned."""

    def setUp(self):
        self._controller = CustomPropertyController(_request(""))

    def _rows(self, count):
        return [CustomPropertyModel(name=f"vm{i}") for i in range(count)]

    def test_no_filters_passes_the_rows_through(self):
        rows = self._rows(3)

        self.assertEqual(rows, self._controller._process_custom_filters(rows, {}))

    def test_a_matching_equality_keeps_every_row(self):
        rows = self._rows(3)

        self.assertEqual(
            rows,
            self._controller._process_custom_filters(
                rows, {"computed": dm_filters.EQ("computed")}
            ),
        )

    def test_a_missing_equality_drops_every_row(self):
        self.assertEqual(
            [],
            self._controller._process_custom_filters(
                self._rows(3), {"computed": dm_filters.EQ("other")}
            ),
        )

    def test_membership_is_honoured(self):
        rows = self._rows(2)

        self.assertEqual(
            rows,
            self._controller._process_custom_filters(
                rows, {"computed": dm_filters.In(["computed", "other"])}
            ),
        )
        self.assertEqual(
            [],
            self._controller._process_custom_filters(
                rows, {"computed": dm_filters.In(["other"])}
            ),
        )

    def test_filters_are_conjoined(self):
        # A row must satisfy all of them, not the last one to look at it.
        rows = self._rows(2)

        self.assertEqual(
            [],
            self._controller._process_custom_filters(
                rows,
                {
                    "computed": dm_filters.EQ("computed"),
                    "name": dm_filters.EQ("nothing"),
                },
            ),
        )

    def test_the_list_passed_in_is_narrowed_in_place(self):
        # The old implementation removed from it, and a caller may be
        # reading that list rather than the returned one.
        rows = self._rows(3)

        returned = self._controller._process_custom_filters(
            rows, {"computed": dm_filters.EQ("other")}
        )

        self.assertEqual([], rows)
        self.assertIs(rows, returned)

    def test_an_unsupported_clause_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._controller._process_custom_filters,
            self._rows(2),
            {"computed": dm_filters.NE("computed")},
        )

    def test_an_unsupported_clause_is_refused_on_an_empty_result(self):
        # Refused on sight: whether the clause is supported cannot depend
        # on how many rows happened to come back.
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            self._controller._process_custom_filters,
            [],
            {"computed": dm_filters.NE("computed")},
        )
