"""Django with the REST framework -- its ORM, its serialiser, WSGI."""

import datetime
import uuid

from bench import call
from bench import config

NAME = "Django + DRF"
KIND = "framework + ORM"

_configured = False


def _configure():
    global _configured
    if _configured:
        return
    import django
    from django.conf import settings

    url = config.DATABASE_URL.split("://", 1)[1]
    credentials, location = url.split("@", 1)
    user = credentials.split(":")[0]
    host_port, database = location.split("/", 1)
    host, port = host_port.split(":")

    settings.configure(
        DEBUG=False,
        ALLOWED_HOSTS=["*"],
        SECRET_KEY="bench",
        USE_TZ=True,
        TIME_ZONE="UTC",
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": database,
                "USER": user,
                "HOST": host,
                "PORT": port,
                "CONN_MAX_AGE": 600,
                "OPTIONS": {},
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "rest_framework",
            "bench.stacks.django_stack",
        ],
        MIDDLEWARE=[],
        ROOT_URLCONF="bench.stacks.django_stack",
        REST_FRAMEWORK={"UNAUTHENTICATED_USER": None},
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )
    django.setup()
    _configured = True


_configure()

from django.db import models as django_models
from django.urls import path
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response


class Item(django_models.Model):
    id = django_models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = django_models.CharField(max_length=255)
    description = django_models.CharField(max_length=255)
    enabled = django_models.BooleanField()
    quantity = django_models.IntegerField()
    project_id = django_models.UUIDField()
    created_at = django_models.DateTimeField()
    updated_at = django_models.DateTimeField()

    class Meta:
        db_table = config.TABLE
        app_label = "django_stack"
        managed = False


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = (
            "id",
            "name",
            "description",
            "enabled",
            "quantity",
            "project_id",
            "created_at",
            "updated_at",
        )


@api_view(["GET", "POST"])
def collection(request):
    if request.method == "POST":
        record = request.data
        now = datetime.datetime.now(datetime.timezone.utc)
        item = Item.objects.create(
            id=uuid.uuid4(),
            name=record["name"],
            description=record["description"],
            enabled=record["enabled"],
            quantity=record["quantity"],
            project_id=uuid.UUID(record["project_id"]),
            created_at=now,
            updated_at=now,
        )
        return Response(ItemSerializer(item).data, status=201)
    items = Item.objects.order_by("quantity")[: config.PAGE]
    return Response(ItemSerializer(items, many=True).data)


@api_view(["GET"])
def resource(request, item_id):
    return Response(ItemSerializer(Item.objects.get(pk=item_id)).data)


urlpatterns = [
    path("items/", collection),
    path("items/<uuid:item_id>", resource),
]


class Stack:
    name = NAME
    kind = KIND

    def setup(self):
        from django.core.wsgi import get_wsgi_application

        self._app = get_wsgi_application()

    def teardown(self):
        from django.db import connections

        connections.close_all()

    def collection(self):
        return call.wsgi(self._app, "GET", "/items/")

    def resource(self, item_id):
        return call.wsgi(self._app, "GET", f"/items/{item_id}")

    def create(self, document):
        return call.wsgi(self._app, "POST", "/items/", document)
