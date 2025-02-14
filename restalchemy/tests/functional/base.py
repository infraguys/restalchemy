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

from restalchemy.storage.sql import migrations
from restalchemy.tests.functional import db_utils

INIT_MIGRATION = "9e335f-test-batch-migration"


class BaseFunctionalTestCase(unittest.TestCase):
    """All other functional tests should inherit from it."""

    pass


class BaseDBEngineTestCase(db_utils.DBEngineMixin, BaseFunctionalTestCase):
    """Base recommended class to inherit from for all db-related tests"""

    @classmethod
    def setUpClass(cls):
        super(BaseDBEngineTestCase, cls).setUpClass()

        cls.init_engine()

    @classmethod
    def tearDownClass(cls):
        super(BaseDBEngineTestCase, cls).tearDownClass()

        cls.drop_all_tables()
        cls.destroy_engine()


class BaseWithDbMigrationsTestCase(BaseDBEngineTestCase):

    __LAST_MIGRATION__ = None
    __FIRST_MIGRATION__ = None

    def setUp(self):
        super(BaseWithDbMigrationsTestCase, self).setUp()

        # configure database structure, apply migrations
        self._migrations = self.get_migration_engine()
        self._migrations.rollback_migration(self.__FIRST_MIGRATION__)
        self._migrations.apply_migration(self.__LAST_MIGRATION__)

    def tearDown(self):
        super(BaseWithDbMigrationsTestCase, self).tearDown()

        # destroy database structure, rollback migrations
        self._migrations = self.get_migration_engine()
        self._migrations.rollback_migration(self.__FIRST_MIGRATION__)

    @staticmethod
    def get_migration_engine():
        migrations_path = os.path.dirname(__file__) + "/migrations/"
        migration_engine = migrations.MigrationEngine(
            migrations_path=migrations_path
        )
        return migration_engine
