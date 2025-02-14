# Copyright 2011 OpenStack Foundation.
# Copyright 2020 Eugene Frolov
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

from restalchemy.common import contexts as common_contexts


SUCCESS_HTTP_METRIC_NAME = "http.all.success"
ERROR_HTTP_METRIC_NAME = "http.all.errors"


def attach_middlewares(app, middlewares_list):
    for middleware in middlewares_list:
        app = middleware(application=app)
    return app


def configure_middleware(middleware_class, *args, **kwargs):

    def build_middleware(application):
        return middleware_class(application=application, *args, **kwargs)

    return build_middleware


class Middleware(object):
    """Base WSGI middleware wrapper.

    These classes require an application to be initialized that will be called
    next.  By default the middleware will simply call its wrapped app, or you
    can override __call__ to customize its behavior.
    """

    def __init__(self, application):
        self.application = application

    def process_request(self, req):
        """Called on each request.

        If this returns None, the next application down the stack will be
        executed. If it returns a response then that response will be returned
        and execution will stop here.
        """
        return None

    def process_response(self, response):
        """Do whatever you'd like to the response."""
        return response

    @dec.wsgify
    def __call__(self, req):
        response = self.process_request(req)
        if response:
            return response
        response = req.get_response(self.application)
        return self.process_response(response)


class ContextMiddleware(Middleware):

    def process_request(self, req):
        req.context = common_contexts.Context()
