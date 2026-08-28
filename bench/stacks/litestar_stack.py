"""Litestar with async SQLAlchemy, serialising through msgspec."""

from __future__ import annotations

import datetime
import uuid

from litestar import Litestar
from litestar import get
from litestar import post
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from bench import call
from bench import config
from bench.stacks import _sqlalchemy_model as model

NAME = "Litestar + SQLAlchemy"
KIND = "framework + ORM"

_sessions = None


@get("/items/")
async def collection() -> list[dict]:
    async with _sessions() as session:
        result = await session.scalars(
            select(model.Item).order_by(model.Item.quantity).limit(config.PAGE)
        )
        return [model.document(item) for item in result.all()]


@get("/items/{item_id:uuid}")
async def resource(item_id: uuid.UUID) -> dict:
    async with _sessions() as session:
        return model.document(await session.get(model.Item, item_id))


@post("/items/", status_code=201)
async def create(data: dict) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    item = model.Item(
        id=uuid.uuid4(),
        name=data["name"],
        description=data["description"],
        enabled=data["enabled"],
        quantity=data["quantity"],
        project_id=uuid.UUID(data["project_id"]),
        created_at=now,
        updated_at=now,
    )
    async with _sessions() as session:
        session.add(item)
        await session.commit()
    return model.document(item)


class Stack:
    name = NAME
    kind = KIND

    def setup(self):
        global _sessions
        self._engine = create_async_engine(
            config.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://"),
            pool_size=4,
            max_overflow=0,
        )
        _sessions = async_sessionmaker(self._engine, expire_on_commit=False)
        self._caller = call.AsgiCaller(Litestar([collection, resource, create]))
        self._caller.startup()

    def teardown(self):
        self._caller.shutdown()

    def collection(self):
        return self._caller("GET", "/items/")

    def resource(self, item_id):
        return self._caller("GET", f"/items/{item_id}")

    def create(self, document):
        return self._caller("POST", "/items/", document)
