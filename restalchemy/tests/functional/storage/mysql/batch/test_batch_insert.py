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

import uuid

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage import exceptions as exc
from restalchemy.storage.sql import orm
from restalchemy.tests.functional import base


class BatchInsertModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "batch_insert"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class InsertTestCase(base.BaseWithDbMigrationsTestCase):

    __LAST_MIGRATION__ = "test-batch-migration-9e335f"
    __FIRST_MIGRATION__ = "test-batch-migration-9e335f"

    def test_correct_batch_insert(self):
        model1 = BatchInsertModel(foo_field1=1, foo_field2="Model1")
        model2 = BatchInsertModel(foo_field1=2, foo_field2="Model2")
        model3 = BatchInsertModel(foo_field1=3, foo_field2="Model3")

        with self.engine.session_manager() as session:
            session.batch_insert([model1, model2, model3])

        all_models = set(BatchInsertModel.objects.get_all())

        self.assertEqual({model1, model2, model3}, all_models)

    def test_duplicate_primary_key_batch_insert(self):
        dup_uuid = uuid.uuid4()
        model1 = BatchInsertModel(
            uuid=dup_uuid, foo_field1=1, foo_field2="Model1"
        )
        model2 = BatchInsertModel(foo_field1=2, foo_field2="Model2")
        model3 = BatchInsertModel(
            uuid=dup_uuid, foo_field1=3, foo_field2="Model3"
        )
        # NOTE(efrolov): PRIMARY - is value from table structure,
        #   unique index for any primary key. Constant in mysql database.
        key_name = "PRIMARY" if self.engine.dialect.name == "mysql" else "uuid"

        with self.engine.session_manager() as session:
            with self.assertRaises(exc.ConflictRecords):
                try:
                    session.batch_insert([model1, model2, model3])
                except exc.ConflictRecords as e:

                    self.assertEqual(key_name, e.key)
                    # NOTE(efrolov): all values from exception in string type
                    self.assertEqual(str(dup_uuid), e.value)
                    raise

        all_models = BatchInsertModel.objects.get_all()

        self.assertEqual([], all_models)

    def test_duplicate_secondary_key_batch_insert(self):
        dup_value = 2
        model1 = BatchInsertModel(foo_field1=1, foo_field2="Model1")
        model2 = BatchInsertModel(foo_field1=dup_value, foo_field2="Model2")
        model3 = BatchInsertModel(foo_field1=dup_value, foo_field2="Model3")

        with self.engine.session_manager() as session:
            with self.assertRaises(exc.ConflictRecords):
                try:
                    session.batch_insert([model1, model2, model3])
                except exc.ConflictRecords as e:
                    self.assertEqual("foo_field1", e.key)
                    # NOTE(efrolov): all values from exception in string type
                    self.assertEqual(str(dup_value), e.value)
                    raise

        all_models = BatchInsertModel.objects.get_all()

        self.assertEqual([], all_models)
