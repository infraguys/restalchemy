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

import unittest

import mock

from restalchemy.api import packers
from restalchemy.api import controllers


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

        self.assertEqual(
            result.headers.get("Location", None), FAKE_LOCATION_PATH
        )

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

        self.assertEqual(
            result.headers.get("Location", None), FAKE_LOCATION_PATH
        )

    def test_location_for_result_and_tuple_location_false(self):
        result = self._controller.process_result(("", 200, None, False))

        self.assertEqual(result.headers.get("Location", None), None)

    @mock.patch("restalchemy.api.resources.ResourceMap")
    def test_location_for_result_and_tuple_location_true(self, resource_map):
        resource_map.get_location.return_value = FAKE_LOCATION_PATH

        result = self._controller.process_result(("", 200, None, True))

        self.assertEqual(
            result.headers.get("Location", None), FAKE_LOCATION_PATH
        )


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
        self.assertEqual(
            result.headers["Content-Type"], headers["Content-Type"]
        )
        self.assertEqual(
            result.headers["Content-Disposition"],
            headers["Content-Disposition"],
        )
