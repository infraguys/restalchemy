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
import logging

import six

from restalchemy.dm import filters
from restalchemy.dm import types

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AbstractExpression(object):

    def __init__(self, value_type, value):
        super(AbstractExpression, self).__init__()
        self._value = self._convert_value(value_type, value)

    def _convert_value(self, value_type, value):
        return value_type.to_simple_type(value)

    @property
    def value(self):
        return self._value

    @abc.abstractmethod
    def construct_expression(self, name):
        raise NotImplementedError()


class EQ(AbstractExpression):

    def construct_expression(self, name):
        return ("`%s` = " % name) + "%s"


class NE(AbstractExpression):

    def construct_expression(self, name):
        return ("`%s` <> " % name) + "%s"


class GT(AbstractExpression):

    def construct_expression(self, name):
        return ("`%s` > " % name) + "%s"


class GE(AbstractExpression):

    def construct_expression(self, name):
        return ("`%s` >= " % name) + "%s"


class LT(AbstractExpression):

    def construct_expression(self, name):
        return ("`%s` < " % name) + "%s"


class LE(AbstractExpression):

    def construct_expression(self, name):
        return ("`%s` <= " % name) + "%s"


class Is(AbstractExpression):

    def construct_expression(self, name):
        return ("`%s` IS " % name) + "%s"


class IsNot(AbstractExpression):

    def construct_expression(self, name):
        return ("`%s` IS NOT " % name) + "%s"


class In(AbstractExpression):

    def _convert_value(self, value_type, value):
        return [value_type.to_simple_type(item) for item in value]

    def construct_expression(self, name):
        return ("`%s` IN " % name) + "%s"


def convert_filter(api_filter, value_type=None):
    FILTER_MAPPING = {
        filters.EQ: EQ,
        filters.NE: NE,
        filters.GT: GT,
        filters.GE: GE,
        filters.LE: LE,
        filters.LT: LT,
        filters.Is: Is,
        filters.IsNot: IsNot,
        filters.In: In
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

    value_type = value_type or AsIsType()
    # Make API compatible with previous versions.
    if not isinstance(api_filter, filters.AbstractExpression):
        LOG.warning("DEPRICATED: pleases use %s wrapper for filter value" %
                    filters.EQ)
        return EQ(value_type, api_filter)

    if type(api_filter) not in FILTER_MAPPING:
        raise ValueError("Can't convert API filter to SQL storage filter. "
                         "Unknown filter %s" % api_filter)

    return FILTER_MAPPING[type(api_filter)](value_type, api_filter.value)
