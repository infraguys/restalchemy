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

"""How many queries reading a collection of related models costs.

The storage path runs for real -- query builder, dialect, result parser,
model restore -- against a session that answers out of canned tables and
counts what it was asked to execute.
"""

import contextlib
import re
import uuid

import mock

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.storage import exceptions
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm
from restalchemy.storage.sql.dialect import pgsql
from restalchemy.tests.unit import base


class FakeSession(object):
    """Answers a `SELECT` out of a dict of tables, and remembers it."""

    def __init__(self, engine, tables):
        self.engine = engine
        self._tables = tables
        self.statements = []

    _FROM = re.compile(r'FROM "(\w+)"(?: AS "(\w+)")?')
    _JOIN = re.compile(
        r'LEFT JOIN "(\w+)" AS "(\w+)" ON \("(\w+)"\."(\w+)" = "(\w+)"\."(\w+)"\)'
    )
    _CONDITION = re.compile(r'(?:"(\w+)"\.)?"(\w+)"\s*=\s*(?:ANY\()?%s')

    def execute(self, statement, values):
        self.statements.append(statement)
        table, alias = self._FROM.search(statement).groups()
        joins = self._JOIN.findall(statement)

        rows = []
        for row in self._tables[table]:
            joined = self._prefixed(row, alias)
            for name, join_alias, left, left_col, _, right_col in joins:
                key = joined.get(self._key(left, left_col))
                match = self._find(name, right_col, key)
                joined.update(self._prefixed(match, join_alias))
            if self._matches(statement, values, joined):
                # A join-free `SELECT` names no aliases, so the driver
                # names the columns itself.
                rows.append(joined if joins else self._unprefixed(joined, alias))
        return rows

    def _find(self, table, column, value):
        for row in self._tables[table]:
            if str(row[column]) == str(value):
                return row
        return {name: None for name in self._tables[table][0]}

    @staticmethod
    def _key(alias, column):
        return "%s_%s" % (alias, column) if alias else column

    @classmethod
    def _unprefixed(cls, row, alias):
        cut = len(alias) + 1 if alias else 0
        return {name[cut:]: value for name, value in row.items()}

    @classmethod
    def _prefixed(cls, row, alias):
        return {cls._key(alias, name): value for name, value in row.items()}

    @classmethod
    def _matches(cls, statement, values, row):
        # The two shapes these tests produce: `col = %s`, `col = ANY(%s)`.
        parts = statement.split(" WHERE ", 1)
        if len(parts) == 1:
            return True
        for (alias, column), value in zip(cls._CONDITION.findall(parts[1]), values):
            actual = str(row[cls._key(alias, column)])
            if isinstance(value, (list, tuple)):
                if actual not in [str(item) for item in value]:
                    return False
            elif actual != str(value):
                return False
        return True

    def queried_tables(self):
        return [re.search(r'FROM "(\w+)"', s).group(1) for s in self.statements]


class FakeEngine(object):
    dialect = pgsql.PgSQLDialect()
    query_cache = False

    def __init__(self, tables):
        self.session = FakeSession(self, tables)

    def escape(self, name):
        return '"%s"' % name

    @contextlib.contextmanager
    def session_manager(self, session=None):
        yield session or self.session


class FakeEngineFactory(object):
    def __init__(self, engine):
        self._engine = engine

    def get_engine(self, name=None):
        return self._engine


