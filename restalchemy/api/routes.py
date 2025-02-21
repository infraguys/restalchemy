# Copyright 2014 Eugene Frolov <eugene@frolov.net.ru>
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
import collections
import inspect
import posixpath
import re

from restalchemy.api import actions
from restalchemy.api import constants
from restalchemy.api import controllers
from restalchemy.common import exceptions as exc
from restalchemy.openapi import constants as oa_c
from restalchemy.openapi import parse
from restalchemy.openapi import structures

# RA HTTP methods
GET = constants.GET
FILTER = constants.FILTER
CREATE = constants.CREATE
UPDATE = constants.UPDATE
DELETE = constants.DELETE

# Other HTTP methods
PUT = constants.PUT
POST = constants.POST

# route constants
COLLECTION_ROUTE = 1
RESOURCE_ROUTE = 2

SPECIAL_SYMBOLS = re.compile(r"[/{}!@#$%^&*())\[\]:,./<>?\|`\~\-\=\_\+]+")


class BaseRoute(metaclass=abc.ABCMeta):
    __controller__ = None
    __allow_methods__ = []
    __tags__ = None  # list of strings or dicts with name and description

    def __init__(self, req):
        super(BaseRoute, self).__init__()
        self._req = req

    @classmethod
    def get_controller_class(cls):
        return cls.__controller__

    @classmethod
    def get_controller(cls, *args, **kwargs):
        return cls.get_controller_class()(*args, **kwargs)

    @classmethod
    def get_allow_methods(cls):
        return cls.__allow_methods__

    @abc.abstractmethod
    def do(self, **kwargs):
        pass

    @classmethod
    def openapi_tags(cls, for_paths=False):
        if not cls.__tags__:
            controller = cls.get_controller_class()
            if controller:
                resource = controller.get_resource()
                if resource:
                    if for_paths:
                        return [resource.get_model().__name__]
                    else:
                        return [
                            {
                                "name": resource.get_model().__name__,
                                "description": "",
                            }
                        ]
            return []
        res = []
        if isinstance(cls.__tags__, list):
            for tag in cls.__tags__:
                if isinstance(tag, str):
                    if for_paths:
                        res.append(tag)
                    else:
                        res.append({"name": tag, "description": ""})
                elif isinstance(tag, structures.OpenApiTag):
                    if for_paths:
                        res.append(tag.name)
                    else:
                        res.append(tag.build())
        return res

    @staticmethod
    def restore_path_info(req):
        """Restore initial values for path_info and script_name to not raise
        UnsupportedHttpMethod exception when RetryOnErrorMiddleware triggers.
        """

        req.path_info, req.script_name = req.script_name, req.path_info


