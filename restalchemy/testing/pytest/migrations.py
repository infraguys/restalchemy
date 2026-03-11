from typing import Protocol, Optional
from contextlib import contextmanager, AbstractContextManager

import pytest

from restalchemy.testing.typing import SimpleGenerator
from restalchemy.testing.utils.migrations import (
    TestMigrationManagerConfig,
    TestMigrationManager,
)


class MigrationEngineCreator(Protocol):
    def __call__(
        self,
        config: Optional[TestMigrationManagerConfig] = None,
    ) -> "AbstractContextManager[TestMigrationManager]": ...


@pytest.fixture(scope="session")
def migration_engine_creator() -> MigrationEngineCreator:
    @contextmanager
    def _creator(
        config: Optional[TestMigrationManagerConfig] = None,
    ) -> SimpleGenerator[TestMigrationManager]:
        with TestMigrationManager(
            migration_config=config
        ) as migration_manager, migration_manager.migrations():
            yield migration_manager

    return _creator


@pytest.fixture(scope="session")
def default_migration_engine(
    migration_engine_creator: MigrationEngineCreator,
) -> SimpleGenerator[TestMigrationManager]:
    with migration_engine_creator() as migration_engine:
        yield migration_engine