class Org(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "orgs"
    name = properties.property(types.String(), default="o")


class Project(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "projects"
    name = properties.property(types.String(), default="p")
    org = relationships.relationship(Org, required=True)


class Role(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "roles"
    name = properties.property(types.String(), default="r")


class Binding(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "bindings"
    name = properties.property(types.String(), default="b")
    project = relationships.relationship(Project, required=True)
    role = relationships.relationship(Role, required=True)


class PrefetchedBinding(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "prefetched_bindings"
    role = relationships.relationship(Role, required=True, prefetch=True)


class TwoKeyed(models.Model, orm.SQLStorableMixin):
    __tablename__ = "two_keyed"
    left = properties.property(types.String(), id_property=True, required=True)
    right = properties.property(types.String(), id_property=True, required=True)


class KeyedBinding(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "keyed_bindings"
    keyed = relationships.relationship(TwoKeyed, required=True)


class RelationshipLoadingTestCase(base.BaseTestCase):
    ROWS = 20

    def setUp(self):
        super(RelationshipLoadingTestCase, self).setUp()

        self.orgs = [{"uuid": str(uuid.uuid4()), "name": "o%d" % i} for i in range(2)]
        self.projects = [
            {
                "uuid": str(uuid.uuid4()),
                "name": "p%d" % i,
                "org": self.orgs[i % len(self.orgs)]["uuid"],
            }
            for i in range(5)
        ]
        self.roles = [{"uuid": str(uuid.uuid4()), "name": "r%d" % i} for i in range(3)]
        self.bindings = [
            {
                "uuid": str(uuid.uuid4()),
                "name": "b%d" % i,
                "project": self.projects[i % len(self.projects)]["uuid"],
                "role": self.roles[i % len(self.roles)]["uuid"],
            }
            for i in range(self.ROWS)
        ]
        self.prefetched_bindings = [
            {"uuid": str(uuid.uuid4()), "role": self.roles[0]["uuid"]}
            for _ in range(self.ROWS)
        ]

        self.tables = {
            "orgs": self.orgs,
            "projects": self.projects,
            "roles": self.roles,
            "bindings": self.bindings,
            "prefetched_bindings": self.prefetched_bindings,
        }
        self.engine = FakeEngine(self.tables)
        self._real_factory = engines.engine_factory
        engines.engine_factory = FakeEngineFactory(self.engine)

    def tearDown(self):
        super(RelationshipLoadingTestCase, self).tearDown()
        engines.engine_factory = self._real_factory

    @property
    def _queried(self):
        return self.engine.session.queried_tables()

    def test_a_relationship_is_asked_for_once_not_once_per_row(self):
        result = Binding.objects.get_all()

        self.assertEqual(self.ROWS, len(result))
        # One for the collection, one per relationship, and one for what
        # the projects themselves point at.
        self.assertEqual(
            ["bindings", "projects", "orgs", "roles"],
            self._queried,
        )

    def test_every_row_gets_the_object_its_column_names(self):
        result = Binding.objects.get_all()

        for binding, row in zip(result, self.bindings):
            self.assertIsInstance(binding.project, Project)
            self.assertEqual(row["project"], str(binding.project.uuid))
            self.assertIsInstance(binding.role, Role)
            self.assertEqual(row["role"], str(binding.role.uuid))
            self.assertIsInstance(binding.project.org, Org)

    def test_a_row_pointing_at_nothing_fails_as_it_always_did(self):
        self.bindings[3]["role"] = str(uuid.uuid4())

        self.assertRaises(exceptions.RecordNotFound, Binding.objects.get_all)

    def test_a_prefetched_relationship_asks_for_nothing(self):
        result = PrefetchedBinding.objects.get_all()

        self.assertEqual(["prefetched_bindings"], self._queried)
        self.assertEqual(self.ROWS, len(result))
        self.assertIsInstance(result[0].role, Role)

    def test_one_row_is_read_the_way_it_was(self):
        binding = Binding.objects.get_one(
            filters={"uuid": self.bindings[0]["uuid"]},
        )

        self.assertEqual(self.bindings[0]["project"], str(binding.project.uuid))
        self.assertEqual(["bindings", "projects", "orgs", "roles"], self._queried)

    def test_rows_naming_the_same_object_are_handed_the_same_one(self):
        result = Binding.objects.get_all()

        first = result[0].project
        same = [b.project for b in result if b.project.get_id() == first.get_id()]

        self.assertGreater(len(same), 1)
        for project in same:
            self.assertIs(first, project)

    def test_the_identifiers_are_asked_for_in_batches(self):
        with mock.patch.object(Binding, "RELATIONSHIP_BATCH_SIZE", 2):
            Binding.objects.get_all()

        # Five projects, two at a time -- and each batch of projects
        # resolves what it points at in turn; three roles, likewise.
        self.assertEqual(
            ["bindings"] + ["projects", "orgs"] * 3 + ["roles"] * 2,
            self._queried,
        )

    def test_a_target_without_one_identifier_is_left_to_the_per_row_path(self):
        self.tables["two_keyed"] = [{"left": "l", "right": "r"}]
        self.tables["keyed_bindings"] = [
            {"uuid": str(uuid.uuid4()), "keyed": "l"} for _ in range(3)
        ]

        result = KeyedBinding.objects.get_all()

        # It cannot be asked for a page of identifiers, so it is read the
        # way it was: a query per row, and the same objects as before.
        self.assertEqual(
            ["keyed_bindings"] + ["two_keyed"] * 3,
            self._queried,
        )
        self.assertEqual("l", result[0].keyed.left)

    def test_a_column_that_is_not_an_identifier_is_left_to_fail_per_row(self):
        self.bindings[0]["role"] = "not a uuid"

        # The batch cannot read it, so the value reaches the per-row path,
        # which reports it the way it always has.
        self.assertRaises(Exception, Binding.objects.get_all)