class Route(BaseRoute):
    __controller__ = None
    __allow_methods__ = [GET, CREATE, UPDATE, DELETE, FILTER]

    @classmethod
    def is_resource_route(cls):
        return False

    @classmethod
    def is_collection_route(cls):
        return True

    @classmethod
    def get_attr_safe(cls, name, the_class):
        try:
            attr = getattr(cls, name.replace("-", "_"))
            if not (inspect.isclass(attr) and issubclass(attr, the_class)):
                raise exc.IncorrectRouteAttributeClass(route=attr)
            return attr
        except AttributeError:
            raise exc.IncorrectRouteAttribute(route=cls, attr=name)

    @classmethod
    def get_route(cls, name):
        return cls.get_attr_safe(name, Route)

    @classmethod
    def get_action(cls, name):
        return cls.get_attr_safe(name, Action)

    @classmethod
    def is_route(cls, name):
        try:
            cls.get_route(name)
            return True
        except (exc.IncorrectRouteAttributeClass, exc.IncorrectRouteAttribute):
            return False

    @classmethod
    def is_action(cls, name):
        try:
            cls.get_action(name)
            return True
        except (exc.IncorrectRouteAttributeClass, exc.IncorrectRouteAttribute):
            return False

    @classmethod
    def get_routes(cls):
        return filter(lambda x: cls.is_route(x), dir(cls))

    @classmethod
    def get_action_names(cls):
        return filter(lambda x: cls.is_action(x), dir(cls))

    @classmethod
    def get_actions_by_names(cls, names):
        return [getattr(cls.get_controller_class(), name) for name in names]

    @classmethod
    def check_allow_methods(cls, *args):
        for method in args:
            if method not in cls.__allow_methods__:
                return False
        return True

    def get_method_by_route_type(self, route_type):
        if route_type == COLLECTION_ROUTE:
            mapping = {GET: FILTER, POST: CREATE}
        else:
            mapping = {GET: GET, PUT: UPDATE, DELETE: DELETE}
        try:
            return mapping[self._req.method]
        except KeyError:
            raise exc.UnsupportedHttpMethod(method=self._req.method)

    def _build_openapi_routes_specification(
        self, route_names, current_path, parameters=None
    ):
        for name in route_names:
            next_route = self.get_route(name)(self._req)
            route_path = posixpath.join(current_path, name + "/")
            yield next_route.build_openapi_specification(
                route_path, parameters
            )

    @staticmethod
    def _build_operation_id(method, current_path):
        operation_id = "{}_{}".format(method.capitalize(), current_path)
        operation_id = re.sub(SPECIAL_SYMBOLS, "_", operation_id)
        operation_id = operation_id.replace("__", "_")
        operation_id = operation_id.rstrip("_")
        return operation_id

    def _build_openapi_method_specification(
        self, method, parameters=None, current_path="/", controller=None
    ):
        controller = controller or self.get_controller(request=self._req)
        if isinstance(method, actions.ActionHandler):
            method_name = method.name
        else:
            method = getattr(controller, method.lower())
            method_name = getattr(method, "method", method.__name__.upper())
        openapi_schema = getattr(method, "openapi_schema", None)
        if openapi_schema:
            summary = openapi_schema.summary
            responses = openapi_schema.responses
            params = openapi_schema.parameters
            operation_id = openapi_schema.operation_id
            r_body = openapi_schema.request_body
            tags = openapi_schema.tags
        else:
            summary, responses, params, operation_id, r_body, tags = [None] * 6

        parsed_doc = parse.parse_docstring(method.__doc__)
        res = controller.get_resource()
        model_name = res.get_model().__name__ if res else "Unknown"
        summary_name = (
            model_name
            if res
            else "{} {}".format(
                self.__class__.__name__, controller.__class__.__name__
            )
        )
        if method_name == constants.FILTER:
            summary_name += "s"
        if not summary:
            summary = parsed_doc["short_description"]
            summary = summary or "%s %s" % (
                (
                    method_name.capitalize()
                    if method_name != constants.FILTER
                    else constants.GET.capitalize()
                ),
                summary_name,
            )

        # Fill responses
        if not responses:
            responses = parsed_doc["returns"]
        method_model_name = "{}_{}".format(
            model_name, method_name.capitalize()
        )
        if not responses:
            if method_name in [constants.UPDATE, constants.GET]:
                if res:
                    responses = oa_c.build_openapi_get_update_response(
                        method_model_name
                    )
                else:
                    responses = oa_c.OPENAPI_FILTER_RESPONSE
            elif method_name == constants.FILTER:
                if res:
                    responses = oa_c.build_openapi_list_model_response(
                        method_model_name
                    )
                else:
                    responses = oa_c.OPENAPI_FILTER_RESPONSE
            elif method_name == constants.CREATE:
                responses = oa_c.build_openapi_create_response(
                    method_model_name
                )
            elif method_name == constants.DELETE:
                responses = oa_c.build_openapi_delete_response(
                    method_model_name
                )
            else:
                responses = oa_c.OPENAPI_DEFAULT_RESPONSE

        # fill url parameters
        if not params:
            params = parsed_doc["params"]
        if not params and parameters:
            path_params = re.findall(r"\{(.*?)\}", current_path)
            for path_param in path_params:
                param = (
                    parameters.get("components", {})
                    .get("parameters", {})
                    .get(path_param, {})
                )
                if param:
                    param["name"] = path_param
                    params.append(param)
            if (
                res
                and self.is_collection_route()
                and (method_name == constants.FILTER)
            ):
                for name, prop in res.get_fields_by_request(self._req):
                    param = (
                        parameters.get("components", {})
                        .get("parameters", {})
                        .get(prop.api_name, {})
                    )
                    # array or object not supported in query
                    if param.get("schema", {}).get("type", "") in [
                        "array",
                        "object",
                    ]:
                        continue
                    # sum type parameter not implemented in Go client
                    # NOTE(v.burygin): maybe in openapi spec somewhere
                    # we should make options
                    # if param.get("schema", {}).get("oneOf"):
                    #     continue
                    if param:
                        params.append(param)

        if not operation_id:
            operation_id = self._build_operation_id(method_name, current_path)
        result = {
            "summary": summary,
            "tags": tags or self.openapi_tags(for_paths=True),
            "parameters": params,
            "responses": responses,
            "operationId": operation_id,
        }

        # Fill request_body
        if r_body:
            result["requestBody"] = r_body
        elif method_name in [constants.CREATE, constants.UPDATE]:
            result["requestBody"] = oa_c.build_openapi_json_req_body(
                method_model_name
            )

        return result

    def build_openapi_specification(self, current_path="/", parameters=None):

        paths_result = collections.defaultdict(dict)
        schemas_result = collections.defaultdict(dict)

        if self.__class__ == OpenApiSpecificationRoute:
            ctr = self.get_controller(request=self._req)
            versions = ctr.filter({})
            for version in versions:
                resource_path = posixpath.join(current_path, version)
                paths_result[resource_path][GET.lower()] = (
                    self._build_openapi_method_specification(
                        GET, parameters, current_path
                    )
                )

        openapi_collection_methods = {GET: FILTER, POST: CREATE}
        openapi_resource_methods = {GET: GET, PUT: UPDATE, DELETE: DELETE}

        # build specification for collection methods
        for http_method, ra_method in openapi_collection_methods.items():
            if self.check_allow_methods(ra_method):
                paths_result[current_path][http_method.lower()] = (
                    self._build_openapi_method_specification(
                        ra_method, parameters, current_path
                    )
                )
            routes = [
                r
                for r in self.get_routes()
                if self.get_route(r).is_collection_route()
            ]
            route_gen = self._build_openapi_routes_specification(
                routes, current_path, parameters
            )
            for p, s in route_gen:
                paths_result.update(p)
                schemas_result.update(s)

        # build specification for resource methods
        resource = self.get_controller(request=self._req).get_resource()
        if resource is not None:
            model = resource.get_model()
            try:
                id_prop_struct = model.get_id_property()
                id_name = list(id_prop_struct)[0]
            except TypeError:
                id_name = ""
            id_parameter_name = "{%s%s}" % (
                model.__name__,
                id_name.capitalize(),
            )
            resource_path = posixpath.join(current_path, id_parameter_name)
            for http_method, ra_method in openapi_resource_methods.items():
                if self.check_allow_methods(ra_method):
                    paths_result[resource_path][http_method.lower()] = (
                        self._build_openapi_method_specification(
                            ra_method, parameters, resource_path
                        )
                    )
            routes = [
                route_name
                for route_name in self.get_routes()
                if self.get_route(route_name).is_resource_route()
            ]
            route_gen = self._build_openapi_routes_specification(
                routes, resource_path, parameters
            )
            for p, s in route_gen:
                paths_result.update(p)
                schemas_result.update(s)

            action_names = [r for r in self.get_action_names()]
            if action_names:
                route_actions = self.get_actions_by_names(action_names)
                for route_action in route_actions:
                    is_invoke = getattr(self, route_action.name).is_invoke()
                    if is_invoke:
                        action_path = posixpath.join(
                            current_path,
                            id_parameter_name,
                            "actions",
                            route_action.name,
                            "invoke",
                        )
                    else:
                        action_path = posixpath.join(
                            current_path,
                            id_parameter_name,
                            "actions",
                            route_action.name,
                        )
                    paths_result[action_path][route_action.method.lower()] = (
                        self._build_openapi_method_specification(
                            route_action, parameters, action_path
                        )
                    )
        return paths_result, schemas_result

    @classmethod
    def build_resource_map(cls, root_route, path_stack=None):
        path_stack = path_stack or []

        def build_path(resource, path_stack):
            path_stack = path_stack[:]
            path_stack.append(resource)
            return path_stack

        def build(route, path_stack):
            result = []

            controller = route.get_controller_class()
            resource = controller.get_resource()

            if route.check_allow_methods(GET):
                route_path_stack = build_path(resource, path_stack)
                result.append((resource, controller, route_path_stack))

            for name in route.get_routes():
                new_route = route.get_route(name)
                new_path = (
                    build_path(resource, path_stack)
                    if new_route.is_resource_route()
                    else path_stack[:]
                )
                new_path.append(name)
                result += build(route.get_route(name), new_path)

            return result

        class ResourceLocator(object):

            def __init__(self, path_stack, controller):
                self.path_stack = path_stack
                self._controller = controller

            def is_your_uri(self, uri):
                uri_pieces = uri.split("/")[1:]
                if len(uri_pieces) == len(self.path_stack):
                    for piece1, piece2 in zip(uri_pieces, self.path_stack):
                        if (isinstance(piece2, str) and piece1 == piece2) or (
                            not isinstance(piece2, str)
                        ):
                            continue
                        return False
                    return True
                else:
                    return False

            def get_parent_model(self, parent_type, model, resource):
                if hasattr(resource, "get_parent_model"):
                    return resource.get_parent_model(model)
                models = []
                for name, prop in resource.get_fields():
                    if prop.get_type() is parent_type:
                        models.append(getattr(model, name))
                if len(models) == 1:
                    return models[0]
                raise ValueError(
                    "Can't find resource %s. Please "
                    "implement get_parent_model in your model "
                    "(%s)" % (parent_type, type(model))
                )

            def get_uri(self, model):
                resource = self.path_stack[-1]
                path = str(resource.get_resource_id(model))
                for piece in reversed(self.path_stack[:-1]):
                    if isinstance(piece, str):
                        path = posixpath.join(piece, path)
                    else:
                        model = self.get_parent_model(
                            piece.get_model(), model, resource
                        )
                        resource = piece
                        path = posixpath.join(
                            resource.get_resource_id(model), path
                        )
                # FIXME(Eugene Frolov): Header must be string. Not unicode.
                return str(posixpath.join("/", path))

            def get_resource(self, request, uri, parent_resource=None):
                uuid = posixpath.basename(uri)
                if parent_resource:
                    return self._controller(
                        request=request
                    ).get_resource_by_uuid(
                        uuid=uuid, parent_resource=parent_resource
                    )
                return self._controller(request=request).get_resource_by_uuid(
                    uuid
                )

        resource_map = {}

        for res, controller, stack in build(root_route, path_stack):
            resource_map[res] = ResourceLocator(stack, controller)

        return resource_map

    def do(self, parent_resource=None, **kwargs):
        super(Route, self).do(**kwargs)

        # TODO(Eugene Frolov): Check the possibility to pass to the method
        #                      specified in a route.
        name, path = self._req.path_info_pop(), self._req.path_info_peek()

        if path is None:
            # Collection or Resource method
            ctrl_method = (
                self.get_method_by_route_type(COLLECTION_ROUTE)
                if name == ""
                else self.get_method_by_route_type(RESOURCE_ROUTE)
            )
            if self.check_allow_methods(ctrl_method):
                worker = self.get_controller(request=self._req)
                self.restore_path_info(self._req)
                if name == "":
                    # Collection method
                    return worker.do_collection(parent_resource)

                # Resource method
                return worker.do_resource(name, parent_resource)
            else:
                raise exc.UnsupportedHttpMethod(method=ctrl_method)

        elif name != "" and path is not None and self.is_route(name):
            # Next route
            route = self.get_route(name)
            if route.is_resource_route():
                raise exc.ResourceNotFoundError(resource=name, path=path)
            worker = route(self._req)
            return worker.do(parent_resource)

        elif name != "" and path == "actions":
            # Action route
            worker = self.get_controller(self._req)
            resource = worker.get_resource_by_uuid(name, parent_resource)
            self._req.path_info_pop()
            action_name = self._req.path_info_peek()
            action = self.get_action(action_name)
            worker = action(self._req)
            return worker.do(resource=resource)

        elif name != "" and path is not None:
            # Intermediate resource route
            worker = self.get_controller(self._req)
            parent_resource = worker.get_resource_by_uuid(
                name, parent_resource
            )
            name, path = self._req.path_info_pop(), self._req.path_info_peek()
            route = self.get_route(name)
            if route.is_collection_route():
                raise exc.CollectionNotFoundError(collection=name, path=path)
            worker = route(self._req)
            return worker.do(parent_resource)

        else:
            # Other
            raise exc.NotFoundError(path=path)


