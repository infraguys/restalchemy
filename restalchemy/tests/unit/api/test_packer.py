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

# TODO(Eugene Frolov): Rewrite tests
import datetime
import decimal
import uuid

import mock
import orjson
import webob

from restalchemy.api import constants
from restalchemy.api import contexts
from restalchemy.api import field_permissions
from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.common import exceptions
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.tests.unit import base


class FakeModel(models.ModelWithUUID):
    field1 = properties.property(types.Integer(), required=False)
    field2 = properties.property(types.Integer())
    field3 = properties.property(types.Integer())
    field4 = properties.property(types.Integer(), required=True)


class TestData(object):
    uuid = None
    field1 = None
    field2 = 2
    field3 = 3
    field4 = 4


class BasePackerTestCase(base.BaseTestCase):
    def setUp(self):
        super(BasePackerTestCase, self).setUp()
        self._test_instance = packers.BaseResourcePacker(
            resources.ResourceByRAModel(FakeModel), mock.Mock()
        )

    def tearDown(self):
        super(BasePackerTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_instance

    def test_none_field_value(self):
        test_data = {"field1": None}

        result = self._test_instance.unpack(test_data)

        self.assertDictEqual(result, test_data)


class PackerFieldPermissionsHiddenTestCase(base.BaseTestCase):
    def setUp(self):
        req = mock.Mock()
        req.context.roles = ["owner"]

        super(PackerFieldPermissionsHiddenTestCase, self).setUp()
        self._test_resource_packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(
                FakeModel,
                fields_permissions=field_permissions.FieldsPermissionsByRole(
                    default=field_permissions.UniversalPermissions(
                        permission=field_permissions.Permissions.HIDDEN
                    )
                ),
            ),
            req,
        )

    def tearDown(self):
        super(PackerFieldPermissionsHiddenTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_resource_packer

    def test_pack(self):
        new_data = TestData()
        expected_data = {}

        result = self._test_resource_packer.pack(new_data)
        self.assertDictEqual(result, expected_data)

    def test_unpack(self):
        new_data = {"field2": 2}

        with self.assertRaises(exceptions.FieldPermissionError) as context:
            self._test_resource_packer.unpack(new_data)

        self.assertEqual("Permission denied for field field2.", str(context.exception))
        self.assertEqual(context.exception.code, 403)


class PackerFieldPermissionsNonDefaultHiddenTestCase(base.BaseTestCase):
    def setUp(self):
        req = mock.Mock()
        req.context.roles = ["owner"]

        super().setUp()
        self._test_resource_packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(
                FakeModel,
                fields_permissions=field_permissions.FieldsPermissionsByRole(
                    default=field_permissions.UniversalPermissions(
                        permission=field_permissions.Permissions.RW
                    ),
                    owner=field_permissions.UniversalPermissions(
                        permission=field_permissions.Permissions.HIDDEN
                    ),
                ),
            ),
            req,
        )

    def tearDown(self):
        super().tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_resource_packer

    def test_pack(self):
        new_data = TestData()
        expected_data = {}

        result = self._test_resource_packer.pack(new_data)
        self.assertDictEqual(result, expected_data)

    def test_unpack(self):
        new_data = {"field2": 2}

        with self.assertRaises(exceptions.FieldPermissionError) as context:
            self._test_resource_packer.unpack(new_data)

        self.assertEqual("Permission denied for field field2.", str(context.exception))
        self.assertEqual(context.exception.code, 403)


