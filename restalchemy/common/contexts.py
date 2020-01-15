# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import contextlib

from restalchemy.storage.sql import engines


class Context(object):

    def __init__(self):
        super(Context, self).__init__()

    def start_new_session(self):
        engine = engines.engine_factory.get_engine()
        storage = engine.get_session_storage()
        session = engine.get_session()
        storage.store_session(session)
        return session

    @contextlib.contextmanager
    def session_manager(self):
        session = self.start_new_session()
        try:
            yield session
            self.session_commit()
        except Exception:
            self.session_rollback()
            raise

    def get_session(self):
        engine = engines.engine_factory.get_engine()
        storage = engine.get_session_storage()
        return storage.get_session()

    def session_commit(self):
        self.get_session().commit()
        self._close()

    def session_rollback(self):
        self.get_session().rollback()
        self._close()

    def _close(self):
        engine = engines.engine_factory.get_engine()
        storage = engine.get_session_storage()
        storage.get_session().close()
        storage.remove_session()
