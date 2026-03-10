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
        self._depends = []

    @property
    def migration_id(self):
        return "1e68bf7b-947d-4b90-bc0e-fe6293ad1b42"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        session.execute("""
        CREATE TABLE second_model (
            name VARCHAR(256) UNIQUE
        )
        """)

    def downgrade(self, session):
        session.execute("""
        DROP TABLE second_model
        """)


migration_step = MigrationStep()
