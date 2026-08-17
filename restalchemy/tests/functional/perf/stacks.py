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

"""The same three requests, served two ways: by RestAlchemy and by hand.

The hand-written one -- psycopg and orjson, no framework at all -- is the
floor: what the database and the JSON cost before anything of ours has
run. A guard reads RestAlchemy against that floor rather than against
microseconds somebody once recorded, because a machine that is slow, busy
or virtual is slow for both of them at once.

Only PostgreSQL: the floor has to speak to the database directly, and
psycopg is the driver both sides then share.
"""

import datetime
import io
import uuid

import orjson
import psycopg
from psycopg import rows as pg_rows
from psycopg_pool import ConnectionPool

from restalchemy.api import applications
from restalchemy.api import controllers
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm

TABLE = "perf_items"
COLUMNS = "id, name, description, enabled, quantity, project_id, created_at, updated_at"
PROJECT_ID = uuid.UUID(int=0x51)
# Out of the range the seeded rows use, so the rows a run creates are the
# rows it sweeps, and a page is the page it was seeded to be.
CREATED_QUANTITY = 10_000_000
CREATE_BODY = orjson.dumps(
    {
        "name": "created item",
        "description": "an item a POST made",
        "enabled": True,
        "quantity": CREATED_QUANTITY,
        "project_id": str(PROJECT_ID),
    }
)
FIRST_ID = str(uuid.UUID(int=1))

SCHEMA = """
DROP TABLE IF EXISTS %(table)s;
CREATE TABLE %(table)s (
    id uuid PRIMARY KEY,
    name varchar(255) NOT NULL,
    description varchar(255) NOT NULL,
    enabled boolean NOT NULL,
    quantity integer NOT NULL,
    project_id uuid NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);
CREATE INDEX %(table)s_quantity ON %(table)s (quantity);
""" % {"table": TABLE}


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def seed(db_url, rows):
    """The same rows every run: seeded ids, seeded timestamps."""
    epoch = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    records = [
        (
            uuid.UUID(int=number + 1),
            "item %d" % number,
            "a description of item %d" % number,
            number % 3 != 0,
            number,
            PROJECT_ID,
            epoch + datetime.timedelta(seconds=number),
            epoch + datetime.timedelta(seconds=number, microseconds=number % 3),
        )
        for number in range(rows)
    ]
    with psycopg.connect(db_url, autocommit=True) as connection:
        connection.execute(SCHEMA)
        connection.cursor().executemany(
            "INSERT INTO %s (%s) VALUES (%s)" % (TABLE, COLUMNS, ", ".join(["%s"] * 8)),
            records,
        )


def sweep(db_url):
    """Take the rows the POSTs wrote back out."""
    with psycopg.connect(db_url, autocommit=True) as connection:
        connection.execute(
            "DELETE FROM %s WHERE quantity >= %d" % (TABLE, CREATED_QUANTITY)
        )


def drop(db_url):
    with psycopg.connect(db_url, autocommit=True) as connection:
        connection.execute("DROP TABLE IF EXISTS %s" % TABLE)


def wsgi(app, method, path, body=b""):
    """Call a WSGI application where a web server would otherwise stand.

    A server would measure the server. Both sides of the guard are called
    at their own interface instead, so what is compared is the framework
    and its database work.
    """
    environ = {
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "SERVER_NAME": "perf",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_HOST": "perf",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": io.BytesIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "CONTENT_LENGTH": str(len(body)),
    }
    if body:
        environ["CONTENT_TYPE"] = "application/json"
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = int(status.split()[0])

    chunks = app(environ, start_response)
    try:
        payload = b"".join(chunks)
    finally:
        if hasattr(chunks, "close"):
            chunks.close()
    return captured["status"], payload


