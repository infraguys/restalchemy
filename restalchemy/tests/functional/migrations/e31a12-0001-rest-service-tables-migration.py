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

from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = [""]

    @property
    def migration_id(self):
        return "e31a12bb-3c3a-4f86-8bdd-ca9f7b613b6c"

    def upgrade(self, session):
        expressions = [
            """
                CREATE TABLE IF NOT EXISTS vms (
                    uuid CHAR(36) NOT NULL,
                    state VARCHAR(10) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    PRIMARY KEY (uuid)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
            """, """
                CREATE TABLE IF NOT EXISTS ports (
                    uuid CHAR(36) NOT NULL,
                    mac CHAR(17) NOT NULL,
                    vm CHAR(36) NOT NULL,
                    PRIMARY KEY (uuid),
                    CONSTRAINT FOREIGN KEY ix_vms_uuid (vm)
                    REFERENCES vms (uuid)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
            """, """
                CREATE TABLE IF NOT EXISTS ip_addresses (
                    uuid CHAR(36) NOT NULL,
                    ip CHAR(17) NOT NULL,
                    port CHAR(36) NOT NULL,
                    PRIMARY KEY (uuid),
                    CONSTRAINT FOREIGN KEY ix_ports_uuid (port)
                    REFERENCES ports (uuid)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
            """
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        tables = ['ip_addresses', 'ports', 'vms']

        for table in tables:
            self._delete_table_if_exists(session, table)


migration_step = MigrationStep()
