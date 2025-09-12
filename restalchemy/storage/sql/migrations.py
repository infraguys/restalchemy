# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

import abc
import logging
import os
import re
import sys
import uuid

from restalchemy.common import contexts
from restalchemy.dm import filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage import exceptions
from restalchemy.storage.sql import orm

HEAD_MIGRATION = "HEAD"
MANUAL_MIGRATION = "MANUAL"

RA_MIGRATION_TABLE_NAME = "ra_migrations"
LOG = logging.getLogger(__name__)

DEFAULT_NEW_MIGRATION_NUMBER = "0000"
MIGRATION_NUMBER_LENGTH = len(DEFAULT_NEW_MIGRATION_NUMBER)
OLD_STYLE_NAME_PATTERN = r"[0-9a-z]{6}"
OLD_STYLE = re.compile(OLD_STYLE_NAME_PATTERN)


class HeadMigrationNotFoundException(Exception):
    pass


class DependenciesException(Exception):
    pass


class AbstractMigrationStep(metaclass=abc.ABCMeta):

    @property
    def depends(self):
        return [dep for dep in self._depends if dep]

    @property
    @abc.abstractmethod
    def migration_id(self):
        raise NotImplementedError()

    @property
    def is_manual(self):
        return False

    @property
    def number(self):
        return self._migration_number

    @number.setter
    def number(self, value):
        self._migration_number = value

    @abc.abstractmethod
    def upgrade(self, session):
        raise NotImplementedError()

    @abc.abstractmethod
    def downgrade(self, session):
        raise NotImplementedError()

    @staticmethod
    def _delete_table_if_exists(session, table_name):
        session.execute(
            f"DROP TABLE IF EXISTS {session.engine.escape(table_name)};"
        )

    @staticmethod
    def _delete_trigger_if_exists(session, trigger_name):
        session.execute(
            f"DROP TRIGGER IF EXISTS {session.engine.escape(trigger_name)};"
        )

    @staticmethod
    def _delete_view_if_exists(session, view_name):
        session.execute(
            f"DROP VIEW IF EXISTS {session.engine.escape(view_name)};"
        )


class AbstarctMigrationStep(AbstractMigrationStep):
    """Legacy class with typo in name, please migrate to valid class"""

    pass


class MigrationModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = RA_MIGRATION_TABLE_NAME

    applied = properties.property(
        types.Boolean(), required=True, default=False
    )


class MigrationStepController(object):

    def __init__(self, migration_step, filename, session):
        self._migration_step = migration_step
        self._filename = filename
        migr_uuid = uuid.UUID(self._migration_step.migration_id)
        try:
            self._migration_model = MigrationModel.objects.get_one(
                filters={"uuid": filters.EQ(migr_uuid)}, session=session
            )
        except exceptions.RecordNotFound:
            self._migration_model = MigrationModel(
                uuid=uuid.UUID(self._migration_step.migration_id)
            )

    def is_applied(self):
        return self._migration_model.applied

    def is_manual(self):
        return self._migration_step.is_manual

    def depends_from(self):
        return self._migration_step.depends

    def apply(self, session, migrations, dry_run=False):
        if self.is_applied():
            LOG.warning("Migration '%s' is already applied", self.name)
            return

        LOG.info(
            "Migration '%s' depends on %r",
            self.name,
            self._migration_step.depends,
        )

        for depend in self._migration_step.depends:
            migrations[depend].apply(session, migrations, dry_run=dry_run)

        if dry_run:
            LOG.info("Dry run upgrade for migration '%s'", self.name)
            return

        self._migration_step.upgrade(session)
        self._migration_model.applied = True
        self._migration_model.save(session=session)

    def rollback(self, session, migrations, dry_run=False):
        if not self.is_applied():
            LOG.warning("Migration '%s' is not applied.", self.name)
            return

        for migration in migrations.values():
            if self._filename in migration.depends_from():
                LOG.info(
                    "Migration '%s' dependent %r", self.name, migration.name
                )
                migration.rollback(session, migrations, dry_run=dry_run)

        if dry_run:
            LOG.info("Dry run downgrade for migration '%s'", self.name)
            return

        self._migration_step.downgrade(session)
        self._migration_model.applied = False
        self._migration_model.save(session=session)

    @property
    def name(self):
        return os.path.splitext(os.path.basename(self._filename))[0]


