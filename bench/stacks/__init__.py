"""Every stack the benchmark knows how to ask the same question of."""

import importlib

MODULES = (
    "bench.stacks.raw_stack",
    "bench.stacks.restalchemy_stack",
    "bench.stacks.django_stack",
    "bench.stacks.flask_stack",
    "bench.stacks.fastapi_stack",
    "bench.stacks.litestar_stack",
)


def load(only=()):
    stacks = []
    for name in MODULES:
        module = importlib.import_module(name)
        if only and not any(key.lower() in module.NAME.lower() for key in only):
            continue
        stacks.append(module.Stack())
    return stacks
