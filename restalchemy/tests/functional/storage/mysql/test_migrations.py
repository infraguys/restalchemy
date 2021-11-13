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

import six.moves

from restalchemy.dm import filters
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import migrations as sql_migrations
from restalchemy.tests.functional import consts

INIT_MIGRATION = "0d06a9-0000-init"
FIRST_MIGRATION = "fc0c16-0001-first"
SECOND_MIGRATION = "562b5a-0002-second"
THIRD_MIGRATION = "bbd5d8-0003-third"

HEAD_MIGRATION = THIRD_MIGRATION

NEW_MIGRATION = "0004-fourth"
NEW_MIGRATION_DEPENDS = [HEAD_MIGRATION]

MIGRATIONS_TOTAL_COUNT = len([
    INIT_MIGRATION,
    FIRST_MIGRATION,
    SECOND_MIGRATION,
    THIRD_MIGRATION
])

NONEXISTENT_MIGRATION = "nonexistent_migration"


class BaseMigrationTestCase(unittest.TestCase):

    def setUp(self):
        super(BaseMigrationTestCase, self).setUp()
        engines.engine_factory.configure_factory(consts.DATABASE_URI)
        engine = engines.engine_factory.get_engine()
        self.engine = engine
        self.session = engine.get_session()
        self.migration_engine = self._migration_engine()

        self._drop_ra_migrations_table()

    def tearDown(self):
        super(BaseMigrationTestCase, self).tearDown()
        self._drop_ra_migrations_table()
        self.session.close()
        # Note(efrolov): Must be deleted otherwise we will start collect
        #                connections and get an error "too many connections"
        #                from MySQL
        del self.engine
        engines.engine_factory.destroy_engine()

    @staticmethod
    def _migration_engine(current_dir="migrations"):
        migrations_path = os.path.join(
            os.path.dirname(__file__),
            current_dir
        )
        return sql_migrations.MigrationEngine(
            migrations_path=migrations_path)

    def _truncate_ra_migrations_table(self):
        # DDL with auto-commit
        self.session.execute("TRUNCATE TABLE `%s`" %
                             sql_migrations.RA_MIGRATION_TABLE_NAME, None)

    def _drop_ra_migrations_table(self):
        self.session.execute("DROP TABLE IF EXISTS `%s`" %
                             sql_migrations.RA_MIGRATION_TABLE_NAME, None)

    def load_migrations(self):
        migrations = self.migration_engine._load_migration_controllers(
            self.session)
        return migrations

    def init_migration_table(self):
        self.migration_engine._init_migration_table(self.session)


