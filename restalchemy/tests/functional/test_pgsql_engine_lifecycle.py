# Copyright 2026 Genesis Corporation.
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

import gc
import os
import subprocess
import sys
import textwrap
import weakref

import psycopg_pool
import pytest

from restalchemy.storage.sql import engines
from restalchemy.tests.functional import consts


@pytest.fixture
def pgsql_uri():
    uri = consts.get_database_uri()
    if not uri.startswith("postgresql:"):
        pytest.skip("PostgreSQL lifecycle test")
    return uri


def new_engine(uri):
    return engines.PgSQLEngine(uri, config={"min_size": 1, "max_size": 1})


@pytest.mark.parametrize("factory", [False, True])
def test_interpreter_shutdown_is_clean(pgsql_uri, factory):
    # Delay cyclic garbage until shutdown, as happens in long-running suites.
    script = textwrap.dedent(
        """
        import gc
        import os
        from restalchemy.storage.sql import engines

        gc.disable()
        for _ in range(5):
            if os.environ['USE_FACTORY'] == '1':
                engines.engine_factory.configure_factory(
                    os.environ['DATABASE_URI'],
                    config={'min_size': 1, 'max_size': 1})
                engine = engines.engine_factory.get_engine()
            else:
                engine = engines.PgSQLEngine(
                    os.environ['DATABASE_URI'],
                    config={'min_size': 1, 'max_size': 1})
            with engine.session_manager() as session:
                assert session.execute('SELECT 42 AS value').fetchone()['value'] == 42
            engine.cycle = engine
            if os.environ['USE_FACTORY'] == '1':
                engines.engine_factory.destroy_engine()
            del engine, session
        print('queries completed', flush=True)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "DATABASE_URI": pgsql_uri, "USE_FACTORY": str(int(factory))},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "queries completed"
    assert result.stderr == ""


def test_close_releases_idle_connections_and_workers(pgsql_uri):
    engine = new_engine(pgsql_uri)
    try:
        conn = engine.get_connection()
        engine.close_connection(conn)
        workers = [*engine._pool._workers, engine._pool._sched_runner]

        engine.close()
        engine.close()

        assert engine._pool.closed
        assert conn.closed
        assert all(not worker.is_alive() for worker in workers)
        with pytest.raises(psycopg_pool.PoolClosed):
            engine.get_connection()
    finally:
        engine._pool.close()


def test_close_keeps_checked_out_connection_until_returned(pgsql_uri):
    engine = new_engine(pgsql_uri)
    conn = engine.get_connection()
    try:
        engine.close()

        assert not conn.closed
        assert conn.execute("SELECT 42").fetchone() == (42,)
        conn.rollback()
        engine.close_connection(conn)
        assert conn.closed
    finally:
        conn.close()
        engine._pool.close()


@pytest.mark.parametrize("destroy_all", [False, True])
def test_factory_cleanup_closes_retained_engines(pgsql_uri, destroy_all):
    factory = engines.engine_factory
    names = ["cassi-lifecycle-first", "cassi-lifecycle-second"]
    retained = []
    try:
        for name in names:
            factory.configure_factory(
                pgsql_uri, name=name, config={"min_size": 1, "max_size": 1}
            )
            retained.append(factory.get_engine(name))
        if destroy_all:
            factory.destroy_all_engines()
            factory.destroy_all_engines()
        else:
            for name in names:
                factory.destroy_engine(name)
                factory.destroy_engine(name)

        for name, engine in zip(names, retained):
            assert engine._pool.closed
            with pytest.raises(ValueError):
                factory.get_engine(name)
    finally:
        for engine in retained:
            engine._pool.close()
        for name in names:
            factory.destroy_engine(name)


def test_repeated_engine_collection_without_cyclic_gc(pgsql_uri):
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(5):
            engine = new_engine(pgsql_uri)
            conn = engine.get_connection()
            assert conn.execute("SELECT 42").fetchone() == (42,)
            conn.rollback()
            engine.close_connection(conn)
            pool = engine._pool
            ref = weakref.ref(engine)
            del engine

            assert ref() is None
            assert pool.closed
            assert conn.closed
    finally:
        if was_enabled:
            gc.enable()
