from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    Generator,
    Optional,
    Set,
    TypeVar,
    Tuple,
    Final,
    final,
)

import os
from dataclasses import dataclass


DEFAULT_NAME = "default"

DictStrAny = Dict[str, Any]
T = TypeVar("T")
SimpleGenerator = Generator[T, None, None]
VALID_TRUE_VALUES: Final[Set] = {"true", "True", "yes", "1"}


class ENVConfigurationError(Exception): ...


class ENVConfigParseError(ENVConfigurationError): ...


@dataclass(frozen=True)
class ENVConfigMissingFieldError(ENVConfigParseError):
    field: str

    def __str__(self) -> str:
        return f"Missing required field '{self.field}'"


@dataclass(frozen=True)
class ENVConfigNotFoundError(ENVConfigurationError):
    engine_name: str
    exceptions: Optional[Iterable[ENVConfigurationError]] = None

    def __str__(self) -> str:
        return (
            f"No valid configuration found for Engine '{self.engine_name}'" + ""
            if not self.exceptions
            else (
                " due exceptions:\n\t" + "\t\n".join(e for e in self.exceptions) + "\n"
            )
        )


@final
@dataclass(frozen=True)
class EngineENVConfig:
    name: str
    database_uri: str
    query_cache: bool = False
    config: Optional[DictStrAny] = None  # TODO: write driver specific parsers

    @classmethod
    def from_env(cls, name: str) -> "EngineENVConfig":
        exceptions = []

        for prefix in cls._prefix_aliases(name):
            try:
                return cls(name=name, **cls._read_from_env(prefix))
            except ENVConfigParseError as e:
                exceptions.append(e)
                continue
        else:
            raise ENVConfigNotFoundError(
                engine_name=name,
                exceptions=exceptions,
            )

    @staticmethod
    def _prefix_aliases(name: str) -> Iterable[str]:
        return (
            [f"DATABASE_{name.upper()}"]
            if name != DEFAULT_NAME
            else ["DATABASE", "DATABASE_DEFAULT"]
        )

    @staticmethod
    def _read_from_env(prefix: str) -> DictStrAny:
        if (database_uri := os.environ.get(field := f"{prefix}_URI", None)) is None:
            raise ENVConfigMissingFieldError(field=field)

        query_cache = os.environ.get(f"{prefix}_QUERY_CACHE", None) in VALID_TRUE_VALUES

        return {
            "database_uri": database_uri,
            "query_cache": query_cache,
        }


@final
class EngineENVConfigs:
    _Self = TypeVar("_Self", bound="EngineENVConfigs")

    ENGINES_ENV_VAR: Final[str] = "DATABASE_ENGINES"

    def __init__(self) -> None:
        self._configs: Dict[str, EngineENVConfig] = {}

    def __getitem__(self, item: str) -> EngineENVConfig:
        if (config := self._configs.get(item)) is not None:
            return config

        config = EngineENVConfig.from_env(item)
        self._configs[item] = config
        return config

    def __iter__(self) -> Iterator[Tuple[str, EngineENVConfig]]:
        return ((name, config) for name, config in self._configs.items())

    def setup(self: _Self) -> _Self:
        self._configs = {
            name: EngineENVConfig.from_env(name) for name in self._get_engine_names()
        }

        return self

    def _get_engine_names(self) -> Iterable[str]:
        return {DEFAULT_NAME}.union(
            name.strip()
            for name in (os.environ.get(self.ENGINES_ENV_VAR, DEFAULT_NAME).split(","))
        )


env_configs: Final[EngineENVConfigs] = EngineENVConfigs()
