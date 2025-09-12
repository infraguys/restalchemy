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


class MigrationStep(migrations.AbstractMigrationStep):

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
                    just_none VARCHAR(255) NULL,
                    status VARCHAR(255) NULL,
                    created TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
                    updated TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (uuid)
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS ports (
                    uuid CHAR(36) NOT NULL,
                    mac CHAR(17) NOT NULL,
                    vm CHAR(36) NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (vm) REFERENCES vms (uuid)
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS ip_addresses (
                    uuid CHAR(36) NOT NULL,
                    ip VARCHAR(17) NOT NULL,
                    port CHAR(36) NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (port) REFERENCES ports (uuid)
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS tags (
                    uuid CHAR(36) NOT NULL,
                    vm CHAR(36) NOT NULL,
                    name VARCHAR(40) NOT NULL,
                    visible BOOLEAN NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (vm) REFERENCES vms (uuid)
                );
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        tables = ["tags", "ip_addresses", "ports", "vms"]

        for table in tables:
            self._delete_table_if_exists(session, table)


migration_step = MigrationStep()
