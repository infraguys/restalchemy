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

import unittest

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


if __name__ == "__main__":
    unittest.main()
