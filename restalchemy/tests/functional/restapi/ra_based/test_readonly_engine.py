#    Copyright 2026 Genesis Corporation.
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

import os
import unittest

from restalchemy.storage.sql import engines


def _can_connect_db(db_url):
    """Check if a database URL is reachable."""
    try:
        schema = db_url.split(":")[0]
        if schema == "postgresql":
            from psycopg_pool import ConnectionPool

            pool = ConnectionPool(db_url, timeout=5, max_waiting=1)
            pool.wait()
            conn = pool.getconn()
            conn.close()
            pool.close()
            return True
        elif schema == "mysql":
            from urllib.parse import urlparse

            from mysql.connector import pooling

            parsed = urlparse(db_url)
            pool = pooling.MySQLConnectionPool(
                pool_name="skip_test_" + str(hash(db_url)),
                pool_size=1,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:],
                host=parsed.hostname,
                port=parsed.port or 3306,
                connection_timeout=5,
            )
            conn = pool.get_connection()
            conn.close()
            pool._remove_connections()
            return True
    except Exception:
        pass
    return False


def _get_db_uri(schema):
    """Get database URI for a given schema.

    Prefers DATABASE_URI env var if it is explicitly set,
    otherwise uses hardcoded test URIs.
    """
    env_uri = os.getenv("DATABASE_URI")
    if schema == "postgresql":
        if env_uri and env_uri.split(":")[0] == "postgresql":
            return env_uri
        return "postgresql://postgres:1234@172.17.0.2:5432/postgres_core"
    else:
        if env_uri and env_uri.split(":")[0] == "mysql":
            return env_uri
        return "mysql://root:1234@172.17.0.3:3306/mysql"


_PG_URI = _get_db_uri("postgresql")
_PG_AVAILABLE = _can_connect_db(_PG_URI)

_MYSQL_URI = _get_db_uri("mysql")
_MYSQL_AVAILABLE = _can_connect_db(_MYSQL_URI)


