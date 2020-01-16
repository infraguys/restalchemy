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

import six

from restalchemy.storage import base
from restalchemy.storage import exceptions
from restalchemy.storage.memory import engines


class ObjectCollection(base.AbstractObjectCollection):

    @property
    def _engine(self):
        return engines.engine_factory.get_engine()

    def get_all(self, filters=None, limit=None):
        return self._engine.get_all(
            cls=self.model_cls, filters=filters, limit=limit)

    def get_one(self, filters=None):
        # get with limit=2 to raise error if there are more than 1 record
        result = self._engine.get_all(
            cls=self.model_cls, filters=filters, limit=2)
        result_len = len(result)
        if result_len == 1:
            return result[0]
        elif result_len == 0:
            raise exceptions.RecordNotFound(model=self.model_cls,
                                            filters=filters)
        else:
            raise exceptions.HasManyRecords(model=self.model_cls,
                                            filters=filters)


@six.add_metaclass(abc.ABCMeta)
class MemoryStorableMixin(base.AbstractStorableMixin):
    _ObjectCollection = ObjectCollection

    _saved = False

    @property
    def _engine(self):
        return engines.engine_factory.get_engine()

    def insert(self):
        self._engine.insert(self)
        self._saved = True

    def update(self):
        self._engine.update(self)

    def save(self):
        if self._saved:
            return self.update()
        return self.insert()

    def delete(self):
        self._engine.delete(self)
