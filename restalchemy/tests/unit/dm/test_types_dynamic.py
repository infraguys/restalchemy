# Copyright 2026 Eugene Frolov <eugene@frolov.net.ru>
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

import http.client as http_client
import unittest

import mock
from webob import request

from restalchemy.api.middlewares import errors
from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.tests.unit.api import base as api_base
from restalchemy.common import exceptions as ra_exc
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.dm import types_dynamic
from restalchemy.openapi import constants as oa_c


class FakeKindModel(types_dynamic.AbstractKindModel):
    KIND = "fake"

    network = properties.property(
        types.AllowNone(types.String(max_length=255)),
        default=None,
    )


class FakeModelWithKind(models.ModelWithUUID):
    payload = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(FakeKindModel),
        ),
        required=True,
    )


class OpenApiDialectTestCase(unittest.TestCase):
    """The dialect must reach the properties inside a kind."""

    def _network_spec(self, openapi_version):
        selector = types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(FakeKindModel),
        )
        spec = selector.to_openapi_spec({types.OPENAPI_KEYWORD: openapi_version})
        return spec["oneOf"][0]["properties"]["network"]

    def test_a_nullable_property_of_a_kind_is_3_0_3_nullable(self):
        network = self._network_spec(oa_c.OPENAPI_SPECIFICATION_3_0_3)

        self.assertEqual("string", network["type"])
        self.assertTrue(network["nullable"])

    def test_a_nullable_property_of_a_kind_is_a_3_1_0_null_type(self):
        network = self._network_spec(oa_c.OPENAPI_SPECIFICATION_3_1_0)

        self.assertEqual(["string", "null"], network["type"])
        self.assertNotIn("nullable", network)


class FakeResponse(object):
    def __init__(self, status, json, **kwargs):
        self.status = status
        self.status_code = int(status)
        self.json = json


class UnknownKindTestCase(unittest.TestCase):
    """A kind that came from the outside is bad input, not a server fault."""

    def setUp(self):
        super(UnknownKindTestCase, self).setUp()
        self._selector = types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(FakeKindModel),
        )

    def test_a_value_without_a_known_kind_is_a_parse_error(self):
        with self.assertRaises(types_dynamic.UnknownType) as ctx:
            self._selector.from_simple_type({"a": "b"})

        self.assertIsInstance(ctx.exception, ra_exc.ParseError)
        self.assertEqual(400, ctx.exception.get_code())
        self.assertEqual("Unknown kind for value: {'a': 'b'}", ctx.exception.msg)

    def test_an_unknown_kind_in_a_json_body_is_a_parse_error(self):
        self.assertRaises(
            types_dynamic.UnknownType,
            self._selector.from_unicode,
            '{"kind": "nonexistent"}',
        )

    def test_an_unknown_kind_survives_the_body_parser_with_its_own_name(self):
        packer = packers.JSONPacker(
            resources.ResourceByRAModel(FakeModelWithKind),
            api_base.request_mock(),
        )
        self.addCleanup(setattr, resources.ResourceMap, "model_type_to_resource", {})

        with self.assertRaises(types_dynamic.UnknownType) as ctx:
            packer.unpack(b'{"payload": {"kind": "nonexistent"}}')

        self.assertEqual(400, ctx.exception.get_code())
        self.assertIn("payload=", ctx.exception.msg)

    def test_an_unknown_kind_answers_400_and_not_500(self):
        middleware = errors.ErrorsHandlerMiddleware("application")
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = types_dynamic.UnknownType(
            value={"a": "b"},
        )
        request_mock.ResponseClass = FakeResponse

        response = middleware.process_request(request_mock)

        self.assertEqual(http_client.BAD_REQUEST, response.status)
        self.assertEqual("UnknownType", response.json["type"])
        self.assertEqual(400, response.json["code"])


if __name__ == "__main__":
    unittest.main()
