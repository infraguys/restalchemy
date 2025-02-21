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
import os

import mock

from restalchemy.dm import filters
from restalchemy.storage.sql import migrations as sql_migrations
from restalchemy.tests.functional import base

INIT_MIGRATION = "0000-init-0d06a9"
FIRST_MIGRATION = "0001-first-fc0c16"
SECOND_MIGRATION = "0002-second-562b5a"
THIRD_MIGRATION = "0003-third-bbd5d8"

HEAD_MIGRATION = THIRD_MIGRATION

NEW_MIGRATION_NUMBER = "0004"
NEW_MIGRATION_MESSAGE = "fourth"
NEW_MIGRATION_DEPENDS = [HEAD_MIGRATION]

MIGRATIONS_TOTAL_COUNT = len(
    [INIT_MIGRATION, FIRST_MIGRATION, SECOND_MIGRATION, THIRD_MIGRATION]
)

MIGRATIONS_FIXTURES_DIR_NAME = "migrations_fixtures"
NONEXISTENT_MIGRATION = "nonexistent_migration"


def ensure_py_extension(filename):
    py_extension = ".py"
    if filename.endswith(py_extension):
        return filename
    return filename + py_extension


def get_filename_hash(filename):
    _, file = os.path.split(filename)
    return file.split("-")[-1].split(".")[0]


def test_get_filename_hash():
    testpath = "/very/long/path/with/file/0000-message-0d6a9.py"
    shortpath = "./0000-message-0d6a9.py"
    onlyname = "0000-message-0d6a9.py"
    longfilename = "0000-very-very-long-message-0d6a9.py"
    wrongname = "0d6a9-0000-message.py"

    expected_hash = "0d6a9"

    assert get_filename_hash(testpath) == expected_hash
    assert get_filename_hash(shortpath) == expected_hash
    assert get_filename_hash(onlyname) == expected_hash
    assert get_filename_hash(longfilename) == expected_hash
    assert get_filename_hash(wrongname) != expected_hash


class BaseMigrationTestCase(base.BaseDBEngineTestCase):

    def setUp(self):
        super(BaseMigrationTestCase, self).setUp()

        self.migration_engine = self.get_migration_engine()

        self._drop_ra_migrations_table()

    def tearDown(self):
        super(BaseMigrationTestCase, self).tearDown()

        self._drop_ra_migrations_table()

    @staticmethod
    def get_migration_engine(migrations_dir_name="migrations"):
        migrations_path = os.path.join(
            os.path.dirname(__file__),
            MIGRATIONS_FIXTURES_DIR_NAME,
            migrations_dir_name,
        )
        migration_engine = sql_migrations.MigrationEngine(
            migrations_path=migrations_path
        )
        return migration_engine

    def _truncate_ra_migrations_table(self):
        with self.engine.session_manager() as session:
            self.truncate_table(
                sql_migrations.RA_MIGRATION_TABLE_NAME, session=session
            )

    def _drop_ra_migrations_table(self):
        with self.engine.session_manager() as session:
            self.drop_table(
                sql_migrations.RA_MIGRATION_TABLE_NAME, session=session
            )

    def load_migrations(self):
        with self.engine.session_manager() as session:
            migrations = self.migration_engine._load_migration_controllers(
                session
            )
        return migrations

    def init_migration_table(self):
        with self.engine.session_manager() as session:
            self.migration_engine._init_migration_table(session)


