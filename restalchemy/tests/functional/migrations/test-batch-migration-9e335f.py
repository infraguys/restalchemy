# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
# Copyright 2021 Eugene Frolov.
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
        return "9e335f87-7d66-4768-be00-05ea4cc24a89"

    def upgrade(self, session):
        sql_expr_list = [
            """
                CREATE TABLE IF NOT EXISTS batch_insert (
                    uuid CHAR(36) NOT NULL,
                    foo_field1 INT NOT NULL,
                    foo_field2 VARCHAR(255) NULL,
                PRIMARY KEY (uuid),
                UNIQUE (foo_field1));
            """,
            """
                CREATE TABLE IF NOT EXISTS batch_delete_one_pk (
                    uuid CHAR(36) NOT NULL,
                    foo_field1 INT NOT NULL,
                    foo_field2 VARCHAR(255) NOT NULL,
                PRIMARY KEY (uuid));
            """,
            """
                CREATE TABLE IF NOT EXISTS batch_delete_two_pk (
                    uuid CHAR(36) NOT NULL,
                    foo_field1 INT NOT NULL,
                    foo_field2 VARCHAR(255) NOT NULL,
                PRIMARY KEY (uuid, foo_field1));
            """,
            """
                INSERT INTO batch_delete_one_pk (
                     uuid, foo_field1, foo_field2
                ) VALUES (
                    '00000000-0000-0000-0000-000000000000', 0, '0'
                ), (
                    '00000000-0000-0000-0000-000000000001', 1, '1'
                ), (
                    '00000000-0000-0000-0000-000000000002', 2, '2'
                ), (
                    '00000000-0000-0000-0000-000000000003', 3, '3'
                )
            """,
            """
                INSERT INTO batch_delete_two_pk (
                     uuid, foo_field1, foo_field2
                ) VALUES (
                    '00000000-0000-0000-0000-000000000000', 0, '0'
                ), (
                    '00000000-0000-0000-0000-000000000001', 1, '1'
                ), (
                    '00000000-0000-0000-0000-000000000002', 2, '2'
                ), (
                    '00000000-0000-0000-0000-000000000003', 3, '3'
                )
            """,
        ]

        [session.execute(expr) for expr in sql_expr_list]

    def downgrade(self, session):
        self._delete_table_if_exists(session, "batch_insert")
        self._delete_table_if_exists(session, "batch_delete_one_pk")
        self._delete_table_if_exists(session, "batch_delete_two_pk")


migration_step = MigrationStep()
