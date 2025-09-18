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

import itertools
import logging

import webob

from restalchemy.api import constants
from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.common import exceptions as exc
from restalchemy.common import utils
from restalchemy.dm import filters as dm_filters
from restalchemy.openapi import constants as oa_c
from restalchemy.openapi import utils as oa_utils
from restalchemy.storage.sql import constants as sql_c

LOG = logging.getLogger(__name__)


class Controller(object):
    __resource__ = None  # type: resources.ResourceByRAModel

    # Not for common cases (Example: for JSONPackerIncludeNullFields)
    __packer__ = None  # type: packers.BaseResourcePacker

    # You can also generate location header for GET and UPDATE methods,
    # just expand the list with the following constants:
    #  * constants.GET
    #  * constants.UPDATE
    __generate_location_for__ = {
        constants.CREATE,
    }

    # List of fields that can be used for user sorting. If '__all__', any field is allowed.
    __sortable_fields__ = "__all__"

    # Default sorting, leave empty for no default sorting.
    __default_sort__ = {}

    def __init__(self, request):
        super(Controller, self).__init__()
        self._req = request

    def __repr__(self):
        return self.__class__.__name__

    @property
    def request(self):
        return self._req

    def get_packer(self, content_type, resource_type=None):
        packer = self.__packer__ or packers.get_packer(content_type)
        rt = resource_type or self.get_resource()
        return packer(rt, request=self._req)

    def _create_response(self, body, status, headers, charset="utf-8"):
        if body is not None:
            headers["Content-Type"] = packers.get_content_type(headers)
            packer = self.get_packer(headers["Content-Type"])
            body = packer.pack(body)

        return webob.Response(
            body=body,
            status=status,
            content_type=headers.get("Content-Type", None),
            headerlist=[(k, v) for k, v in headers.items()],
            charset=charset,
        )

    def process_result(
        self, result, status_code=200, headers=None, add_location=False
    ):
        headers = headers or {}

        def correct(
            body, c=status_code, h=None, h_location=add_location, *args
        ):
            h = h or {}
            if h_location:
                try:
                    headers["Location"] = resources.ResourceMap.get_location(
                        body
                    )
                except (
                    exc.UnknownResourceLocation,
                    exc.CanNotFindResourceByModel,
                ) as e:
                    LOG.warning(
                        "Can't construct location header by reason: %r", e
                    )
            headers.update(h)
            return body, c, headers

        if isinstance(result, tuple):
            return self._create_response(*correct(*result))
        else:
            return self._create_response(*correct(result))

    def _make_kwargs(self, parent_resource, **kwargs):
        if parent_resource:
            kwargs["parent_resource"] = parent_resource
        return kwargs

    @utils.raise_parse_error_on_fail
    def _parse_field_value(self, name, value, resource_field):
        return resource_field.parse_value_from_unicode(self._req, value)

    def _prepare_filter(self, param_name, value):
        if self.model is None:
            raise exc.ValidationFilterIncompatibleError(val=param_name)
        try:
            resource_field = self.__resource__.get_field(
                self.__resource__.get_model_field_name(param_name)
            )
        except ValueError:
            raise exc.ValidationFilterIncompatibleError(val=param_name)

        value = self._parse_field_value(param_name, value, resource_field)

        return resource_field.name, value

    def _prepare_sorts(self, params):
        keys = params.getall("sort_key")
        if not keys:
            return self.__default_sort__
        if keys and self.__sortable_fields__ != "__all__":
            keys = [key for key in keys if key in self.__sortable_fields__]

        dirs = params.getall("sort_dir")
        for dir in dirs:
            if dir.upper() not in sql_c.SQL_SORT_SET:
                raise exc.ValidationSortInvalidDirValueError(dir=dir)
        if dirs:
            if len(keys) != len(dirs):
                raise exc.ValidationSortIncompatibleDirCountError()
            return dict(itertools.zip_longest(keys, dirs, fillvalue="asc"))

        return {key: "asc" for key in keys}

    def _prepare_filters(self, params):
        result = {}
        process = self.__resource__ and self.__resource__.is_process_filters()
        for param, value in params.items():
            filter_name, filter_value = (
                self._prepare_filter(param, value)
                if process
                else (param, value)
            )
            if filter_name not in result:
                result[filter_name] = dm_filters.EQ(filter_value)
            else:
                values = (
                    [result[filter_name].value]
                    if not isinstance(result[filter_name], dm_filters.In)
                    else result[filter_name].value
                )
                values.append(filter_value)
                result[filter_name] = dm_filters.In(values)

        return result

    def do_collection(self, parent_resource=None):
        method = self._req.method

        api_context = self._req.api_context
        if method == "GET":
            api_context.set_active_method(constants.FILTER)
            order_by = self._prepare_sorts(
                params=self._req.api_context.params,
            )
            filters = self._prepare_filters(
                params=self._req.api_context.params_filters,
            )
            kwargs = self._make_kwargs(parent_resource, filters=filters)
            return self.process_result(
                result=self.filter(**kwargs, order_by=order_by)
            )
        elif method == "POST":
            api_context.set_active_method(constants.CREATE)
            content_type = packers.get_content_type(self._req.headers)
            packer = self.get_packer(content_type)
            kwargs = self._make_kwargs(
                parent_resource, **packer.unpack(value=self._req.body)
            )

            return self.process_result(
                result=self.create(**kwargs),
                status_code=201,
                add_location=constants.CREATE
                in self.__generate_location_for__,
            )
        else:
            raise exc.UnsupportedHttpMethod(method=method)

    def get_resource_by_uuid(self, uuid, parent_resource=None):
        kwargs = self._make_kwargs(parent_resource)

        parsed_id = (
            self._parse_resource_uuid(
                "uuid", uuid, self.get_resource().get_id_type()
            )
            if self.__resource__
            else uuid
        )

        result = self.get(uuid=parsed_id, **kwargs)
        if isinstance(result, tuple):
            return result[0]
        return result

    @utils.raise_parse_error_on_fail
    def _parse_resource_uuid(self, name, value, id_type):
        return id_type.from_unicode(value)

    def do_resource(self, uuid, parent_resource=None):
        method = self._req.method
        kwargs = self._make_kwargs(parent_resource)

        parsed_id = (
            self._parse_resource_uuid(
                "uuid", uuid, self.get_resource().get_id_type()
            )
            if self.__resource__
            else uuid
        )

        api_context = self._req.api_context

        if method == "GET":
            api_context.set_active_method(constants.GET)
            return self.process_result(
                result=self.get(uuid=parsed_id, **kwargs),
                add_location=constants.GET in self.__generate_location_for__,
            )
        elif method == "PUT":
            api_context.set_active_method(constants.UPDATE)
            content_type = packers.get_content_type(self._req.headers)
            packer = self.get_packer(content_type)
            kwargs.update(packer.unpack(value=self._req.body))
            # TODO(v.burygin) We need carefully change params of method update
            #  in new major version for updating uuid in model
            if "uuid" in kwargs:
                if kwargs["uuid"] != parsed_id:
                    raise exc.NotEqualUuidException(
                        uuid=kwargs["uuid"], parsed_id=parsed_id
                    )
                kwargs.pop("uuid", None)
            return self.process_result(
                result=self.update(uuid=parsed_id, **kwargs),
                add_location=constants.UPDATE
                in self.__generate_location_for__,
            )
        elif method == "DELETE":
            api_context.set_active_method(constants.DELETE)
            result = self.delete(uuid=parsed_id, **kwargs)
            return self.process_result(
                result=result,
                status_code=200 if result else 204,
            )
        else:
            raise exc.UnsupportedHttpMethod(method=method)

    @classmethod
    def get_resource(cls):
        return cls.__resource__

    @property
    def model(self):
        return self.get_resource().get_model()

    def create(self, **kwargs):
        raise exc.NotImplementedError(
            msg="method create in %s" % self.__class__.__name__
        )

    def get(self, uuid):
        raise exc.NotImplementedError(
            msg="method get in %s" % self.__class__.__name__
        )

    def filter(self, filters, order_by=None):
        raise exc.NotImplementedError(
            msg="method filter in %s" % self.__class__.__name__
        )

    def delete(self, uuid):
        raise exc.NotImplementedError(
            msg="method delete in %s" % self.__class__.__name__
        )

    def update(self, uuid, **kwargs):
        raise exc.NotImplementedError(
            msg="method update in %s" % self.__class__.__name__
        )

    def get_context(self):
        try:
            return self._req.context
        except AttributeError:
            return None


