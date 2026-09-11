#    Copyright 2026 Genesis Corporation.
#
#    All Rights Reserved.
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

import gc
import weakref

import mock

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import tables
from restalchemy.tests import fixtures
from restalchemy.tests.unit import base


class TableModel(models.ModelWithUUID):
    __tablename__ = "table_models"

    zeta = properties.property(types.String())
    alpha = properties.property(types.String())


class SQLTableColumnNamesTestCase(base.BaseTestCase):
    """The column names a statement is built from.

    A table answers the same questions for every statement over it, and
    keeps the answers; the escaped ones belong to the engine that escaped
    them, and a model can be read through one engine and written through
    another.
    """

    def setUp(self):
        super(SQLTableColumnNamesTestCase, self).setUp()
        self.engine = fixtures.EngineFixture()
        self.session = mock.Mock(engine=self.engine)
        self.table = tables.SQLTable(
            engine=self.engine,
            table_name=TableModel.__tablename__,
            model=TableModel,
        )

    def test_the_columns_are_sorted_and_include_the_key(self):
        self.assertEqual(
            ["alpha", "uuid", "zeta"],
            self.table.get_column_names(self.session),
        )

    def test_the_key_can_be_left_out(self):
        self.assertEqual(
            ["alpha", "zeta"],
            self.table.get_column_names(self.session, with_pk=False),
        )

    def test_asking_twice_answers_the_same(self):
        self.assertEqual(
            self.table.get_column_names(self.session),
            self.table.get_column_names(self.session),
        )
        self.assertEqual(
            ["alpha", "zeta"],
            self.table.get_column_names(self.session, with_pk=False),
        )
        self.assertEqual(
            ["alpha", "uuid", "zeta"],
            self.table.get_column_names(self.session),
        )

    def test_the_primary_key_is_its_own_question(self):
        self.assertEqual(["uuid"], self.table.get_pk_names(self.session))
        self.assertEqual(["`uuid`"], self.table.get_escaped_pk_names(self.session))

    def test_each_engine_escapes_the_way_it_escapes(self):
        class DoubleQuoteEngine(fixtures.EngineFixture):
            def escape(self, value):
                return '"%s"' % value

        other = mock.Mock(engine=DoubleQuoteEngine())

        self.assertEqual(
            ["`alpha`", "`uuid`", "`zeta`"],
            self.table.get_escaped_column_names(self.session),
        )
        self.assertEqual(
            ['"alpha"', '"uuid"', '"zeta"'],
            self.table.get_escaped_column_names(other),
        )
        self.assertEqual(
            ["`alpha`", "`uuid`", "`zeta`"],
            self.table.get_escaped_column_names(self.session),
        )


class EngineLifetimeTestCase(base.BaseTestCase):
    """Nothing kept here may outlive the engine it was built for.

    An engine that cannot be collected is a connection pool that is
    never closed, and its connections stay open for the life of the
    process. What a table and a query keep is therefore weak on the
    engine -- including what sits inside a weak map, which would
    otherwise pin its own key.
    """

    def test_a_table_lets_its_engine_go(self):
        table = tables.SQLTable(
            engine=None,
            table_name=TableModel.__tablename__,
            model=TableModel,
        )
        engine = fixtures.EngineFixture()
        table.get_escaped_column_names(mock.Mock(engine=engine))
        dead = weakref.ref(engine)

        del engine
        gc.collect()

        self.assertIsNone(dead())
