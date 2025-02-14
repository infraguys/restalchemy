#    Copyright 2021 Eugene Frolov.
#
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

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import orm
from restalchemy.tests.functional import base


class BatchDeleteModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "batch_delete_two_pk"
    foo_field1 = properties.property(
        types.Integer(), required=True, id_property=True
    )
    foo_field2 = properties.property(types.String(), default="foo_str")

    @property
    def super_id(self):
        return "%s-%s" % (self.uuid, self.foo_field1)

    @classmethod
    def get_id_property(cls):
        return {
            "super_id": (
                cls.properties["uuid"],
                cls.properties["foo_field1"],
            )
        }


class WithDbMigrationsDeleteTwoPkTestCase(base.BaseWithDbMigrationsTestCase):
    __LAST_MIGRATION__ = "test-batch-migration-9e335f"
    __FIRST_MIGRATION__ = "test-batch-migration-9e335f"

    def test_correct_batch_delete(self):
        my_models = BatchDeleteModel.objects.get_all()
        target = [my_models.pop(0), my_models.pop(2)]

        with self.engine.session_manager() as session:
            session.batch_delete(my_models)
        result = BatchDeleteModel.objects.get_all()

        self.assertEqual(target, result)
