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

from restalchemy.api import constants
from restalchemy.common import exceptions as exc


class ActionHandler(object):

    def __init__(self, get=None, post=None, put=None):
        self._get = get
        self._post = post
        self._put = put
        self._method_actions_map = {
            get: constants.ACTION_GET,
            post: constants.ACTION_POST,
            put: constants.ACTION_PUT,
        }
        if get:
            self._name = get.__name__
            self._method = constants.GET
        elif post:
            self._name = post.__name__
            self._method = constants.POST
        elif put:
            self._name = put.__name__
            self._method = constants.PUT

    def get(self, fn):
        self._get = fn
        return self

    @property
    def name(self):
        return self._name

    @property
    def method(self):
        return self._method

    def post(self, fn):
        self._post = fn
        return self

    def put(self, fn):
        self._put = fn
        return self

    def do(self, fn, controller, *args, **kwargs):
        if fn:
            api_context = controller.request.api_context
            api_context.set_active_method(self._method_actions_map[fn])
            result = fn(self=controller, *args, **kwargs)
            return controller.process_result(result=result)
        else:
            raise exc.NotImplementedError()

    def do_get(self, *args, **kwargs):
        return self.do(self._get, *args, **kwargs)

    def do_post(self, *args, **kwargs):
        return self.do(self._post, *args, **kwargs)

    def do_put(self, *args, **kwargs):
        return self.do(self._put, *args, **kwargs)


def get(fn):
    return ActionHandler(get=fn)


def post(fn):
    return ActionHandler(post=fn)


def put(fn):
    return ActionHandler(put=fn)
