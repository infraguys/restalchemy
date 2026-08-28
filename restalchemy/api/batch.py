# Copyright 2026 George Melikov
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

import orjson

from restalchemy.api import constants
from restalchemy.api import controllers
from restalchemy.api import packers
from restalchemy.api import routes
from restalchemy.api.middlewares import errors as errors_mw
from restalchemy.common import exceptions as exc


class BatchController(controllers.Controller):
    """Replays a list of sub-requests through the existing routing tree.

    Each item in ``requests`` is dispatched as its own WebOb request through
    the *whole* middleware stack wrapping this endpoint (not just the inner
    WSGIApp), so auth, per-route policy, rate limiting and retry behave the
    same for a batch item as for a direct request. Because of that, each
    item also gets its own independent DB transaction (if the deploying
    app's ContextMiddleware opens one) -- there is no cross-item atomicity;
    every item's success/failure is independent, same as calling each
    endpoint directly.
    """

    __resource__ = None
    __max_batch_size__ = 100
    __error_status_resolver__ = staticmethod(errors_mw.get_status_code_for_exception)

    # Marker stored in a sub-request's environ to reject a batch item that
    # targets the batch endpoint itself (would otherwise recurse unbounded).
    __in_batch_environ_key__ = "restalchemy.in_batch"

    def do_collection(self, parent_resource=None):
        # __allow_methods__ only permits CREATE (POST), so this is only ever
        # reached for POST; unlike the base do_collection this always returns
        # 200, not 201, since the batch call itself doesn't create a
        # resource -- per-item results carry their own status codes instead.
        api_context = self._req.api_context
        api_context.set_active_method(constants.CREATE)
        content_type = packers.get_content_type(self._req.headers)
        packer = self.get_packer(content_type)
        kwargs = self._make_kwargs(
            parent_resource, **packer.unpack(value=self._req.body)
        )
        return self.process_result(result=self.create(**kwargs), status_code=200)

    def create(self, requests, **kwargs):
        if self.request.environ.get(self.__in_batch_environ_key__):
            raise exc.NestedBatchNotAllowed()
        if not isinstance(requests, list):
            raise exc.ParseError(value="requests (must be a list)")
        if len(requests) > self.__max_batch_size__:
            raise exc.BatchSizeLimitExceeded(
                size=len(requests), max_size=self.__max_batch_size__
            )

        # The outermost app wrapping this request (recorded by
        # Middleware.__call__ the first time any layer sees this request) --
        # replaying through it, rather than just the inner WSGIApp, is what
        # subjects each item to the full middleware chain. Falls back to the
        # inner WSGIApp for apps with no middlewares at all.
        outer_app = self.request.environ.get(
            "restalchemy.wsgi_app", self.request.application
        )

        results = []
        for item in requests:
            try:
                sub_req = self._build_sub_request(item)
                sub_resp = sub_req.get_response(outer_app)
                results.append(self._pack_response(sub_resp))
            except Exception as e:
                results.append(
                    {
                        "status": self.__error_status_resolver__(e),
                        "body": errors_mw.exception2dict(e),
                    }
                )
        return results

    def _build_sub_request(self, item):
        sub_req = self.request.copy()

        # WebOb stores every ad-hoc attribute (req.context, req.api_context,
        # req.application, ...) in environ["webob.adhoc_attrs"], and
        # Request.copy() only shallow-copies environ, so this dict would
        # otherwise be shared by reference between the outer /batch request
        # and every sub-request dispatched below. Replace it so each
        # sub-request's dispatch state can't leak back into the outer
        # request or into sibling items.
        sub_req.environ["webob.adhoc_attrs"] = {}
        sub_req.environ[self.__in_batch_environ_key__] = True

        sub_req.method = item["method"]
        path, _, query_string = item["path"].partition("?")
        sub_req.script_name = ""
        sub_req.path_info = path
        sub_req.query_string = query_string

        body = item.get("body")
        sub_req.body = orjson.dumps(body) if body is not None else b""
        sub_req.content_type = constants.CONTENT_TYPE_APPLICATION_JSON
        for name, value in (item.get("headers") or {}).items():
            sub_req.headers[name] = value

        return sub_req

    @staticmethod
    def _pack_response(resp):
        return {
            "status": resp.status_code,
            "body": orjson.loads(resp.body) if resp.body else None,
        }


class BatchRoute(routes.Route):
    __controller__ = BatchController
    __allow_methods__ = [routes.CREATE]
