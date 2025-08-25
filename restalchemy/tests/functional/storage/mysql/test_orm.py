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
from parameterized import parameterized

from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm
from restalchemy.tests.functional import base
from restalchemy.tests.functional import consts
from restalchemy.tests.utils import make_test_name


class FakeModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "batch_insert"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String())


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

    @parameterized.expand(
        [
            (None, ("1", "2")),
            ("ASC", ("1", "2")),
            ("DESC", ("2", "1")),
            ("ASC NULLS FIRST", (None, "1", "2")),
            ("ASC NULLS LAST", ("1", "2", None)),
            ("DESC NULLS FIRST", (None, "2", "1")),
            ("DESC NULLS LAST", ("2", "1", None)),
        ],
        name_func=make_test_name,
    )
    def test_with_various_order_bys(self, sort_dir, correct_order):
        items = [
            FakeModel(foo_field1=idx, foo_field2=val)
            for idx, val in enumerate(correct_order)
        ]
        with self.engine.session_manager() as session:
            session.batch_insert(items)

        results_from_db = FakeModel.objects.get_all(
            order_by={"foo_field2": sort_dir}
        )
        values_from_db = tuple(i.foo_field2 for i in results_from_db)
        self.assertEqual(correct_order, values_from_db)


class TestLikeTestCase(base.BaseWithDbMigrationsTestCase):

    __LAST_MIGRATION__ = "test-batch-migration-9e335f"
    __FIRST_MIGRATION__ = "test-batch-migration-9e335f"

    def test_filter_like_not_like(self):
        model1 = FakeModel(foo_field1=1, foo_field2="Model1")
        model2 = FakeModel(foo_field1=2, foo_field2="Model2")
        model3 = FakeModel(foo_field1=3, foo_field2="FooModel3")
        model4 = FakeModel(foo_field1=4, foo_field2="TestMod-4")
        model5 = FakeModel(foo_field1=5, foo_field2="Mod'el")

        with self.engine.session_manager() as session:
            session.batch_insert([model1, model2, model3, model4, model5])

        # Like: Startswith Model
        all_models = set(
            FakeModel.objects.get_all(
                filters={"foo_field2": dm_filters.Like("Model%")}
            )
        )

        self.assertEqual({model1, model2}, all_models)

        # Like: del in center
        all_models = set(
            FakeModel.objects.get_all(
                filters={"foo_field2": dm_filters.Like("%del%")}
            )
        )

        self.assertEqual({model1, model2, model3}, all_models)

        # Like: Endswith 3
        all_models = set(
            FakeModel.objects.get_all(
                filters={"foo_field2": dm_filters.Like("%3")}
            )
        )

        self.assertEqual(
            {
                model3,
            },
            all_models,
        )

        # Like: TestMod + random symbol + 4
        all_models = set(
            FakeModel.objects.get_all(
                filters={"foo_field2": dm_filters.Like("TestMod_4")}
            )
        )

        self.assertEqual(
            {
                model4,
            },
            all_models,
        )

        # Like: Endswith 5
        all_models = set(
            FakeModel.objects.get_all(
                filters={"foo_field2": dm_filters.Like("%5")}
            )
        )

        self.assertEqual(set(), all_models)

        # Like: Startswith Foo or Test
        # TODO(v.burygin) Зачем тут AND, - неизвестно, надо разбираться
        filter_list = dm_filters.AND(
            dm_filters.OR(
                {"foo_field2": dm_filters.Like("Foo%")},
                {"foo_field2": dm_filters.Like("Test%")},
            )
        )
        all_models = set(FakeModel.objects.get_all(filters=filter_list))

        self.assertEqual({model3, model4}, all_models)

        # Like: ' in center with escape symbol
        all_models = set(
            FakeModel.objects.get_all(
                filters={"foo_field2": dm_filters.Like(r"Mod\'el")}
            )
        )

        self.assertEqual(
            {
                model5,
            },
            all_models,
        )

        # NotLike: Not startswith Foo
        all_models = set(
            FakeModel.objects.get_all(
                filters={"foo_field2": dm_filters.NotLike("Foo%")}
            )
        )

        self.assertEqual({model1, model2, model4, model5}, all_models)

        # NotLike: Mod in center
        all_models = set(
            FakeModel.objects.get_all(
                filters={"foo_field2": dm_filters.NotLike("%Mod%")}
            )
        )

        self.assertEqual(set(), all_models)

        # NotLike: ' in center with escape symbol
        all_models = set(
            FakeModel.objects.get_all(
                filters={"foo_field2": dm_filters.NotLike(r"Mod\'el")}
            )
        )

        self.assertEqual({model1, model2, model3, model4}, all_models)


class TestCacheTestCase(base.BaseWithDbMigrationsTestCase):

    __LAST_MIGRATION__ = "test-batch-migration-9e335f"
    __FIRST_MIGRATION__ = "test-batch-migration-9e335f"

    @classmethod
    def init_engine(cls):
        engines.engine_factory.configure_factory(
            db_url=consts.DATABASE_URI, query_cache=True
        )
        cls.__ENGINE__ = engines.engine_factory.get_engine()

    def test_get_one_all_with_cache(self):
        model1 = FakeModel(foo_field1=1, foo_field2="Model1")

        with self.engine.session_manager() as session:
            session.batch_insert([model1])

            tgt_model = FakeModel.objects.get_one(session=session, cache=True)
            tgt_model_cached = FakeModel.objects.get_one(
                session=session, cache=True
            )

            assert tgt_model is tgt_model_cached

    def test_get_one_all_without_cache(self):
        model1 = FakeModel(foo_field1=1, foo_field2="Model1")

        with self.engine.session_manager() as session:
            session.batch_insert([model1])

            tgt_model = FakeModel.objects.get_one(session=session, cache=True)
            tgt_model_cached = FakeModel.objects.get_one(
                session=session, cache=False
            )

            assert tgt_model is not tgt_model_cached