class TestPostgresReadonlyEngineFunctional(unittest.TestCase):
    """Functional tests for PostgreSQL readonly engine configuration."""

    @classmethod
    def setUpClass(cls):
        super(TestPostgresReadonlyEngineFunctional, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestPostgresReadonlyEngineFunctional, cls).tearDownClass()
        engines.engine_factory.destroy_all_engines()

    @unittest.skipIf(not _PG_AVAILABLE, "PostgreSQL not available")
    def test_readonly_engine_property(self):
        """Test that readonly engine has readonly property set correctly."""
        readonly_engine = engines.PgSQLEngine(db_url=_PG_URI, readonly=True)
        self.assertTrue(readonly_engine.readonly)

        normal_engine = engines.PgSQLEngine(db_url=_PG_URI, readonly=False)
        self.assertFalse(normal_engine.readonly)

        # Cleanup
        readonly_engine._pool.close()
        normal_engine._pool.close()

    @unittest.skipIf(not _PG_AVAILABLE, "PostgreSQL not available")
    def test_readonly_connection_enforces_db_level_restriction(self):
        """Test that readonly connection blocks write operations at DB level.

        This test verifies that setting readonly=True on PgSQLEngine actually
        sets conn.read_only=True on the underlying psycopg2 connection,
        causing the database to reject write operations with an error.
        """
        # Create table with a non-readonly engine
        normal_engine = engines.PgSQLEngine(db_url=_PG_URI, readonly=False)
        normal_session = normal_engine.get_session()
        normal_session.execute(
            "CREATE TABLE IF NOT EXISTS _pg_test_rollback (id INT, value TEXT)"
        )
        normal_session.commit()
        normal_session.close()
        normal_engine._pool.close()

        try:
            readonly_engine = engines.PgSQLEngine(db_url=_PG_URI, readonly=True)
            session = readonly_engine.get_session()
            try:
                with self.assertRaises(Exception) as cm:
                    session.execute("INSERT INTO _pg_test_rollback VALUES (1, 'test')")

                error_message = str(cm.exception).lower()
                self.assertIn(
                    "read-only",
                    error_message,
                    "Expected readonly transaction error, got: %s" % cm.exception,
                )
            finally:
                session.close()
                readonly_engine._pool.close()
        finally:
            normal_engine = engines.PgSQLEngine(db_url=_PG_URI, readonly=False)
            normal_session = normal_engine.get_session()
            normal_session.execute("DROP TABLE IF EXISTS _pg_test_rollback")
            normal_session.commit()
            normal_session.close()
            normal_engine._pool.close()

    @unittest.skipIf(not _PG_AVAILABLE, "PostgreSQL not available")
    def test_readonly_session_rollback_on_write(self):
        """Test that context with readonly engine blocks write operations.

        Verifies that when a context is set to readonly mode and a write
        is attempted through session_manager, the DB rejects the operation
        and the data is not inserted.
        """
        # Setup: create test table with normal engine
        normal_engine = engines.PgSQLEngine(db_url=_PG_URI, readonly=False)
        normal_session = normal_engine.get_session()
        normal_session.execute(
            "CREATE TABLE IF NOT EXISTS _pg_rollback (id INT, value TEXT)"
        )
        normal_session.execute("INSERT INTO _pg_rollback VALUES (1, 'initial')")
        normal_session.commit()
        normal_session.close()

        # Configure readonly engine
        engines.engine_factory.configure_factory(
            name="pg_readonly",
            db_url=_PG_URI,
            readonly=True,
        )

        from restalchemy.common import contexts as common_contexts

        ctx = common_contexts.Context(
            engine_name=engines.DEFAULT_NAME,
            readonly_engine_name="pg_readonly",
        )

        # Try to write with readonly context - should fail with DB error
        ctx.set_readonly(True)
        with self.assertRaises(Exception) as cm:
            with ctx.session_manager() as session:
                session.execute("INSERT INTO _pg_rollback VALUES (2, 'readonly_write')")

        # Verify the error is related to readonly transaction
        error_message = str(cm.exception).lower()
        self.assertIn(
            "read-only",
            error_message,
            "Expected readonly error, got: %s" % cm.exception,
        )

        # Verify data was not inserted
        normal_session = normal_engine.get_session()
        result = normal_session.execute("SELECT COUNT(*) FROM _pg_rollback").fetchone()
        self.assertEqual(result["count"], 1)

        # Cleanup
        normal_session.execute("DROP TABLE IF EXISTS _pg_rollback")
        normal_session.commit()
        normal_session.close()
        normal_engine._pool.close()
        engines.engine_factory.destroy_engine(name="pg_readonly")

    @unittest.skipIf(not _PG_AVAILABLE, "PostgreSQL not available")
    def test_readonly_read_operation_succeeds(self):
        """Test that readonly connection allows read operations."""
        readonly_engine = engines.PgSQLEngine(db_url=_PG_URI, readonly=True)

        session = readonly_engine.get_session()
        try:
            result = session.execute("SELECT 1 AS test_value").fetchone()
            self.assertEqual(result["test_value"], 1)
        finally:
            session.close()
            readonly_engine._pool.close()

    @unittest.skipIf(not _PG_AVAILABLE, "PostgreSQL not available")
    def test_context_get_readonly_engine(self):
        """Test that context can get readonly engine explicitly."""
        engines.engine_factory.configure_factory(
            name="pg_ro",
            db_url=_PG_URI,
            readonly=True,
        )

        from restalchemy.common import contexts as common_contexts

        ctx = common_contexts.Context(
            engine_name=engines.DEFAULT_NAME,
            readonly_engine_name="pg_ro",
        )

        ro_engine = ctx.get_readonly_engine()
        self.assertTrue(ro_engine.readonly)
        self.assertEqual(
            ro_engine,
            engines.engine_factory.get_engine(name="pg_ro"),
        )

        engines.engine_factory.destroy_engine(name="pg_ro")

    @unittest.skipIf(not _PG_AVAILABLE, "PostgreSQL not available")
    def test_context_get_readwrite_engine(self):
        """Test that context can get readwrite engine explicitly."""
        engines.engine_factory.configure_factory(
            name="pg_ro",
            db_url=_PG_URI,
            readonly=True,
        )
        engines.engine_factory.configure_factory(
            db_url=_PG_URI,
            name=engines.DEFAULT_NAME,
        )

        from restalchemy.common import contexts as common_contexts

        ctx = common_contexts.Context(
            engine_name=engines.DEFAULT_NAME,
            readonly_engine_name="pg_ro",
        )

        rw_engine = ctx.get_readwrite_engine()
        self.assertFalse(rw_engine.readonly)
        self.assertEqual(
            rw_engine,
            engines.engine_factory.get_engine(name=engines.DEFAULT_NAME),
        )

        engines.engine_factory.destroy_engine(name="pg_ro")


