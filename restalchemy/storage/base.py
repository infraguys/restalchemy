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
import functools
import logging

import six

from restalchemy.common import exceptions as common_exc
from restalchemy.common import utils
from restalchemy.storage import exceptions


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AbstractObjectCollection(object):

    def __init__(self, model_cls):
        super(AbstractObjectCollection, self).__init__()
        self.model_cls = model_cls

    @abc.abstractmethod
    def get_all(self, filters=None, limit=None, order_by=None, locked=False):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_one(self, filters=None, locked=False):
        raise NotImplementedError()

    def get_one_or_none(self, filters=None):
        try:
            return self.get_one(filters=filters)
        except exceptions.RecordNotFound:
            return None


@six.add_metaclass(abc.ABCMeta)
class AbstractStorableMixin(object):

    _ObjectCollection = AbstractObjectCollection

    def _get_prepared_data(self, properties=None):
        result = {}
        props = properties or self.properties
        for name, prop in props.items():
            result[name] = prop.property_type.to_simple_type(prop.value)
        return result

    @utils.classproperty
    def objects(cls):
        return cls._ObjectCollection(cls)

    @abc.abstractmethod
    def insert(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def update(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(self):
        raise NotImplementedError()

    def get_storable_snapshot(self):
        return self._get_prepared_data()


def error_catcher(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except common_exc.RestAlchemyException:
            raise
        except Exception as e:
            LOG.exception("Some exception has been raised:")
            raise exceptions.UnknownStorageException(caused=e)

    return wrapper