class MigrationsModelTestCase(BaseMigrationTestCase):

    def test_instantiate_migration_model(self):
        model_cls = sql_migrations.MigrationModel

        self.assertIsInstance(model_cls(), model_cls)

    def test_migration_already_applied(self):

        self.migration_engine.apply_migration(
            migration_name=FIRST_MIGRATION)

        with mock.patch.object(logging.Logger, "warning") as warning:
            self.migration_engine.apply_migration(
                migration_name=FIRST_MIGRATION)
            warning.assert_called_with("Migration '%s' is already applied",
                                       FIRST_MIGRATION)

    def test_migration_not_applied(self):

        with mock.patch.object(logging.Logger, "warning") as warning:
            self.migration_engine.rollback_migration(
                migration_name=FIRST_MIGRATION)
            warning.assert_called_with("Migration '%s' is not applied",
                                       FIRST_MIGRATION)

    def test_migration_in_db_is_correct(self):

        self.migration_engine.apply_migration(
            migration_name=FIRST_MIGRATION)

        db_migrations = sql_migrations.MigrationModel.objects.get_all()
        self.assertTrue(all([m.applied for m in db_migrations]))
        self.assertEqual(len(db_migrations), 2)

        self.migration_engine.rollback_migration(
            migration_name=FIRST_MIGRATION)

        # Only one applied init migration after rollback
        db_filter = {'applied': filters.EQ(True)}
        m = sql_migrations.MigrationModel.objects.get_one(filters=db_filter)
        hash_len = self.migration_engine.FILENAME_HASH_LEN
        self.assertEqual(
            str(m.uuid)[:hash_len],
            INIT_MIGRATION[:hash_len])

    def test_migration_head_is_latest(self):
        expected_uuids = ["0d06a988-90cc-48ab-a842-b979cdf8975d",
                          "fc0c165e-9c69-4e47-b7e3-0bc3a2bebfab",
                          "562b5a12-cb70-4f77-896b-3a6cab7c3019",
                          "bbd5d871-4b0e-4856-b56e-95b2abb7cf48"
                          ]
        self.migration_engine._init_migration_table(
            self.session)
        filter = {'applied': filters.EQ(True)}
        db_migrations = sql_migrations.MigrationModel.objects.get_all(
            filters=filter)
        self.assertEqual(0, len(db_migrations))

        latest_migration_name = self.migration_engine.get_latest_migration()

        self.migration_engine.apply_migration(
            migration_name=latest_migration_name)
        db_migrations = sql_migrations.MigrationModel.objects.get_all(
            filters=filter)
        self.assertEqual(4, len(db_migrations))
        self.assertTrue(str(migration.uuid) in expected_uuids
                        for migration in db_migrations)

    def test_find_head_in_two_migration_sequences(self):
        # test valid migrations
        #
        # migrations dependencies:
        # 0000-init.py <- 0001-first.py
        # 0002-second.py(MANUAL) <- 0003-third.py(MANUAL)
        # Expected last migration: 0001-first.py
        expected_last_migration = "a8a827-0001-first.py"
        custom_migration_engine = self._migration_engine(
            "migration_ok_1")

        last_migration = custom_migration_engine.get_latest_migration()

        self.assertEqual(expected_last_migration, last_migration)

    def test_find_head_in_two_separate_migrations(self):
        # test valid migrations
        #
        # migrations dependencies:
        # 0000-init.py  0001-first.py(MANUAL)
        # Expected last migration: 0000-init.py
        expected_last_migration = "672a1b-0000-init.py"
        custom_migration_engine = self._migration_engine(
            "migration_ok_3")

        last_migration = custom_migration_engine.get_latest_migration()

        self.assertEqual(expected_last_migration, last_migration)

    def test_find_head_in_long_sequence_migrations(self):
        # test valid migrations
        #
        # migrations dependencies:
        #               0000-init.py  0001-first.py(MANUAL)
        # 0004-fourth.py  ^-- 0002-second.py   ^-- 0003-third.py(MANUAL)
        #    ^-- 0005-fifth.py --^        ^-- 0006-sixth.py
        #                ^-- 0007-seventh.py --^
        # Expected last migration: 0007-seventh.py
        expected_last_migration = "7368be-0007-seventh.py"
        custom_migration_engine = self._migration_engine(
            "migration_ok_2")

        last_migration = custom_migration_engine.get_latest_migration()

        self.assertEqual(expected_last_migration, last_migration)

    def test_migrations_with_two_head(self):
        # test invalid migrations
        #
        # migrations dependencies:
        # 0000-init.py <- 0001-first.py   0002-second.py
        # Expected: has two last migrations: 0001-first.py, 0002-second.py
        custom_migration_engine = self._migration_engine(
            "migrations_invalid_two_last_migrations")

        with self.assertRaises(sql_migrations.HeadMigrationNotFoundException):
            custom_migration_engine.get_latest_migration()

    def test_migrations_depends_from_manual(self):
        # test valid migrations
        #
        # migrations dependencies:
        # 0000-init.py <- 0001-first.py
        #                      ^--  0002-second.py --> 0003-third.py(MANUAL)
        # Expected: 0002-second.py
        expected_last_migration = "c9221f-0002-second.py"
        custom_migration_engine = self._migration_engine(
            "migration_ok_4")

        last_migration = custom_migration_engine.get_latest_migration()

        self.assertEqual(expected_last_migration, last_migration)

    def test_not_manual_migration_depends_from_manual(self):
        custom_migration_engine = self._migration_engine(
            "migration_ok_1")
        new_migration_depends = ["11f1da-0003-third.py"]
        fmdm = custom_migration_engine.validate_auto_migration_dependencies

        with mock.patch.object(logging.Logger, "warning") as warning:
            result = fmdm(new_migration_depends)
            warning.assert_called_with(
                "Manual migration(s) is(are) in dependencies!")

        self.assertFalse(result)

    def test_not_manual_migration_depends_from_not_manual(self):
        custom_migration_engine = self._migration_engine(
            "migration_ok_1")
        new_migration_depends = ["a8a827-0001-first.py"]
        fmdm = custom_migration_engine.validate_auto_migration_dependencies

        with mock.patch.object(logging.Logger, "warning") as warning:
            result = fmdm(new_migration_depends)
            warning.assert_not_called()

        self.assertTrue(result)

    def test_get_unapplied_migrations(self):
        custom_migration_engine = self._migration_engine(
            "migration_ok_1")
        expected_result = ["1711de-0000-init.py",
                           "a8a827-0001-first.py"
                           ]

        result = custom_migration_engine.get_unapplied_migrations(
            session=self.session,
            include_manual=False
        )
        result = list(result.keys())
        result.sort(key=lambda x: x.split('-')[1])

        self.assertListEqual(expected_result, result)

    def test_get_unapplied_mixed_migrations(self):
        custom_migration_engine = self._migration_engine(
            "migration_ok_1")
        expected_result = ["a8a827-0001-first.py",
                           "377e90-0002-second.py",
                           "11f1da-0003-third.py"
                           ]
        migration_to_apply = "1711de-0000-init.py"
        custom_migration_engine.apply_migration(
            migration_name=migration_to_apply)

        result = custom_migration_engine.get_unapplied_migrations(
            session=self.session,
            include_manual=True
        )
        result = list(result.keys())
        result.sort(key=lambda x: x.split('-')[1])

        self.assertListEqual(expected_result, result)

    def test_no_unapplied_migrations(self):
        custom_migration_engine = self._migration_engine(
            "migration_ok_1")
        head_migration = "a8a827-0001-first.py"
        custom_migration_engine.apply_migration(migration_name=head_migration)
        expected_result = []

        result = custom_migration_engine.get_unapplied_migrations(
            session=self.session,
            include_manual=False
        )

        self.assertListEqual(expected_result, list(result.keys()))

    def test_get_unapplied_manual_migrations(self):
        custom_migration_engine = self._migration_engine(
            "migration_ok_1")
        head_migration = "a8a827-0001-first.py"
        custom_migration_engine.apply_migration(migration_name=head_migration)
        expected_result = ["377e90-0002-second.py",
                           "11f1da-0003-third.py"
                           ]

        result = custom_migration_engine.get_unapplied_migrations(
            session=self.session,
            include_manual=True
        )
        result = list(result.keys())
        result.sort(key=lambda x: x.split('-')[1])

        self.assertListEqual(expected_result, result)