class RawStack(object):
    """psycopg and orjson, nothing else.

    It takes its connection from a pool, as a service would and as ours
    does: a floor that keeps one connection to itself would be measuring
    a program nobody deploys.
    """

    name = "raw psycopg + orjson"

    def __init__(self, db_url, page):
        self._db_url = db_url
        self._page = page

    def setup(self):
        self._pool = ConnectionPool(self._db_url, min_size=1, max_size=4, open=True)

    def teardown(self):
        self._pool.close()

    @staticmethod
    def _document(row):
        row["id"] = str(row["id"])
        row["project_id"] = str(row["project_id"])
        row["created_at"] = row["created_at"].isoformat()
        row["updated_at"] = row["updated_at"].isoformat()
        return row

    def collection(self):
        with self._pool.connection() as connection:
            with connection.cursor(row_factory=pg_rows.dict_row) as cursor:
                cursor.execute(
                    "SELECT %s FROM %s ORDER BY quantity LIMIT %%s" % (COLUMNS, TABLE),
                    (self._page,),
                )
                documents = [self._document(row) for row in cursor.fetchall()]
        return 200, orjson.dumps(documents)

    def resource(self, item_id):
        with self._pool.connection() as connection:
            with connection.cursor(row_factory=pg_rows.dict_row) as cursor:
                cursor.execute(
                    "SELECT %s FROM %s WHERE id = %%s" % (COLUMNS, TABLE), (item_id,)
                )
                row = cursor.fetchone()
        return 200, orjson.dumps(self._document(row))

    def create(self, document):
        record = orjson.loads(document)
        now = _now()
        values = (
            uuid.uuid4(),
            record["name"],
            record["description"],
            record["enabled"],
            record["quantity"],
            uuid.UUID(record["project_id"]),
            now,
            now,
        )
        with self._pool.connection() as connection:
            with connection.cursor(row_factory=pg_rows.dict_row) as cursor:
                cursor.execute(
                    "INSERT INTO %s (%s) VALUES (%s) RETURNING %s"
                    % (TABLE, COLUMNS, ", ".join(["%s"] * 8), COLUMNS),
                    values,
                )
                row = cursor.fetchone()
        return 201, orjson.dumps(self._document(row))


class Item(models.ModelWithID, orm.SQLStorableMixin):
    __tablename__ = TABLE

    id = properties.property(
        types.UUID(), id_property=True, default=lambda: uuid.uuid4()
    )
    name = properties.property(types.String(max_length=255), required=True)
    description = properties.property(types.String(max_length=255), default="")
    enabled = properties.property(types.Boolean(), default=True)
    quantity = properties.property(types.Integer(), default=0)
    project_id = properties.property(types.UUID(), required=True)
    created_at = properties.property(types.UTCDateTimeZ(), default=_now)
    updated_at = properties.property(types.UTCDateTimeZ(), default=_now)


class ItemController(controllers.Controller):
    __resource__ = resources.ResourceByRAModel(
        Item,
        process_filters=True,
        convert_underscore=False,
    )
    # The page the guard reads, set once the stack knows how wide it is.
    page = 100

    def filter(self, filters, order_by=None):
        return Item.objects.get_all(
            order_by={"quantity": "asc"}, limit=ItemController.page
        )

    def get(self, uuid):
        return Item.objects.get_one(filters={"id": dm_filters.EQ(uuid)})

    def create(self, **kwargs):
        item = Item(**kwargs)
        item.save()
        return item


class ItemsRoute(routes.Route):
    __controller__ = ItemController
    __allow_methods__ = [routes.FILTER, routes.GET, routes.CREATE]


class Root(routes.Route):
    __controller__ = ItemController
    __allow_methods__ = []
    items = routes.route(ItemsRoute)


class RestAlchemyStack(object):
    """A REST resource of ours, routed, fetched through the ORM, packed."""

    name = "restalchemy"

    def __init__(self, db_url, page):
        self._db_url = db_url
        self._page = page

    def setup(self):
        ItemController.page = self._page
        engines.engine_factory.configure_factory(db_url=self._db_url)
        self._app = applications.WSGIApp(route_class=Root)

    def teardown(self):
        engines.engine_factory.destroy_all_engines()

    def collection(self):
        return wsgi(self._app, "GET", "/items/")

    def resource(self, item_id):
        return wsgi(self._app, "GET", "/items/%s" % item_id)

    def create(self, document):
        return wsgi(self._app, "POST", "/items/", document)


# What to ask a stack, by the name the guard reports it under.
ASK = {
    "collection": lambda stack: stack.collection(),
    "resource": lambda stack: stack.resource(FIRST_ID),
    "create": lambda stack: stack.create(CREATE_BODY),
}
SCENARIOS = tuple(ASK)


def check(stack, page):
    """Nobody is measured before answering what the table holds."""
    status, body = stack.collection()
    documents = orjson.loads(body)
    assert status == 200, "%s: collection answered %s" % (stack.name, status)
    assert len(documents) == page, "%s: collection is %d rows, not %d" % (
        stack.name,
        len(documents),
        page,
    )

    status, body = stack.resource(FIRST_ID)
    assert status == 200, "%s: resource answered %s" % (stack.name, status)
    resource = orjson.loads(body)
    assert resource["id"] == FIRST_ID, "%s: resource is another row" % stack.name
    assert set(resource) >= set(documents[0]), (
        "%s: a resource answers with less than a collection row" % stack.name
    )

    status, body = stack.create(CREATE_BODY)
    assert status == 201, "%s: create answered %s" % (stack.name, status)
    created = orjson.loads(body)
    posted = orjson.loads(CREATE_BODY)
    assert all(created[field] == posted[field] for field in posted), (
        "%s: create echoes the posted fields back wrong" % stack.name
    )
