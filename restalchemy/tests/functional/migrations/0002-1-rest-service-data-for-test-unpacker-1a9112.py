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
        self._depends = ["0001-rest-service-tables-migration-e31a12.py"]

    @property
    def migration_id(self):
        return "1a911273-3ffd-4e24-8323-b5433b7e1109"

    def upgrade(self, session):
        expressions = [
            """
                INSERT INTO vms (
                     uuid, name, state
                ) VALUES (
                    '00000000-0000-0000-0000-000000000001', 'vm1', 'on'
                );
            """,
            """
                INSERT INTO ports (
                     uuid, mac, vm
                ) VALUES (
                    '00000000-0000-0000-0000-000000000002',
                    '00:00:00:00:00:00',
                    '00000000-0000-0000-0000-000000000001'
                );
            """,
            """
                INSERT INTO ip_addresses (
                     uuid, ip, port
                ) VALUES (
                    '00000000-0000-0000-0000-000000000003',
                    '192.168.0.1',
                    '00000000-0000-0000-0000-000000000002'
                );
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                DELETE from tags;
            """,
            """
                DELETE from ip_addresses;
            """,
            """
                DELETE FROM ports;
            """,
            """
                DELETE FROM vms;
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
