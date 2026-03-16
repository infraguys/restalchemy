import contextlib
import dataclasses
import pathlib

import typing as tp

from types import TracebackType

from restalchemy.storage.sql import migrations

from restalchemy.testing import typing as testing_tp


@dataclasses.dataclass()
class TestMigrationManagerConfig:
    migrations_path: testing_tp.OptionalStr = None
    first_migration: testing_tp.OptionalStr = None
    last_migration: testing_tp.OptionalStr = None
    engine_alias: testing_tp.OptionalStr = None

    def __post_init__(self) -> None:
        self.migrations_path = self.migrations_path or (
            str(pathlib.Path().cwd().joinpath("migrations").resolve())
        )


class TestMigrationManager:
    _Self = tp.TypeVar("_Self", bound="TestMigrationManager")

    _migration_engine: migrations.MigrationEngine

    def __init__(
        self,
        migration_config: tp.Optional[TestMigrationManagerConfig] = None,
    ) -> None:
        self.migration_config = migration_config or TestMigrationManagerConfig()

    def setup(self: _Self) -> _Self:
        self._migration_engine = migrations.MigrationEngine(
            migrations_path=self.migration_config.migrations_path,
            engine=self.migration_config.engine_alias,
        )

        return self

    def __enter__(self: _Self) -> _Self:
        return self.setup()

    def __exit__(
        self,
        exc_type: tp.Type[Exception],
        exc_val: Exception,
        exc_tb: TracebackType,
    ) -> None:
        return

    def apply_migrations(self: _Self) -> _Self:
        last_migration = (
            self.migration_config.last_migration
            or self._migration_engine.get_latest_migration()
        )

        self._migration_engine.apply_migration(
            migration_name=last_migration,
        )

        return self

    def rollback_migrations(self) -> None:
        self._migration_engine.rollback_migration(
            migration_name=self.migration_config.first_migration,
        )

    @contextlib.contextmanager
    def migrations(self: _Self) -> testing_tp.SimpleGenerator[_Self]:
        try:
            yield self.apply_migrations()
        finally:
            self.rollback_migrations()
