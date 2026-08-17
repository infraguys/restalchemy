"""Flask with SQLAlchemy's ORM, serialising by hand -- WSGI."""

import datetime
import uuid

import orjson
from flask import Flask
from flask import request
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

from bench import call
from bench import config
from bench.stacks import _sqlalchemy_model as model

NAME = "Flask + SQLAlchemy"
KIND = "framework + ORM"


class Stack(object):
    name = NAME
    kind = KIND

    def setup(self):
        self._engine = create_engine(
            config.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://"),
            pool_size=4,
            max_overflow=0,
        )
        app = Flask(__name__)

        @app.get("/items/")
        def collection():
            with Session(self._engine) as session:
                items = session.scalars(
                    select(model.Item).order_by(model.Item.quantity).limit(config.PAGE)
                ).all()
                body = orjson.dumps([model.document(item) for item in items])
            return app.response_class(body, mimetype="application/json")

        @app.get("/items/<item_id>")
        def resource(item_id):
            with Session(self._engine) as session:
                item = session.get(model.Item, uuid.UUID(item_id))
                body = orjson.dumps(model.document(item))
            return app.response_class(body, mimetype="application/json")

        @app.post("/items/")
        def create():
            record = orjson.loads(request.get_data())
            now = datetime.datetime.now(datetime.timezone.utc)
            item = model.Item(
                id=uuid.uuid4(),
                name=record["name"],
                description=record["description"],
                enabled=record["enabled"],
                quantity=record["quantity"],
                project_id=uuid.UUID(record["project_id"]),
                created_at=now,
                updated_at=now,
            )
            # expire_on_commit would send us back for the row we
            # just wrote; every other stack here keeps it too.
            with Session(self._engine, expire_on_commit=False) as session:
                session.add(item)
                session.commit()
                body = orjson.dumps(model.document(item))
            return app.response_class(body, status=201, mimetype="application/json")

        self._app = app

    def teardown(self):
        self._engine.dispose()

    def collection(self):
        return call.wsgi(self._app, "GET", "/items/")

    def resource(self, item_id):
        return call.wsgi(self._app, "GET", "/items/%s" % item_id)

    def create(self, document):
        return call.wsgi(self._app, "POST", "/items/", document)
