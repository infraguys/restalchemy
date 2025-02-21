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

import abc

from restalchemy.storage.sql.dialect.query_builder import q
from restalchemy.storage.sql import filters as sql_filters


class AbstractProcessResult(metaclass=abc.ABCMeta):

    def __init__(self, result, session):
        self._result = result
        self._session = session

    def get_count(self):
        """
        Retrieves the number of rows affected by the query.

        :return: The number of rows affected by the executed SQL statement.
        :rtype: int
        """

        return self._result.rowcount

    @property
    def rows(self):
        """
        Retrieves all rows from the executed SQL statement.

        :return: All rows from the executed SQL statement.
        :rtype: list
        """
        return self.get_rows()

    @abc.abstractmethod
    def fetchall(self):
        """
        Retrieves all rows from the executed SQL statement.

        :return: All rows from the executed SQL statement.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_rows(self):
        """
        Retrieves all rows from the executed SQL statement.

        :return: All rows from the executed SQL statement.
        :rtype: list
        """
        raise NotImplementedError()


class BaseProcessResult(AbstractProcessResult):

    def __init__(self, result, session):
        """
        Initializes the BaseProcessResult object.

        :param result: The result of the executed SQL statement.
        :param session: The session object used for the execution
            of the SQL statement.
        """
        super(BaseProcessResult, self).__init__(result, session)
        self._rows = None

    def fetchall(self):
        """
        Retrieves all rows from the executed SQL statement.

        :return: All rows from the executed SQL statement.
        """
        for row in self._result:
            yield row

    def get_rows(self):
        """
        Retrieves all rows from the executed SQL statement and caches them.

        If the rows have not been previously retrieved, it fetches all rows
        from the result and stores them in the `_rows` attribute. Otherwise,
        it returns the cached rows.

        :return: All rows from the executed SQL statement.
        :rtype: list
        """

        if self._rows is None:
            self._rows = self._result.fetchall()
        return self._rows


class BaseOrmProcessResult(BaseProcessResult):

    def __init__(self, result, query, session):
        """
        Initializes the BaseOrmProcessResult object.

        :param result: The result of the executed ORM query
        :param query: The ORM query object used for the execution
            of the SQL statement
        :param session: The session object used for the execution
            of the SQL statement
        """
        super(BaseOrmProcessResult, self).__init__(
            result=result,
            session=session,
        )
        self._query = query
        self._rows = None

    def fetchall(self):
        """
        Retrieves all rows from the executed ORM query.

        :return: All rows from the executed ORM query, parsed into objects.
        """
        for row in self._result:
            yield self._query.parse_row(row)

    def get_rows(self):
        """
        Retrieves all rows from the executed ORM query, parsing them into
        objects and caching the result for future access.

        If the rows have not been previously retrieved, it fetches all rows
        from the result, parses them using the query's result parser, and
        stores them in the `_rows` attribute. Otherwise, it returns the cached
        rows.

        :return: All rows from the executed ORM query, parsed into objects.
        :rtype: list
        """

        if self._rows is None:
            self._rows = self._query.parse_results(self._result.fetchall())
        return self._rows


class AbstractDialectCommand(metaclass=abc.ABCMeta):

    def __init__(self, table, data, session):
        """
        Initializes the AbstractDialectCommand with the given table, data,
        and session.

        :param table: The table associated with the command.
        :param data: The data to be used in the command.
        :param session: The session to be used for executing the command.
        """

        self._table = table
        self._data = data
        self._session = session

    @abc.abstractmethod
    def get_values(self):
        """
        Retrieves the values to be used in the SQL command execution.

        This method should be implemented by subclasses to provide the logic
        for extracting or constructing the values required for the SQL
        statement. The values should be returned in a format compatible with
        the SQL execution context.

        :return: A collection of values to be used in the SQL command.
        """

        raise NotImplementedError()

    @abc.abstractmethod
    def get_statement(self):
        """
        Retrieves the SQL statement to be used in the command execution.

        This method should be implemented by subclasses to provide the logic
        for constructing the SQL statement required for the command. The
        statement should be returned as a string, with placeholders for the
        values to be inserted.

        :return: The SQL statement to be used in the command execution.
        :rtype: str
        """
        raise NotImplementedError()

    def execute(self):
        """
        Executes the SQL command using the values and statement provided by
        the abstract methods.

        :return: A ProcessResult object containing the result of the SQL
            command.
        """
        values = self.get_values()
        statement = self.get_statement()
        return BaseProcessResult(
            result=self._session.execute(statement, values),
            session=self._session,
        )


class BaseInsertCommand(AbstractDialectCommand):

    EXPRESSION = "INSERT INTO `%s` (%s) VALUES (%s)"

    def get_values(self):
        """
        Retrieves the values to be inserted into the SQL command.

        This method iterates over the column names of the table and collects
        the corresponding data values into a tuple. These values are then
        used as the data to be inserted into the SQL statement.

        :return: A tuple of values corresponding to the column names of the
            table.
        :rtype: tuple
        """

        values = tuple()
        for column_name in self._table.get_column_names(self._session):
            values += (self._data[column_name],)
        return values

    def get_statement(self):
        """
        Retrieves the SQL statement to be used in the command execution.

        This method constructs the SQL statement to be used in the command
        execution by inserting the table name and column names into the
        EXPRESSION template string. The column names are escaped according to
        the dialect's escaping rules, and the placeholders for the values are
        created by repeating the string "%s" for each column.

        :return: The SQL statement to be used in the command execution.
        :rtype: str
        """
        column_names = self._table.get_escaped_column_names(self._session)
        return self.EXPRESSION % (
            self._table.name,
            ", ".join(column_names),
            ", ".join(["%s"] * len(column_names)),
        )


class BaseUpdateCommand(AbstractDialectCommand):

    EXPRESSION = "UPDATE `%s` SET %s WHERE %s"

    def __init__(self, table, ids, data, session):
        """
        Initializes the BaseUpdateCommand with the given table, ids, data,
        and session.

        :param table: The table associated with the command.
        :param ids: The ids to be updated.
        :param data: The data to be used in the command.
        :param session: The session to be used for executing the command.
        """
        super().__init__(table, data, session=session)
        self._ids = ids

    def get_values(self):
        """
        Retrieves the values to be updated in the SQL command.

        This method iterates over the column names of the table (excluding the
        primary key) and collects the corresponding data values into a tuple.
        Additionally, it collects the primary key values from the `_ids` attr
        into the same tuple. These values are then used as the data to be
        updated in the SQL statement.

        :return: A tuple of values corresponding to the column names of the
            table.
        :rtype: tuple
        """
        values = tuple()
        column_names = self._table.get_column_names(
            self._session,
            with_pk=False,
        )
        pk_names = self._table.get_pk_names(session=self._session)
        for column_name in column_names:
            values += (self._data[column_name],)
        for column_name in pk_names:
            values += (self._ids[column_name],)
        return values

    def get_statement(self):
        """
        Retrieves the SQL statement to be used in the command execution.

        This method constructs the SQL statement to be used in the command
        execution by inserting the table name, column names, and primary key
        names into the EXPRESSION template string. The column names are escaped
        according to the dialect's escaping rules, and the placeholders for the
        values are created by repeating the string "%s" for each column.

        :return: The SQL statement to be used in the command execution.
        :rtype: str
        """
        column_names = self._table.get_escaped_column_names(
            session=self._session,
            with_pk=False,
        )
        pk_names = self._table.get_escaped_pk_names(session=self._session)
        return self.EXPRESSION % (
            self._table.name,
            ", ".join([f"{name} = %s" for name in column_names]),
            " AND ".join([f"{name} = %s" for name in pk_names]),
        )


class BaseDeleteCommand(AbstractDialectCommand):

    EXPRESSION = "DELETE FROM `%s` WHERE %s"

    def __init__(self, table, ids, session):
        """
        Initializes the BaseDeleteCommand with the given table, ids, and
        session.

        :param table: The table associated with the command.
        :param ids: The ids to be used for deleting the rows.
        :param session: The session to be used for executing the command.
        """
        super().__init__(table=table, data={}, session=session)
        self._ids = ids

    def get_values(self):
        """
        Retrieves the values to be used in the SQL command execution.

        This method iterates over the primary key column names of the table
        and collects the corresponding data values into a tuple. These
        values are then used as the data to be deleted in the SQL statement.

        :return: A tuple of values corresponding to the primary key column
            names of the table.
        :rtype: tuple
        """
        values = tuple()
        pk_names = self._table.get_pk_names(session=self._session)
        for column_name in pk_names:
            values += (self._ids[column_name],)
        return values

    def get_statement(self):
        """
        Retrieves the SQL statement to be used in the command execution.

        This method constructs the SQL statement to be used in the command
        execution by inserting the table name and primary key column names
        into the EXPRESSION template string.

        :return: The SQL statement to be used in the command execution.
        :rtype: str
        """
        pk_names = self._table.get_escaped_pk_names(session=self._session)
        return self.EXPRESSION % (
            self._table.name,
            " AND ".join([f"{name} = %s" for name in pk_names]),
        )


class BaseBatchDelete(AbstractDialectCommand):

    EXPRESSION_IN = "DELETE FROM `%s` WHERE %s in %s"
    EXPRESSION_FILTER = "DELETE FROM `%s` WHERE %s"

    def __init__(self, table, snapshot, session):
        """
        Initializes the BaseBatchDelete with the given table, snapshot, and
        session.

        :param table: The table associated with the command.
        :param snapshot: The snapshot containing the rows to be deleted.
        :param session: The session to be used for executing the command.
        """
        super().__init__(
            table=table,
            data={},
            session=session,
        )
        self._snapshot = snapshot
        self._pk_keys = self._table.get_escaped_pk_names(session=session)
        keys_count = len(self._pk_keys)
        if keys_count == 1:
            self._is_multiple_primary_key = False
        elif keys_count > 1:
            self._is_multiple_primary_key = True
        else:
            raise ValueError(
                f"The model with table {table!r} has 0 primary keys"
            )

    def _get_values(self):
        """
        Retrieves the values to be used in the SQL command execution.

        This method iterates over the snapshot rows and collects the values
        corresponding to the primary key column names of the table into a
        list. These values are then used as the data to be deleted in the SQL
        statement.

        :return: A list of values corresponding to the primary key column
            names of the table.
        :rtype: list
        """
        values = []
        for snapshot in self._snapshot:
            for key in self._table.get_pk_names(session=self._session):
                values.append(snapshot[key])
        return values

    def _get_multiple_primary_key_values(self):
        """
        Retrieves the values to be used in the SQL command execution when
        multiple primary keys are declared for the table.

        :return: A list of values corresponding to the primary key column
            names of the table.
        :rtype: list
        """
        return self._get_values()

    def _get_single_primary_key_values(self):
        """
        Retrieves the primary key values for tables with a single primary key.

        This method wraps the result of `_get_multiple_primary_key_values` in a
        list to optimize the `in` operation for SQL command execution.

        :return: A list containing the primary key values.
        :rtype: list
        """
        # NOTE(efrolov): Wrap to list for `in` optimization
        return [self._get_multiple_primary_key_values()]

    def get_values(self):
        """
        Retrieves the values to be used in the SQL command execution.

        Depending on the presence of multiple primary keys declared for the
        table,this method returns either a list of values corresponding to
        the primary key column names of the table or a list containing the
        primary key values for tables with a single primary key.

        :return: List of values to be used in the SQL command execution.
        :rtype: list
        """
        return (
            self._get_multiple_primary_key_values()
            if self._is_multiple_primary_key
            else self._get_single_primary_key_values()
        )

    def _get_single_primary_key_statement(self):
        """
        Retrieves the SQL statement to be used in the command execution
        when a single primary key is declared for the table.

        This method constructs the SQL statement to be used in the command
        execution by inserting the table name and primary key column name
        into the EXPRESSION_IN template string.

        :return: The SQL statement to be used in the command execution.
        :rtype: str
        """
        return self.EXPRESSION_IN % (
            self._table.name,
            self._pk_keys[0],
            "%s",
        )

    def _get_multiple_primary_key_statement(self):
        """
        Retrieves the SQL statement to be used in the command execution
        when multiple primary keys are declared for the table.

        This method constructs the SQL statement to be used in the command
        execution by inserting the table name and primary key column names
        into the EXPRESSION_FILTER template string. The `where_condition` is
        constructed by joining the condition for each primary key column
        with the `OR` operator.

        :return: The SQL statement to be used in the command execution.
        :rtype: str
        """
        where_part = " AND ".join([f"{key} = %s" for key in self._pk_keys])
        where_condition = " OR ".join(
            [where_part for _ in range(len(self._snapshot))]
        )
        return self.EXPRESSION_FILTER % (
            self._table.name,
            where_condition,
        )

    def get_statement(self):
        """
        Retrieves the SQL statement to be used in the command execution.

        This method constructs the SQL statement based on whether the table
        has multiple primary keys or a single primary key. It selects the
        appropriate expression template and formats it with the table name
        and primary key conditions.

        :return: The SQL statement to be used in the command execution.
        :rtype: str
        """

        return (
            self._get_multiple_primary_key_statement()
            if self._is_multiple_primary_key
            else self._get_single_primary_key_statement()
        )


class BaseBasicSelectCommand(AbstractDialectCommand):

    EXPRESSION = "SELECT %s FROM `%s`"

    def __init__(
        self,
        table,
        session,
        limit=None,
        order_by=None,
        locked=False,
    ):
        """
        Initializes the BaseBasicSelectCommand with the given parameters.

        :param table: The table from which data is to be selected.
        :param session: The session to be used for executing the command.
        :param limit: The maximum number of rows to return. Optional.
        :type limit: int, optional
        :param order_by: A dictionary specifying the columns to order by and
            their sort types. Optional.
        :param locked: Whether to lock the selected rows for update. Defaults
            to False.
        :type locked: bool
        """

        super().__init__(table=table, data={}, session=session)
        self._limit = limit
        self._order_by = order_by
        self._locked = locked

    def construct_limit(self):
        """
        Constructs the LIMIT clause for the SQL statement based on the given
        limit.

        :return: The LIMIT clause for the SQL statement.
        :rtype: str
        """
        if self._limit:
            return " LIMIT " + str(self._limit)
        return ""

    def construct_locked(self):
        """
        Constructs the FOR UPDATE clause for the SQL statement based on the
        given locked status.

        :return: The FOR UPDATE clause for the SQL statement.
        :rtype: str
        """
        if self._locked:
            return " FOR UPDATE"
        return ""

    def construct_order_by(self):
        """
        Constructs the ORDER BY clause for the SQL statement based on the
        given order_by.

        :return: The ORDER BY clause for the SQL statement.
        :rtype: str
        """

        if self._order_by:
            res = []
            for name, sorttype in self._order_by.items():
                sorttype = sorttype.upper()
                if sorttype not in ["ASC", "DESC", "", None]:
                    raise ValueError(f"Unknown order: {sorttype}.")
                res.append(
                    f"{self._session.engine.escape(name)} {sorttype or 'ASC'}"
                )
            return " ORDER BY " + ", ".join(res)
        return ""


class BaseSelectCommand(BaseBasicSelectCommand):

    def __init__(
        self,
        table,
        session,
        filters=None,
        limit=None,
        order_by=None,
        locked=False,
    ):
        """
        Initializes the BaseSelectCommand with the given parameters.

        :param table: The table from which data is to be selected.
        :param session: The session to be used for executing the command.
        :param filters: The filters to be applied to the query. Optional.
        :param limit: The maximum number of rows to return. Optional.
        :type limit: int, optional
        :param order_by: A dictionary specifying the columns to order by
            and their sort types. Optional.
        :param locked: Whether to lock the selected rows for update. Defaults
            to False.
        :type locked: bool
        """
        super(BaseSelectCommand, self).__init__(
            table=table,
            session=session,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )
        self._filters = sql_filters.convert_filters(
            model=self._table.model,
            filters_root=filters,
            session=session,
        )

    def get_values(self):
        """
        Retrieves the values to be used in the SQL command execution.

        This method returns the values part of the WHERE clause of the
        SQL statement, which is used to filter the results of the query.

        :return: The values part of the WHERE clause.
        :rtype: tuple
        """

        return self._filters.value

    def construct_where(self):
        """
        Constructs the WHERE clause part of the SQL statement.

        This method returns the WHERE clause part of the SQL statement,
        which is used to filter the results of the query.

        :return: The WHERE clause part of the SQL statement.
        :rtype: str
        """
        return self._filters.construct_expression()

    def get_statement(self):
        sql = self.EXPRESSION % (
            ", ".join(self._table.get_escaped_column_names(self._session)),
            self._table.name,
        )
        filt = self.construct_where()

        return (
            (f"{sql} WHERE {filt}" if filt else sql)
            + self.construct_order_by()
            + self.construct_limit()
            + self.construct_locked()
        )


class BaseCustomSelectCommand(BaseBasicSelectCommand):

    def __init__(
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
        :param table: Table to select from
        :type table: :class:`~restalchemy.storage.sql.tables.SQLTable`
        :param where_conditions: Conditions for the WHERE clause in the SQL
            statement.
        :param where_values: Values for the WHERE clause in the SQL statement.
        :type where_values: tuple
        :param session: Session to use for the query
        :type session: :class:`~restalchemy.storage.sql.sessions.SQLSession`
        :param limit: Maximum number of records to return
        :type limit: int
        :param order_by: Fields to order the records by
        :type order_by: dict
        :param locked: Whether to lock the records using a FOR UPDATE clause
        :type locked: bool
        """
        super().__init__(
            table=table,
            session=session,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )
        self._where_conditions = where_conditions
        self._where_values = where_values

    def get_values(self):
        """
        Retrieves the values to be used in the SQL command execution.

        This method returns the values part of the WHERE clause of the
        SQL statement, which is used to filter the results of the query.

        :return: The values part of the WHERE clause.
        :rtype: tuple
        """
        return self._where_values

    def construct_where(self):
        """
        Constructs the WHERE clause part of the SQL statement.

        This method returns the WHERE clause part of the SQL statement,
        which is used to filter the results of the query.

        :return: The WHERE clause part of the SQL statement.
        :rtype: str
        """
        return self._where_conditions

    def get_statement(self):
        """
        Retrieves the full SQL statement for the query.

        :return: The full SQL statement for the query.
        :rtype: str
        """
        sql = self.EXPRESSION % (
            ", ".join(
                self._table.get_escaped_column_names(
                    self._session,
                )
            ),
            self._table.name,
        )
        return (
            sql
            + " WHERE "
            + self.construct_where()
            + self.construct_order_by()
            + self.construct_limit()
            + self.construct_locked()
        )


