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

import webob
from webob import dec

from restalchemy.api import constants
from restalchemy.api import contexts
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.openapi import cache as openapi_cache


class WSGIApp:
    def __init__(self, route_class):
        super().__init__()
        self._main_route = routes.route(route_class)
        resources.ResourceMap.set_resource_map(
            routes.Route.build_resource_map(route_class),
        )

    @property
    def main_route(self):
        return self._main_route

    def process_request(self, req):
        req.api_context = contexts.RequestContext(req)
        return self._main_route(req).do()

    @dec.wsgify
    def __call__(self, req):
        req.application = self
        return self.process_request(req)


class OpenApiApplication(WSGIApp):
    def __init__(self, route_class, openapi_engine, warm_up_openapi=True):
        super().__init__(route_class)
        self._openapi_engine = openapi_engine
        if warm_up_openapi:
            openapi_cache.warm_up(self, self._build_warm_up_request())

    def _build_warm_up_request(self) -> webob.Request:
        """Stand in for the GET that would otherwise build the document.

        Field visibility is decided per request, so this has to look like the
        request it replaces: a plain read, which is what asking for the
        specification is.
        """
        request = webob.Request.blank("/")
        request.application = self
        request.api_context = contexts.RequestContext(request)
        request.api_context.set_active_method(constants.GET)
        return request

    @property
    def openapi_engine(self):
        return self._openapi_engine


Application = WSGIApp