def route(route_class, resource_route=False):
    @classmethod
    def is_resource_route(cls):
        return resource_route

    @classmethod
    def is_collection_route(cls):
        return not resource_route

    route_class.is_resource_route = is_resource_route
    route_class.is_collection_route = is_collection_route

    return route_class


class Action(BaseRoute):
    __controller__ = None
    __allow_methods__ = [GET]

    @classmethod
    def is_invoke(cls):
        return False

    def do(self, resource, **kwargs):
        super(Action, self).do(**kwargs)

        method = self._req.method
        action_name = self._req.path_info_pop().replace("-", "_")
        invoke_info = self._req.path_info_pop()
        if invoke_info == "invoke":
            invoke = True
        elif invoke_info is None:
            invoke = False
        else:
            raise exc.UnsupportedMethod(
                method=invoke_info, object_name=action_name
            )
        controller = self.get_controller(self._req)
        action = getattr(controller, action_name)
        content_type = self._req.headers.get("Content-Type")
        if content_type == constants.DEFAULT_CONTENT_TYPE:
            body = self._req.body
            if body:
                # NOTE(v.burygin): update kwargs by request body
                packer = controller.get_packer(content_type)
                # set packer _rt None for sending any fields to action method
                packer._rt = None
                kwargs.update(**packer.unpack(value=body))
        else:
            kwargs.update(**self._req.api_context.params)
        if (method in [GET, POST, PUT] and self.is_invoke() and invoke) or (
            method == GET and not self.is_invoke() and not invoke
        ):
            action_method = getattr(action, "do_%s" % method.lower())
            self.restore_path_info(self._req)
            return action_method(
                controller=controller, resource=resource, **kwargs
            )
        else:
            raise exc.IncorrectActionCall(action=action, method=method)


def action(action_class, invoke=False):
    @classmethod
    def is_invoke(cls):
        return invoke

    action_class.is_invoke = is_invoke
    return action_class


class OpenApiSpecificationRoute(Route):
    __controller__ = controllers.OpenApiSpecificationController
    __allow_methods__ = [FILTER, GET]


class RootRoute(Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [FILTER, GET]

    specifications = route(OpenApiSpecificationRoute)
