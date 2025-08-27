# Copyright 2018 Eugene Frolov <eugene@frolov.net.ru>
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
from collections import abc as collections_abc
import logging

from restalchemy.dm import filters
from restalchemy.dm import types
from restalchemy.storage.sql.dialect.query_builder import common


LOG = logging.getLogger(__name__)


class AbstractClause(metaclass=abc.ABCMeta):

    def __init__(self, column, value_type, value, session):
        super(AbstractClause, self).__init__()
        self._value = self._convert_value(value_type, value)
        self._column = column
        self._session = session

    def _convert_value(self, value_type, value):
        return value_type.to_simple_type(value)

    @property
    def value(self):
        return self._value

    @property
    def column(self):
        return (
            self._column.compile()
            if isinstance(self._column, common.ColumnFullPath)
            else self._column
        )

    @abc.abstractmethod
    def construct_expression(self):
        raise NotImplementedError()


class EQ(AbstractClause):

    def construct_expression(self):
        return f"{self.column} = %s"


class NE(AbstractClause):

    def construct_expression(self):
        return f"{self.column} <> %s"


class GT(AbstractClause):

    def construct_expression(self):
        return f"{self.column} > %s"


class GE(AbstractClause):

    def construct_expression(self):
        return f"{self.column} >= %s"


class LT(AbstractClause):

    def construct_expression(self):
        return f"{self.column} < %s"


class LE(AbstractClause):

    def construct_expression(self):
        return f"{self.column} <= %s"


class Is(AbstractClause):

    def construct_expression(self):
        return f"{self.column} IS %s"


class IsNot(AbstractClause):

    def construct_expression(self):
        return f"{self.column} IS NOT %s"


class In(AbstractClause):

    def _convert_value(self, value_type, value):
        # Note(efrolov): Replace empty list with [Null]. Some SQL servers
        #                forbid empty lists in "in" operator.
        return [value_type.to_simple_type(item) for item in value] or [None]


class MySqlIn(In):

    def construct_expression(self):
        return f"{self.column} IN %s"


class PostgreSqlIn(In):

    def construct_expression(self):
        return f"{self.column} = ANY(%s)"


class MySqlNotIn(In):

    def construct_expression(self):
        return f"{self.column} NOT IN %s"


class PostgreSqlNotIn(In):

    def construct_expression(self):
        return f"{self.column} != ANY(%s)"


class PostgreSqlIs(Is):

    def construct_expression(self):
        return f"{self.column} IS NOT DISTINCT FROM (%s)"


class PostgreSqlIsNot(IsNot):

    def construct_expression(self):
        return f"{self.column} IS DISTINCT FROM (%s)"


class Like(AbstractClause):

    def construct_expression(self):
        return ("%s LIKE " % self.column) + "%s"


class NotLike(AbstractClause):

    def construct_expression(self):
        return ("%s NOT LIKE " % self.column) + "%s"


class AbstractExpression(metaclass=abc.ABCMeta):

    def __init__(self, *clauses):
        super(AbstractExpression, self).__init__()
        self._clauses = clauses

    def extend_clauses(self, clauses):
        self._clauses = self._clauses + clauses

    @property
    def clauses(self):
        return self._clauses

    @property
    def value(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def construct_expression(self):
        raise NotImplementedError()


class ClauseList(AbstractExpression):
    @property
    def value(self):
        res = []
        for val in self._clauses:
            if isinstance(val, AbstractExpression):
                res.extend(val.value)
            else:
                res.append(val.value)
        return res

    @property
    def operator(self):
        raise NotImplementedError

    def construct_expression(self):
        clause_count = len(self._clauses)

        if clause_count == 0:
            return ""

        if clause_count == 1:
            return self._clauses[0].construct_expression()

        joined = f" {self.operator} ".join(
            clause.construct_expression() for clause in self._clauses
        )
        return f"({joined})"


class AND(ClauseList):
    operator = "AND"


class OR(ClauseList):
    operator = "OR"


FILTER_MAPPING = {
    "mysql": {
        filters.EQ: EQ,
        filters.NE: NE,
        filters.GT: GT,
        filters.GE: GE,
        filters.LE: LE,
        filters.LT: LT,
        filters.Is: Is,
        filters.IsNot: IsNot,
        filters.In: MySqlIn,
        filters.NotIn: MySqlNotIn,
        filters.Like: Like,
        filters.NotLike: NotLike,
    },
    "postgresql": {
        filters.EQ: EQ,
        filters.NE: NE,
        filters.GT: GT,
        filters.GE: GE,
        filters.LE: LE,
        filters.LT: LT,
        filters.Is: PostgreSqlIs,
        filters.IsNot: PostgreSqlIsNot,
        filters.In: PostgreSqlIn,
        filters.NotIn: PostgreSqlNotIn,
        filters.Like: Like,
        filters.NotLike: NotLike,
    },
}

FILTER_EXPR_MAPPING = {
    filters.AND: AND,
    filters.OR: OR,
}


class AsIsType(types.BaseType):

    def validate(self, value):
        return True

    def to_simple_type(self, value):
        return value

    def from_simple_type(self, value):
        return value

    def from_unicode(self, value):
        return value


def convert_filters(model, filters_root, session):
    filters_root = filters_root or filters.AND()
    if isinstance(filters_root, filters.AbstractExpression):
        return iterate_filters(model, filters_root, session=session)
    return iterate_filters(
        model,
        filters.AND(filters_root),
        session=session,
    )


def iterate_filters(model, filter_list, session):
    # Just expression
    if isinstance(filter_list, filters.AbstractExpression):
        clauses = iterate_filters(model, filter_list.clauses, session)
        return FILTER_EXPR_MAPPING[type(filter_list)](*clauses)

    # Tuple of causes from expression
    if isinstance(filter_list, tuple):
        clauses = []
        for cause in filter_list:
            c_causes = iterate_filters(model, cause, session)
            if isinstance(cause, filters.AbstractExpression):
                clauses.append(c_causes)
            else:
                clauses.extend(c_causes)
        return clauses

    # old style mappings (dict, multidict)
    if isinstance(filter_list, collections_abc.Mapping):
        clauses = []
        for name, filt in filter_list.items():
            if isinstance(model, common.TableAlias):
                value_type = (
                    model.original.model.properties.properties[
                        name
                    ].get_property_type()
                ) or AsIsType()
                column = model.get_column_by_name(
                    name,
                    wrap_alias=False,
                )
            else:
                value_type = (
                    model.properties.properties[name].get_property_type()
                ) or AsIsType()
                column = session.engine.escape(name)
            # Make API compatible with previous versions.
            if not isinstance(filt, filters.AbstractClause):
                LOG.warning(
                    "DEPRECATED: pleases use %s wrapper for filter value",
                    filters.EQ,
                )
                clauses.append(EQ(column, value_type, filt, session=session))
                continue

            try:
                clauses.append(
                    FILTER_MAPPING[session.engine.dialect.name][type(filt)](
                        column,
                        value_type,
                        filt.value,
                        session=session,
                    ),
                )
            except KeyError:
                raise ValueError(
                    "Can't convert API filter to SQL storage "
                    "filter. Unknown filter %s" % filt
                )
        return clauses

    raise ValueError("Unknown type of filters: %s" % filter_list)
