"""psycopg and orjson, nothing else: the floor the others are read against."""

import datetime
import uuid

import orjson
from psycopg import rows as pg_rows
from psycopg_pool import ConnectionPool

from bench import config

NAME = "raw psycopg + orjson"
KIND = "no framework"

COLUMNS = "id, name, description, enabled, quantity, project_id, created_at, updated_at"


class Stack:
    name = NAME
    kind = KIND

    def setup(self):
        self._pool = ConnectionPool(
            config.DATABASE_URL, min_size=1, max_size=4, open=True
        )

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
        with self._pool.connection() as connection, connection.cursor(
            row_factory=pg_rows.dict_row
        ) as cursor:
            cursor.execute(
                f"SELECT {COLUMNS} FROM {config.TABLE} ORDER BY quantity LIMIT %s",
                (config.PAGE,),
            )
            documents = [self._document(row) for row in cursor.fetchall()]
        return 200, orjson.dumps(documents)

    def resource(self, item_id):
        with self._pool.connection() as connection, connection.cursor(
            row_factory=pg_rows.dict_row
        ) as cursor:
            cursor.execute(
                f"SELECT {COLUMNS} FROM {config.TABLE} WHERE id = %s",
                (item_id,),
            )
            row = cursor.fetchone()
        return 200, orjson.dumps(self._document(row))

    def create(self, document):
        record = orjson.loads(document)
        now = datetime.datetime.now(datetime.timezone.utc)
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
        with self._pool.connection() as connection, connection.cursor(
            row_factory=pg_rows.dict_row
        ) as cursor:
            cursor.execute(
                f"INSERT INTO {config.TABLE} ({COLUMNS})"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                f" RETURNING {COLUMNS}",
                values,
            )
            row = cursor.fetchone()
        return 201, orjson.dumps(self._document(row))
