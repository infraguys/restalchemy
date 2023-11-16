# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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


class FakeModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "batch_insert"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class TestOrderByTestCase(base.BaseWithDbMigrationsTestCase):

    __LAST_MIGRATION__ = "test-batch-migration-9e335f"
    __FIRST_MIGRATION__ = "test-batch-migration-9e335f"

    def test_without_order_by(self):
        model1 = FakeModel(foo_field1=1, foo_field2="Model1")
        model2 = FakeModel(foo_field1=2, foo_field2="Model2")

        with self.engine.session_manager() as session:
            session.batch_insert([model1, model2])

        all_models = set(FakeModel.objects.get_all())

        self.assertEqual({model1, model2}, all_models)

    def test_with_order_by_asc(self):
        model1 = FakeModel(foo_field1=1, foo_field2="Model1")
        model2 = FakeModel(foo_field1=2, foo_field2="Model2")

        with self.engine.session_manager() as session:
            session.batch_insert([model1, model2])

        all_models = FakeModel.objects.get_all(
            order_by={'foo_field1': 'ASC'})

        self.assertEqual([model1, model2], all_models)

    def test_with_order_by_desc(self):
        model1 = FakeModel(foo_field1=1, foo_field2="Model1")
        model2 = FakeModel(foo_field1=2, foo_field2="Model2")

        with self.engine.session_manager() as session:
            session.batch_insert([model1, model2])

        all_models = FakeModel.objects.get_all(
            order_by={'foo_field1': 'DESC'})

        self.assertEqual([model2, model1], all_models)