class MigrationsModelTestCase(BaseMigrationTestCase):

    def test_instantiate_migration_model(self):
        model_cls = sql_migrations.MigrationModel

        self.assertIsInstance(model_cls(), model_cls)

    def test_migration_already_applied(self):

        self.migration_engine.apply_migration(migration_name=FIRST_MIGRATION)

        with mock.patch.object(logging.Logger, "warning") as warning:
            self.migration_engine.apply_migration(
                migration_name=FIRST_MIGRATION
            )
            warning.assert_called_with(
                "Migration '%s' is already applied", FIRST_MIGRATION
            )

    def test_migration_not_applied(self):

        with mock.patch.object(logging.Logger, "warning") as warning:
            self.migration_engine.rollback_migration(
                migration_name=FIRST_MIGRATION
            )
            warning.assert_called_with(
                "Migration '%s' is not applied", FIRST_MIGRATION
            )

    def test_migration_in_db_is_correct(self):

        self.migration_engine.apply_migration(migration_name=FIRST_MIGRATION)

        db_migrations = sql_migrations.MigrationModel.objects.get_all()
        self.assertTrue(all([m.applied for m in db_migrations]))
        self.assertEqual(len(db_migrations), 2)

        self.migration_engine.rollback_migration(
            migration_name=FIRST_MIGRATION
        )

        # Only one applied init migration after rollback
        db_filter = {"applied": filters.EQ(True)}
        m = sql_migrations.MigrationModel.objects.get_one(filters=db_filter)
        hash_len = self.migration_engine.FILENAME_HASH_LEN
        self.assertEqual(str(m.uuid)[:hash_len], INIT_MIGRATION[-hash_len:])

    def test_migration_head_is_latest(self):
        expected_uuids = [
            "0d06a988-90cc-48ab-a842-b979cdf8975d",
            "fc0c165e-9c69-4e47-b7e3-0bc3a2bebfab",
            "562b5a12-cb70-4f77-896b-3a6cab7c3019",
            "bbd5d871-4b0e-4856-b56e-95b2abb7cf48",
        ]
        with self.engine.session_manager() as session:
            self.migration_engine._init_migration_table(session)

        db_filter = {"applied": filters.EQ(True)}
        db_migrations = sql_migrations.MigrationModel.objects.get_all(
            filters=db_filter
        )
        self.assertEqual(0, len(db_migrations))

        latest_migration_name = self.migration_engine.get_latest_migration()

        self.migration_engine.apply_migration(
            migration_name=latest_migration_name
        )
        db_migrations = sql_migrations.MigrationModel.objects.get_all(
            filters=db_filter
        )
        self.assertEqual(4, len(db_migrations))
        self.assertTrue(
            str(migration.uuid) in expected_uuids
            for migration in db_migrations
        )

    def test_find_head_in_two_migration_sequences(self):
        # test valid migrations
        #
        # migrations dependencies:
        # 0000-init.py <- 0001-first.py
        # 0002-second.py(MANUAL) <- 0003-third.py(MANUAL)
        # Expected last migration: 0001-first.py
        expected_last_migration = "0001-first-a8a827.py"
        custom_migration_engine = self.get_migration_engine("migration_ok_1")

        last_migration = custom_migration_engine.get_latest_migration()

        self.assertEqual(expected_last_migration, last_migration)

    def test_find_head_in_two_separate_migrations(self):
        # test valid migrations
        #
        # migrations dependencies:
        # 0000-init.py  0001-first.py(MANUAL)
        # Expected last migration: 0000-init.py
        expected_last_migration = "0000-init-672a1b.py"
        custom_migration_engine = self.get_migration_engine("migration_ok_3")

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
        expected_last_migration = "0007-seventh-7368be.py"
        custom_migration_engine = self.get_migration_engine("migration_ok_2")

        last_migration = custom_migration_engine.get_latest_migration()

        self.assertEqual(expected_last_migration, last_migration)

    def test_migrations_with_two_head(self):
        # test invalid migrations
        #
        # migrations dependencies:
        # 0000-init.py <- 0001-first.py   0002-second.py
        # Expected: has two last migrations: 0001-first.py, 0002-second.py
        custom_migration_engine = self.get_migration_engine(
            "migrations_invalid_two_last_migrations"
        )

        with self.assertRaises(sql_migrations.HeadMigrationNotFoundException):
            custom_migration_engine.get_latest_migration()

    def test_migrations_depends_from_manual(self):
        # test valid migrations
        #
        # migrations dependencies:
        # 0000-init.py <- 0001-first.py
        #                      ^--  0002-second.py --> 0003-third.py(MANUAL)
        # Expected: 0002-second.py
        expected_last_migration = "0002-second-c9221f.py"
        custom_migration_engine = self.get_migration_engine("migration_ok_4")

        last_migration = custom_migration_engine.get_latest_migration()

        self.assertEqual(expected_last_migration, last_migration)

    def test_not_manual_migration_depends_from_manual(self):
        custom_migration_engine = self.get_migration_engine("migration_ok_1")
        new_migration_depends = ["0003-third-11f1da.py"]
        fmdm = custom_migration_engine.validate_auto_migration_dependencies

        with mock.patch.object(logging.Logger, "warning") as warning:
            result = fmdm(new_migration_depends)
            warning.assert_called_with(
                "Manual migration(s) is(are) in dependencies!"
            )

        self.assertFalse(result)

    def test_not_manual_migration_depends_from_not_manual(self):
        custom_migration_engine = self.get_migration_engine("migration_ok_1")
        new_migration_depends = ["0001-first-a8a827.py"]
        fmdm = custom_migration_engine.validate_auto_migration_dependencies

        with mock.patch.object(logging.Logger, "warning") as warning:
            result = fmdm(new_migration_depends)
            warning.assert_not_called()

        self.assertTrue(result)

    def test_get_unapplied_migrations(self):
        custom_migration_engine = self.get_migration_engine("migration_ok_1")
        expected_result = ["0000-init-1711de.py", "0001-first-a8a827.py"]

        with self.engine.session_manager() as session:
            result = custom_migration_engine.get_unapplied_migrations(
                session=session, include_manual=False
            )
        result = list(result.keys())
        result.sort(key=lambda x: x.split("-")[0])

        self.assertListEqual(expected_result, result)

    def test_get_unapplied_mixed_migrations(self):
        custom_migration_engine = self.get_migration_engine("migration_ok_1")
        expected_result = [
            "0001-first-a8a827.py",
            "0002-second-377e90.py",
            "0003-third-11f1da.py",
        ]
        migration_to_apply = "0000-init-1711de.py"
        custom_migration_engine.apply_migration(
            migration_name=migration_to_apply
        )

        with self.engine.session_manager() as session:
            result = custom_migration_engine.get_unapplied_migrations(
                session=session, include_manual=True
            )
        result = list(result.keys())
        result.sort(key=lambda x: x.split("-")[1])

        self.assertListEqual(expected_result, result)

    def test_no_unapplied_migrations(self):
        custom_migration_engine = self.get_migration_engine("migration_ok_1")
        head_migration = "0001-first-a8a827.py"
        custom_migration_engine.apply_migration(migration_name=head_migration)
        expected_result = []

        with self.engine.session_manager() as session:
            result = custom_migration_engine.get_unapplied_migrations(
                session=session, include_manual=False
            )

        self.assertListEqual(expected_result, list(result.keys()))

    def test_get_unapplied_manual_migrations(self):
        custom_migration_engine = self.get_migration_engine("migration_ok_1")
        head_migration = "0001-first-a8a827.py"
        custom_migration_engine.apply_migration(migration_name=head_migration)
        expected_result = ["0002-second-377e90.py", "0003-third-11f1da.py"]

        with self.engine.session_manager() as session:
            result = custom_migration_engine.get_unapplied_migrations(
                session=session, include_manual=True
            )
        result = list(result.keys())
        result.sort(key=lambda x: x.split("-")[1])

        self.assertListEqual(expected_result, result)