class TestMySQLEngineFunctional(unittest.TestCase):
    """Functional tests for MySQL readonly engine configuration."""

    @classmethod
    def setUpClass(cls):
        super(TestMySQLEngineFunctional, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestMySQLEngineFunctional, cls).tearDownClass()
        engines.engine_factory.destroy_all_engines()

    @unittest.skipIf(not _MYSQL_AVAILABLE, "MySQL not available")
    def test_mysql_readonly_engine_property(self):
        """Test that MySQL readonly engine has readonly property set."""
        readonly_engine = engines.MySQLEngine(db_url=_MYSQL_URI, readonly=True)
        self.assertTrue(readonly_engine.readonly)

        normal_engine = engines.MySQLEngine(db_url=_MYSQL_URI, readonly=False)
        self.assertFalse(normal_engine.readonly)

        # Cleanup
        readonly_engine._pool._remove_connections()
        normal_engine._pool._remove_connections()

    @unittest.skipIf(not _MYSQL_AVAILABLE, "MySQL not available")
    def test_mysql_readonly_connection_enforces_db_level(self):
        """Test that MySQL readonly connection blocks write operations.

        Verifies that setting readonly=True on MySQLEngine sets
        init_command to 'SET SESSION TRANSACTION READ ONLY',
        causing the database to reject write operations.
        """
        # Create table with a non-readonly engine
        normal_engine = engines.MySQLEngine(db_url=_MYSQL_URI, readonly=False)
        normal_session = normal_engine.get_session()
        normal_session.execute("CREATE TABLE IF NOT EXISTS _mysql_rollback (id INT)")
        normal_session.commit()
        normal_session.close()
        normal_engine._pool._remove_connections()

        try:
            readonly_engine = engines.MySQLEngine(db_url=_MYSQL_URI, readonly=True)
            session = readonly_engine.get_session()
            try:
                with self.assertRaises(Exception) as cm:
                    session.execute("INSERT INTO _mysql_rollback VALUES (1)")

                error_message = str(cm.exception).lower()
                self.assertIn(
                    "read only",
                    error_message,
                    "Expected readonly error, got: %s" % cm.exception,
                )
            finally:
                session.close()
                readonly_engine._pool._remove_connections()
        finally:
            normal_engine = engines.MySQLEngine(db_url=_MYSQL_URI, readonly=False)
            normal_session = normal_engine.get_session()
            normal_session.execute("DROP TABLE IF EXISTS _mysql_rollback")
            normal_session.commit()
            normal_session.close()
            normal_engine._pool._remove_connections()

    @unittest.skipIf(not _MYSQL_AVAILABLE, "MySQL not available")
    def test_mysql_readonly_read_operation_succeeds(self):
        """Test that MySQL readonly connection allows read operations."""
        readonly_engine = engines.MySQLEngine(db_url=_MYSQL_URI, readonly=True)

        session = readonly_engine.get_session()
        try:
            result = session.execute("SELECT 1 AS test_value").fetchone()
            self.assertEqual(result["test_value"], 1)
        finally:
            session.close()
            readonly_engine._pool._remove_connections()

    @unittest.skipIf(not _MYSQL_AVAILABLE, "MySQL not available")
    def test_mysql_normal_write_succeeds(self):
        """Test that normal MySQL engine allows write operations."""
        normal_engine = engines.MySQLEngine(db_url=_MYSQL_URI, readonly=False)
        session = normal_engine.get_session()
        try:
            session.execute("CREATE TABLE IF NOT EXISTS _mysql_write_test (id INT)")
            session.execute("INSERT INTO _mysql_write_test VALUES (1)")
            session.commit()
            # Verify write worked
            result = session.execute(
                "SELECT COUNT(*) AS cnt FROM _mysql_write_test"
            ).fetchone()
            self.assertEqual(result["cnt"], 1)
        finally:
            session.close()
            normal_engine._pool._remove_connections()
            # Cleanup
            normal_engine = engines.MySQLEngine(db_url=_MYSQL_URI, readonly=False)
            session = normal_engine.get_session()
            session.execute("DROP TABLE IF EXISTS _mysql_write_test")
            session.commit()
            session.close()
            normal_engine._pool._remove_connections()

    @unittest.skipIf(not _MYSQL_AVAILABLE, "MySQL not available")
    def test_mysql_context_readonly_engine(self):
        """Test that context can get MySQL readonly engine."""
        engines.engine_factory.configure_factory(
            name="mysql_readonly",
            db_url=_MYSQL_URI,
            readonly=True,
        )

        from restalchemy.common import contexts as common_contexts

        ctx = common_contexts.Context(
            engine_name=engines.DEFAULT_NAME,
            readonly_engine_name="mysql_readonly",
        )

        ro_engine = ctx.get_readonly_engine()
        self.assertTrue(ro_engine.readonly)
        self.assertEqual(
            ro_engine,
            engines.engine_factory.get_engine(name="mysql_readonly"),
        )

        engines.engine_factory.destroy_engine(name="mysql_readonly")

    @unittest.skipIf(not _MYSQL_AVAILABLE, "MySQL not available")
    def test_mysql_context_readwrite_engine(self):
        """Test that context can get MySQL readwrite engine."""
        engines.engine_factory.configure_factory(
            name="mysql_ro",
            db_url=_MYSQL_URI,
            readonly=True,
        )
        engines.engine_factory.configure_factory(
            db_url=_MYSQL_URI,
            name=engines.DEFAULT_NAME,
        )

        from restalchemy.common import contexts as common_contexts

        ctx = common_contexts.Context(
            engine_name=engines.DEFAULT_NAME,
            readonly_engine_name="mysql_ro",
        )

        rw_engine = ctx.get_readwrite_engine()
        self.assertFalse(rw_engine.readonly)
        self.assertEqual(
            rw_engine,
            engines.engine_factory.get_engine(name=engines.DEFAULT_NAME),
        )

        engines.engine_factory.destroy_engine(name="mysql_ro")