class BaseResourceController(Controller):

    def create(self, **kwargs):
        dm = self.model(**kwargs)
        dm.insert()
        return dm

    def get(self, uuid, **kwargs):
        # TODO(d.burmistrov): replace this hack with normal argument passing
        kwargs[self.model.get_id_property_name()] = dm_filters.EQ(uuid)
        return self.model.objects.get_one(filters=kwargs)

    def _split_filters(self, filters):
        if hasattr(self.model, "get_custom_properties"):
            custom_filters = {}
            storage_filters = {}
            custom_properties = dict(self.model.get_custom_properties())
            for name, value in filters.items():
                if name in custom_properties:
                    custom_filters[name] = value
                    continue
                storage_filters[name] = value

            return custom_filters, storage_filters

        return {}, filters

    def _process_custom_filters(self, result, filters):
        if not filters:
            return result
        for item in result[:]:
            for field_name, filter_value in filters.items():
                if not result:
                    break
                elif item not in result:
                    continue
                elif isinstance(filter_value, dm_filters.In):
                    if getattr(item, field_name) not in filter_value.value:
                        result.remove(item)
                        continue
                elif isinstance(filter_value, dm_filters.EQ):
                    if getattr(item, field_name) != filter_value.value:
                        result.remove(item)
                        continue
                else:
                    raise exc.ValidationFilterIncompatibleError(val=field_name)
        return result

    def _process_storage_filters(self, filters, order_by=None):
        return self.model.objects.get_all(filters=filters, order_by=order_by)

    @staticmethod
    def _convert_raw_filters_to_dm_filters(filters):
        """For use in places, where we manually work with input raw filters"""
        for k, v in filters.items():
            if not isinstance(v, dm_filters.AbstractClause):
                filters[k] = dm_filters.EQ(v)
        return filters

    def filter(self, filters, order_by=None):
        custom_filters, storage_filters = self._split_filters(filters)

        result = self._process_storage_filters(
            storage_filters, order_by=order_by
        )

        return self._process_custom_filters(result, custom_filters)

    def delete(self, uuid):
        self.get(uuid=uuid).delete()

    def update(self, uuid, **kwargs):
        dm = self.get(uuid=uuid)
        dm.update_dm(values=kwargs)
        dm.update()
        return dm