class MigrationEngineTestCase(BaseMigrationTestCase):

    def test_get_file_name(self):
        file_name = self.migration_engine.get_file_name(FIRST_MIGRATION)

        self.assertEqual("%s.py" % FIRST_MIGRATION, file_name)

    def test_get_file_name_ambiguous_name(self):
        ambiguous_name = "0"

        self.assertRaises(
            ValueError, self.migration_engine.get_file_name, ambiguous_name
        )

    def test_get_file_name_nonexistent(self):

        self.assertRaises(
            ValueError,
            self.migration_engine.get_file_name,
            NONEXISTENT_MIGRATION,
        )

    def test__calculate_depends_head(self):
        depends = [sql_migrations.HEAD_MIGRATION]
        files = self.migration_engine._calculate_depends(depends)
        expected_files = list(
            map(
                ensure_py_extension,
                [
                    HEAD_MIGRATION,
                ],
            )
        )

        self.assertListEqual(expected_files, files)

    def test__calculate_depends_multiple(self):
        depends = [FIRST_MIGRATION, SECOND_MIGRATION]
        files = self.migration_engine._calculate_depends(depends)
        expected_files = list(
            map(
                ensure_py_extension,
                [
                    FIRST_MIGRATION,
                    SECOND_MIGRATION,
                ],
            )
        )

        self.assertListEqual(expected_files, files)

    def test_apply_migration(self):
        with self.engine.session_manager() as session:
            self.migration_engine._init_migration_table(session)
        migrations_before = self.load_migrations()
        self.migration_engine.apply_migration(HEAD_MIGRATION, dry_run=False)
        migrations_after = self.load_migrations()

        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_before.keys()))
        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_after.keys()))

        # total number of migrations before and after apply should be same
        self.assertEqual(migrations_before.keys(), migrations_after.keys())

        self.assertTrue(
            all([m.is_applied() is False for m in migrations_before.values()])
        )

        self.assertTrue(
            all([m.is_applied() is True for m in migrations_after.values()])
        )

    def test_apply_migration_dry_run(self):
        with self.engine.session_manager() as session:
            self.migration_engine._init_migration_table(session)
        migrations_before = self.load_migrations()

        self.migration_engine.apply_migration(HEAD_MIGRATION, dry_run=True)
        migrations_after = self.load_migrations()

        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_before.keys()))
        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_after.keys()))

        # total number of migrations before and after apply should be same
        self.assertEqual(migrations_before.keys(), migrations_after.keys())

        self.assertTrue(
            all([m.is_applied() is False for m in migrations_before.values()])
        )

        self.assertTrue(
            all([m.is_applied() is False for m in migrations_after.values()])
        )

    def test_rollback_migration(self):
        self.migration_engine.apply_migration(HEAD_MIGRATION, dry_run=False)
        migrations_before = self.load_migrations()

        self.migration_engine.rollback_migration(INIT_MIGRATION, dry_run=False)
        migrations_after = self.load_migrations()

        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_before.keys()))
        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_after.keys()))

        # total number of migrations before and after rollback should be same
        self.assertEqual(migrations_before.keys(), migrations_after.keys())

        self.assertTrue(
            all([m.is_applied() is True for m in migrations_before.values()])
        )

        self.assertTrue(
            all([m.is_applied() is False for m in migrations_after.values()])
        )

    def test_rollback_migration_dry_run(self):
        self.migration_engine.apply_migration(HEAD_MIGRATION, dry_run=False)
        migrations_before = self.load_migrations()

        self.migration_engine.rollback_migration(INIT_MIGRATION, dry_run=True)
        migrations_after = self.load_migrations()

        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_before.keys()))
        self.assertEqual(MIGRATIONS_TOTAL_COUNT, len(migrations_after.keys()))

        # total number of migrations before and after rollback should be same
        self.assertEqual(migrations_before.keys(), migrations_after.keys())

        self.assertTrue(
            all([m.is_applied() is True for m in migrations_before.values()])
        )

        self.assertTrue(
            all([m.is_applied() is True for m in migrations_after.values()])
        )

    @mock.patch("builtins.open", new_callable=mock.mock_open())
    def test_create_new_migration(self, file_mock):

        self.migration_engine.new_migration(
            NEW_MIGRATION_DEPENDS, NEW_MIGRATION_MESSAGE, dry_run=False
        )

        self.assertTrue(file_mock.called)

        # two calls - load template, write new migration
        self.assertEqual(2, file_mock.call_count)

        template_path = os.path.join(
            os.path.dirname(sql_migrations.__file__), "migration_templ.tmpl"
        )

        template_read_args = file_mock.call_args_list[1][0]
        migration_write_args = file_mock.call_args_list[0][0]

        self.assertEqual((template_path, "r"), template_read_args)

        self.assertEqual("w", migration_write_args[1])

        self.assertTrue(
            migration_write_args[0].endswith(
                "%s-%s-%s.py"
                % (
                    NEW_MIGRATION_NUMBER,
                    NEW_MIGRATION_MESSAGE,
                    get_filename_hash(migration_write_args[0]),
                )
            )
        )

    @mock.patch("builtins.open", new_callable=mock.mock_open())
    def test_create_new_migration_manual(self, file_mock):

        self.migration_engine.new_migration(
            NEW_MIGRATION_DEPENDS,
            NEW_MIGRATION_MESSAGE,
            dry_run=False,
            is_manual=True,
        )

        self.assertTrue(file_mock.called)

        # two calls - load template, write new migration
        self.assertEqual(2, file_mock.call_count)

        template_path = os.path.join(
            os.path.dirname(sql_migrations.__file__), "migration_templ.tmpl"
        )

        template_read_args = file_mock.call_args_list[1][0]
        migration_write_args = file_mock.call_args_list[0][0]

        self.assertEqual((template_path, "r"), template_read_args)

        self.assertEqual("w", migration_write_args[1])

        self.assertTrue(
            migration_write_args[0].endswith(
                "%s-%s-%s.py"
                % (
                    sql_migrations.MANUAL_MIGRATION,
                    NEW_MIGRATION_MESSAGE,
                    get_filename_hash(migration_write_args[0]),
                )
            )
        )

    @mock.patch("builtins.open", new_callable=mock.mock_open())
    def test_create_new_migration_dry_run(self, file_mock):
        self.migration_engine.new_migration(
            NEW_MIGRATION_DEPENDS, NEW_MIGRATION_MESSAGE, dry_run=True
        )

        self.assertFalse(file_mock.called)
