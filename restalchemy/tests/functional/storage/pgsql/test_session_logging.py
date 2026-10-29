# Copyright 2026 Genesis Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from psycopg import errors
import pytest

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage import exceptions
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm
from restalchemy.storage.sql import sessions
from restalchemy.tests.functional import consts

pytestmark = pytest.mark.skipif(
    not consts.get_database_uri().startswith("postgresql"),
    reason="Requires PostgreSQL JSONB",
)


class LoggingPayload(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "cassi_logging_payloads"
    payload = properties.property(types.Dict(), required=True)


@pytest.fixture
def session():
    engines.engine_factory.configure_factory(
        db_url=consts.get_database_uri(), config={"min_size": 1, "max_size": 1}
    )
    engine = engines.engine_factory.get_engine()
    try:
        with engine.session_manager() as session:
            session.execute(
                "CREATE TEMP TABLE cassi_logging_payloads "
                "(uuid UUID PRIMARY KEY, payload JSONB NOT NULL)"
            )
            session.commit()
            yield session
    finally:
        engine._pool.close()
        engines.engine_factory.destroy_engine()


@pytest.mark.parametrize("batch", [False, True], ids=["single", "batch"])
@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO], ids=["debug", "info"])
@pytest.mark.parametrize("failure", [False, True], ids=["success", "failure"])
def test_jsonb_model_values_are_not_logged(session, batch, level, failure, caplog):
    marker = "synthetic-jsonb-private-value"
    payload = {"registration_token": marker, "nested": {"password": marker}}
    first = LoggingPayload(payload=payload)
    second = LoggingPayload(payload=payload)
    if failure:
        first.insert(session=session)
        session.commit()
    caplog.clear()

    def insert():
        if batch:
            session.batch_insert([second, first])
        else:
            first.insert(session=session)

    with caplog.at_level(level, logger=sessions.LOG.name):
        if failure:
            # batch_insert and the ORM translate the driver exception.
            with pytest.raises(exceptions.ConflictRecords) as caught:
                insert()
            assert "duplicate key" in str(caught.value)
            session.rollback()
        else:
            insert()
            session.commit()

    assert marker not in caplog.text
    assert marker not in repr([record.args for record in caplog.records])
    if level == logging.DEBUG:
        assert len(caplog.records) == 1
        assert 'INSERT INTO "cassi_logging_payloads"' in caplog.text
        assert "%s" in caplog.text
        assert session.engine.db_name in caplog.text
        assert (
            "Execute batch statement" if batch else "Execute statement"
        ) in caplog.text
    else:
        assert not caplog.records

    # Check the actual JSONB contents and all-or-nothing batch rollback.
    rows = session.execute("SELECT payload FROM cassi_logging_payloads").fetchall()
    assert [row["payload"] for row in rows] == [payload] * (
        1 if failure or not batch else 2
    )


@pytest.mark.parametrize("batch", [False, True], ids=["single", "batch"])
def test_failed_jsonb_statement_keeps_driver_diagnostics(session, batch, caplog):
    marker = "synthetic-failed-jsonb-value"
    statement = "INSERT INTO cassi_logging_payloads (uuid, payload) VALUES (%s, %s)"
    values = (None, {"registration_token": marker})
    execute = session.execute_many if batch else session.execute
    with caplog.at_level(logging.DEBUG, logger=sessions.LOG.name):
        with pytest.raises(errors.NotNullViolation) as caught:
            execute(statement, [values] if batch else values)
        session.rollback()
    assert caught.value.sqlstate == "23502"
    assert caught.value.diag.column_name == "uuid"
    assert statement in caplog.text
    assert marker not in caplog.text
    assert marker not in repr([record.args for record in caplog.records])
