import typing as tp

import pathlib

import pytest

from restalchemy.testing import utils as testing_utils
from restalchemy.testing import pytest as testing_pytest

from . import models as test_models


@pytest.fixture(scope="session")
def default_db_manager(
    db_manager_creator: testing_pytest.TestDBManagerCreator,
) -> tp.Iterable[testing_utils.TestDBManager]:
    with db_manager_creator("default") as manager:
        yield manager


@pytest.fixture(scope="session")
def second_db_manager(
    db_manager_creator: testing_pytest.TestDBManagerCreator,
) -> tp.Iterable[testing_utils.TestDBManager]:
    with db_manager_creator("second") as manager:
        yield manager


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(
    default_db_manager: testing_utils.TestDBManager,
    second_db_manager: testing_utils.TestDBManager,
    migration_engine_creator: testing_pytest.MigrationEngineCreator,
) -> tp.Iterable[None]:
    self_path = pathlib.Path(__file__).resolve().parent
    default_migrations_path = str(self_path.joinpath("migrations"))
    second_migrations_path = str(self_path.joinpath("second_migrations"))

    with migration_engine_creator(
        config=testing_utils.TestMigrationManagerConfig(
            migrations_path=default_migrations_path,
            first_migration="0000-init-cb5624.py",
            engine_alias="default",
        ),
    ), migration_engine_creator(
        config=testing_utils.TestMigrationManagerConfig(
            migrations_path=second_migrations_path,
            first_migration="0000-init-1e68bf.py",
            engine_alias="second",
        ),
    ):
        yield


def test_clear_tables(default_db_manager: testing_utils.TestDBManager) -> None:
    with default_db_manager.clear_tables(test_models.Model):
        test_models.Model(name="test").insert()

    with default_db_manager.clear_tables(test_models.Model):
        test_models.Model(name="test").insert()


def test_insert_into_separate_engines(
    default_db_manager: testing_utils.TestDBManager,
    second_db_manager: testing_utils.TestDBManager,
) -> None:
    with default_db_manager.clear_tables(
        test_models.Model
    ), second_db_manager.clear_tables(test_models.SecondModel):
        test_models.Model(name="name").insert()
        test_models.SecondModel(name="name").insert()