class MigrationEngine(object):
    FILENAME_HASH_LEN = 6

    def __init__(self, migrations_path):
        self._migrations_path = migrations_path

    def get_file_name(self, part_of_name):
        candidates = []
        for filename in os.listdir(self._migrations_path):
            if part_of_name in filename and filename.endswith(".py"):
                candidates.append(filename)

        candidates_count = len(candidates)

        if candidates_count == 1:
            return candidates[0]

        if candidates_count > 1:
            raise ValueError(
                "Multiple file found for name '%s': %s."
                % (part_of_name, candidates)
            )

        raise ValueError(
            "Migration file for dependency %s not found" % part_of_name
        )

    def _calculate_depends(self, depends):
        files = []

        for depend in depends:
            if depend.upper() == HEAD_MIGRATION:
                file_name = self.get_latest_migration()
            else:
                file_name = self.get_file_name(depend)
            files.append(file_name)
        return files

    def _suggest_new_migration_number(self):
        suggestion_number = DEFAULT_NEW_MIGRATION_NUMBER
        migrations = self._load_migrations()
        migration_numbers = set()
        for migration in migrations:
            parts = migration.split("-")
            if len(parts) > 1:
                number_part = parts[0].rstrip(".py")
                if OLD_STYLE.match(number_part):
                    number_part = parts[1].rstrip("py")
                if number_part.isdigit():
                    migration_numbers.add(number_part)

        if not migration_numbers:
            return suggestion_number

        max_number = int(max(migration_numbers, key=int))
        max_len = len(max(migration_numbers, key=len))

        suggestion_number = str(max_number + 1).zfill(max_len)
        return suggestion_number

    def new_migration(self, depends, message, dry_run=False, is_manual=False):
        files = self._calculate_depends(depends)
        depends = '"{}"'.format('", "'.join(files)) if files else ""

        migration_id = str(uuid.uuid4())
        filename_hash = migration_id[: self.FILENAME_HASH_LEN]
        migration_number = (
            MANUAL_MIGRATION
            if is_manual
            else self._suggest_new_migration_number()
        )
        message = message.replace(" ", "-")

        first_part_of_message = message.split("-")[0]

        if (
            first_part_of_message.isdigit()
            and len(first_part_of_message) == MIGRATION_NUMBER_LENGTH
        ):
            migration_number = first_part_of_message
            message = message.lstrip(first_part_of_message + "-")

        mfilename = (
            "-".join([migration_number, message, filename_hash]) + ".py"
        )

        mpath = os.path.join(self._migrations_path, mfilename)

        if dry_run:
            LOG.info(
                "Dry run create migration '%s'. File: %s, path: %s",
                message,
                mfilename,
                mpath,
            )
            return

        with open(mpath, "w") as fp_output:
            template_path = os.path.join(
                os.path.dirname(__file__), "migration_templ.tmpl"
            )
            with open(template_path, "r") as fp_input:
                fp_output.write(
                    fp_input.read()
                    % {
                        "migration_id": migration_id,
                        "depends": depends,
                        "is_manual": is_manual,
                    }
                )

        LOG.info("New migration '%s' has been created: %s", mfilename, mpath)

    @staticmethod
    def _init_migration_table(session):
        statement = f"""CREATE TABLE IF NOT EXISTS {RA_MIGRATION_TABLE_NAME} (
            uuid CHAR(36) NOT NULL PRIMARY KEY,
            applied BOOLEAN NOT NULL
        )"""
        session.execute(statement, None)

    def _load_migrations(self):
        migrations = {}
        sys.path.insert(0, self._migrations_path)
        try:
            for filename in os.listdir(self._migrations_path):
                if filename.endswith(".py"):
                    migration = __import__(filename[:-3])
                    if not hasattr(migration, "migration_step"):
                        continue
                    migrations[filename] = migration.migration_step
            return migrations
        finally:
            sys.path.remove(self._migrations_path)

    def _load_migration_controllers(self, session):
        return {
            filename: MigrationStepController(
                migration_step=step,
                filename=filename,
                session=session,
            )
            for filename, step in self._load_migrations().items()
        }

    def apply_migration(self, migration_name, dry_run=False):
        filename = self.get_file_name(migration_name)
        with contexts.Context().session_manager() as session:
            self._init_migration_table(session)
            migrations = self._load_migration_controllers(session)

            migration = migrations[filename]
            if migration.is_applied():
                LOG.warning(
                    "Migration '%s' is already applied", migration.name
                )
            else:
                LOG.info("Applying migration '%s'", migration.name)
                migrations[filename].apply(
                    session, migrations, dry_run=dry_run
                )

    def rollback_migration(self, migration_name, dry_run=False):
        filename = self.get_file_name(migration_name)
        with contexts.Context().session_manager() as session:
            self._init_migration_table(session)
            migrations = self._load_migration_controllers(session)
            migration = migrations[filename]
            if not migration.is_applied():
                LOG.warning("Migration '%s' is not applied", migration.name)
            else:
                LOG.info("Rolling back migration '%s'", migration.name)
                migrations[filename].rollback(
                    session, migrations, dry_run=dry_run
                )

    def _calculate_indexes(self):
        indexed_migrations = []
        migrations = self._load_migrations()
        current_migration = self.get_latest_migration()

        indexed_migrations.append(current_migration)

        while True:
            if not migrations[current_migration].depends:
                break
            for d in migrations[current_migration].depends:
                indexed_migrations.append(d)
                current_migration = d

        indexed_migrations.reverse()

        for index, filename in enumerate(indexed_migrations):
            migrations[filename].number = index
        return migrations

    def get_all_migrations(self):
        return {
            filename: {
                "is_manual": m.is_manual,
                "depends": m.depends,
                "uuid": m.migration_id,
                "index": m.number if hasattr(m, "number") else 0,
            }
            for filename, m in self._calculate_indexes().items()
        }

    def get_latest_migration(self):
        migrations = {
            filename: m
            for filename, m in self._load_migrations().items()
            if m.is_manual is False
        }

        for migration in list(migrations.values()):
            for depend in migration._depends:
                if depend in migrations:
                    migrations.pop(depend, None)
        if len(migrations) == 1:
            return migrations.popitem()[0]

        raise HeadMigrationNotFoundException(
            "Head migration for current migrations couldn't be found"
        )

    def validate_auto_migration_dependencies(self, depends):
        depends = self._calculate_depends(depends)

        migrations = self._load_migrations()

        for filename in depends:
            if migrations[filename].is_manual:
                LOG.warning("Manual migration(s) is(are) in dependencies!")
                return False
        return True

    def get_unapplied_migrations(self, session, include_manual=False):
        self._init_migration_table(session)
        migrations = self._load_migration_controllers(session)

        filtered_migrations = {}
        for filename, migration in migrations.items():
            if migration.is_applied() is False:
                if migration.is_manual() is False or include_manual is True:
                    filtered_migrations[filename] = migration
        return filtered_migrations
