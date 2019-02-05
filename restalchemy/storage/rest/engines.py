# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2018 Mail.ru Group
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

from restalchemy.common import singletons


class RESTEngine(object):

    def __init__(self, api_endpoint, config=None):
        super(RESTEngine, self).__init__()
        self._api_endpoint = api_endpoint
        self._config = config or {}

    def post(self, uri, params, context):
        return context.make_post_request(self._api_endpoint, uri, params)

    def put(self, uri, params, context):
        return context.make_put_request(self._api_endpoint, uri, params)

    def list(self, uri, params, context):
        return context.make_list_request(self._api_endpoint, uri, params)

    def get(self, uri, params, context):
        return context.make_get_request(self._api_endpoint, uri, params)

    def delete(self, uri, context):
        return context.make_delete_request(self._api_endpoint, uri)


class EngineFactory(singletons.InheritSingleton):

    def __init__(self):
        super(EngineFactory, self).__init__()
        self._engine = None
        self._engines_map = {
            'http': RESTEngine,
            'https': RESTEngine
        }

    def configure_factory(self, api_endpoint, config=None):
        """Configure_factory

        @property db_url: str. For example driver://user:passwd@host:port/db
        """
        schema = api_endpoint.split(':')[0]
        try:
            self._engine = self._engines_map[schema.lower()](api_endpoint,
                                                             config)
        except KeyError:
            raise ValueError("Can not find driver for schema %s" % schema)

    def get_engine(self):
        if self._engine:
            return self._engine
        raise ValueError("Can not return engine. Please configure "
                         "EngineFactory")


engine_factory = EngineFactory()
