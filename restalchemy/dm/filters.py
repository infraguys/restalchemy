# Copyright 2019 Eugene Frolov
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


class AbstractClause(metaclass=abc.ABCMeta):

    def __init__(self, value):
        super(AbstractClause, self).__init__()
        self._value = value

    @property
    def value(self):
        return self._value

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.value == other.value

    def __repr__(self):
        return "<%s (%r)>" % (type(self).__name__, self.value)

    def __str__(self):
        return str(self._value)


class EQ(AbstractClause):
    pass


class NE(AbstractClause):
    pass


class GT(AbstractClause):
    pass


class GE(AbstractClause):
    pass


class LT(AbstractClause):
    pass


class LE(AbstractClause):
    pass


class Is(AbstractClause):
    pass


class IsNot(AbstractClause):
    pass


class In(AbstractClause):
    pass


class NotIn(AbstractClause):
    pass


class Like(AbstractClause):
    pass


class NotLike(AbstractClause):
    pass


class AbstractExpression(metaclass=abc.ABCMeta):

    def __init__(self, *clauses):
        super(AbstractExpression, self).__init__()
        self._clauses = clauses

    @property
    def clauses(self):
        return self._clauses

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.clauses == other.clauses

    def __repr__(self):
        return "<%s (%r)>" % (type(self).__name__, self.clauses)


class ClauseList(AbstractExpression):
    pass


class AND(ClauseList):
    pass


class OR(ClauseList):
    pass
