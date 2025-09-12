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
        return "743d3857-7780-4cdd-8452-2c0aaf316a8b"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                CREATE TABLE IF NOT EXISTS binary_data (
                    uuid CHAR(36) NOT NULL,
                    data TEXT NOT NULL,
                PRIMARY KEY (uuid))
            """
        ]
        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        tables_to_delete = ["binary_data"]

        for table in tables_to_delete:
            self._delete_table_if_exists(session, table)


migration_step = MigrationStep()
