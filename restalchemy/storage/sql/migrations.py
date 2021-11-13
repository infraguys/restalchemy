# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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
import six
import sys
import uuid

from restalchemy.dm import filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage import exceptions
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm
from restalchemy.storage.sql import sessions


RA_MIGRATION_TABLE_NAME = "ra_migrations"
LOG = logging.getLogger(__name__)


class HeadMigrationNotFoundException(Exception):
    pass


class DependenciesException(Exception):
    pass


@six.add_metaclass(abc.ABCMeta)
class AbstarctMigrationStep(object):

    @property
    def depends(self):
        return [dep for dep in self._depends if dep]

    @abc.abstractproperty
    def migration_id(self):
        raise NotImplementedError()

    @property
    def is_manual(self):
        return False

    @abc.abstractmethod
    def upgrade(self, session):
        raise NotImplementedError()

    @abc.abstractmethod
    def downgrade(self, session):
        raise NotImplementedError()

    @staticmethod
    def _delete_table_if_exists(session, table_name):
        session.execute("DROP TABLE IF EXISTS `%s`;" % table_name, None)

    @staticmethod
    def _delete_trigger_if_exists(session, trigger_name):
        session.execute("DROP TRIGGER IF EXISTS `%s`;" % trigger_name, None)

    @staticmethod
    def _delete_view_if_exists(session, view_name):
        session.execute("DROP VIEW IF EXISTS `%s`;" % view_name, None)


class MigrationModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = RA_MIGRATION_TABLE_NAME

    applied = properties.property(types.Boolean(), required=True,
                                  default=False)


class MigrationStepController(object):

    def __init__(self, migration_step, filename, session):
        self._migration_step = migration_step
        self._filename = filename
        migr_uuid = uuid.UUID(self._migration_step.migration_id)
        try:
            self._migration_model = MigrationModel.objects.get_one(
                filters={"uuid": filters.EQ(migr_uuid)},
                session=session)
        except exceptions.RecordNotFound:
            self._migration_model = MigrationModel(
                uuid=uuid.UUID(self._migration_step.migration_id))

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

        LOG.info("Migration '%s' depends on %r",
                 self.name,
                 self._migration_step.depends)

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
                LOG.info("Migration '%s' dependent %r",
                         self.name, migration.name)
                migration.rollback(session, migrations, dry_run=dry_run)

        if dry_run:
            LOG.info("Dry run downgrade for migration '%s'", self.name)
            return

        self._migration_step.downgrade(session)
        self._migration_model.applied = False
        self._migration_model.save(session=session)

    @property
    def name(self):
        return os.path.splitext(
            os.path.basename(self._filename)
        )[0]


class MigrationEngine(object):
    FILENAME_HASH_LEN = 6

    def __init__(self, migrations_path):
        self._migrations_path = migrations_path

    def get_file_name(self, part_of_name):
        for filename in os.listdir(self._migrations_path):
            if part_of_name in filename and filename.endswith('.py'):
                return filename
        raise ValueError("Migration file for dependency %s not found" %
                         part_of_name)

    def _calculate_depends(self, depends):
        files = []

        for depend in depends:
            files.append(self.get_file_name(depend))
        return files

    def new_migration(self, depends, message, dry_run=False, is_manual=False):
        files = self._calculate_depends(depends)
        depends = '", "'.join(files)
        migration_id = str(uuid.uuid4())
        mfilename = "%s-%s.py" % (migration_id[:self.FILENAME_HASH_LEN],
                                  message.replace(" ", "-"))
        mpath = os.path.join(self._migrations_path, mfilename)

        if dry_run:
            LOG.info("Dry run create migration '%s'. File: %s, path: %s",
                     message, mfilename, mpath)
            return

        with open(mpath, "w") as fp_output:
            template_path = os.path.join(os.path.dirname(__file__),
                                         'migration_templ.tmpl')
            with open(template_path, "r") as fp_input:
                fp_output.write(fp_input.read() % {
                    "migration_id": migration_id,
                    "depends": depends,
                    "is_manual": is_manual
                })

    @staticmethod
    def _init_migration_table(session):
        statement = ("""CREATE TABLE IF NOT EXISTS %s (
            uuid CHAR(36) NOT NULL,
            applied BIT(1) NOT NULL,
            PRIMARY KEY (uuid)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
        """) % RA_MIGRATION_TABLE_NAME
        session.execute(statement, None)

    def _load_migrations(self):
        migrations = {}
        sys.path.insert(0, self._migrations_path)
        try:
            for filename in os.listdir(self._migrations_path):
                if filename.endswith('.py'):
                    migration = __import__(filename[:-3])
                    if not hasattr(migration, 'migration_step'):
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
            ) for filename, step in self._load_migrations().items()
        }

    def apply_migration(self, migration_name, dry_run=False):
        engine = engines.engine_factory.get_engine()

        filename = self.get_file_name(migration_name)
        with sessions.session_manager(engine=engine) as session:
            self._init_migration_table(session)
            migrations = self._load_migration_controllers(session)

            migration = migrations[filename]
            if migration.is_applied():
                LOG.warning("Migration '%s' is already applied",
                            migration.name)
            else:
                LOG.info("Applying migration '%s'", migration.name)
                migrations[filename].apply(session, migrations,
                                           dry_run=dry_run)

    def rollback_migration(self, migration_name, dry_run=False):
        engine = engines.engine_factory.get_engine()
        filename = self.get_file_name(migration_name)
        with sessions.session_manager(engine=engine) as session:
            self._init_migration_table(session)
            migrations = self._load_migration_controllers(session)
            migration = migrations[filename]
            if not migration.is_applied():
                LOG.warning("Migration '%s' is not applied",
                            migration.name)
            else:
                LOG.info("Rolling back migration '%s'", migration.name)
                migrations[filename].rollback(session, migrations,
                                              dry_run=dry_run)

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

        raise HeadMigrationNotFoundException("Head migration for "
              "current migrations couldnt be found")

    def validate_auto_migration_dependencies(self, depends):
        depends = self._calculate_depends(depends)

        migrations = self._load_migrations()

        for filename in depends:
            if migrations[filename].is_manual:
                LOG.warning(
                    "Manual migration(s) is(are) in dependencies!")
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
