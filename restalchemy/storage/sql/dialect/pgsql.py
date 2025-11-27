# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

from __future__ import absolute_import  # noqa

from functools import wraps

from psycopg import errors

from restalchemy.storage.sql.dialect import base
from restalchemy.storage.sql.dialect import exceptions as exc

SAVEPOINT_EXP_MAP = {
    "savepoint": "SAVEPOINT {name};",
    "rollback": "ROLLBACK TO SAVEPOINT {name};",
    "release": "RELEASE SAVEPOINT {name};",
}


def handle_database_errors(func):
    """
    A decorator to handle PostgreSQL database errors.

    This decorator catches specific database errors from the
    `psycopg` library and raises them as :class:`.DeadLock` or
    :class:`.Conflict` exceptions when appropriate.

    :param func: The function to be wrapped.
    :type func: callable
    :return: A function that wraps `func` and handles database errors.
    :rtype: callable
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except errors.DeadlockDetected as e:
            raise exc.DeadLock(code=e.sqlstate, message=str(e))
        except (errors.UniqueViolation, errors.ForeignKeyViolation) as e:
            raise exc.Conflict(code=e.sqlstate, message=str(e))

    return wrapper


class PgSQLInsert(base.BaseInsertCommand):

    EXPRESSION = 'INSERT INTO "%s" (%s) VALUES (%s)'

    @handle_database_errors
    def execute(self):
        """
        Executes the PostgreSQL insert command.

        This method utilizes the base class's execute method to perform the
        command execution. It is decorated with `handle_database_errors` to
        handle any PostgreSQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class PgSQLUpdate(base.BaseUpdateCommand):

    EXPRESSION = 'UPDATE "%s" SET %s WHERE %s'

    @handle_database_errors
    def execute(self):
        """
        Executes the PostgreSQL update command.

        This method utilizes the base class's execute method to perform the
        command execution. It is decorated with `handle_database_errors` to
        handle any PostgreSQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class PgSQLDelete(base.BaseDeleteCommand):

    EXPRESSION = 'DELETE FROM "%s" WHERE %s'

    @handle_database_errors
    def execute(self):
        """
        Executes the PostgreSQL delete command.

        This method utilizes the base class's execute method to perform the
        command execution. It is decorated with `handle_database_errors` to
        handle any PostgreSQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class PgSQLBatchDelete(base.BaseBatchDelete):

    EXPRESSION_IN = 'DELETE FROM "%s" WHERE %s = ANY(%s)'
    EXPRESSION_FILTER = 'DELETE FROM "%s" WHERE %s'

    @handle_database_errors
    def execute(self):
        """
        Executes the PostgreSQL batch delete command.

        This method utilizes the base class's execute method to perform the
        command execution. It is decorated with `handle_database_errors` to
        handle any PostgreSQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class PgSQLSelect(base.BaseSelectCommand):

    EXPRESSION = 'SELECT %s FROM "%s"'

    @handle_database_errors
    def execute(self):
        """
        Executes the PostgreSQL select command.

        This method utilizes the base class's execute method to perform the
        command execution. It is decorated with `handle_database_errors` to
        handle any PostgreSQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class PgSQLCustomSelect(base.BaseCustomSelectCommand):

    EXPRESSION = 'SELECT %s FROM "%s"'

    @handle_database_errors
    def execute(self):
        """
        Executes the PostgreSQL custom select command.

        This method utilizes the base class's execute method to perform the
        command execution. It is decorated with `handle_database_errors` to
        handle any PostgreSQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class PgSQLCount(base.BaseCountCommand):

    EXPRESSION = 'SELECT COUNT(*) as count FROM "%s"'

    @handle_database_errors
    def execute(self):
        """
        Executes the PostgreSQL count command.

        This method utilizes the base class's execute method to perform the
        command execution. It is decorated with `handle_database_errors` to
        handle any PostgreSQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class PgSqlOrmDialectCommand(base.BaseOrmDialectCommand):

    @handle_database_errors
    def execute(self):
        """
        Executes the PostgreSQL ORM command.

        This method compiles the query using the `get_statement` method and
        retrieves the values required for the query execution using the
        `get_values` method. Subsequently, it executes the SQL command using
        the parent class's `execute` method, passing the compiled statement
        and values to it. It is decorated with `handle_database_errors` to
        handle any PostgreSQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the query execution.
        """

        return super().execute()