class BaseCountCommand(BaseSelectCommand):

    EXPRESSION = "SELECT COUNT(*) as count FROM `%s`"

    def __init__(self, table, session, filters=None):
        """
        Initializes the BaseCountCommand with the provided table, session,
        and optional filters.

        :param table: The table from which to perform the count query.
        :param session: The session used to execute the SQL command.
        :param filters: Optional filters to apply to the count query.
        :type filters: Any, optional
        """

        super().__init__(table=table, session=session, filters=filters)

    def get_statement(self):
        """
        Retrieves the full SQL statement for the query.

        :return: The full SQL statement for the query.
        :rtype: str
        """
        sql = self.EXPRESSION % (self._table.name)
        filt = self.construct_where()

        return f"{sql} WHERE {filt}" if filt else sql


class BaseOrmDialectCommand(AbstractDialectCommand):

    def __init__(self, table, query, session):
        """
        Initializes the BaseOrmDialectCommand with the given table, query, and
        session.

        :param table: The table to be used in the ORM dialect command.
        :param query: The query object that contains the SQL query to be
            compiled.
        :param session: The session to be used for executing the command.
        """

        super().__init__(table=table, session=session, data=None)
        self._query = query

    def get_statement(self):
        """
        Compiles and retrieves the SQL statement for the query.

        This method utilizes the `compile` method of the query object
        to generate the SQL statement that represents the query.

        :return: The compiled SQL statement for the query.
        :rtype: str
        """

        return self._query.compile()

    def get_values(self):
        """
        Retrieves the values to be used in the SQL command execution.

        This method should be implemented by subclasses to provide the logic
        for extracting or constructing the values required for the SQL
        statement. The values should be returned in a format compatible with
        the SQL execution context.

        :return: A collection of values to be used in the SQL command.
        :rtype: iterable
        """
        return self._query.values()

    def execute(self):
        """
        Executes the SQL command associated with the query.

        This method compiles the query using the `get_statement` method and
        retrieves the values required for the query execution using the
        `get_values` method. Subsequently, it executes the SQL command using
        the parent class's `execute` method, passing the compiled statement and
        values to it. The result of the execution is then wrapped in a
        `BaseOrmProcessResult` object and returned.

        :return: The result of the query execution, wrapped in a
            `BaseOrmProcessResult` object.
        :rtype: BaseOrmProcessResult
        """
        return BaseOrmProcessResult(
            result=super().execute(),
            query=self._query,
            session=self._session,
        )


