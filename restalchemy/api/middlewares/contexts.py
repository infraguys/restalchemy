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


import re

from restalchemy.api import middlewares
from restalchemy.common import contexts


class ContextMiddleware(middlewares.Middleware):
    def __init__(
        self,
        application,
        context_class=contexts.Context,
        context_kwargs=None,
        readonly_whitelist=None,
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
        :param readonly_whitelist: A dict mapping HTTP methods to URL regex patterns
            or lists of regex patterns. Requests matching the method and any URL pattern
            will use the read-only engine (if configured via context_kwargs["readonly_engine_name"]).
            For example: {"GET": r"^/v1/.*"} or {"GET": [r"^/v1/.*", r"^/api/.*"]}
        :type readonly_whitelist: dict or None
        """
        super().__init__(application)
        self._context_class = context_class
        self._context_kwargs = context_kwargs or {}
        self._readonly_whitelist = self._normalize_whitelist(readonly_whitelist)

    @staticmethod
    def _normalize_whitelist(readonly_whitelist):
        """Pre-process whitelist: normalize values to lists and compile patterns.

        :param readonly_whitelist: Raw whitelist dict.
        :return: Dict mapping methods to lists of compiled regex patterns, or None.
        """
        if not readonly_whitelist:
            return None
        normalized = {}
        for method, patterns in readonly_whitelist.items():
            if isinstance(patterns, str):
                patterns = [patterns]
            normalized[method] = [re.compile(p) for p in patterns]
        return normalized

    def _is_readonly_request(self, req):
        """
        Check if the request matches the read-only whitelist.

        :param req: The request object.
        :return: True if the request matches a whitelist rule.
        :rtype: bool
        """
        if not self._readonly_whitelist:
            return False
        patterns = self._readonly_whitelist.get(req.method)
        if not patterns:
            return False
        for p in patterns:
            if p.match(req.path):
                return True
        return False

    def _construct_context(self, req):
        """
        Constructs a context for the given request.

        This method initializes and returns an instance of the context
        class specified during the middleware initialization. The context
        is used to manage request-specific state and operations.

        If the request matches the read-only whitelist, the context is
        switched to read-only mode.

        :param req: The request object for which the context is being
            constructed.
        :return: An instance of the context class.
        """

        ctx = self._context_class(**self._context_kwargs)
        return ctx

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
        if self._is_readonly_request(req):
            ctx.set_readonly(True)
        req.context = ctx
        with ctx.session_manager():
            return self._get_response(ctx, req)
