# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import os
import unittest
import uuid

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage import exceptions as exc
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import migrations
from restalchemy.storage.sql import orm
from restalchemy.tests.functional import consts


INIT_MIGRATION = "9e335f-test-batch-insert-migration"


class BatchInsertModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "batch_insert"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class InsertCase(unittest.TestCase):

    def setUp(self):
        # configure engine factory
        engines.engine_factory.configure_factory(
            db_url=consts.DATABASE_URI)
        self._engine = engines.engine_factory.get_engine()

        # configure database structure, apply migrations
        self._migrations = self._migration_engine()
        self._migrations.rollback_migration(INIT_MIGRATION)
        self._migrations.apply_migration(INIT_MIGRATION)

    def tearDown(self):
        # destroy database structure, rollback migrations
        self._migrations = self._migration_engine()
        self._migrations.rollback_migration(INIT_MIGRATION)

    @staticmethod
    def _migration_engine():
        migrations_path = os.path.dirname(__file__)
        return migrations.MigrationEngine(
            migrations_path=migrations_path)

    def test_correct_batch_insert(self):
        model1 = BatchInsertModel(foo_field1=1, foo_field2="Model1")
        model2 = BatchInsertModel(foo_field1=2, foo_field2="Model2")
        model3 = BatchInsertModel(foo_field1=3, foo_field2="Model3")

        with self._engine.session_manager() as session:
            session.batch_insert([model1, model2, model3])

        all_models = set(BatchInsertModel.objects.get_all())

        self.assertEqual({model1, model2, model3}, all_models)

    def test_duplicate_primary_key_batch_insert(self):
        dup_uuid = uuid.uuid4()
        model1 = BatchInsertModel(uuid=dup_uuid, foo_field1=1,
                                  foo_field2="Model1")
        model2 = BatchInsertModel(foo_field1=2, foo_field2="Model2")
        model3 = BatchInsertModel(uuid=dup_uuid, foo_field1=3,
                                  foo_field2="Model3")

        with self._engine.session_manager() as session:
            with self.assertRaises(exc.ConflictRecords):
                try:
                    session.batch_insert([model1, model2, model3])
                except exc.ConflictRecords as e:
                    # NOTE(efrolov): PRIMARY - is value from table structure,
                    # unique index for any primary key. Constant in database.
                    self.assertEqual("PRIMARY", e.key)
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

        with self._engine.session_manager() as session:
            with self.assertRaises(exc.ConflictRecords):
                try:
                    session.batch_insert([model1, model2, model3])
                except exc.ConflictRecords as e:
                    # NOTE(efrolov): index2 - is value from table structure,
                    # unique index for foo_field1.
                    self.assertEqual("index2", e.key)
                    # NOTE(efrolov): all values from exception in string type
                    self.assertEqual(str(dup_value), e.value)
                    raise

        all_models = BatchInsertModel.objects.get_all()

        self.assertEqual([], all_models)