class PackerFieldPermissionsRWTestCase(base.BaseTestCase):
    def setUp(self):
        req = mock.Mock()
        req.context.roles = ["owner"]

        super(PackerFieldPermissionsRWTestCase, self).setUp()
        self._test_resource_packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(
                FakeModel,
                fields_permissions=field_permissions.FieldsPermissionsByRole(
                    default=field_permissions.UniversalPermissions()
                ),
            ),
            req,
        )

    def tearDown(self):
        super(PackerFieldPermissionsRWTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_resource_packer

    def test_pack(self):
        new_data = TestData()
        expected_data = {"field2": 2, "field3": 3, "field4": 4}

        result = self._test_resource_packer.pack(new_data)
        self.assertDictEqual(result, expected_data)

    def test_unpack(self):
        new_data = {"field1": None, "field2": 2}

        result = self._test_resource_packer.unpack(new_data)
        self.assertDictEqual(result, new_data)


class JSONPackerIncludeNullTestCase(base.BaseTestCase):
    def setUp(self):
        req = mock.Mock()
        req.context.roles = ["owner"]

        super(JSONPackerIncludeNullTestCase, self).setUp()
        self._test_resource_packer = packers.JSONPackerIncludeNullFields(
            resources.ResourceByRAModel(
                FakeModel,
                fields_permissions=field_permissions.FieldsPermissionsByRole(
                    default=field_permissions.UniversalPermissions()
                ),
            ),
            req,
        )

    def tearDown(self):
        super(JSONPackerIncludeNullTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_resource_packer

    def test_pack(self):
        new_data = TestData()
        expected_data = {
            "field1": None,
            "field2": 2,
            "field3": 3,
            "field4": 4,
            "uuid": None,
        }

        result = orjson.loads(self._test_resource_packer.pack(new_data))
        self.assertDictEqual(result, expected_data)

    def test_unpack(self):
        new_data = {"field1": None, "field2": 2}

        result = self._test_resource_packer.unpack(
            orjson.dumps(new_data, option=orjson.OPT_NON_STR_KEYS)
        )
        self.assertDictEqual(result, new_data)


class MultipartPackerTestCase(base.BaseTestCase):
    _raw_http_request = (
        "POST /v1/docs/5fc2e03d-8b22-4baf-b16d-772c373b98e1/files/ "
        "HTTP/1.1\r\n"
        "Accept: */*\r\n"
        "Content-Length: 200\r\n"
        "Content-Type: multipart/form-data; "
        "boundary=------------------------hSlQJvPejd4JFNPeCJtXm0\r\n"
        "Host: 127.0.0.1:8080\r\n"
        "User-Agent: curl/8.12.1-DEV\r\n"
        "\r\n"
        "--------------------------hSlQJvPejd4JFNPeCJtXm0\r\n"
        'Content-Disposition: form-data; name="data"; filename="test.md"\r\n'
        "Content-Type: */*\r\n"
        "\r\n"
        "test_body\n"
        "\r\n"
        "--------------------------hSlQJvPejd4JFNPeCJtXm0--\r\n"
    )

    def setUp(self):
        super().setUp()
        self._req = webob.Request.from_text(self._raw_http_request)
        self._packer = packers.MultipartPacker(
            resources.ResourceByRAModel(FakeModel),
            self._req,
        )

    def tearDown(self):
        super().tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._packer

    def test_pack(self):
        new_data = b"test"

        result = self._packer.pack(new_data)
        assert result == new_data

    def test_unpack(self):
        result = self._packer.unpack(None)
        assert packers.MultipartPacker._multipart_key in result
        assert len(result[packers.MultipartPacker._parts_key]) == 1
        assert (
            next(iter(result[packers.MultipartPacker._parts_key]["data"].file))
            == b"test_body\n"
        )


class OtherModel(models.ModelWithUUID):
    other_field = properties.property(types.Integer(), required=False)


class PackerResourceSwapTestCase(base.BaseTestCase):
    """A packer's resource is not as fixed as its request.

    `routes.Action.do` builds a packer and then clears `_rt` on it, so
    fields resolved for one resource must not answer for another.
    """

    def setUp(self):
        super(PackerResourceSwapTestCase, self).setUp()
        req = mock.Mock()
        req.context.roles = ["owner"]
        self._req = req
        self._packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(FakeModel),
            req,
        )

    def tearDown(self):
        super(PackerResourceSwapTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._packer

    def test_fields_follow_the_resource(self):
        first = sorted(name for name, _ in self._packer._get_fields())

        self._packer._rt = resources.ResourceByRAModel(OtherModel)
        second = sorted(name for name, _ in self._packer._get_fields())

        self.assertIn("field1", first)
        self.assertNotIn("field1", second)
        self.assertIn("other_field", second)

    def test_the_packed_fields_follow_the_resource_too(self):
        model = OtherModel(other_field=7)

        self._packer._rt = resources.ResourceByRAModel(OtherModel)

        self.assertEqual(
            {"other-field": 7, "uuid": str(model.uuid)},
            self._packer.pack_resource(model),
        )

    def test_clearing_the_resource_is_what_unpack_checks(self):
        # Action.do sets _rt to None so any field reaches the action.
        self._packer._rt = None

        self.assertEqual({"anything": 1}, self._packer.unpack({"anything": 1}))


class ShadowedFieldModel(FakeModel):
    """A model that computes a field its parent stores."""

    @property
    def field2(self):
        return 22


class PackerFieldSourceTestCase(base.BaseTestCase):
    """Where a packed value comes from.

    A stored property is read off the model's own properties; a name the
    class itself defines -- a `@property` over a declared field -- keeps
    the attribute lookup, and so keeps winning.
    """

    def setUp(self):
        super(PackerFieldSourceTestCase, self).setUp()
        self._req = mock.Mock()

    def tearDown(self):
        super(PackerFieldSourceTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}

    def test_a_stored_field_is_packed_from_the_model(self):
        packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(FakeModel), self._req
        )
        model = FakeModel(field2=2, field3=3, field4=4)

        self.assertEqual(2, packer.pack_resource(model)["field2"])

    def test_a_computed_field_beats_the_stored_one(self):
        packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(ShadowedFieldModel), self._req
        )
        model = ShadowedFieldModel(field2=2, field3=3, field4=4)

        self.assertEqual(22, packer.pack_resource(model)["field2"])

    def test_an_object_that_is_not_a_model_is_packed_by_attribute(self):
        packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(FakeModel), self._req
        )

        self.assertEqual(
            {"field2": 2, "field3": 3, "field4": 4},
            packer.pack_resource(TestData()),
        )


