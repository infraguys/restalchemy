# Copyright 2019 Eugene Frolov
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


from restalchemy.api import middlewares

from restalchemy.common import contexts


class ContextMiddleware(middlewares.Middleware):

    def __init__(
        self, application, context_class=contexts.Context, context_kwargs=None
    ):
        """
        Initialize the middleware with a context class.

        :param application: The next application down the WSGI stack.
        :type application: callable
        :param context_class: The class used to construct a request context.
        :type context_class: restalchemy.common.contexts.Context
        :param conext_kwargs: Additional keyword arguments to pass to the
            context class constructor.
        :type conext_kwargs: dict
        """
        super().__init__(application)
        self._context_class = context_class
        self._context_kwargs = context_kwargs or {}

    def _construct_context(self, req):
        """
        Constructs a context for the given request.

        This method initializes and returns an instance of the context
        class specified during the middleware initialization. The context
        is used to manage request-specific state and operations.

        :param req: The request object for which the context is being
            constructed.
        :return: An instance of the context class.
        """

        return self._context_class(**self._context_kwargs)

    def _get_response(self, ctx, req):
        """Call next application down the stack and return response.

        If this returns None, the next application down the stack will be
        executed. If it returns a response then that response will be returned
        and execution will stop here.

        :param ctx: The context object.
        :param req: The request object.
        :return: The response object.
        """
        return req.get_response(self.application)

    def process_request(self, req):
        """Called on each request.

        If this returns None, the next application down the stack will be
        executed. If it returns a response then that response will be returned
        and execution will stop here.

        :param req: The request object.
        :return: The response object.
        """
        ctx = self._construct_context(req)
        req.context = ctx
        with ctx.session_manager():
            return self._get_response(ctx, req)
