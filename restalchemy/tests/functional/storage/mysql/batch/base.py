# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2019 Eugene Frolov.
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

from restalchemy.storage.sql import engines
from restalchemy.storage.sql import migrations
from restalchemy.tests.functional import consts


INIT_MIGRATION = "9e335f-test-batch-migration"


class BaseBatchTestCase(unittest.TestCase):

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
