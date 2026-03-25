# Copyright 2026 Eugene Frolov
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

"""Unit tests for soft delete controller mixin."""

import datetime
import unittest

import mock

from restalchemy.api import controllers
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import orm


class FakeSoftDeleteModel(models.ModelSoftDelete, orm.SQLStorableSoftDeleteMixin):
    """Test model with soft delete support."""

    __tablename__ = "fake_controller_soft_delete_table"

    uuid = properties.property(
        types.UUID(), read_only=True, id_property=True
    )
    name = properties.property(types.String(max_length=255), default="")


class FakeResource:
    """Fake resource for testing."""

    @staticmethod
    def get_model():
        return FakeSoftDeleteModel

    @staticmethod
    def get_model_field_name(name):
        return name

    @staticmethod
    def get_field(name):
        field_mock = mock.Mock()
        field_mock.name = name
        field_mock.parse_value_from_unicode = lambda req, value: value
        return field_mock

    @staticmethod
    def is_process_filters():
        return True


class SoftDeleteControllerMixinTestCase(unittest.TestCase):
    """Test cases for SoftDeleteControllerMixin."""

    def setUp(self):
        super().setUp()
        self.request_mock = mock.Mock()
        self.request_mock.method = "GET"
        self.request_mock.api_context = mock.Mock()
        self.request_mock.api_context.params = {}
        self.request_mock.api_context.params_filters = {}

        class TestController(
            controllers.SoftDeleteControllerMixin,
            controllers.BaseResourceController,
        ):
            __resource__ = FakeResource

        self.controller = TestController(self.request_mock)

    def test_prepare_filter_with_include_deleted(self):
        """Test that include_deleted filter is handled correctly."""
        result = self.controller._prepare_filter("include_deleted", True)
        self.assertEqual(result, ("include_deleted", True))

    def test_prepare_filter_with_normal_field(self):
        """Test that normal filters pass through correctly."""
        result = self.controller._prepare_filter("name", "test")
        self.assertEqual(result, ("name", "test"))

    @mock.patch.object(FakeSoftDeleteModel, "objects")
    def test_get_objects_collection_without_include_deleted(
        self, objects_mock
    ):
        """Test that default collection excludes deleted records."""
        filters = {"name": "test"}
        collection = self.controller._get_objects_collection(filters)

        self.assertEqual(collection, FakeSoftDeleteModel.objects)
        # Filter should not be modified
        self.assertEqual(filters, {"name": "test"})

    @mock.patch.object(FakeSoftDeleteModel, "all_objects")
    def test_get_objects_collection_with_include_deleted(self, all_objects_mock):
        """Test that include_deleted=True uses all_objects collection."""
        filters = {"name": "test", "include_deleted": True}
        collection = self.controller._get_objects_collection(filters)

        self.assertEqual(collection, FakeSoftDeleteModel.all_objects)
        # include_deleted should be removed from filters
        self.assertNotIn("include_deleted", filters)

    @mock.patch.object(FakeSoftDeleteModel, "objects")
    def test_process_storage_filters_excludes_deleted(self, objects_mock):
        """Test that _process_storage_filters uses correct collection."""
        collection_mock = mock.Mock()
        objects_mock.get_all.return_value = collection_mock

        filters = {"name": "test"}
        result = self.controller._process_storage_filters(filters)

        objects_mock.get_all.assert_called_once_with(
            filters=filters, order_by=None
        )
        self.assertEqual(result, collection_mock)

    @mock.patch.object(FakeSoftDeleteModel, "all_objects")
    def test_process_storage_filters_with_include_deleted(
        self, all_objects_mock
    ):
        """Test that _process_storage_filters includes deleted when requested."""
        collection_mock = mock.Mock()
        all_objects_mock.get_all.return_value = collection_mock

        filters = {"name": "test", "include_deleted": True}
        result = self.controller._process_storage_filters(filters)

        all_objects_mock.get_all.assert_called_once_with(
            filters={"name": "test"}, order_by=None
        )
        self.assertEqual(result, collection_mock)
