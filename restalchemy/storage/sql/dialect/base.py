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

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class AbstractProcessResult(object):

    def __init__(self, result):
        self._result = result

    @abc.abstractmethod
    def get_count(self):
        raise NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class AbstractDialectCommand(object):

    def __init__(self, table, data):
        self._table = table
        self._data = data

    @abc.abstractmethod
    def get_values(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_statement(self):
        raise NotImplementedError()

    def execute(self, session):
        values = self.get_values()
        statement = self.get_statement()
        return session.execute(statement, values)


@six.add_metaclass(abc.ABCMeta)
class AbstractDialect(object):

    @abc.abstractproperty
    def insert(self, table, data):
        raise NotImplementedError()

    @abc.abstractproperty
    def update(self, table, ids, data):
        raise NotImplementedError()

    @abc.abstractproperty
    def delete(self, table, ids):
        raise NotImplementedError()

    @abc.abstractproperty
    def select(self, table, filters, limit=None):
        raise NotImplementedError()
