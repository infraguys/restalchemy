import os
import typing as tp
import contextlib
from types import TracebackType

from dataclasses import dataclass

from restalchemy.testing import typing as ra_tp
from restalchemy.storage.sql import engines, sessions, orm


T = tp.TypeVar("T")
SimpleGenerator = ra_tp.SimpleGenerator
DBEscapeFunction = tp.Callable[[str], str]
OptionalDBEscapeFunction = tp.Optional[DBEscapeFunction]


_DATABASE_URI_DEFAULT = "mysql://test:test@127.0.0.1:/test"
_DATABASE_POSTFIX = "test"


def get_database_uri() -> str:
    return os.getenv("DATABASE_URI", _DATABASE_URI_DEFAULT)


def get_database_postfix() -> str:
    return os.getenv("DATABASE_POSTFIX", _DATABASE_POSTFIX)


TableNameOrModel = tp.Union[str, tp.Type[orm.SQLStorableMixin]]


class ClearTableRecord:
    def __init__(
        self,
        table: TableNameOrModel,
        truncate: bool = True,
    ) -> None:
        if issubclass(table, orm.SQLStorableMixin):
            table = table.__tablename__
            if table is None:
                raise ValueError(f"'{table}' has no valid '__tablename__' attribute")

        self._table = table
        self._truncate = truncate

    def __hash__(self) -> int:
        return hash(self._table)

    def statement(self, escape_function: OptionalDBEscapeFunction = None) -> str:
        table = (
            escape_function(self._table) if escape_function is not None else self._table
        )

        if self._truncate:
            return f"TRUNCATE TABLE {table}"
        else:
            return f"DELETE FROM {table}"


DictClearTableRecords = tp.Dict[ClearTableRecord, ClearTableRecord]


class ClearTableRecords:
    _Self = tp.TypeVar("_Self", bound="ClearTableRecords")

    def __init__(self) -> None:
        self._records: DictClearTableRecords = {}
        self._level = 0

    def at_lowest_level(self) -> bool:
        return self._level <= 0

    def add(
        self: _Self,
        table: TableNameOrModel,
        *tables: TableNameOrModel,
        truncate: bool = True,
    ) -> _Self:
        for table in [table, *tables]:
            record = ClearTableRecord(table, truncate=truncate)
            self._records[record] = record

        return self

    def __iter__(self) -> tp.Iterator[ClearTableRecord]:
        return (record for record in reversed(self._records.values()))

    def statements(
        self,
        escape_function: OptionalDBEscapeFunction = None,
    ) -> tp.Iterator[str]:
        return (record.statement(escape_function=escape_function) for record in self)

    def __enter__(self: _Self) -> _Self:
        self._level += 1

        return self

    def __exit__(
        self,
        exc_type: tp.Optional[tp.Type[Exception]],
        exc_val: tp.Optional[Exception],
        exc_tb: tp.Optional[TracebackType],
    ) -> None:
        self._level -= 1


@dataclass()
class TestDBManagerConfig:
    database_url: ra_tp.OptionalStr = None
    engine_alias: ra_tp.OptionalStr = None
    create_db: ra_tp.OptionalStr = None

    def __post_init__(self) -> None:
        self.database_url = self.database_url or get_database_uri()
        self.engine_alias = self.engine_alias or engines.DEFAULT_NAME


class TestDBManager:
    _Self = tp.TypeVar("_Self", bound="TestDBManager")

    _engine: engines.AbstractEngine

    def __init__(self, *, manager_config: TestDBManagerConfig = None) -> None:
        self.manager_config = manager_config or TestDBManagerConfig()
        self._clear_tables = ClearTableRecords()

    @property
    def engine(self) -> engines.AbstractEngine:
        return self._engine

    def setup(self: _Self) -> _Self:
        engine_alias = self.manager_config.engine_alias

        engines.engine_factory.configure_factory(
            db_url=self.manager_config.database_url,
            name=engine_alias,
        )
        self._engine = engines.engine_factory.get_engine(engine_alias)

        return self

    def teardown(self) -> None:
        engines.engine_factory.destroy_engine(
            name=self.manager_config.engine_alias,
        )

    def __enter__(self: _Self) -> _Self:
        return self.setup()

    def __exit__(
        self,
        exc_type: tp.Type[Exception],
        exc_val: Exception,
        exc_tb: TracebackType,
    ) -> None:
        self.teardown()

    @contextlib.contextmanager
    def session(self) -> SimpleGenerator[sessions.AbstractSession]:
        session = self._engine.get_session()

        try:
            with engines.using(self._engine) as engine:
                session = engine.get_session()
                yield session
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextlib.contextmanager
    def connection(
        self,
        autocommit: bool = False,
    ) -> SimpleGenerator[sessions.AbstractConnection]:
        connection = self._engine.get_connection()

        try:
            if hasattr(connection, "autocommit"):
                connection.autocommit = autocommit

            yield connection
            connection.commit()

        except Exception:
            if not autocommit:
                connection.rollback()
            raise
        finally:
            self._engine.close_connection(connection)

    def create_db(self) -> None:
        create_db = self.manager_config.create_db
        if create_db is None:
            return

        with self.connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE {self._engine.escape(create_db)}")

    def drop_db(self) -> None:
        create_db = self.manager_config.create_db
        if create_db is None:
            return

        with self.connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE {self._engine.escape(create_db)}")

    @contextlib.contextmanager
    def db(self: _Self) -> SimpleGenerator[_Self]:
        try:
            self.create_db()
            yield self

        finally:
            self.drop_db()

    def _finally_clear_tables(self) -> None:
        if not self._clear_tables.at_lowest_level():
            return

        with self.connection() as connection, connection.cursor() as cursor:
            for statement in self._clear_tables.statements(
                escape_function=self._engine.escape,
            ):
                cursor.execute(statement)

    @contextlib.contextmanager
    def clear_tables(
        self: _Self,
        table: TableNameOrModel,
        *tables: TableNameOrModel,
        truncate: bool = True,
    ) -> SimpleGenerator[_Self]:
        clear_tables = self._clear_tables.add(
            table,
            *tables,
            truncate=truncate,
        )

        try:
            with clear_tables:
                yield self
        finally:
            self._finally_clear_tables()
