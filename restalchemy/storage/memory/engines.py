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

import copy

from restalchemy.common import singletons
from restalchemy.storage import exceptions


class Collection(object):

    def __init__(self, name):
        super(Collection, self).__init__()
        self._name = name
        self._models = []
        self._indexes = {}

    def insert(self, model):
        if model in self._models:
            raise exceptions.ConflictRecords(
                model=model,
                msg="Model with %d id already inserterd" % id(model))
        self._models.append(model)

    def update(self, model):
        if model not in self._models:
            raise exceptions.RecordNotFound(model=model, filters=None)

    def delete(self, model):
        if model not in self._models:
            raise exceptions.RecordNotFound(model=model, filters=None)
        self._models.remove(model)

    def get_all(self, filters=None, limit=None):
        filters = filters or {}
        if not filters:
            return copy.copy(self._models[:limit] if limit else self._models)
        result = self._models
        for name, value in filters.items():
            result = [model for model in result
                      if getattr(model, name) == value]
        if limit:
            return result[:limit]
        return result


class MemoryEngine(object):

    def __init__(self):
        super(MemoryEngine, self).__init__()
        self._collections = {}

    def _get_collection(self, name):
        if name not in self._collections:
            self._collections[name] = Collection(str(name))
        return self._collections[name]

    def insert(self, model):
        collection = self._get_collection(type(model))
        collection.insert(model)

    def update(self, model):
        collection = self._get_collection(type(model))
        collection.update(model)

    def delete(self, model):
        collection = self._get_collection(type(model))
        collection.delete(model)

    def get_all(self, cls, filters=None, limit=None):
        collection = self._get_collection(cls)
        return collection.get_all(filters=filters, limit=limit)

    def reset(self):
        self._collections = {}


class EngineFactory(singletons.InheritSingleton):

    def __init__(self):
        super(EngineFactory, self).__init__()
        self._engine = None
        self.configure_factory()

    def configure_factory(self):
        """Configure_factory

        @property db_url: str. For example driver://user:passwd@host:port/db
        """
        self._engine = MemoryEngine()

    def get_engine(self):
        if self._engine:
            return self._engine
        raise ValueError("Can not return engine. Please configure "
                         "EngineFactory")


engine_factory = EngineFactory()