class BaseNestedResourceController(BaseResourceController):

    __pr_name__ = "parent_resource"

    def _prepare_kwargs(self, parent_resource, **kwargs):
        kw_params = kwargs.copy()
        kw_params[self.__pr_name__] = parent_resource
        return kw_params

    def create(self, **kwargs):
        return super(BaseNestedResourceController, self).create(
            **self._prepare_kwargs(**kwargs)
        )

    def get(self, **kwargs):
        return super(BaseNestedResourceController, self).get(
            **self._prepare_kwargs(**kwargs)
        )

    def filter(self, parent_resource, filters, order_by=None):
        filters = filters.copy()
        filters[self.__pr_name__] = dm_filters.EQ(parent_resource)
        return super(BaseNestedResourceController, self).filter(
            filters=filters, order_by=order_by
        )

    def delete(self, parent_resource, uuid):
        dm = self.get(parent_resource=parent_resource, uuid=uuid)
        dm.delete()

    def update(self, parent_resource, uuid, **kwargs):
        dm = self.get(parent_resource=parent_resource, uuid=uuid)
        dm.update_dm(values=kwargs)
        dm.update()
        return dm


class PaginationFilterBuilder:
    """
    Represents a pagination cursor with sort value and ID.
    Handles non-trivial logic for paginating by non-unique column.
    """

    def __init__(
        self, model, marker_id, sort_column=None, sort_direction="asc"
    ):
        """
        Create pagination cursor from marker ID.

        Problem: when we sort by non-unique field, there'll be rows
        which were in the previous response too.
        So, we need to remove them somehow.
        Example of a target query:
            SELECT * FROM table WHERE
                filters
                AND
                (
                    order_key > marker_order_val
                        AND
                        (
                            order_key <> marker_order_val
                            OR
                            id_name > _pagination_marker
                        )
                    )
            ORDER BY
                order_key order_dir, id_name ASC
            LIMIT X;

        Args:
            model: The model to query
            marker_id: The ID of the last row from previous page
            sort_column: Column name to sort by (None for ID-only sort)
            sort_direction: "asc" or "desc"
        """
        self.marker_id = marker_id
        self.sort_col = sort_column
        self.sort_dir = sort_direction
        self.id_name = model.get_id_property_name()
        self.sort_value = self._fetch_sort_val(model)

    def _fetch_sort_val(self, model):
        """Fetch the sort value for this marker ID"""
        # No need for extra query, if we're sorting by UUID
        if self.sort_col in (None, self.id_name):
            return self.marker_id

        # Get last seen row
        marker_row = model.objects.get_one(
            filters={self.id_name: dm_filters.EQ(self.marker_id)}
        )
        return getattr(marker_row, self.sort_col)

    def build_filter(self):
        """Build the compound pagination filter."""
        if not self.sort_col:
            return {self.id_name: dm_filters.GT(self.marker_id)}

        # Check if sorting by ID directly
        id_op = dm_filters.GT if self.sort_dir == "asc" else dm_filters.LT
        if self.sort_col == self.id_name:
            return {self.id_name: id_op(self.marker_id)}

        # Standard compound cursor for non-ID primary sort
        return dm_filters.OR(
            {self.sort_col: id_op(self.sort_value)},
            dm_filters.AND(
                {self.sort_col: dm_filters.EQ(self.sort_value)},
                {self.id_name: dm_filters.GT(self.marker_id)},
            ),
        )


