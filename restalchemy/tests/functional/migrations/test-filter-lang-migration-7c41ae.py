# Copyright 2026 Genesis Corporation
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
    """Tables for the filter language tests.

    Two of them, because the language spans both dialects but its array
    operators do not. `test_filter_lang` is scalars only and exists
    everywhere; `test_filter_lang_tags` carries the `text[]` and `jsonb`
    columns and is created under PostgreSQL alone.
    """

    def __init__(self):
        self._depends = [""]

    @property
    def migration_id(self):
        return "7c41ae64-1d0b-4f2e-9a35-6c0f4b18d2e7"

    def upgrade(self, session):
        postgresql = session.engine.dialect.name == "postgresql"
        uuid_type = "UUID" if postgresql else "CHAR(36)"
        session.execute(
            f"""
            CREATE TABLE test_filter_lang (
                uuid {uuid_type} NOT NULL,
                project_id {uuid_type} NOT NULL,
                name VARCHAR(255) NOT NULL DEFAULT '',
                state VARCHAR(255) NOT NULL DEFAULT '',
                size INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (uuid)
            )
        """
        )
        session.execute(
            "CREATE INDEX idx_test_filter_lang_project ON test_filter_lang (project_id)"
        )
        if not postgresql:
            return
        session.execute("""
            CREATE TABLE test_filter_lang_tags (
                uuid UUID NOT NULL,
                name VARCHAR(255) NOT NULL DEFAULT '',
                tags TEXT[] NOT NULL DEFAULT '{}',
                spec JSONB NOT NULL DEFAULT '{}',
                PRIMARY KEY (uuid)
            )
        """)
        session.execute(
            "CREATE INDEX idx_test_filter_lang_tags ON test_filter_lang_tags"
            " USING GIN (tags)"
        )

    def downgrade(self, session):
        self._delete_table_if_exists(session, "test_filter_lang_tags")
        self._delete_table_if_exists(session, "test_filter_lang")


migration_step = MigrationStep()
