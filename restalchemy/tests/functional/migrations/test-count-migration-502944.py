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
        return "502944fe-e739-4c1a-a413-24fa787ae14d"

    def upgrade(self, session):
        sql_expr_list = [
            """
                CREATE TABLE test_count (
                    uuid CHAR(36) NOT NULL,
                    foo_field1 INT NOT NULL,
                    foo_field2 VARCHAR(255) NOT NULL,
                PRIMARY KEY (uuid));
            """,
            """
                INSERT INTO test_count (
                     uuid, foo_field1, foo_field2
                ) VALUES (
                    '00000000-0000-0000-0000-000000000000', 1, 'value1'
                ), (
                    '00000000-0000-0000-0000-000000000001', 2, 'value2'
                ), (
                    '00000000-0000-0000-0000-000000000002', 3, 'value3'
                ), (
                    '00000000-0000-0000-0000-000000000003', 4, 'other1'
                )
            """,
        ]

        [session.execute(expr) for expr in sql_expr_list]

    def downgrade(self, session):
        self._delete_table_if_exists(session, "test_count")


migration_step = MigrationStep()
