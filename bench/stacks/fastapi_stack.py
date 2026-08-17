"""FastAPI the way FastAPI is written: async SQLAlchemy, pydantic out."""

import datetime
import uuid

from fastapi import FastAPI
from pydantic import BaseModel
from pydantic import ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from bench import call
from bench import config
from bench.stacks import _sqlalchemy_model as model

NAME = "FastAPI + SQLAlchemy"
KIND = "framework + ORM"


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    enabled: bool
    quantity: int
    project_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ItemIn(BaseModel):
    name: str
    description: str
    enabled: bool
    quantity: int
    project_id: uuid.UUID


class Stack(object):
    name = NAME
    kind = KIND

    def setup(self):
        self._engine = create_async_engine(
            config.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://"),
            pool_size=4,
            max_overflow=0,
        )
        sessions = async_sessionmaker(self._engine, expire_on_commit=False)
        app = FastAPI()

        @app.get("/items/", response_model=list[ItemOut])
        async def collection():
            async with sessions() as session:
                result = await session.scalars(
                    select(model.Item).order_by(model.Item.quantity).limit(config.PAGE)
                )
                return result.all()

        @app.get("/items/{item_id}", response_model=ItemOut)
        async def resource(item_id: uuid.UUID):
            async with sessions() as session:
                return await session.get(model.Item, item_id)

        @app.post("/items/", response_model=ItemOut, status_code=201)
        async def create(payload: ItemIn):
            now = datetime.datetime.now(datetime.timezone.utc)
            item = model.Item(
                id=uuid.uuid4(),
                name=payload.name,
                description=payload.description,
                enabled=payload.enabled,
                quantity=payload.quantity,
                project_id=payload.project_id,
                created_at=now,
                updated_at=now,
            )
            async with sessions() as session:
                session.add(item)
                await session.commit()
            return item

        self._caller = call.AsgiCaller(app)
        self._caller.startup()

    def teardown(self):
        self._caller.shutdown()

    def collection(self):
        return self._caller("GET", "/items/")

    def resource(self, item_id):
        return self._caller("GET", "/items/%s" % item_id)

    def create(self, document):
        return self._caller("POST", "/items/", document)
