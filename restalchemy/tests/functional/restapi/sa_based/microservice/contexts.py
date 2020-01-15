# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

from restalchemy.common import contexts
from restalchemy.tests.functional.restapi.sa_based.microservice import db


class Context(contexts.Context):

    _Session = None
    _session = None

    def get_session(self):
        if self._Session is None:
            self._Session = db.get_session()
        return self._Session()

    @property
    def session(self):
        if self._session is None:
            self._session = self.get_session()
        return self._session

    def release(self):
        if self._session:
            self._session.close()
            self._session = None
        if self._Session:
            self._Session.close_all()
            self._Session = None
