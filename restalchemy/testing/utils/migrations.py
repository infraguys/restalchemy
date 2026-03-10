from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager

from typing import Type, TypeVar, Optional
from types import TracebackType

from restalchemy.storage.sql.migrations import MigrationEngine

from restalchemy.testing.typing import OptionalStr, SimpleGenerator
from restalchemy.testing.utils.db import TestDBManager


@dataclass()
class TestMigrationManagerConfig:
    migrations_path: OptionalStr = None
    first_migration: OptionalStr = None
    last_migration: OptionalStr = None
    engine_alias: OptionalStr = None

    def __post_init__(self) -> None:
        self.migrations_path = (
            self.migrations_path
            or (
                str(
                    Path().cwd()
                    .joinpath("/migrations/")
                    .resolve()
                )
            )
        )


class TestMigrationManager:
    _Self = TypeVar("_Self", bound="TestMigrationManager")

    _migration_engine: MigrationEngine

    def __init__(
        self,
        migration_config: Optional[TestMigrationManagerConfig] = None,
    ) -> None:
        self.migration_config = migration_config or TestMigrationManagerConfig()

    def setup(self: _Self) -> _Self:
        self._migration_engine = MigrationEngine(
            migrations_path=self.migration_config.migrations_path,
            engine=self.migration_config.engine_alias,
        )

        return self

    def __enter__(self: _Self) -> _Self:
        return self.setup()

    def __exit__(
        self,
        exc_type: Type[Exception],
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

    @contextmanager
    def migrations(self: _Self) -> SimpleGenerator[_Self]:
        try:
            yield self.apply_migrations()
        finally:
            self.rollback_migrations()