class DumpCallableTestCase(base.BaseTestCase):
    """Which types a packer may write out without converting."""

    def tearDown(self):
        super(DumpCallableTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}

    def _field(self, prop_type):
        return resources.ResourceRAProperty(
            resource=resources.ResourceByRAModel(FakeModel),
            prop_type=prop_type,
            model_property_name="field1",
        )

    def test_a_value_that_is_its_own_simple_form_needs_no_call(self):
        for prop_type in (
            types.String(),
            types.Integer(),
            types.Boolean(),
            types.Enum(["a", "b"]),
            types.Mac(),
        ):
            self.assertIsNone(self._field(prop_type).get_dump_callable())

    def test_a_value_that_is_converted_is_converted(self):
        for prop_type, value in (
            (types.UUID(), uuid.uuid4()),
            (types.UTCDateTimeZ(), types.DEFAULT_DATE_Z),
            (types.Decimal(), decimal.Decimal("1.5")),
        ):
            field = self._field(prop_type)
            dump = field.get_dump_callable()

            self.assertIsNotNone(dump)
            self.assertEqual(field.dump_value(value), dump(value))


class NativeTypesTestCase(base.BaseTestCase):
    """What a packer hands over unconverted, and what that must not change."""

    def setUp(self):
        super(NativeTypesTestCase, self).setUp()
        self._resource = resources.ResourceByRAModel(FakeModel)
        # A real request, so the resource does share what it resolves --
        # which is the thing these packers must not share blindly.
        self._req = webob.Request.blank("/things/")
        self._req.api_context = contexts.RequestContext(self._req)
        self._req.api_context.set_active_method(constants.GET)
        self._model = FakeModel(field2=2, field3=3, field4=4)

    def tearDown(self):
        super(NativeTypesTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}

    def test_the_json_a_uuid_ends_up_in_is_the_same(self):
        packer = packers.JSONPacker(self._resource, self._req)

        self.assertEqual(
            orjson.dumps(
                {
                    "uuid": str(self._model.uuid),
                    "field2": 2,
                    "field3": 3,
                    "field4": 4,
                }
            ),
            packer.pack(self._model),
        )

    def test_a_packer_that_writes_no_json_still_gets_a_string(self):
        packer = packers.BaseResourcePacker(self._resource, self._req)

        self.assertEqual(
            str(self._model.uuid), packer.pack_resource(self._model)["uuid"]
        )

    def test_packers_do_not_share_what_they_write_out_differently(self):
        # Both read the same resource for the same request, and the
        # resource shares what it resolved between them -- but only one
        # of them may leave a UUID for the document to write.
        json_packer = packers.JSONPacker(self._resource, self._req)
        plain_packer = packers.BaseResourcePacker(self._resource, self._req)

        json_result = json_packer.pack_resource(self._model)
        plain_result = plain_packer.pack_resource(self._model)

        self.assertIsNotNone(self._resource.request_cache(self._req))

        self.assertIsInstance(json_result["uuid"], uuid.UUID)
        self.assertIsInstance(plain_result["uuid"], str)


