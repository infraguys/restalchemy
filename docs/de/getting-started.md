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

# Getting started

In diesem Leitfaden erstellen Sie einen kleinen REST-Service, der:

- Ein in-memory-Storage (ohne Datenbank) nutzt.
- Ein einfaches DM-Modell verwendet.
- Eine minimale API-Schicht (Controller + Route) besitzt.
- Als WSGI-Anwendung läuft.

Am Ende läuft ein HTTP-API unter `http://127.0.0.1:8000/`.

---

## 1. Projektstruktur

Legen Sie ein Verzeichnis und eine Datei an:

```text
myservice/
  app.py
```

Der gesamte folgende Code kommt in `app.py`.

---

## 2. Einfaches DM-Modell

```python
from wsgiref.simple_server import make_server

from restalchemy.api import applications
from restalchemy.api import controllers
from restalchemy.api import middlewares
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types


# Simple data model for a "Foo" resource
class FooModel(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)
```

`FooModel` ist ein DM-Modell mit:

- Automatisch generierter UUID (von `ModelWithUUID` geerbt).
- Einem ganzzahligen Feld `value`.

---

## 3. In-memory-Storage

Für erste Schritte reicht ein Dictionary:

```python
FOO_STORAGE = {}
```

---

## 4. Controller

Der Controller implementiert die Logik für `CREATE`, `GET` und `FILTER`:

```python
class FooController(controllers.Controller):
    __resource__ = resources.ResourceByRAModel(FooModel, process_filters=True)

    def create(self, value):
        foo = self.model(value=value)
        FOO_STORAGE[str(foo.get_id())] = foo
        return foo

    def get(self, uuid):
        return FOO_STORAGE[uuid]

    def filter(self, filters, order_by=None):
        return FOO_STORAGE.values()
```

---

## 5. Routen

Routen ordnen URLs und Methoden den Controllern zu:

```python
class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.CREATE, routes.GET, routes.FILTER]


class ApiRoot(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]

    foos = routes.route(FooRoute)
```

Damit:

- `GET /` — Root-Route.
- `POST /foos/` — erstellt ein neues `FooModel`.
- `GET /foos/<uuid>` — holt ein einzelnes Objekt.
- `GET /foos/` — listet alle Objekte auf.

---

## 6. WSGI-Anwendung

```python
def get_user_api_application():
    return ApiRoot


def build_wsgi_application():
    return middlewares.attach_middlewares(
        applications.WSGIApp(get_user_api_application()),
        [],
    )
```

---

## 7. Server starten

```python
HOST = "127.0.0.1"
PORT = 8000


def main():
    server = make_server(HOST, PORT, build_wsgi_application())

    try:
        print(f"Serve forever on {HOST}:{PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    main()
```

Start:

```bash
python app.py
```

---

## 8. API testen

Neues `Foo` anlegen:

```bash
curl -X POST "http://127.0.0.1:8000/foos/" \
  -H "Content-Type: application/json" \
  -d '{"value": 42}'
```

Alle Objekte auflisten:

```bash
curl "http://127.0.0.1:8000/foos/"
```

Ein einzelnes Objekt holen (`<uuid>` ersetzen):

```bash
curl "http://127.0.0.1:8000/foos/<uuid>"
```

---

## 9. Nächste Schritte

Nach diesem minimalen in-memory-Service können Sie:

- Auf SQL-Storage umsteigen (siehe `concepts/data-model.md`, `concepts/storage-layer.md` und das DM+SQL-How-to).
- Das vollständige Beispiel `examples/restapi_foo_bar_service.py` ansehen.
- Filter, Beziehungen und weitere Szenarien in den How-to-Guides erkunden.
