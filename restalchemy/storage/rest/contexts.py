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

import bazooka

from restalchemy.storage.rest import utils


class Context(object):

    def __init__(self, request_id=None, request_id_header_name=None,
                 enable_cache=False):
        super(Context, self).__init__()
        self._http_client = {}
        self._request_id = request_id
        self._request_id_header_name = (
            request_id_header_name or 'correlation-id')
        self._cache = {}
        self._enable_cache = enable_cache

    def _get_client(self, endpoint):
        if endpoint in self._http_client:
            return self._http_client[endpoint]
        cli = bazooka.Client(
            correlation_id=self._request_id,
            correlation_id_header_name=self._request_id_header_name)
        self._http_client[endpoint] = cli
        return cli

    def make_post_request(self, endpoint, uri, params):
        cli = self._get_client(endpoint)
        url = utils.build_collection_uri(endpoint, uri)
        response = cli.post(url, json=params)
        response_dict = response.json()
        if self._enable_cache:
            location = response.headers['Location']
            self._cache[location] = response_dict
        return response_dict

    def make_put_request(self, endpoint, uri, params):
        cli = self._get_client(endpoint)
        url = utils.build_resource_uri(endpoint, uri)
        response = cli.put(url, json=params)
        response_dict = response.json()
        if self._enable_cache:
            self._cache[url] = response_dict
        return response_dict

    def make_list_request(self, endpoint, uri, params):
        cli = self._get_client(endpoint)
        url = utils.build_collection_uri(endpoint, uri)
        response = cli.get(url, params=params)
        response_dict = response.json()
        return response_dict

    def make_get_request(self, endpoint, uri, params):
        url = utils.build_resource_uri(endpoint, uri)
        if self._enable_cache and url in self._cache:
            return self._cache[url]
        cli = self._get_client(endpoint)
        response = cli.get(url, params=params)
        response_dict = response.json()
        if self._enable_cache:
            self._cache[url] = response_dict
        return response_dict

    def make_delete_request(self, endpoint, uri):
        url = utils.build_resource_uri(endpoint, uri)
        self._get_client(endpoint).delete(url)
        self._cache.pop(url, None)
