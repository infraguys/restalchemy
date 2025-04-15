#    Copyright 2021 Eugene Frolov.
#
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

from webob import multidict

from restalchemy.common import exceptions


class CanNotGetActiveMethod(exceptions.RestAlchemyException):
    message = "Can not get active RA method from API context"


class RequestContext(object):

    _special_params = frozenset(
        ("fields", "page_limit", "page_marker", "sort_key", "sort_dir")
    )

    def __init__(self, request):
        super(RequestContext, self).__init__()
        self._req = request
        self._fields_to_show = request.params.getall("fields")
        self._method = None

    def set_active_method(self, method):
        self._method = method

    def get_active_method(self):
        if self._method:
            return self._method
        raise CanNotGetActiveMethod()

    @property
    def params(self):
        return multidict.MultiDict(self._req.params.items())

    @property
    def params_filters(self):
        result_multi_dict_items = [
            (name, value)
            for name, value in self._req.params.items()
            if name not in self._special_params
        ]
        return multidict.MultiDict(result_multi_dict_items)

    def can_be_shown_field(self, resource_field_name):
        if self._fields_to_show:
            return resource_field_name in self._fields_to_show
        return True
