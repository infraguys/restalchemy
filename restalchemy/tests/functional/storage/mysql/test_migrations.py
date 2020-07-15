# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2019 Eugene Frolov
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

import logging
import mock
import os
import unittest

from restalchemy.dm import filters
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import migrations
from restalchemy.tests.functional import consts


class MigrationsModelTestCase(unittest.TestCase):
    INIT_MIGRATION = "0d06a9-0000-init"
    FIRST_MIGRATION = "fc0c16-0001-first"

    def setUp(self):
        super(MigrationsModelTestCase, self).setUp()
        engines.engine_factory.configure_factory(consts.DATABASE_URI)
        engine = engines.engine_factory.get_engine()
        self.session = engine.get_session()
        self.migration_engine = self._migration_engine()

        self._drop_ra_migrations_table()
        self.migration_engine.apply_migration(
            migration_name=self.INIT_MIGRATION)

    def tearDown(self):
        super(MigrationsModelTestCase, self).tearDown()
        self._drop_ra_migrations_table()

    def test_instantiate_migration_model(self):
        model_cls = migrations.MigrationModel

        self.assertIsInstance(model_cls(), model_cls)

    @staticmethod
    def _migration_engine():
        migrations_path = os.path.join(
            os.path.dirname(__file__),
            "migrations"
        )
        return migrations.MigrationEngine(
            migrations_path=migrations_path)

    def test_migration_already_applied(self):
        self._truncate_ra_migrations_table()

        self.migration_engine.apply_migration(
            migration_name=self.FIRST_MIGRATION)

        with mock.patch.object(logging.Logger, "warning") as warning:
            self.migration_engine.apply_migration(
                migration_name=self.FIRST_MIGRATION)
            warning.assert_called_with(
                "Migration '%s' is already applied",
                self.FIRST_MIGRATION)

    def test_migration_not_applied(self):
        self._truncate_ra_migrations_table()

        with mock.patch.object(logging.Logger, "warning") as warning:
            self.migration_engine.rollback_migration(
                migration_name=self.FIRST_MIGRATION)
            warning.assert_called_with(
                "Migration '%s' is not applied",
                self.FIRST_MIGRATION)

    def test_migration_in_db_is_correct(self):
        self._truncate_ra_migrations_table()

        self.migration_engine.apply_migration(
            migration_name=self.FIRST_MIGRATION)

        db_migrations = migrations.MigrationModel.objects.get_all()
        self.assertTrue(all([m.applied for m in db_migrations]))
        self.assertEqual(len(db_migrations), 2)

        self.migration_engine.rollback_migration(
            migration_name=self.FIRST_MIGRATION)

        # Only one applied init migration after rollback
        db_filter = {'applied': filters.EQ(True)}
        m = migrations.MigrationModel.objects.get_one(filters=db_filter)
        hash_len = self.migration_engine.FILENAME_HASH_LEN
        self.assertEqual(str(m.uuid)[:hash_len],
                         self.INIT_MIGRATION[:hash_len])

    def _truncate_ra_migrations_table(self):
        # DDL with auto-commit
        self.session.execute("TRUNCATE TABLE `%s`" %
                             migrations.RA_MIGRATION_TABLE_NAME, None)

    def _drop_ra_migrations_table(self):
        self.session.execute("DROP TABLE IF EXISTS `%s`" %
                             migrations.RA_MIGRATION_TABLE_NAME, None)
