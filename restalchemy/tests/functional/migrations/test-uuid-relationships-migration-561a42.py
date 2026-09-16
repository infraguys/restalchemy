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
    """Tables for the bare UUID relationship tests.

    A VM served on a path of its own, a port served under its VM, and a
    rule pointing at both -- the two shapes a relationship can address,
    in one place.
    """

    def __init__(self):
        self._depends = [""]

    @property
    def migration_id(self):
        return "561a4294-b031-49d8-849d-e1d86a993ccd"

    def upgrade(self, session):
        uuid_type = (
            "UUID" if session.engine.dialect.name == "postgresql" else "CHAR(36)"
        )
        expressions = [
            """
                CREATE TABLE test_uuid_rel_vms (
                    uuid %(uuid)s NOT NULL,
                    name VARCHAR(255) NOT NULL DEFAULT '',
                    PRIMARY KEY (uuid)
                )
            """,
            """
                CREATE TABLE test_uuid_rel_ports (
                    uuid %(uuid)s NOT NULL,
                    vm %(uuid)s NOT NULL,
                    mac CHAR(17) NOT NULL,
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (vm) REFERENCES test_uuid_rel_vms (uuid)
                )
            """,
            """
                CREATE TABLE test_uuid_rel_rules (
                    uuid %(uuid)s NOT NULL,
                    vm %(uuid)s NOT NULL,
                    port %(uuid)s NOT NULL,
                    name VARCHAR(255) NOT NULL DEFAULT '',
                    PRIMARY KEY (uuid),
                    FOREIGN KEY (vm) REFERENCES test_uuid_rel_vms (uuid),
                    FOREIGN KEY (port) REFERENCES test_uuid_rel_ports (uuid)
                )
            """,
        ]

        for expression in expressions:
            session.execute(expression % {"uuid": uuid_type})

    def downgrade(self, session):
        tables = [
            "test_uuid_rel_rules",
            "test_uuid_rel_ports",
            "test_uuid_rel_vms",
        ]

        for table in tables:
            self._delete_table_if_exists(session, table)


migration_step = MigrationStep()