class TimestampModel(models.ModelWithUUID):
    when = properties.property(types.UTCDateTimeZ(), required=True)
    naive = properties.property(types.UTCDateTime(), required=True)
    payload = properties.property(types.Dict(), default=dict)


class TimestampFormatTestCase(base.BaseTestCase):
    """The shape of a timestamp on the wire.

    orjson writes a UTC datetime as RFC 3339 itself, and this packer
    lets it: the same bytes as before, except that a timestamp landing
    exactly on a second no longer carries `.000000`.
    """

    UTC = datetime.timezone.utc

    def setUp(self):
        super(TimestampFormatTestCase, self).setUp()
        self._resource = resources.ResourceByRAModel(TimestampModel)
        self._req = webob.Request.blank("/things/")
        self._req.api_context = contexts.RequestContext(self._req)
        self._req.api_context.set_active_method(constants.GET)

    def tearDown(self):
        super(TimestampFormatTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}

    def _packed(self, when, naive=None, payload=None):
        model = TimestampModel(
            when=when,
            naive=naive or datetime.datetime(2026, 8, 16, 1, 2, 3, 4),
            payload=payload or {},
        )
        return orjson.loads(packers.JSONPacker(self._resource, self._req).pack(model))

    def test_a_fraction_is_written_as_it_always_was(self):
        packed = self._packed(
            datetime.datetime(2026, 8, 16, 12, 34, 56, 123456, tzinfo=self.UTC)
        )

        self.assertEqual("2026-08-16T12:34:56.123456Z", packed["when"])

    def test_a_whole_second_carries_no_fraction(self):
        packed = self._packed(
            datetime.datetime(2026, 8, 16, 12, 34, 56, tzinfo=self.UTC)
        )

        self.assertEqual("2026-08-16T12:34:56Z", packed["when"])

    def test_the_naive_type_writes_its_own_form(self):
        packed = self._packed(
            datetime.datetime(2026, 8, 16, 12, 34, 56, tzinfo=self.UTC),
            naive=datetime.datetime(2026, 8, 16, 12, 34, 56),
        )

        self.assertEqual("2026-08-16T12:34:56.000000Z", packed["naive"])

    def test_a_timestamp_inside_a_value_ends_in_z(self):
        packed = self._packed(
            datetime.datetime(2026, 8, 16, 12, 34, 56, 1, tzinfo=self.UTC),
            payload={
                "seen": datetime.datetime(2026, 8, 16, 1, 2, 3, 4, tzinfo=self.UTC)
            },
        )

        self.assertEqual("2026-08-16T01:02:03.000004Z", packed["payload"]["seen"])
