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
import threading

from restalchemy.common import exceptions as e
from restalchemy.storage.sql import engines


LOG = logging.getLogger(__name__)


class Context(object):

    def __init__(self, engine_name=engines.DEFAULT_NAME):
        """
        Initializes the context with a given engine name.

        :param engine_name: The name of the engine to use. Defaults to
            DEFAULT_NAME.
        :type engine_name: str
        """
        super(Context, self).__init__()
        self._engine_name = engine_name

    def start_new_session(self):
        """
        Starts a new session.

        :return: A session object.
        :rtype: Session
        """
        engine = self._engine
        storage = engine.get_session_storage()
        session = engine.get_session()
        try:
            storage.store_session(session)
        except Exception:
            # Return the session to the pool and raise the exception.
            session.close()
            raise
        LOG.debug("New session %r has been started", session)
        return session

    @property
    def _engine(self):
        """
        Property that returns the current engine instance.

        The engine instance is retrieved from the engine factory based on the
        engine name provided during object initialization. If the engine
        instance does not exist, a ValueError is raised.

        :returns: The current engine instance.
        :rtype: AbstractEngine
        :raises ValueError: If the engine instance does not exist.
        """
        return engines.engine_factory.get_engine(name=self._engine_name)

    @contextlib.contextmanager
    def session_manager(self):
        """
        A context manager for managing a database session.

        This method provides a context for executing database operations within
        a session. If a session is not provided, it attempts to retrieve one
        from storage or creates a new session. The session is automatically
        committed if no exceptions occur, otherwise it is rolled back. The
        session is always closed when the context exits.

        :returns: The active session for database operations.
        :raises Exception: Any exceptions raised during the session's execution
            will result in a rollback of the session.
        """
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
        """
        Retrieve the session storage object from the engine.

        This method accesses the engine associated with the context to
        obtain the session storage object. The session storage object
        is responsible for managing session objects within the engine.

        :returns: The session storage object.
        :rtype: SessionThreadStorage
        """

        engine = self._engine
        return engine.get_session_storage()

    def get_session(self):
        """
        Returns a session object from the session storage associated with
        this context's engine.

        If a session object does not exist in the session storage, a new
        session object is created and returned.

        :returns: A session object.
        :rtype: Session
        """
        return self._get_storage().get_session()

    def session_close(self):
        """
        Close a session object from thread storage and remove it from
        thread storage.

        If session object is not found in thread storage, this method
        doesn't do anything.

        :raises: Any exceptions raised during session's closing will
            result in a log message and then discarded.
        """
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


class StorageRuntimeException(e.RestAlchemyException):
    __template__ = "Storage runtime error: %(message)s"


class ReadOnlyStorage(StorageRuntimeException):
    __template__ = "%(name)s Key is read only."


class ContextRuntimeException(e.RestAlchemyException):
    __template__ = "Context runtime error: %(message)s"


class ContextAlreadyInStorage(ContextRuntimeException):

    def __init__(self, message="Context is already in storage."):
        super().__init__(message=message)


class ContextIsNotExistsInStorage(ContextRuntimeException):

    def __init__(self, message="Context is not exists in storage."):
        super().__init__(message=message)


class Storage:
    def __init__(self, data: dict = None):
        """
        Initialize the global storage.

        :param data: The dictionary with initial data.
        :type data: dict
        """
        self._storage = {}
        if data is not None:
            self._storage = data.copy()

    def put(self, name, value, read_only=False):
        """
        Store a key-value pair in the storage.

        :param name: The name of the key to store the value.
        :type name: str
        :param value: The value to be stored associated with the key.
        :type value: object
        :param read_only: A boolean indicating whether the key is read only.
            If True, the key can't be changed once it is set.
        :type read_only: bool
        """

        if name in self._storage and self._storage[name]["read_only"]:
            raise ReadOnlyStorage(name=name)

        self._storage[name] = {
            value: value,
            "read_only": read_only,
        }

    def get(self, name):
        """
        Get the value from the storage by name.

        :param name: The name of the key in the storage.
        :type name: str
        :return: The value associated with the key.
        :rtype: object
        :raises KeyError: When there is no key with the given name.
        """
        return self._storage[name]["value"]

    def delete(self, name, force=False):
        """
        Delete the key-value pair from the storage.

        :param name: The name of the key to delete.
        :type name: str
        :param force: Force deletion of the key-value pair even if
            the key is read only.
        :type force: bool
        :raises KeyError: If there is no key with the given name.
        :raises ReadOnlyStorageError: If the key is read only and
            force is False.
        """

        if name in self._storage and self._storage[name]["read_only"]:
            if not force:
                raise ReadOnlyStorage(name=name)

        del self._storage[name]


class ContextWithStorage(Context):

    _local_thread_storage = threading.local()

    def __init__(
        self,
        engine_name: str = engines.DEFAULT_NAME,
        context_storage: Storage = None,
    ):
        """
        Initialize the context with storage.

        :param engine_name: The name of the engine to use. Defaults to
            DEFAULT_NAME.
        :type engine_name: str
        :param context_storage: The storage object to use. Defaults to None,
            which means a new Storage object will be created.
        :type context_storage: Storage
        """
        super(ContextWithStorage, self).__init__(engine_name=engine_name)
        self._context_storage = context_storage or Storage()

    @property
    def context_storage(self):
        """
        The storage object associated with the context.

        :rtype: Storage
        """
        return self._context_storage

    @classmethod
    def _store_context_session(cls, context):
        """
        Store the context in the local thread storage.

        :param context: The context to be stored.
        :type context: ContextWithStorage
        :raises RuntimeError: If the context is already stored.
        """
        if hasattr(cls._local_thread_storage, "context"):
            raise ContextAlreadyInStorage()

        cls._local_thread_storage.context = context

    @classmethod
    def _clear_context(cls):
        """
        Clear the context from the local thread storage.

        :raises ContextIsNotExistsInStorage: If there is no context associated
            with the local thread.
        """
        if not hasattr(cls._local_thread_storage, "context"):
            raise ContextIsNotExistsInStorage()
        del cls._local_thread_storage.context

    @classmethod
    def get_context(cls):
        """
        Get the current context.

        Returns the current context from the storage associated with the local
        thread.

        :return: The current context.
        :rtype: ContextWithStorage
        :raises ContextIsNotExistsInStorage: If there is no context associated
            with the local thread.
        """
        if not hasattr(cls._local_thread_storage, "context"):
            raise ContextIsNotExistsInStorage()
        return cls._local_thread_storage.context

    @contextlib.contextmanager
    def context_manager(self):
        """
        Context manager to manage the lifecycle of a context.

        This context manager temporarily stores the context in a local thread
        storage, making it accessible within the managed block. Upon exiting
        the block, the context is cleared from the storage.

        :yields: The current context.
        :raises ContextAlreadyInStorage: If a context is already stored.
        :raises ContextIsNotExistsInStorage: If the context does not exist in
            storage when attempting to clear it.
        """

        LOG.debug("Start context manager with context %r", self)
        self._store_context_session(self)
        try:
            yield self.get_context()
        finally:
            LOG.debug("End context manager with context %r", self)
            self._clear_context()


def get_context():
    """
    Get the current context.

    Returns the current context from the storage associated with the local
    thread.

    :return: The current context.
    :rtype: ContextWithStorage
    :raises ContextIsNotExistsInStorage: If there is no context associated
        with the local thread.
    """
    return ContextWithStorage.get_context()
