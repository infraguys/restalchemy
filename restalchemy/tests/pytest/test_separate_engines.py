from typing import Iterable

from pathlib import Path

import pytest

from restalchemy.testing.utils import (
    TestDBManager,
    TestMigrationManagerConfig,
)
from restalchemy.testing.pytest import (
    TestDBManagerCreator,
    MigrationEngineCreator,
)

from .models import Model, SecondModel


@pytest.fixture(scope="session")
def default_db_manager(
    db_manager_creator: TestDBManagerCreator,
) -> Iterable[TestDBManager]:
    with db_manager_creator("default") as manager:
        yield manager


@pytest.fixture(scope="session")
def second_db_manager(
    db_manager_creator: TestDBManagerCreator,
) -> Iterable[TestDBManager]:
    with db_manager_creator("second") as manager:
        yield manager


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(
    default_db_manager: TestDBManager,
    second_db_manager: TestDBManager,
    migration_engine_creator: MigrationEngineCreator,
) -> Iterable[None]:
    self_path = Path(__file__).resolve().parent
    default_migrations_path = str(self_path.joinpath("migrations"))
    second_migrations_path = str(self_path.joinpath("second_migrations"))
    print("PATH", default_migrations_path, second_migrations_path)

    with migration_engine_creator(
        config=TestMigrationManagerConfig(
            migrations_path=default_migrations_path,
            first_migration="0000-init-cb5624.py",
            engine_alias="default",
        ),
    ), migration_engine_creator(
        config=TestMigrationManagerConfig(
            migrations_path=second_migrations_path,
            first_migration="0000-init-1e68bf.py",
            engine_alias="second",
        ),
    ):
        yield


def test_clear_tables(default_db_manager: TestDBManager) -> None:
    with default_db_manager.clear_tables(Model):
        Model(name="test").insert()

    with default_db_manager.clear_tables(Model):
        Model(name="test").insert()


def test_insert_into_separate_engines(
    default_db_manager: TestDBManager,
    second_db_manager: TestDBManager,
) -> None:
    with default_db_manager.clear_tables(Model), second_db_manager.clear_tables(
        SecondModel
    ):
        Model(name="name").insert()
        SecondModel(name="name").insert()
