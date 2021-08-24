# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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
import collections
import logging

import six

from restalchemy.dm import filters
from restalchemy.dm import types

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AbstractClause(object):

    def __init__(self, name, value_type, value):
        super(AbstractClause, self).__init__()
        self._value = self._convert_value(value_type, value)
        self._name = name

    def _convert_value(self, value_type, value):
        return value_type.to_simple_type(value)

    @property
    def value(self):
        return self._value

    @property
    def name(self):
        return self._name

    @abc.abstractmethod
    def construct_expression(self):
        raise NotImplementedError()


class EQ(AbstractClause):

    def construct_expression(self):
        return ("%s = " % self._name) + "%s"


class NE(AbstractClause):

    def construct_expression(self):
        return ("%s <> " % self._name) + "%s"


class GT(AbstractClause):

    def construct_expression(self):
        return ("%s > " % self._name) + "%s"


class GE(AbstractClause):

    def construct_expression(self):
        return ("%s >= " % self._name) + "%s"


class LT(AbstractClause):

    def construct_expression(self):
        return ("%s < " % self._name) + "%s"


class LE(AbstractClause):

    def construct_expression(self):
        return ("%s <= " % self._name) + "%s"


class Is(AbstractClause):

    def construct_expression(self):
        return ("%s IS " % self._name) + "%s"


class IsNot(AbstractClause):

    def construct_expression(self):
        return ("%s IS NOT " % self._name) + "%s"


class In(AbstractClause):

    def _convert_value(self, value_type, value):
        # Note(efrolov): Replace empty list with [Null]. Some SQL servers
        #                forbid empty lists in "in" operator.
        return [value_type.to_simple_type(item) for item in value] or [None]

    def construct_expression(self):
        return ("%s IN " % self._name) + "%s"


@six.add_metaclass(abc.ABCMeta)
class AbstractExpression(object):

    def __init__(self, *clauses):
        super(AbstractExpression, self).__init__()
        self._clauses = clauses

    @property
    def value(self):
        raise NotImplementedError

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
        return (
            "("
            + (" " + self.operator + " ").join(
                val.construct_expression() for val in self._clauses)
            + ")"
        ) if self._clauses else ""


class AND(ClauseList):
    operator = "AND"


class OR(ClauseList):
    operator = "OR"


FILTER_MAPPING = {
    filters.EQ: EQ,
    filters.NE: NE,
    filters.GT: GT,
    filters.GE: GE,
    filters.LE: LE,
    filters.LT: LT,
    filters.Is: Is,
    filters.IsNot: IsNot,
    filters.In: In,
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


def convert_filters(model, filters_root):
    if isinstance(filters_root, filters.AbstractExpression):
        return iterate_filters(model, filters_root)
    return iterate_filters(model, filters.AND(filters_root))


def iterate_filters(model, filter_list):
    # Just expression
    if isinstance(filter_list, filters.AbstractExpression):
        clauses = iterate_filters(model, filter_list.clauses)
        return FILTER_EXPR_MAPPING[type(filter_list)](*clauses)

    # Tuple of causes from expression
    if isinstance(filter_list, tuple):
        clauses = []
        for cause in filter_list:
            c_causes = iterate_filters(model, cause)
            if isinstance(cause, filters.AbstractExpression):
                clauses.append(c_causes)
            else:
                clauses.extend(c_causes)
        return clauses

    # old style mappings (dict, multidict)
    if isinstance(filter_list, collections.Mapping):
        clauses = []
        for name, filt in filter_list.items():
            value_type = (model.properties.properties[name]
                          .get_property_type()) or AsIsType()
            # Make API compatible with previous versions.
            if not isinstance(filt, filters.AbstractClause):
                LOG.warning("DEPRECATED: pleases use %s wrapper for filter "
                            "value", filters.EQ)
                clauses.append(EQ(name, value_type, filt))
                continue

            try:
                clauses.append(FILTER_MAPPING[type(filt)](
                    name, value_type, filt.value))
            except KeyError:
                raise ValueError("Can't convert API filter to SQL storage "
                                 "filter. Unknown filter %s" % filt)
        return clauses

    raise ValueError("Unknown type of filters: %s" % filter_list)
