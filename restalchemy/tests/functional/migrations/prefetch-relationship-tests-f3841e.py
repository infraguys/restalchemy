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
        return "f3841e0e-e180-4144-bd82-6113d646c2c9"

    def upgrade(self, session):
        expressions = [
            """
                CREATE TABLE IF NOT EXISTS root (
                    uuid CHAR(36) NOT NULL,
                    field_str VARCHAR(255) NOT NULL,
                    field_int INT NOT NULL,
                    field_bool BOOL NOT NULL,
                    PRIMARY KEY (uuid)
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS lnp1_1 (
                    uuid CHAR(36) NOT NULL,
                    root CHAR(36) NOT NULL,
                    field_str VARCHAR(255) NOT NULL,
                    field_int INT NOT NULL,
                    field_bool BOOL NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (root)
                        REFERENCES root (uuid)
                        ON DELETE RESTRICT
                        ON UPDATE RESTRICT
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS lnp1_2 (
                    uuid CHAR(36) NOT NULL,
                    root CHAR(36),
                    field_str VARCHAR(255) NOT NULL,
                    field_int INT NOT NULL,
                    field_bool BOOL NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (root)
                        REFERENCES root (uuid)
                        ON DELETE RESTRICT
                        ON UPDATE RESTRICT
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS lwp1_1 (
                    uuid CHAR(36) NOT NULL,
                    root CHAR(36) NOT NULL,
                    field_str VARCHAR(255) NOT NULL,
                    field_int INT NOT NULL,
                    field_bool BOOL NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (root)
                        REFERENCES root (uuid)
                        ON DELETE RESTRICT
                        ON UPDATE RESTRICT
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS lwp1_2 (
                    uuid CHAR(36) NOT NULL,
                    root CHAR(36),
                    field_str VARCHAR(255) NOT NULL,
                    field_int INT NOT NULL,
                    field_bool BOOL NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (root)
                        REFERENCES root (uuid)
                        ON DELETE RESTRICT
                        ON UPDATE RESTRICT
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS lwp2_1 (
                    uuid CHAR(36) NOT NULL,
                    lwp1_1 CHAR(36) NOT NULL,
                    field_str VARCHAR(255) NOT NULL,
                    field_int INT NOT NULL,
                    field_bool BOOL NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (lwp1_1)
                        REFERENCES lwp1_1 (uuid)
                        ON DELETE RESTRICT
                        ON UPDATE RESTRICT
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS lwp2_2 (
                    uuid CHAR(36) NOT NULL,
                    lwp1_1 CHAR(36),
                    field_str VARCHAR(255) NOT NULL,
                    field_int INT NOT NULL,
                    field_bool BOOL NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (lwp1_1)
                        REFERENCES lwp1_1 (uuid)
                        ON DELETE RESTRICT
                        ON UPDATE RESTRICT
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS lwp2_3 (
                    uuid CHAR(36) NOT NULL,
                    lwp1_2 CHAR(36) NOT NULL,
                    field_str VARCHAR(255) NOT NULL,
                    field_int INT NOT NULL,
                    field_bool BOOL NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (lwp1_2)
                        REFERENCES lwp1_2 (uuid)
                        ON DELETE RESTRICT
                        ON UPDATE RESTRICT
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS lwp2_4 (
                    uuid CHAR(36) NOT NULL,
                    lwp1_2 CHAR(36),
                    field_str VARCHAR(255) NOT NULL,
                    field_int INT NOT NULL,
                    field_bool BOOL NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (lwp1_2)
                        REFERENCES lwp1_2 (uuid)
                        ON DELETE RESTRICT
                        ON UPDATE RESTRICT
                );
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        tables = [
            "lwp2_4",
            "lwp2_3",
            "lwp2_2",
            "lwp2_1",
            "lwp1_2",
            "lwp1_1",
            "lnp1_2",
            "lnp1_1",
            "root",
        ]

        for table in tables:
            self._delete_table_if_exists(session, table)


migration_step = MigrationStep()
