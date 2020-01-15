# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import logging

import six
import webob

from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.common import exceptions as exc
from restalchemy.dm import filters as dm_filters


LOG = logging.getLogger(__name__)


class Controller(object):
    __resource__ = None  # type: resources.ResourceByRAModel

    def __init__(self, request):
        super(Controller, self).__init__()
        self._req = request

    def get_packer(self, content_type, resource_type=None):
        packer = packers.get_packer(content_type)
        rt = resource_type or self.get_resource()
        return packer(rt, request=self._req)

    def process_result(self, result, status_code=200, headers=None,
                       add_location=False):
        headers = headers or {}

        def correct(body, c=status_code, h=None, *args):
            h = h or {}
            if add_location:
                try:
                    headers['Location'] = resources.ResourceMap.get_location(
                        body)
                except (exc.UnknownResourceLocation,
                        exc.CanNotFindResourceByModel) as e:
                    LOG.warning(
                        "Can't construct location header by reason: %r",
                        e)
            headers.update(h)
            return body, c, headers

        def create_response(body, status, headers):
            if body is not None:
                headers['Content-Type'] = packers.get_content_type(headers)
                packer = self.get_packer(headers['Content-Type'])
                body = packer.pack(body)

            return webob.Response(
                body=six.b(body or ''),
                status=status,
                content_type=headers.get('Content-Type', None),
                headerlist=[(k, v) for k, v in headers.items()])

        if type(result) == tuple:
            return create_response(*correct(*result))
        else:
            return create_response(*correct(result))

    def _make_kwargs(self, parent_resource, **kwargs):
        if parent_resource:
            kwargs['parent_resource'] = parent_resource
        return kwargs

    def _prepare_filter(self, param_name, value):
        resource_fields = {}
        if self.model is not None:
            resource_fields = {
                self.__resource__.get_resource_field_name(name): prop
                for name, prop in self.__resource__.get_fields()
            }
        if param_name not in resource_fields:
            raise ValueError("Unknown filter '%s' with value %r for "
                             "resource %r" % (param_name,
                                              value,
                                              self.__resource__))
        value = resource_fields[param_name].parse_value_from_unicode(
            self._req, value)
        param_name = resource_fields[param_name].name

        return param_name, value

    def _prepare_filters(self, params):
        if not (self.__resource__ and self.__resource__.is_process_filters()):
            return params
        result = {}
        for param, value in params.items():
            filter_name, filter_value = self._prepare_filter(param, value)
            if filter_name not in result:
                result[filter_name] = dm_filters.EQ(filter_value)
            else:
                values = ([result[filter_name].value]
                          if not isinstance(result[filter_name], dm_filters.In)
                          else result[filter_name].value)
                values.append(filter_value)
                result[filter_name] = dm_filters.In(values)

        return result

    def do_collection(self, parent_resource=None):
        method = self._req.method

        if method == 'GET':
            filters = self._prepare_filters(params=self._req.params)
            kwargs = self._make_kwargs(parent_resource, filters=filters)
            return self.process_result(self.filter(**kwargs))
        elif method == 'POST':
            content_type = packers.get_content_type(self._req.headers)
            packer = self.get_packer(content_type)
            kwargs = self._make_kwargs(parent_resource,
                                       **packer.unpack(self._req.body))

            return self.process_result(self.create(**kwargs), 201,
                                       add_location=True)
        else:
            raise exc.UnsupportedHttpMethod(method=method)

    def get_resource_by_uuid(self, uuid, parent_resource=None):
        kwargs = self._make_kwargs(parent_resource)
        result = self.get(uuid=uuid, **kwargs)
        if isinstance(result, tuple):
            return result[0]
        return result

    def do_resource(self, uuid, parent_resource=None):
        method = self._req.method
        kwargs = self._make_kwargs(parent_resource)

        parsed_id = (self.get_resource().get_id_type().from_unicode(uuid)
                     if self.__resource__ else uuid)

        if method == 'GET':
            return self.process_result(self.get(uuid=parsed_id, **kwargs))
        elif method == 'PUT':
            content_type = packers.get_content_type(self._req.headers)
            packer = self.get_packer(content_type)
            kwargs.update(packer.unpack(self._req.body))
            return self.process_result(self.update(uuid=parsed_id, **kwargs))
        elif method == 'DELETE':
            result = self.delete(uuid=parsed_id, **kwargs)
            return self.process_result(result, 200 if result else 204)
        else:
            raise exc.UnsupportedHttpMethod(method=method)

    @classmethod
    def get_resource(cls):
        return cls.__resource__

    @property
    def model(self):
        return self.get_resource().get_model()

    def create(self, **kwargs):
        raise exc.NotImplementedError()

    def get(self, uuid):
        raise exc.NotImplementedError()

    def filter(self, filters):
        raise exc.NotImplementedError()

    def delete(self, uuid):
        raise exc.NotImplementedError()

    def update(self, uuid, **kwargs):
        raise exc.NotImplementedError()

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
        kwargs[self.model.get_id_property_name()] = uuid
        return self.model.objects.get_one(filters=kwargs)

    def _split_filters(self, filters):
        if hasattr(self.model, 'get_custom_properties'):
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

    def filter(self, filters):
        custom_filters, storage_filters = self._split_filters(filters)

        result = self.model.objects.get_all(filters=storage_filters)

        for item in result[:]:
            for field_name, filter_value in custom_filters.items():
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
                    raise ValueError("Unknown filter %s<%s>" % (field_name,
                                                                filter_value))
        return result

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
            **self._prepare_kwargs(**kwargs))

    def get(self, **kwargs):
        return super(BaseNestedResourceController, self).get(
            **self._prepare_kwargs(**kwargs))

    def filter(self, parent_resource, filters):
        filters = filters.copy()
        filters[self.__pr_name__] = dm_filters.EQ(parent_resource)
        return super(BaseNestedResourceController, self).filter(
            filters=filters)

    def delete(self, parent_resource, uuid):
        dm = self.get(parent_resource=parent_resource, uuid=uuid)
        dm.delete()

    def update(self, parent_resource, uuid, **kwargs):
        dm = self.get(parent_resource=parent_resource, uuid=uuid)
        dm.update_dm(values=kwargs)
        dm.update()
        return dm
