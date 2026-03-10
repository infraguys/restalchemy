import os
import typing as tp
from dataclasses import dataclass
from urllib.parse import urlparse
from contextlib import AbstractContextManager, contextmanager

import pytest

from restalchemy.storage.sql.env_config import (
    EngineENVConfig,
    env_configs,
    DEFAULT_NAME,
)
from restalchemy.testing.typing import SimpleGenerator, WorkerID
from restalchemy.testing.utils.db import (
    TestDBManagerConfig,
    TestDBManager,
    get_database_uri,
    get_database_postfix,
)


@dataclass(frozen=True)
class DBConfig:
    database_uri: str
    database_postfix: str = "test"
    worker_id: WorkerID = None

    def test_database_postfix(self) -> str:
        return (
            self.database_postfix
            if self.worker_id is None
            else f"{self.database_postfix}_{self.worker_id}"
        )

    def test_database_name(self) -> str:
        parsed = urlparse(self.database_uri)
        return f"{parsed.path}_{self.test_database_postfix()}".strip("/")

    def test_database_uri(self) -> str:
        parsed = urlparse(self.database_uri)
        return parsed._replace(path=self.test_database_name()).geturl()


class SetupEngineFromENV(tp.Protocol):
    def __call__(self, name: str) -> EngineENVConfig:
        ...


@pytest.fixture(scope="session")
def setup_engine_from_env() -> SetupEngineFromENV:
    def _setup(name: str) -> EngineENVConfig:
        return env_configs[name]

    return _setup


class DatabaseConfigFromENV(tp.Protocol):
    def __call__(self, name: str, postfix: tp.Optional[str] = None) -> DBConfig:
        ...


@pytest.fixture(scope="session")
def database_config_from_env(
    setup_engine_from_env: SetupEngineFromENV,
    xdist_worker_id: WorkerID,
) -> DatabaseConfigFromENV:
    def _config(name: str, postfix: tp.Optional[str] = None) -> DBConfig:
        config = setup_engine_from_env(name)

        return DBConfig(
            database_uri=config.database_uri,
            database_postfix=postfix or get_database_postfix(),
            worker_id=xdist_worker_id,
        )

    return _config


class TestDBManagerCreator(tp.Protocol):
    def __call__(
        self,
        engine_alias: str = DEFAULT_NAME,
    ) -> AbstractContextManager[TestDBManager]:
        ...


@pytest.fixture(scope="session")
def db_manager_creator(
    database_config_from_env: DatabaseConfigFromENV,
) -> TestDBManagerCreator:
    @contextmanager
    def _creator(
        engine_alias: str = DEFAULT_NAME,
    ) -> SimpleGenerator[TestDBManager]:
        database_config = database_config_from_env(engine_alias)

        db_manager_config = TestDBManagerConfig(
            database_url=database_config.database_uri,
            create_db=database_config.test_database_name(),
            engine_alias=engine_alias,
        )

        test_db_manager_config = TestDBManagerConfig(
            database_url=database_config.test_database_uri(),
            engine_alias=engine_alias,
        )

        with \
            TestDBManager(manager_config=db_manager_config) as db_manager, \
            db_manager.db() \
        :
            with TestDBManager(
                manager_config=test_db_manager_config,
            ) as test_db_manager:
                yield test_db_manager

    return _creator


@pytest.fixture(scope="session")
def default_db_manager(
    db_manager_creator: TestDBManagerCreator,
) -> SimpleGenerator[TestDBManager]:
    with db_manager_creator() as db_manager:
        yield db_manager