class PgSQLDialect(base.AbstractDialect):

    DIALECT_NAME = "postgresql"

    def orm_command(self, table, query, session):
        """
        Creates a new PostgreSQL ORM command for the given table, query, and
        session.

        This method creates an instance of `PgSqlOrmDialectCommand` and
        initializes it with the given table, query, and session.

        :param table: The table to be used in the ORM dialect command.
        :param query: The query object that contains the SQL query to be
            compiled.
        :param session: The session to be used for executing the command.
        :return: The created PostgreSQL ORM command.
        :rtype: PgSqlOrmDialectCommand
        """

        return PgSqlOrmDialectCommand(table, query, session=session)

    def insert(self, table, data, session):
        """
        Inserts data into the specified table using a PostgreSQL dialect command.

        This method creates an instance of `PgSQLInsert` to insert the
        provided data into the given table within the specified session
        context.

        :param table: The table into which data is to be inserted.
        :param data: The data to be inserted into the table.
        :param session: The session to be used for executing the insert
            command.
        :return: An instance of `PgSQLInsert` configured with the table, data,
            and session.
        :rtype: PgSQLInsert
        """
        return PgSQLInsert(table, data, session=session)

    def update(self, table, ids, data, session):
        """
        Updates records in the specified table using a PostgreSQL dialect
        command.

        This method creates an instance of `PgSQLUpdate` to update records
        identified by the provided IDs in the given table with the specified
        data within the session context.

        :param table: The table where records are to be updated.
        :param ids: The IDs of the records to be updated.
        :param data: The data to update the records with.
        :param session: The session to be used for executing the update
            command.
        :return: An instance of `PgSQLUpdate` configured with the table,
            IDs, data, and session.
        :rtype: PgSQLUpdate
        """

        return PgSQLUpdate(table, ids, data, session=session)

    def delete(self, table, ids, session):
        """
        Deletes records from the specified table using a PostgreSQL dialect
        command.

        This method creates an instance of `PgSQLDelete` to delete
        records identified by the provided IDs from the given table within
        the session context.

        :param table: The table from which records are to be deleted.
        :param ids: The IDs of the records to be deleted.
        :param session: The session to be used for executing the delete
            command.
        :return: An instance of `PgSQLDelete` configured with the table, IDs,
            and session.
        :rtype: PgSQLDelete
        """

        return PgSQLDelete(table, ids, session=session)

    def select(
        self,
        table,
        filters,
        session,
        limit=None,
        order_by=None,
        locked=False,
    ):
        """
        Retrieves records from the specified table using a PostgreSQL dialect
        command.

        This method creates an instance of `PgSQLSelect` to select records
        from the given table based on the provided filters, with optional
        limit, order by, and locking constraints, within the session context.

        :param table: The table from which records are to be retrieved.
        :param filters: The filters to be used for selecting the records.
        :param session: The session to be used for executing the select
            command.
        :param limit: The maximum number of records to be retrieved.
        :type limit: int, optional
        :param order_by: The ordering criteria for the selected records.
        :param locked: Whether to lock the selected records for update.
            Defaults to False.
        :type locked: bool
        :return: An instance of `PgSQLSelect` configured with the table,
            filters, session, limit, order by, and locked parameters.
        :rtype: PgSQLSelect
        """
        return PgSQLSelect(
            table=table,
            session=session,
            filters=filters,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )

    def custom_select(
        self,
        table,
        session,
        where_conditions,
        where_values,
        limit=None,
        order_by=None,
        locked=False,
    ):
        """
        Retrieves records from the specified table using a custom PostgreSQL
        dialect command.

        This method creates an instance of `PgSQLCustomSelect` to select
        records from the given table based on the provided where conditions
        and values, with optional limit, order by, and locking constraints,
        within the session context.

        :param table: The table from which records are to be retrieved.
        :param session: The session to be used for executing the select
            command.
        :param where_conditions: The conditions for the WHERE clause in the
            SQL statement.
        :param where_values: The values for the WHERE clause in the SQL
            statement.
        :param limit: The maximum number of records to be retrieved.
        :type limit: int, optional
        :param order_by: The ordering criteria for the selected records.
        :param locked: Whether to lock the selected records for update.
            Defaults to False.
        :type locked: bool
        :return: An instance of `PgSQLCustomSelect` configured with the table,
            where conditions, where values, session, limit, order by, and
            locked parameters.
        :rtype: PgSQLCustomSelect
        """
        return PgSQLCustomSelect(
            table=table,
            session=session,
            where_conditions=where_conditions,
            where_values=where_values,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )

    def count(self, table, filters, session):
        """
        Retrieves the count of records from the specified table based on the
        provided filters.

        This method creates an instance of `PgSQLCount` to count records
        from the given table using the specified session and filters.

        :param table: The table from which records are to be counted.
        :param filters: The filters to be used for counting the records.
        :param session: The session to be used for executing the count
            command.
        :return: An instance of `PgSQLCount` configured with the table,
            filters, and session parameters.
        :rtype: PgSQLCount
        """
        return PgSQLCount(
            table=table,
            session=session,
            filters=filters,
        )
