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
import logging

from restalchemy.storage.sql import engines


LOG = logging.getLogger(__name__)


class Context(object):

    def __init__(self, engine_name=engines.DEFAULT_NAME):
        super(Context, self).__init__()
        self._engine_name = engine_name

    def start_new_session(self):
        engine = self._engine
        storage = engine.get_session_storage()
        session = engine.get_session()
        storage.store_session(session)
        LOG.debug("New session %r has been started", session)
        return session

    @property
    def _engine(self):
        return engines.engine_factory.get_engine(name=self._engine_name)

    @contextlib.contextmanager
    def session_manager(self):
        session = self.start_new_session()
        try:
            yield session
            session.commit()
            LOG.debug("Session %r has been committed", session)
        except Exception:
            session.rollback()
            LOG.exception(
                "Session %r has been rolled back by reason:", session
            )
            raise
        finally:
            self.session_close()

    def _get_storage(self):
        engine = self._engine
        return engine.get_session_storage()

    def get_session(self):
        return self._get_storage().get_session()

    def session_close(self):
        session = self.get_session()
        try:
            session.close()
            LOG.debug("Session %r has been closed", session)
        except Exception:
            LOG.exception("Can't close session by reason:")
        finally:
            self._get_storage().remove_session()
            LOG.debug(
                "Session %r has been removed from thread storage", session
            )
