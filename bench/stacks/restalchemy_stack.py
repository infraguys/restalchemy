"""RestAlchemy: its own ORM, its own resources, WSGI."""

import sys
import typing
import uuid

from bench import call
from bench import config

sys.path.insert(0, config.RESTALCHEMY_PATH)

from restalchemy.api import applications
from restalchemy.api import controllers
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm

NAME = "RestAlchemy"
KIND = "framework + its own ORM"


class Item(models.ModelWithID, orm.SQLStorableMixin):
    __tablename__ = config.TABLE

    id = properties.property(
        types.UUID(), id_property=True, default=lambda: uuid.uuid4()
    )
    name = properties.property(types.String(max_length=255), required=True)
    description = properties.property(types.String(max_length=255), default="")
    enabled = properties.property(types.Boolean(), default=True)
    quantity = properties.property(types.Integer(), default=0)
    project_id = properties.property(types.UUID(), required=True)
    created_at = properties.property(types.UTCDateTimeZ(), default=lambda: _now())
    updated_at = properties.property(types.UTCDateTimeZ(), default=lambda: _now())


def _now():
    import datetime

    return datetime.datetime.now(datetime.timezone.utc)


class ItemController(controllers.Controller):
    __resource__ = resources.ResourceByRAModel(
        Item,
        process_filters=True,
        convert_underscore=False,
    )

    def filter(self, filters, order_by=None):
        return Item.objects.get_all(order_by={"quantity": "asc"}, limit=config.PAGE)

    def get(self, uuid):
        return Item.objects.get_one(filters={"id": dm_filters.EQ(uuid)})

    def create(self, **kwargs):
        item = Item(**kwargs)
        item.save()
        return item


class ItemsRoute(routes.Route):
    __controller__ = ItemController
    __allow_methods__: typing.ClassVar = [
        routes.FILTER,
        routes.GET,
        routes.CREATE,
    ]


class Root(routes.Route):
    __controller__ = ItemController
    __allow_methods__: typing.ClassVar = []
    items = routes.route(ItemsRoute)


class Stack:
    name = NAME
    kind = KIND

    def setup(self):
        engines.engine_factory.configure_factory(db_url=config.DATABASE_URL)
        self._app = applications.WSGIApp(route_class=Root)

    def teardown(self):
        engines.engine_factory.destroy_all_engines()

    def collection(self):
        return call.wsgi(self._app, "GET", "/items/")

    def resource(self, item_id):
        return call.wsgi(self._app, "GET", f"/items/{item_id}")

    def create(self, document):
        return call.wsgi(self._app, "POST", "/items/", document)
