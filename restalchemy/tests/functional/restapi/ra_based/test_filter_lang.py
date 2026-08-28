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

"""The filter language over HTTP, against a real database.

The unit tests stop at the DM filters the language builds. These drive the
whole path a caller uses -- query string, controller, SQL, rows back --
and so are the only place the generated SQL is ever executed. The scalar
cases run under both dialects; the array ones need PostgreSQL, and there
is a case asserting that MySQL says so rather than failing deeper down.
"""

import contextlib
import socket
import typing
import unittest
import uuid

import requests

from restalchemy.api import controllers
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import orm
from restalchemy.tests.functional import base
from restalchemy.tests.functional import consts
from restalchemy.tests.functional.restapi.ra_based.microservice import service

MIGRATION = "test-filter-lang-migration-7c41ae"

PROJECT1 = uuid.UUID("00000000-0000-0000-0000-0000000000f1")
PROJECT2 = uuid.UUID("00000000-0000-0000-0000-0000000000f2")

UUID1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
UUID2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
UUID3 = uuid.UUID("00000000-0000-0000-0000-000000000003")
UUID4 = uuid.UUID("00000000-0000-0000-0000-000000000004")


class FilterLangModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "test_filter_lang"

    project_id = properties.property(types.UUID(), required=True)
    name = properties.property(types.String(max_length=255), default="")
    state = properties.property(types.String(max_length=255), default="")
    size = properties.property(types.Integer(), default=0)


class FilterLangController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        FilterLangModel,
        process_filters=True,
        convert_underscore=False,
    )


class PaginatedFilterLangController(controllers.BaseResourceControllerPaginated):
    __resource__ = resources.ResourceByRAModel(
        FilterLangModel,
        process_filters=True,
        convert_underscore=False,
    )


class TaggedModel(models.ModelWithUUID, models.ModelWithTags, orm.SQLStorableMixin):
    __tablename__ = "test_filter_lang_tags"

    name = properties.property(types.String(max_length=255), default="")
    spec = properties.property(types.Dict(), default=dict)


class TaggedController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        TaggedModel,
        process_filters=True,
        convert_underscore=False,
    )


class FilterLangRoute(routes.Route):
    __controller__ = FilterLangController
    __allow_methods__: typing.ClassVar = [routes.CREATE, routes.FILTER, routes.GET]


class PaginatedFilterLangRoute(routes.Route):
    __controller__ = PaginatedFilterLangController
    __allow_methods__: typing.ClassVar = [routes.CREATE, routes.FILTER, routes.GET]


class TaggedRoute(routes.Route):
    __controller__ = TaggedController
    __allow_methods__: typing.ClassVar = [routes.CREATE, routes.FILTER, routes.GET]


class Root(routes.RootRoute):
    things = routes.route(FilterLangRoute)
    paginated = routes.route(PaginatedFilterLangRoute)
    tagged = routes.route(TaggedRoute)


