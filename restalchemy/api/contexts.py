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

from restalchemy.common import exceptions


class CanNotGetActiveMethod(exceptions.RestAlchemyException):
    message = "Can not get active RA method from API context"


class RequestContext(object):

    def __init__(self, request):
        super(RequestContext, self).__init__()
        self._fields_to_show = request.params.getall('fields')
        self._method = None

    def set_active_method(self, method):
        self._method = method

    def get_active_method(self):
        if self._method:
            return self._method
        raise CanNotGetActiveMethod()
