#    Copyright 2014 Eugene Frolov <eugene@frolov.net.ru>
#    Copyright 2021 Eugene Frolov.
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

from webob import dec

from restalchemy.api import contexts
from restalchemy.api import resources
from restalchemy.api import routes


DEFAULT_CONTENT_TYPE = 'application/json'


class WSGIApp(object):

    def __init__(self, route_class):
        super(WSGIApp, self).__init__()
        self._main_route = routes.route(route_class)
        resources.ResourceMap.set_resource_map(
            routes.Route.build_resource_map(route_class))

    def process_request(self, req):
        req.api_context = contexts.RequestContext(req)
        return self._main_route(req).do()

    @dec.wsgify
    def __call__(self, req):
        return self.process_request(req)


Application = WSGIApp