class BaseFilterLangTestCase(base.BaseWithDbMigrationsTestCase):
    __LAST_MIGRATION__ = MIGRATION
    __FIRST_MIGRATION__ = MIGRATION

    #: Collection the `_get` helper talks to.
    COLLECTION = "things"

    def setUp(self):
        super().setUp()
        self.populate()
        self._port = self._find_free_port()
        self._service = service.RESTService(
            bind_host="127.0.0.1",
            bind_port=self._port,
            app_root=service.build_wsgi_application(app_root=Root),
        )
        self._service.start()
        self.addCleanup(self._service.stop)

    def populate(self):
        raise NotImplementedError()

    @staticmethod
    def _find_free_port():
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(("127.0.0.1", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def _get(self, query="", collection=None):
        return requests.get(
            f"http://127.0.0.1:{self._port}/{collection or self.COLLECTION}/{query}",
        )

    def _uuids(self, response):
        self.assertEqual(200, response.status_code, response.text)
        return {uuid.UUID(item["uuid"]) for item in response.json()}


class FilterLangTestCase(BaseFilterLangTestCase):
    """Scalar filtering, on every dialect."""

    def populate(self):
        FilterLangModel(
            uuid=UUID1, project_id=PROJECT1, name="web-1", state="active", size=10
        ).save()
        FilterLangModel(
            uuid=UUID2, project_id=PROJECT1, name="web-2", state="active", size=20
        ).save()
        FilterLangModel(
            uuid=UUID3, project_id=PROJECT1, name="db-1", state="error", size=30
        ).save()
        FilterLangModel(
            uuid=UUID4, project_id=PROJECT2, name="web-1", state="active", size=40
        ).save()

    def test_equality(self):
        self.assertEqual({UUID1, UUID4}, self._uuids(self._get('?q=name = "web-1"')))

    def test_inequality(self):
        self.assertEqual(
            {UUID1, UUID2, UUID4}, self._uuids(self._get('?q=name != "db-1"'))
        )

    def test_a_range(self):
        self.assertEqual(
            {UUID2, UUID3}, self._uuids(self._get("?q=size >= 20 AND size < 40"))
        )

    def test_an_implicit_and(self):
        self.assertEqual(
            {UUID2, UUID3},
            self._uuids(self._get("?q=size >= 20 size < 40")),
        )

    def test_or_over_one_field_becomes_one_any(self):
        # UUID4 is a second web-1, in another project.
        self.assertEqual(
            {UUID1, UUID3, UUID4},
            self._uuids(self._get('?q=name = "web-1" OR name = "db-1"')),
        )

    def test_or_over_two_fields(self):
        self.assertEqual(
            {UUID3, UUID4},
            self._uuids(self._get('?q=state = "error" OR size = 40')),
        )

    def test_negation(self):
        self.assertEqual(
            {UUID1, UUID2, UUID4},
            self._uuids(self._get('?q=NOT (state = "error")')),
        )

    def test_negation_of_a_conjunction_is_not_a_conjunction_of_negations(self):
        # NOT (a AND b) keeps every row failing either half.
        self.assertEqual(
            {UUID1, UUID3},
            self._uuids(self._get('?q=NOT (state = "active" AND size >= 20)')),
        )

    def test_or_binds_tighter_than_and(self):
        # (name = web-1 OR name = web-2) AND size > 10 -- and not
        # name = web-1 OR (name = web-2 AND size > 10), which would also
        # bring in UUID1, whose size is exactly 10.
        self.assertEqual(
            {UUID2, UUID4},
            self._uuids(self._get('?q=name = "web-1" OR name = "web-2" AND size > 10')),
        )

    def test_parentheses_override_the_precedence(self):
        self.assertEqual(
            {UUID1, UUID2, UUID4},
            self._uuids(
                self._get('?q=name = "web-1" OR (name = "web-2" AND size > 10)')
            ),
        )

    def test_a_field_parameter_and_an_expression_are_anded(self):
        self.assertEqual(
            {UUID1},
            self._uuids(self._get(f'?name=web-1&q=project_id = "{PROJECT1}"')),
        )

    def test_presence_of_a_field(self):
        # Everything has a name here, empty string included: `:*` asks
        # whether the column is NULL, not whether it is empty.
        self.assertEqual(
            {UUID1, UUID2, UUID3, UUID4}, self._uuids(self._get("?q=name:*"))
        )

    def test_a_uuid_value_goes_through_the_field_type(self):
        self.assertEqual(
            {UUID4}, self._uuids(self._get(f'?q=project_id = "{PROJECT2}"'))
        )

    def test_an_empty_expression_filters_nothing(self):
        self.assertEqual({UUID1, UUID2, UUID3, UUID4}, self._uuids(self._get("?q=")))

    def test_an_unknown_field_is_refused(self):
        self.assertEqual(400, self._get("?q=nope = 1").status_code)

    def test_a_value_the_type_rejects_is_refused(self):
        self.assertEqual(400, self._get("?q=size = notanumber").status_code)

    def test_a_syntax_error_is_refused(self):
        self.assertEqual(400, self._get('?q=name = "unterminated').status_code)

    def test_two_expressions_are_refused(self):
        self.assertEqual(
            400, self._get('?q=name = "web-1"&q=name = "web-2"').status_code
        )

    def test_too_complex_an_expression_is_refused(self):
        self.assertEqual(
            400,
            self._get("?q=" + " AND ".join(["size = 1"] * 40)).status_code,
        )

    def test_an_expression_that_selects_nothing(self):
        self.assertEqual(set(), self._uuids(self._get('?q=name = "nowhere"')))


class FilterLangPaginationTestCase(BaseFilterLangTestCase):
    """The cursor and the expression walking one collection together."""

    COLLECTION = "paginated"

    def populate(self):
        for index, item in enumerate(
            (
                (UUID1, "web-1", "active", 10),
                (UUID2, "web-2", "active", 20),
                (UUID3, "db-1", "error", 30),
                (UUID4, "web-3", "active", 40),
            )
        ):
            item_uuid, name, state, size = item
            FilterLangModel(
                uuid=item_uuid,
                project_id=PROJECT1,
                name=name,
                state=state,
                size=size + index,
            ).save()

    def _page(self, query, marker=None):
        if marker is not None:
            query = f"{query}&page_marker={marker}"
        response = self._get(query)
        self.assertEqual(200, response.status_code, response.text)
        return response

    def test_an_expression_walks_every_page_exactly_once(self):
        seen = []
        marker = None
        for _ in range(4):
            response = self._page('?q=state = "active"&page_limit=1', marker)
            rows = response.json()
            if not rows:
                break
            seen.extend(uuid.UUID(row["uuid"]) for row in rows)
            marker = response.headers.get("X-Pagination-Marker")
            if marker is None:
                break

        self.assertEqual([UUID1, UUID2, UUID4], seen)

    def test_a_page_is_limited(self):
        response = self._page('?q=state = "active"&page_limit=2')

        self.assertEqual(2, len(response.json()))

    def test_the_expression_narrows_the_page(self):
        response = self._page("?q=size > 100&page_limit=10")

        self.assertEqual([], response.json())

    def test_sorting_by_another_column_with_an_expression(self):
        # This is the path that looks the marker row up separately.
        first = self._page('?q=state = "active"&sort_key=size&page_limit=1')
        marker = first.headers["X-Pagination-Marker"]
        second = self._page('?q=state = "active"&sort_key=size&page_limit=1', marker)

        self.assertEqual([UUID1], [uuid.UUID(r["uuid"]) for r in first.json()])
        self.assertEqual([UUID2], [uuid.UUID(r["uuid"]) for r in second.json()])


@unittest.skipUnless(
    consts.get_database_uri().startswith("postgresql"),
    "array containment is a PostgreSQL operator",
)
class FilterLangArrayTestCase(BaseFilterLangTestCase):
    """`tags:"x"`, and the folding of several of them into one operator."""

    COLLECTION = "tagged"

    def populate(self):
        TaggedModel(
            uuid=UUID1, name="a", tags=["env:prod", "region:eu"], spec={"kind": "totp"}
        ).save()
        TaggedModel(uuid=UUID2, name="b", tags=["env:prod", "region:us"]).save()
        TaggedModel(uuid=UUID3, name="c", tags=["env:staging"]).save()
        TaggedModel(uuid=UUID4, name="d", tags=[]).save()

    def test_one_element(self):
        self.assertEqual({UUID1, UUID2}, self._uuids(self._get('?q=tags:"env:prod"')))

    def test_and_of_two_holds_both(self):
        self.assertEqual(
            {UUID1},
            self._uuids(self._get('?q=tags:"env:prod" AND tags:"region:eu"')),
        )

    def test_or_of_two_holds_either(self):
        self.assertEqual(
            {UUID2, UUID3},
            self._uuids(self._get('?q=tags:"env:staging" OR tags:"region:us"')),
        )

    def test_a_wider_containment_ored_with_another(self):
        # Not `&& ARRAY['env:prod','region:eu','env:staging']`: that would
        # take UUID2 as well, which holds `env:prod` but not `region:eu`.
        self.assertEqual(
            {UUID1, UUID3},
            self._uuids(
                self._get(
                    '?q=(tags:"env:prod" AND tags:"region:eu") OR tags:"env:staging"'
                )
            ),
        )

    def test_a_tag_nobody_carries(self):
        self.assertEqual(set(), self._uuids(self._get('?q=tags:"env:nowhere"')))

    def test_a_tag_carrying_punctuation_needs_quoting(self):
        # Unquoted, the second colon reads as another comparator.
        self.assertEqual(400, self._get("?q=tags:env:prod").status_code)

    def test_containment_next_to_a_scalar(self):
        self.assertEqual(
            {UUID1},
            self._uuids(self._get('?q=tags:"env:prod" AND name = "a"')),
        )

    def test_the_operator_needs_an_array_field(self):
        self.assertEqual(400, self._get('?q=name:"a"').status_code)

    def test_json_traversal_reaches_the_key(self):
        self.assertEqual({UUID1}, self._uuids(self._get('?q=spec.kind = "totp"')))

    def test_a_json_key_the_sql_cannot_carry_is_refused(self):
        # A 400 over HTTP, not something the escaping has to survive --
        # the key is inlined into the statement, so it never gets there.
        for key in (r"a\') IS NOT NULL OR 1=1 --", "%s", "a'b"):
            with self.subTest(key=key):
                response = self._get(
                    '?q=spec."{}" = 1'.format(key.replace("\\", "\\\\"))
                )

                self.assertEqual(400, response.status_code, response.text)

    def test_the_bare_array_field_is_still_exact_equality(self):
        # `?tags=x` compares the whole array, as it always did; searching
        # by element is what the expression is for.
        self.assertEqual({UUID3}, self._uuids(self._get("?tags=env:staging")))


@unittest.skipIf(
    consts.get_database_uri().startswith("postgresql"),
    "the point is what a dialect without array operators answers",
)
class FilterLangDialectGateTestCase(BaseFilterLangTestCase):
    """A clause the dialect cannot compile is a 400, not a 500."""

    def populate(self):
        FilterLangModel(
            uuid=UUID1, project_id=PROJECT1, name="web-1", state="active", size=10
        ).save()

    def test_scalar_filtering_works_here(self):
        self.assertEqual({UUID1}, self._uuids(self._get('?q=name = "web-1"')))

    def test_json_traversal_is_refused(self):
        self.assertEqual(400, self._get('?q=name.kind = "x"').status_code)