class BasePaginationMixin(object):
    """Pagination mixin, marker based, not offset based!

    Contract:
    - Works via `page_limit` and `page_marker` params.
    - All results are sorted by `order by id ASC`, if sort_key was not provided
    - page_limit: sets limit of each "page"
    - page_marker: sets marker of last ID in previous batch,
      next batch will by filtered by `where id > MARKER`
    - There are next "pages" while X-Pagination-Marker exists in response

    Example:
    # get first "page"
    curl '/some/collection/?page_limit=5' -i
    HTTP/1.1 200 OK
    X-Pagination-Limit: 5
    X-Pagination-Marker: XXX_UUID1

    # get next "page" by marker
    curl '/some/collection/?page_limit=5&page_marker=XXX_UUID1' -i
    HTTP/1.1 200 OK
    X-Pagination-Limit: 5
    X-Pagination-Marker: XXX_UUID2

    # get last "page" by marker
    curl '/some/collection/?page_limit=5&page_marker=XXX_UUID2' -i
    HTTP/1.1 200 OK
    X-Pagination-Limit: 5
    (Last page won't have Marker)
    """

    _pagination_limit = 0
    _header_page_limit = "X-Pagination-Limit"
    _header_page_marker = "X-Pagination-Marker"

    _param_page_limit = "page_limit"
    _param_page_marker = "page_marker"

    def _create_response(self, body, status, headers):
        if self._pagination_limit:
            headers[self._header_page_limit] = str(self._pagination_limit)
            if len(body) == self._pagination_limit:
                headers[self._header_page_marker] = str(
                    getattr(body[-1], self.model.get_id_property_name())
                )

        return super(BasePaginationMixin, self)._create_response(
            body, status, headers
        )

    def _prepare_pagination_meta(self):
        try:
            self._pagination_limit = int(
                self._req.api_context.params.get(self._param_page_limit, 0)
            )
            if self._pagination_limit < 0:
                raise ValueError()
        except ValueError:
            raise exc.ParseError(value="%s" % (self._pagination_limit,))
        # TODO(g.melikov): do we need to validate if marker ID record exists?
        self._pagination_marker = self._req.api_context.params.get(
            self._param_page_marker
        )
        if self._pagination_marker:
            self._pagination_marker = (
                self._parse_resource_uuid(
                    "uuid",
                    self._pagination_marker,
                    self.get_resource().get_id_type(),
                )
                if self.__resource__
                else self._pagination_marker
            )

    def do_collection(self, parent_resource=None):
        self._prepare_pagination_meta()

        return super(BasePaginationMixin, self).do_collection(
            parent_resource=parent_resource
        )

    def _process_storage_filters(self, filters, order_by=None):
        self._validate_params(filters, order_by)
        filters, order_by = self._build_pagination_with_cursor(
            filters, order_by
        )
        return self.model.objects.get_all(
            filters=filters,
            limit=self._pagination_limit,
            order_by=order_by,
        )

    def _validate_params(self, filters, order_by):
        if order_by and len(order_by) > 1:
            raise exc.ValidationSortNumberError()

    def _build_pagination_with_cursor(self, filters, order_by):
        if self._pagination_marker:
            sort_col, sort_dir = (
                next(iter(order_by.items())) if order_by else (None, "asc")
            )
            cursor = PaginationFilterBuilder(
                self.model,
                self._pagination_marker,
                sort_col,
                sort_dir,
            )
            pagination_filters = cursor.build_filter()
            filters = dm_filters.AND(pagination_filters, filters)

        # Build final ordering
        # Don't add ID tiebreaker if ID is already the primary sort
        id_name = self.model.get_id_property_name()
        if order_by:
            order_by = order_by.copy()
            if id_name not in order_by:
                order_by[id_name] = "asc"
        else:
            order_by = {id_name: "asc"}

        return filters, order_by

    def paginated_filter(self, filters, order_by=None):
        custom_filters, storage_filters = self._split_filters(filters)

        cleaned_results = []

        # Get additional data from DB if some was filtered by custom props
        while len(cleaned_results) < self._pagination_limit:
            result = self._process_storage_filters(
                storage_filters, order_by=order_by
            )

            if not len(result):
                break

            self._pagination_marker = getattr(
                result[-1], self.model.get_id_property_name()
            )

            cleaned_results.extend(
                self._process_custom_filters(result, custom_filters)
            )

        if len(cleaned_results) > self._pagination_limit:
            cleaned_results = cleaned_results[: self._pagination_limit]

        return cleaned_results


