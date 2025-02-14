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

from restalchemy.dm import filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import orm
from restalchemy.tests.functional import base


class CountModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "test_count"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class WithDbMigrationsCountTestCase(base.BaseWithDbMigrationsTestCase):

    __LAST_MIGRATION__ = "test-count-migration-502944"
    __FIRST_MIGRATION__ = "test-count-migration-502944"

    def test_count(self):
        target_cnt = 4

        cnt = CountModel.objects.count()

        self.assertEqual(target_cnt, cnt)

    def test_count_filter_single_row(self):
        target_cnt = 1

        cnt = CountModel.objects.count(filters={"foo_field2": "value2"})

        self.assertEqual(target_cnt, cnt)

    def test_count_filter_many_rows(self):
        target_cnt = 2

        cnt = CountModel.objects.count(filters={"foo_field1": filters.GT(2)})

        self.assertEqual(target_cnt, cnt)
