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
from restalchemy.tests.functional.storage.mysql.prefetch import models


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = ["prefetch-relationship-tests-f3841e.py"]

    @property
    def migration_id(self):
        return "9727f325-aab6-4393-8edb-3c66c18ed772"

    def upgrade(self, session):
        root = models.Root()
        root.insert()

        lnp1_1 = models.LNP1_1(root=root)
        lnp1_1.insert()

        lnp1_2 = models.LNP1_2()
        lnp1_2.insert()

        lwp1_1 = models.LWP1_1(root=root)
        lwp1_1.insert()
        lwp1_2 = models.LWP1_2()
        lwp1_2.insert()

        lwp2_1 = models.LWP2_1(lwp1_1=lwp1_1)
        lwp2_1.insert()
        lwp2_2 = models.LWP2_2()
        lwp2_2.insert()
        lwp2_3 = models.LWP2_3(lwp1_2=lwp1_2)
        lwp2_3.insert()
        lwp2_4 = models.LWP2_4()
        lwp2_4.insert()

    def downgrade(self, session):
        for Model in [
            models.LWP2_1,
            models.LWP2_2,
            models.LWP2_3,
            models.LWP2_4,
            models.LWP1_1,
            models.LWP1_2,
            models.LNP1_1,
            models.LNP1_2,
            models.Root,
        ]:
            for model in Model.objects.get_all():
                model.delete()


migration_step = MigrationStep()
