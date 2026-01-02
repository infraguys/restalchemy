#    Copyright 2025 Genesis Corporation.
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

import os
from urllib.parse import urlparse


import pytest

from restalchemy.tests.functional import consts
from restalchemy.storage.sql import engines


@pytest.fixture(scope="session", autouse=True)
def setup_db_for_worker():
    db_uri = consts.get_database_uri()
    if not (worker_id := os.environ.get("PYTEST_XDIST_WORKER", "")):
        yield
        return

    parsed = urlparse(db_uri)
    worker_db_name_with_slash = f"{parsed.path}_{worker_id}"
    worker_db_name = worker_db_name_with_slash.strip("/")
    db_type = parsed.scheme
    db_created = False
    engines.engine_factory.configure_factory(db_url=db_uri)
    engine = engines.engine_factory.get_engine()
    conn = engine.get_connection()

    # Check if database exists
    if db_type == "postgresql":
        conn.autocommit = True
        c = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (worker_db_name,)
        )
        exists = c.fetchall()
    elif db_type == "mysql":
        c = conn.cursor()
        c.execute(
            "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
            (worker_db_name,),
        )
        exists = c.fetchall()
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    if not exists:
        db_created = True
        if db_type == "postgresql":
            conn.autocommit = True
            conn.execute(f"CREATE DATABASE {worker_db_name}")
        elif db_type == "mysql":
            conn.cursor().execute(f"CREATE DATABASE {worker_db_name}")

    engine.close_connection(conn)
    del engine
    engines.engine_factory.destroy_engine()

    os.environ["DATABASE_URI"] = parsed._replace(
        path=worker_db_name_with_slash
    ).geturl()
    yield

    if db_created:
        engines.engine_factory.configure_factory(db_url=db_uri)
        engine = engines.engine_factory.get_engine()
        conn = engine.get_connection()
        if db_type == "postgresql":
            conn.autocommit = True
            conn.execute(
                f"DROP DATABASE IF EXISTS {worker_db_name} WITH (FORCE)"
            )
        elif db_type == "mysql":
            conn.cursor().execute(f"DROP DATABASE IF EXISTS {worker_db_name}")

        engine.close_connection(conn)
        del engine
        engines.engine_factory.destroy_engine()