class BaseSqlOrm(object):

    @staticmethod
    def select(model, session):
        """
        Creates a new Q object for the given model and session.

        :param model: The model class for which the Q object is to be created.
        :param session: The session to be used for executing the query.
        :return: A new Q object instance.
        """
        return q.Q.select(model, session)


class AbstractDialect(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def DIALECT_NAME(self):
        """
        The name of the dialect as a string.

        This property must be overridden by subclasses to provide a valid
        dialect name.

        :return: The name of the dialect as a string.
        :rtype: str
        """
        raise NotImplementedError()

    def __init__(self):
        """
        Initializes the AbstractDialect instance.

        This constructor sets up the base SQL ORM for the dialect by
        creating an instance of BaseSqlOrm.

        """

        super(AbstractDialect, self).__init__()
        self._orm = BaseSqlOrm()

    @property
    def orm(self):
        """
        Retrieves the BaseSqlOrm instance associated with the dialect.

        This property returns the BaseSqlOrm instance that is used by the
        dialect for ORM operations.

        :return: The BaseSqlOrm instance associated with the dialect.
        :rtype: BaseSqlOrm
        """
        return self._orm

    @property
    def name(self):
        """
        Retrieves the name of the dialect as a string.

        This property returns the string value of the DIALECT_NAME property of
        the dialect.

        :return: The name of the dialect as a string.
        :rtype: str
        """
        return self.DIALECT_NAME

    @abc.abstractmethod
    def insert(self, table, data, session):
        """
        Inserts data into the specified table within the session context.

        This method should be implemented by subclasses to provide the logic
        for inserting the provided data into the given table using the
        specified session. The method should construct and execute an SQL
        insert command appropriate for the dialect.

        :param table: The table into which data is to be inserted.
        :param data: The data to be inserted into the table.
        :param session: The session to be used for executing the insert
            command.
        :raises NotImplementedError: If the method is not implemented by a
            subclass.
        """

        raise NotImplementedError()

    @abc.abstractmethod
    def update(self, table, ids, data, session):
        """
        Updates existing records in the specified table with the provided data
        within the session context.

        This method should be implemented by subclasses to provide the logic
        for updating existing records in the given table using the specified
        session. The method should construct and execute an SQL update command
        appropriate for the dialect.

        :param table: The table to be updated.
        :param ids: The IDs of the records to be updated.
        :type ids: list
        :param data: The data to be used for updating the records.
        :param session: The session to be used for executing the update
            command.
        :raises NotImplementedError: If the method is not implemented by a
            subclass.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(self, table, ids, session):
        """
        Deletes records from the specified table based on the provided IDs
        within the session context.

        This method should be implemented by subclasses to provide the logic
        for deleting records from the given table using the specified session.
        The method should construct and execute an SQL delete command
        appropriate for the dialect.

        :param table: The table from which records are to be deleted.
        :param ids: The IDs of the records to be deleted.
        :param session: The session to be used for executing the delete
            command.
        :raises NotImplementedError: If the method is not implemented by a
            subclass.
        """

        raise NotImplementedError()

    @abc.abstractmethod
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
        Retrieves records from the specified table based on the provided
        filters and ordering criteria, with optional limit and locking
        constraints, within the session context.

        This method should be implemented by subclasses to provide the logic
        for selecting records from the given table using the specified
        session. The method should construct and execute an SQL select command
        appropriate for the dialect.

        :param table: The table from which records are to be retrieved.
        :param filters: The filters to be used for selecting the records.
        :param session: The session to be used for executing the select
            command.
        :param limit: The maximum number of records to be retrieved.
        :type limit: int
        :param order_by: The ordering criteria to be used for selecting the
            records.
        :param locked: Whether or not to lock the records for this session.
        :type locked: bool
        :raises NotImplementedError: If the method is not implemented by a
            subclass.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def count(self, table, filters, session):
        """
        Retrieves the number of records in the specified table that match the
        given filters within the session context.

        This method should be implemented by subclasses to provide the logic
        for counting the records from the given table using the specified
        session. The method should construct and execute an SQL count command
        appropriate for the dialect.

        :param table: The table from which records are to be counted.
        :param filters: The filters to be used for counting the records.
        :param session: The session to be used for executing the count command.
        :raises NotImplementedError: If the method is not implemented by a
            subclass.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def orm_command(self, table, query, session):
        """
        Creates a new ORM command for the given table, query, and session.

        This method should be implemented by subclasses to provide the logic
        for creating an ORM command that is appropriate for the dialect.

        :param table: The table to be used in the ORM dialect command.
        :param query: The query object that contains the SQL query to be
            compiled.
        :param session: The session to be used for executing the command.
        :raises NotImplementedError: If the method is not implemented by a
            subclass.
        """
        raise NotImplementedError()

    @abc.abstractmethod
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
        Constructs and executes a custom SQL select command for the specified
        table, using the given session and where conditions.

        This method should be implemented by subclasses to provide the logic
        for selecting records based on custom where conditions and values, with
        optional limit, order by, and locking constraints.

        :param table: The table from which records are to be selected.
        :param session: The session to be used for executing the select
            command.
        :param where_conditions: The conditions for the WHERE clause in the SQL
            statement.
        :param where_values: The values for the WHERE clause in the SQL
            statement.
        :param limit: The maximum number of records to be retrieved.
        :type limit: int, optional
        :param order_by: The ordering criteria for the selected records.
        :param locked: Whether or not to lock the selected records for update.
        :type locked: bool
        :raises NotImplementedError: If the method is not implemented by a
            subclass.
        """

        raise NotImplementedError()
