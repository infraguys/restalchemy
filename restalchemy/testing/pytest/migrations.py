import typing as tp
import contextlib

import pytest

from restalchemy.testing import typing as testing_tp
from restalchemy.testing.utils import migrations as testing_utils_migrations


class MigrationEngineCreator(tp.Protocol):
    def __call__(
        self,
        config: tp.Optional[testing_utils_migrations.TestMigrationManagerConfig] = None,
    ) -> "contextlib.AbstractContextManager[testing_utils_migrations.TestMigrationManager]": ...


@pytest.fixture(scope="session")
def migration_engine_creator() -> MigrationEngineCreator:
    @contextlib.contextmanager
    def _creator(
        config: tp.Optional[testing_utils_migrations.TestMigrationManagerConfig] = None,
    ) -> testing_tp.SimpleGenerator[testing_utils_migrations.TestMigrationManager]:
        with testing_utils_migrations.TestMigrationManager(
            migration_config=config
        ) as migration_manager, migration_manager.migrations():
            yield migration_manager

    return _creator


@pytest.fixture(scope="session")
def default_migration_engine(
    migration_engine_creator: MigrationEngineCreator,
) -> testing_tp.SimpleGenerator[testing_utils_migrations.TestMigrationManager]:
    with migration_engine_creator() as migration_engine:
        yield migration_engine