class MigrationEngineTestCase(BaseMigrationTestCase):

    def test_get_file_name(self):
        file_name = self.migration_engine.get_file_name(FIRST_MIGRATION)

        self.assertEqual("%s.py" % FIRST_MIGRATION, file_name)

    def test_get_file_name_nonexistent(self):

        self.assertRaises(ValueError,
                          self.migration_engine.get_file_name,
                          NONEXISTENT_MIGRATION)

    def test_apply_migration(self):
        self.migration_engine._init_migration_table(self.session)
        migrations_before = self.load_migrations()
        self.session.commit()
        self.migration_engine.apply_migration(HEAD_MIGRATION, dry_run=False)
        migrations_after = self.load_migrations()

        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_before.keys()))
        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_after.keys()))

        # total number of migrations before and after apply should be same
        self.assertEqual(migrations_before.keys(), migrations_after.keys())

        self.assertTrue(all([
            m.is_applied() is False
            for m in migrations_before.values()
        ]))

        self.assertTrue(all([
            m.is_applied() is True
            for m in migrations_after.values()
        ]))

    def test_apply_migration_dry_run(self):
        self.migration_engine._init_migration_table(self.session)
        migrations_before = self.load_migrations()
        self.session.commit()

        self.migration_engine.apply_migration(HEAD_MIGRATION, dry_run=True)
        migrations_after = self.load_migrations()

        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_before.keys()))
        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_after.keys()))

        # total number of migrations before and after apply should be same
        self.assertEqual(migrations_before.keys(), migrations_after.keys())

        self.assertTrue(all([
            m.is_applied() is False
            for m in migrations_before.values()
        ]))

        self.assertTrue(all([
            m.is_applied() is False
            for m in migrations_after.values()
        ]))

    def test_rollback_migration(self):
        self.migration_engine.apply_migration(HEAD_MIGRATION, dry_run=False)
        migrations_before = self.load_migrations()
        self.session.commit()

        self.migration_engine.rollback_migration(INIT_MIGRATION, dry_run=False)
        migrations_after = self.load_migrations()
        self.session.commit()

        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_before.keys()))
        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_after.keys()))

        # total number of migrations before and after rollback should be same
        self.assertEqual(migrations_before.keys(), migrations_after.keys())

        self.assertTrue(all([
            m.is_applied() is True
            for m in migrations_before.values()
        ]))

        self.assertTrue(all([
            m.is_applied() is False
            for m in migrations_after.values()
        ]))

    def test_rollback_migration_dry_run(self):
        self.migration_engine.apply_migration(HEAD_MIGRATION, dry_run=False)
        migrations_before = self.load_migrations()
        self.session.commit()

        self.migration_engine.rollback_migration(INIT_MIGRATION, dry_run=True)
        migrations_after = self.load_migrations()
        self.session.commit()

        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_before.keys()))
        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_after.keys()))

        # total number of migrations before and after rollback should be same
        self.assertEqual(migrations_before.keys(), migrations_after.keys())

        self.assertTrue(all([
            m.is_applied() is True
            for m in migrations_before.values()
        ]))

        self.assertTrue(all([
            m.is_applied() is True
            for m in migrations_after.values()
        ]))

    @mock.patch(
        "%s.open" % six.moves.builtins.__name__,
        new_callable=mock.mock_open())
    def test_create_new_migration(self, file_mock):

        self.migration_engine.new_migration(NEW_MIGRATION_DEPENDS,
                                            NEW_MIGRATION,
                                            dry_run=False)

        self.assertTrue(file_mock.called)

        # two calls - load template, write new migration
        self.assertEqual(2, file_mock.call_count)

        template_path = os.path.join(
            os.path.dirname(sql_migrations.__file__),
            'migration_templ.tmpl'
        )

        template_read_args = file_mock.call_args_list[1][0]
        migration_write_args = file_mock.call_args_list[0][0]

        self.assertEqual((template_path, "r"), template_read_args)

        self.assertEqual("w", migration_write_args[1])
        self.assertTrue(migration_write_args[0].endswith(
            "%s.py" % NEW_MIGRATION
        ))

    @mock.patch(
        "%s.open" % six.moves.builtins.__name__,
        new_callable=mock.mock_open())
    def test_create_new_migration_dry_run(self, file_mock):
        self.migration_engine.new_migration(NEW_MIGRATION_DEPENDS,
                                            NEW_MIGRATION,
                                            dry_run=True)

        self.assertFalse(file_mock.called)
