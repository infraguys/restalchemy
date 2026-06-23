# Copyright 2026 George Melikov
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
import uuid

from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import orm
from restalchemy.tests.functional import base
from restalchemy.tests.functional import consts


class TaggedModel(models.ModelWithUUID, models.ModelWithTags, orm.SQLStorableMixin):
    __tablename__ = "test_tagged"
    name = properties.property(types.String(), default="")


UUID1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
UUID2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
UUID3 = uuid.UUID("00000000-0000-0000-0000-000000000003")
UUID4 = uuid.UUID("00000000-0000-0000-0000-000000000004")


@unittest.skipUnless(
    consts.get_database_uri().startswith("postgresql"),
    "ContainsAll/ContainsAny are PostgreSQL-only operators",
)
class TagsFilterTestCase(base.BaseWithDbMigrationsTestCase):
    __LAST_MIGRATION__ = "test-tags-filter-migration-2d6229"
    __FIRST_MIGRATION__ = "test-tags-filter-migration-2d6229"

    def setUp(self):
        super().setUp()
        TaggedModel(uuid=UUID1, name="prod-eu", tags=["env:prod", "region:eu"]).save()
        TaggedModel(uuid=UUID2, name="prod-us", tags=["env:prod", "region:us"]).save()
        TaggedModel(uuid=UUID3, name="staging", tags=["env:staging"]).save()
        TaggedModel(uuid=UUID4, name="empty", tags=[]).save()

    def _uuids(self, objs):
        return {o.uuid for o in objs}

    def test_contains_all_single_tag(self):
        result = TaggedModel.objects.get_all(
            filters={"tags": dm_filters.ContainsAll(["env:prod"])}
        )
        self.assertEqual(self._uuids(result), {UUID1, UUID2})

    def test_contains_all_multiple_tags(self):
        result = TaggedModel.objects.get_all(
            filters={"tags": dm_filters.ContainsAll(["env:prod", "region:eu"])}
        )
        self.assertEqual(self._uuids(result), {UUID1})

    def test_contains_all_no_match(self):
        result = TaggedModel.objects.get_all(
            filters={"tags": dm_filters.ContainsAll(["nonexistent"])}
        )
        self.assertEqual(result, [])

    def test_contains_all_empty_list_matches_all(self):
        # empty array @> empty array is true for every row
        result = TaggedModel.objects.get_all(
            filters={"tags": dm_filters.ContainsAll([])}
        )
        self.assertEqual(len(result), 4)

    def test_contains_any_single_tag(self):
        result = TaggedModel.objects.get_all(
            filters={"tags": dm_filters.ContainsAny(["env:staging"])}
        )
        self.assertEqual(self._uuids(result), {UUID3})

    def test_contains_any_multiple_tags(self):
        result = TaggedModel.objects.get_all(
            filters={"tags": dm_filters.ContainsAny(["region:eu", "region:us"])}
        )
        self.assertEqual(self._uuids(result), {UUID1, UUID2})

    def test_contains_any_no_match(self):
        result = TaggedModel.objects.get_all(
            filters={"tags": dm_filters.ContainsAny(["nonexistent"])}
        )
        self.assertEqual(result, [])
