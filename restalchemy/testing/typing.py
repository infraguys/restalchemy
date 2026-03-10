import typing as tp

T = tp.TypeVar("T")
OptionalStr = tp.Optional[str]

WorkerID = OptionalStr
SimpleGenerator = tp.Generator[T, None, None]