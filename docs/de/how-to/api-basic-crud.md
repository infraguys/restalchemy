<!--
Copyright 2025 Genesis Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# API basic CRUD

Dieses How-to zeigt, wie Sie mit der REST-Alchemy-API-Schicht ein einfaches REST-API aufbauen.

Wir werden:

- DM-Modelle definieren.
- Controller definieren.
- Routen definieren.
- Eine WSGI-Anwendung bauen.
- Das API mit `curl` testen.

Das Beispiel basiert auf `examples/restapi_foo_bar_service.py`.

---

## 1. DM-Modelle

```python
from restalchemy.dm import models, properties, relationships, types


class FooModel(models.ModelWithUUID):
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID):
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

- `FooModel` und `BarModel` sind reine DM-Modelle (hier ohne Storage, in-memory).
- `BarModel.foo` beschreibt eine Beziehung zu `FooModel`.

---

## 2. In-memory-Storage

Zur Vereinfachung nutzen wir Python-Dictionaries:

```python
foo_storage = {}
bar_storage = {}
```

In einer realen Anwendung würden Sie stattdessen SQL-Storage (`SQLStorableMixin`) verwenden, die API-Schicht bleibt dabei gleich.

---

## 3. Controller

Controller verbinden HTTP-Methoden mit Python-Code.

```python
from restalchemy.api import controllers, resources


class FooController(controllers.Controller):
    """Handler für /foos/-Endpunkte."""

    __resource__ = resources.ResourceByRAModel(FooModel, process_filters=True)

    def create(self, foo_field1, foo_field2):
        foo = self.model(foo_field1=foo_field1, foo_field2=foo_field2)
        foo_storage[str(foo.get_id())] = foo
        return foo

    def get(self, uuid):
        return foo_storage[uuid]

    def filter(self, filters, order_by=None):
        # Einfache Implementierung: Filter und Sortierung ignorieren
        return foo_storage.values()


bar_resource = resources.ResourceByRAModel(BarModel, process_filters=True)


class BarController1(controllers.Controller):
    """Handler für /foo/<uuid>/bars/ Endpunkte."""

    __resource__ = bar_resource

    def create(self, bar_field1, parent_resource):
        bar = BarModel(bar_field1=bar_field1, foo=parent_resource)
        bar_storage[str(bar.get_id())] = bar
        return bar


class BarController2(controllers.Controller):
    """Handler für /bars/<uuid> Endpunkte."""

    __resource__ = bar_resource

    def get(self, uuid):
        return bar_storage[uuid]

    def delete(self, uuid):
        del bar_storage[uuid]
```

Wichtige Punkte:

- `__resource__` gibt an, mit welchem DM-Modell/Resource der Controller arbeitet.
- `create/get/filter/delete` sind RA-Methoden, die über Routen auf HTTP gemappt werden.
- `process_filters=True` am Resource-Objekt aktiviert die automatische Auswertung von Query-Parametern.

---

## 4. Routen

Routen ordnen URLs und HTTP-Methoden den Controllern zu.

```python
from restalchemy.api import routes


class BarRoute1(routes.Route):
    __controller__ = BarController1
    __allow_methods__ = [routes.CREATE]


class BarRoute2(routes.Route):
    __controller__ = BarController2
    __allow_methods__ = [routes.GET, routes.DELETE]


class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.FILTER, routes.CREATE, routes.GET]

    # Nested Route für /foo/<uuid>/bars/
    bars = routes.route(BarRoute1, resource_route=True)


class V1Route(routes.Route):
    """Router für den Pfad /v1/."""

    __controller__ = controllers.RoutesListController
    __allow_methods__ = [routes.FILTER]

    # /v1/foos/
    foos = routes.route(FooRoute)
    # /v1/bars/<uuid>
    bars = routes.route(BarRoute2)


class UserApiApp(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]


# Route zu /v1/
setattr(UserApiApp, "v1", routes.route(V1Route))
```

- `FooRoute` behandelt `/v1/foos/` und `/v1/foos/<uuid>`.
- `BarRoute1` behandelt `/v1/foos/<uuid>/bars/`.
- `BarRoute2` behandelt `/v1/bars/<uuid>`.
- `V1Route` und `UserApiApp` gruppieren diese Routen unter `/v1/` bzw. `/`.

---

## 5. WSGI-Anwendung

```python
from wsgiref.simple_server import make_server
from restalchemy.api import applications, middlewares


HOST = "0.0.0.0"
PORT = 8000


def get_user_api_application():
    return UserApiApp


def build_wsgi_application():
    return middlewares.attach_middlewares(
        applications.WSGIApp(get_user_api_application()),
        [],  # hier könnten Middlewares eingehängt werden
    )


def main():
    server = make_server(HOST, PORT, build_wsgi_application())
    try:
        print("Serve forever on %s:%s" % (HOST, PORT))
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    main()
```

---

## 6. API mit curl testen

Angenommen, der Server läuft auf `http://127.0.0.1:8000`.

Top-Level-Routen anzeigen:

```bash
curl http://127.0.0.1:8000/
```

Foo anlegen:

```bash
curl -X POST "http://127.0.0.1:8000/v1/foos/" \
  -H "Content-Type: application/json" \
  -d '{"foo_field1": 10, "foo_field2": "bar"}'
```

Alle Foos auflisten:

```bash
curl "http://127.0.0.1:8000/v1/foos/"
```

Foo per UUID holen:

```bash
curl "http://127.0.0.1:8000/v1/foos/<uuid>"
```

Bar für einen Foo anlegen:

```bash
curl -X POST "http://127.0.0.1:8000/v1/foos/<uuid>/bars/" \
  -H "Content-Type: application/json" \
  -d '{"bar_field1": "test"}'
```

Bar per UUID holen:

```bash
curl "http://127.0.0.1:8000/v1/bars/<uuid>"
```

Bar per UUID löschen:

```bash
curl -X DELETE "http://127.0.0.1:8000/v1/bars/<uuid>"
```

---

## Zusammenfassung

- DM-Modelle beschreiben Ihre Daten.
- Controller kapseln die Geschäftslogik für RA-Methoden (FILTER/CREATE/GET/UPDATE/DELETE).
- Routen mappen HTTP-Pfade und -Methoden auf Controller und Ressourcen.
- `WSGIApp` verbindet alles zu einer WSGI-Anwendung.

Dieses Muster skaliert von einfachen In-Memory-Beispielen bis hin zu produktiven Setups mit SQL-Storage und OpenAPI.
