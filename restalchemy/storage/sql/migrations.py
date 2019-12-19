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
import os
import sys
import uuid

import six


from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage import exceptions
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm
from restalchemy.storage.sql import sessions


RA_MIGRATION_TABLE_NAME = "ra_migrations"


@six.add_metaclass(abc.ABCMeta)
class AbstarctMigrationStep(object):

    @property
    def depends(self):
        return [dep for dep in self._depends if dep]

    @abc.abstractproperty
    def migration_id(self):
        raise NotImplementedError()

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
        try:
            self._migration_model = MigrationModel.objects.get_one(
                filters={"uuid": uuid.UUID(self._migration_step.migration_id)},
                session=session)
        except exceptions.RecordNotFound:
            self._migration_model = MigrationModel(
                uuid=uuid.UUID(self._migration_step.migration_id))

    def is_applied(self):
        return self._migration_model.applied

    def depends_from(self):
        return self._migration_step.depends

    def apply(self, session, migrations):
        if self.is_applied():
            return
        for depend in self._migration_step.depends:
            migrations[depend].apply(session, migrations)
        self._migration_step.upgrade(session)
        self._migration_model.applied = True
        self._migration_model.save(session=session)

    def rollback(self, session, migrations):
        if not self.is_applied():
            return
        for migration in migrations.values():
            if self._filename in migration.depends_from():
                migration.rollback(session, migrations)
        self._migration_step.downgrade(session)
        self._migration_model.applied = False
        self._migration_model.save(session=session)


class MigrationEngine(object):

    def __init__(self, migrations_path):
        self._migrations_path = migrations_path

    def get_file_name(self, part_of_name):
        for filename in os.listdir(self._migrations_path):
            if (part_of_name in filename and filename.endswith('.py')):
                return filename
        raise ValueError("Migration file for dependensy %s not found" %
                         part_of_name)

    def _calculate_depends(self, depends):
        files = []

        for depend in depends:
            files.append(self.get_file_name(depend))
        return '", "'.join(files)

    def new_migration(self, depends, message):
        depends = self._calculate_depends(depends)
        migration_id = str(uuid.uuid4())
        mfilename = "%s-%s.py" % (migration_id[:6], message.replace(" ", "-"))
        mpath = os.path.join(self._migrations_path, mfilename)
        with open(mpath, "w") as fp_output:
            template_path = os.path.join(os.path.dirname(__file__),
                                         'migration_templ.py')
            with open(template_path, "r") as fp_input:
                fp_output.write(fp_input.read() % {
                    "migration_id": migration_id,
                    "depends": depends
                })

    def _init_migration_table(self, session):
        statement = ("""CREATE TABLE IF NOT EXISTS %s (
            uuid CHAR(36) NOT NULL,
            applied BIT(1) NOT NULL,
            PRIMARY KEY (uuid)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
        """) % RA_MIGRATION_TABLE_NAME
        session.execute(statement, None)

    def _load_migrations(self, session):
        migrations = {}
        sys.path.insert(0, self._migrations_path)
        try:
            for filename in os.listdir(self._migrations_path):
                if filename.endswith('.py'):
                    migration = __import__(filename[:-3])
                    if not hasattr(migration, 'migration_step'):
                        continue
                    migrations[filename] = MigrationStepController(
                        migration_step=migration.migration_step,
                        filename=filename,
                        session=session)
            return migrations
        finally:
            sys.path.remove(self._migrations_path)

    def apply_migration(self, migration_name):
        engine = engines.engine_factory.get_engine()
        filename = self.get_file_name(migration_name)
        with sessions.session_manager(engine=engine) as session:
            self._init_migration_table(session)
            migrations = self._load_migrations(session)
            if migrations[filename].is_applied():
                for migration in migrations.values():
                    if filename in migration.depends_from():
                        migration.rollback(session, migrations)
            else:
                migrations[filename].apply(session, migrations)

    def rollback_migration(self, migration_name):
        engine = engines.engine_factory.get_engine()
        filename = self.get_file_name(migration_name)
        with sessions.session_manager(engine=engine) as session:
            self._init_migration_table(session)
            migrations = self._load_migrations(session)
            migrations[filename].rollback(session, migrations)
