# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import six


@six.add_metaclass(abc.ABCMeta)
class AbstractExpression(object):

    def __init__(self, value, type_value=None):
        super(AbstractExpression, self).__init__()
        self._value = value
        self._type_value = type_value

    @property
    def value(self):
        return self._value

    @property
    def type_value(self):
        return self._type_value

    def __repr__(self):
        return "<%s (%r: %r)>" % (type(self).__name__,
                                  self.value,
                                  self._type_value)


class EQ(AbstractExpression):
    pass


class NE(AbstractExpression):
    pass


class GT(AbstractExpression):
    pass


class GE(AbstractExpression):
    pass


class LT(AbstractExpression):
    pass


class LE(AbstractExpression):
    pass


class Is(AbstractExpression):
    pass


class IsNot(AbstractExpression):
    pass


class In(AbstractExpression):
    pass
