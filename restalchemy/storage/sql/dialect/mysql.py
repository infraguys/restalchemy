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

from mysql.connector import errors

from restalchemy.storage.sql.dialect import base
from restalchemy.storage.sql.dialect import exceptions as exc

SAVEPOINT_EXP_MAP = {
    "savepoint": "SAVEPOINT {name};",
    "rollback": "ROLLBACK TO {name};",
    "release": "RELEASE SAVEPOINT {name};",
}


def handle_database_errors(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """
        A decorator to handle database errors.

        This decorator catches database errors from the
        ``mysql-connector-python`` library and raises them as
        :class:`.DeadLock` or :class:`.Conflict` exceptions when appropriate.

        :param func: The function to be wrapped.
        :type func: callable
        :return: A function that wraps `func` and handles database errors.
        :rtype: callable
        """
        try:
            return func(self, *args, **kwargs)
        except errors.DatabaseError as e:
            if e.errno == 1213:
                raise exc.DeadLock(code=e.sqlstate, message=e.msg)
            elif e.errno == 1062:
                raise exc.Conflict(code=e.sqlstate, message=e.msg)
            raise

    return wrapper


class MySQLInsert(base.BaseInsertCommand):

    @handle_database_errors
    def execute(self):
        """
        Executes the MySQL command.

        This method utilizes the base class's execute method to
        perform the command execution. It is decorated with
        `handle_database_errors` to handle any MySQL database
        errors that may occur during execution, such as deadlocks
        or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """

        return super().execute()


class MySQLUpdate(base.BaseUpdateCommand):

    @handle_database_errors
    def execute(self):
        """
        Executes the MySQL command.

        This method utilizes the base class's execute method to
        perform the command execution. It is decorated with
        `handle_database_errors` to handle any MySQL database
        errors that may occur during execution, such as deadlocks
        or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class MySQLDelete(base.BaseDeleteCommand):

    @handle_database_errors
    def execute(self):
        """
        Executes the MySQL command.

        This method utilizes the base class's execute method to
        perform the command execution. It is decorated with
        `handle_database_errors` to handle any MySQL database
        errors that may occur during execution, such as deadlocks
        or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class MySQLBatchDelete(base.BaseBatchDelete):

    @handle_database_errors
    def execute(self):
        """
        Executes the MySQL batch delete command.

        This method utilizes the base class's execute method to perform the
        batch delete operation. It is decorated with `handle_database_errors`
        to handle any MySQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """

        return super().execute()


class MySQLSelect(base.BaseSelectCommand):

    @handle_database_errors
    def execute(self):
        """
        Executes the MySQL select command.

        This method utilizes the base class's execute method to perform the
        select operation. It is decorated with `handle_database_errors` to
        handle any MySQL database errors that may occur during execution,
        such as deadlocks or conflicts, and raise appropriate exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class MySQLCustomSelect(base.BaseCustomSelectCommand):

    @handle_database_errors
    def execute(self):
        """
        Executes the MySQL custom select command.

        This method performs the custom select operation by invoking the base
        class's execute method. It is decorated with `handle_database_errors`
        to manage any MySQL database errors, such as deadlocks or conflicts,
        that may arise during the operation, and raises the appropriate
        exceptions.

        :return: The result of the command execution.
        """

        return super().execute()


class MySQLCount(base.BaseCountCommand):

    @handle_database_errors
    def execute(self):
        """
        Executes the MySQL count command.

        This method performs the count operation by invoking the base
        class's execute method. It is decorated with `handle_database_errors`
        to manage any MySQL database errors, such as deadlocks or conflicts,
        that may arise during the operation, and raises the appropriate
        exceptions.

        :return: The result of the command execution.
        """
        return super().execute()


class MySqlOrmDialectCommand(base.BaseOrmDialectCommand):

    @handle_database_errors
    def execute(self):
        """
        Executes the MySQL ORM command.

        This method compiles the query using the `get_statement` method and
        retrieves the values required for the query execution using the
        `get_values` method. Subsequently, it executes the SQL command using
        the parent class's `execute` method, passing the compiled statement
        and values to it. The result of the execution is then wrapped in a
        `BaseOrmProcessResult` object and returned.

        :return: The result of the query execution, wrapped in a
            `BaseOrmProcessResult` object.
        :rtype: BaseOrmProcessResult
        """
        return super().execute()


class MySQLDialect(base.AbstractDialect):

    DIALECT_NAME = "mysql"

    def orm_command(self, table, query, session):
        """
        Creates a new MySQL ORM command for the given table, query, and
        session.

        This method creates an instance of `MySqlOrmDialectCommand` and
        initializes it with the given table, query, and session.

        :param table: The table to be used in the ORM dialect command.
        :param query: The query object that contains the SQL query to be
            compiled.
        :param session: The session to be used for executing the command.
        :return: The created MySQL ORM command.
        :rtype: MySqlOrmDialectCommand
        """
        return MySqlOrmDialectCommand(
            table,
            query,
            session=session,
        )

    def insert(self, table, data, session):
        """
        Inserts data into the specified table using a MySQL dialect command.

        This method creates an instance of `MySQLInsert` to insert the
        provided data into the given table within the specified session
        context.

        :param table: The table into which data is to be inserted.
        :param data: The data to be inserted into the table.
        :param session: The session to be used for executing the insert
            command.
        :return: An instance of `MySQLInsert` configured with the table, data,
            and session.
        :rtype: MySQLInsert
        """

        return MySQLInsert(
            table,
            data,
            session=session,
        )

    def update(self, table, ids, data, session):
        """
        Updates records in the specified table using a MySQL dialect command.

        This method creates an instance of `MySQLUpdate` to update records
        identified by the provided IDs in the given table with the specified
        data within the session context.

        :param table: The table where records are to be updated.
        :param ids: The IDs of the records to be updated.
        :param data: The data to update the records with.
        :param session: The session to be used for executing the update
            command.
        :return: An instance of `MySQLUpdate` configured with the table,
            IDs, data, and session.
        :rtype: MySQLUpdate
        """

        return MySQLUpdate(
            table,
            ids,
            data,
            session=session,
        )

    def delete(self, table, ids, session):
        """
        Deletes records from the specified table using a MySQL dialect
        command.

        This method creates an instance of `MySQLDelete` to delete
        records identified by the provided IDs from the given table within
        the session context.

        :param table: The table from which records are to be deleted.
        :param ids: The IDs of the records to be deleted.
        :param session: The session to be used for executing the delete
            command.
        :return: An instance of `MySQLDelete` configured with the table, IDs,
            and session.
        :rtype: MySQLDelete
        """

        return MySQLDelete(
            table,
            ids,
            session=session,
        )

    def select(
        self, table, filters, session, limit=None, order_by=None, locked=False
    ):
        """
        Retrieves records from the specified table using a MySQL dialect
        command.

        This method creates an instance of `MySQLSelect` to select records
        from the given table based on the provided filters, with optional
        limit and order by constraints, within the session context.

        :param table: The table from which records are to be selected.
        :param filters: The filters to be used for selecting the records.
        :param session: The session to be used for executing the select
            command.
        :param limit: The maximum number of records to be retrieved.
        :type limit: int, optional
        :param order_by: The ordering criteria for the selected records.
        :param locked: Whether or not to lock the selected records for update.
        :type locked: bool
        :return: An instance of `MySQLSelect` configured with the table,
            filters, session, limit, order by, and locked parameters.
        :rtype: MySQLSelect
        """
        return MySQLSelect(
            table=table,
            filters=filters,
            session=session,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )

    def custom_select(
        self,
        table,
        where_conditions,
        where_values,
        session,
        limit=None,
        order_by=None,
        locked=False,
    ):
        """
        Retrieves records from the specified table using a custom MySQL
        dialect command.

        This method creates an instance of `MySQLCustomSelect` to select
        records from the given table based on the provided where conditions
        and values, with optional limit and order by constraints, within the
        session context.

        :param table: The table from which records are to be selected.
        :param where_conditions: The conditions for the WHERE clause in the
            SQL statement.
        :param where_values: The values for the WHERE clause in the SQL
            statement.
        :type where_values: tuple
        :param session: The session to be used for executing the select
            command.
        :param limit: The maximum number of records to be retrieved.
        :type limit: int, optional
        :param order_by: The ordering criteria for the selected records.
        :param locked: Whether or not to lock the selected records for update.
        :type locked: bool
        :return: An instance of `MySQLCustomSelect` configured with the table,
            where conditions, where values, session, limit, order by, and
            locked parameters.
        :rtype: MySQLCustomSelect
        """
        return MySQLCustomSelect(
            table=table,
            where_conditions=where_conditions,
            where_values=where_values,
            session=session,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )

    def count(self, table, filters, session):
        """
        Retrieves the count of records from the specified table using a
        custom MySQL dialect command.

        This method creates an instance of `MySQLCount` to count records
        from the given table based on the provided filters, with optional
        limit and order by constraints, within the session context.

        :param table: The table from which records are to be counted.
        :param filters: The filters to be used for counting the records.
        :param session: The session to be used for executing the count
            command.
        :return: An instance of `MySQLCount` configured with the table,
            filters, and session parameters.
        :rtype: MySQLCount
        """
        return MySQLCount(
            table=table,
            filters=filters,
            session=session,
        )
