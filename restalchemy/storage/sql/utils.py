# Copyright 2017 Eugene Frolov <eugene@frolov.net.ru>
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
import contextlib
import logging

from restalchemy.common import contexts
from restalchemy.storage.sql.dialect import mysql as mysql_dialect
from restalchemy.storage.sql.dialect import pgsql as pgsql_dialect

LOG = logging.getLogger(__name__)
DEFAULT_SAVEPOINT_NAME = "default_savepoint"


def escape(value):
    return "`%s`" % value


@contextlib.contextmanager
def savepoint(
    name: str = DEFAULT_SAVEPOINT_NAME,
    defer_release: bool = False,
):
    """Context manager that creates a savepoint and rolls back to it on error.

    The function can be used as a decorator or a context manager. For example:

    @savepoint()
    def my_function():
        pass

    with savepoint() as session:
        pass

    When ``defer_release`` is ``False`` (the default) an explicit ``RELEASE``
    is issued on both the success and the error paths, matching the historical
    behavior. When ``defer_release`` is ``True`` the ``RELEASE`` is skipped on
    the success path and issued only on the error path (after the
    ``ROLLBACK TO``).

    The deferred mode is safe when several savepoints sharing the same name
    are created sequentially inside a single enclosing transaction: in both
    PostgreSQL and MySQL issuing ``SAVEPOINT <name>`` with an already existing
    name implicitly releases the previous savepoint of that name, and
    committing or rolling back the enclosing transaction releases every
    remaining savepoint. Skipping the explicit ``RELEASE`` therefore carries
    no observable effect while saving one round-trip per decorated call on the
    hot path. It must not be used with nested savepoints that rely on an
    explicit release in between.
    """
    if not name.isidentifier():
        raise ValueError(f"Invalid savepoint name: {name}")

    ctx = contexts.Context()
    engine = ctx._engine
    dialect_name = engine.dialect.name

    if dialect_name == pgsql_dialect.PgSQLDialect.DIALECT_NAME:
        expression_map = pgsql_dialect.SAVEPOINT_EXP_MAP
    elif dialect_name == mysql_dialect.MySQLDialect.DIALECT_NAME:
        expression_map = mysql_dialect.SAVEPOINT_EXP_MAP
    else:
        raise ValueError("Unsupported database dialect: %s" % dialect_name)

    savepoint_exp = expression_map["savepoint"].format(name=name)
    rollback_exp = expression_map["rollback"].format(name=name)
    release_exp = expression_map["release"].format(name=name)

    session = ctx.get_session()
    session.execute(savepoint_exp, tuple())

    success = False

    try:
        yield session
        success = True
    except Exception:
        LOG.error("Exception occurred, rolling back to savepoint")
        session.execute(rollback_exp, tuple())
        raise
    finally:
        if not success or not defer_release:
            session.execute(release_exp, tuple())