class BaseResourceControllerPaginated(
    BasePaginationMixin, BaseResourceController
):

    def filter(self, filters, order_by=None):
        # NOTE(g.melikov): if you want to add pagination and you need to
        #  override `filter` method - it's better to add custom filters into
        #  `_process_custom_filters`.
        if self._pagination_limit:
            return self.paginated_filter(filters, order_by=order_by)

        return super(BasePaginationMixin, self).filter(
            filters, order_by=order_by
        )


class BaseNestedResourceControllerPaginated(
    BasePaginationMixin, BaseNestedResourceController
):

    def filter(self, parent_resource, filters, order_by=None):
        filters = filters.copy()
        filters[self.__pr_name__] = dm_filters.EQ(parent_resource)

        if self._pagination_limit:
            return self.paginated_filter(filters, order_by=order_by)

        return super(BaseNestedResourceController, self).filter(
            filters, order_by=order_by
        )


class RoutesListController(Controller):
    __TARGET_PATH__ = "/"

    def _get_target_route(self, target_path):
        """
        Finds the route from main route by target_path.

        :param target_path: the path to find the route from main route
        :return: the target route
        """
        result = self.request.application.main_route
        for next_path in target_path.rstrip("/").split("/")[1:]:
            result = getattr(result, next_path)
        return result

    def filter(self, filters, order_by=None):
        """
        Returns a list of all routes in the main route that are collection
        routes.

        The `__TARGET_PATH__` attribute on the class determines the target
        route that is filtered.

        :param filters: the filters to apply when filtering the routes (Is not
            implemented now)
        :param order_by: fields to order the routes by (Is not implemented
            now)
        :return: a list of route names
        """
        target_route = self._get_target_route(self.__TARGET_PATH__)
        req = self.request
        return [
            route_name
            for route_name in target_route.get_routes()
            if target_route.get_route(route_name)(req).is_collection_route()
        ]


class RootController(RoutesListController):

    def filter(self, filters, order_by=None):
        main_route = self.request.application.main_route
        req = self.request
        return [
            route_name
            for route_name in main_route.get_routes()
            if main_route.get_route(route_name)(req).is_collection_route()
        ]


class OpenApiSpecificationController(Controller):

    @oa_utils.extend_schema(
        summary="OpenApi specification",
        responses=oa_c.build_openapi_object_response(
            properties={}, description="OpenApi specification"
        ),
        operation_id="Get_OpenApi_specification",
    )
    def get(self, uuid):
        openapi_engine = self.request.application.openapi_engine
        if openapi_engine:
            return openapi_engine.build_openapi_specification(
                version=uuid,
                request=self._req,
            )
        raise exc.NotExtended()

    def filter(self, filters, order_by=None):
        openapi_engine = self.request.application.openapi_engine
        if openapi_engine:
            return openapi_engine.list_supported_openapi_versions()
        return []
