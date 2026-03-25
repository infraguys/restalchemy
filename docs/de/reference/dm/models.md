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

# DM-Modelle

Modul: `restalchemy.dm.models`

Dieses Modul definiert Basisklassen und Mixins für Datenmodelle (DM) in RESTAlchemy.

---

## MetaModel und Model

### `MetaModel`

`MetaModel` ist die Metaklasse aller DM-Modelle. Sie:

- Sammelt Felddefinitionen, die mit `properties.property()` und `properties.container()` erstellt wurden.
- Führt Properties aus Basisklassen zusammen.
- Verfolgt ID-Properties in `id_properties`.
- Hängt pro Modellklasse ein operatives Storage `__operational_storage__` an.

Normalerweise benutzen Sie `MetaModel` nicht direkt, sondern erben von `Model` oder dessen Subklassen.

### `Model`

`Model` ist die grundlegende Basisklasse für DM-Modelle:

```python
from restalchemy.dm import models, properties, types


class Foo(models.Model):
    foo_id = properties.property(types.Integer(), id_property=True, required=True)
    name = properties.property(types.String(max_length=255), default="")
```

Wichtiges Verhalten:

- Der Konstruktor nimmt Keyword-Argumente entgegen und gibt sie an `pour()` weiter.
- `pour()` baut einen `PropertyManager` aus der `properties`-Collection und validiert die Felder.
- Attributzugriffe werden auf Properties gemappt:
  - `model.field` liest `properties[field].value`.
  - `model.field = value` setzt den Wert mit Validierung.
- `as_plain_dict()` gibt eine einfache Dictionary-Repräsentation zurück.
- Das Modell verhält sich wie ein Mapping über seine Properties (`__getitem__`, `__iter__`, `__len__`).

Fehlerbehandlung:

- Falscher Typ → `ModelTypeError`.
- Fehlendes Pflichtfeld → `PropertyRequired`.
- Änderung eines read-only oder ID-Feldes → `ReadOnlyProperty`.

Eigene Validierung:

```python
class PositiveFoo(models.Model):
    value = properties.property(types.Integer(), required=True)

    def validate(self):
        if self.value <= 0:
            raise ValueError("value must be positive")
```

`validate()` wird aus `pour()` heraus aufgerufen.

---

## ID-Verarbeitung

### `ModelWithID`

`ModelWithID` erweitert `Model` für Modelle mit genau einem ID-Property:

- `get_id()` gibt den aktuellen Wert des ID-Feldes zurück.
- Gleichheit und Hashing basieren auf `get_id()`.

Wenn es kein oder mehrere ID-Felder gibt, wirft `get_id_property()` einen `TypeError`, und Sie sollten die ID-Logik selbst implementieren.

### `ModelWithUUID` und `ModelWithRequiredUUID`

`ModelWithUUID` definiert eine UUID als Primärschlüssel:

```python
class ModelWithUUID(ModelWithID):
    uuid = properties.property(
        types.UUID(),
        read_only=True,
        id_property=True,
        default=lambda: uuid.uuid4(),
    )
```

Beispiel:

```python
class Foo(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)

foo = Foo(value=10)
print(foo.uuid)       # automatisch generierte UUID
print(foo.get_id())   # identisch zu foo.uuid
```

`ModelWithRequiredUUID` ist ähnlich, verlangt aber eine explizit gesetzte UUID ohne Default.

---

## Operational Storage

### `DmOperationalStorage`

Ein kleines Hilfsobjekt, das von `MetaModel` als `__operational_storage__` verwendet wird:

- `store(name, data)` — speichert beliebige Daten unter einem Namen.
- `get(name)` — liest Daten oder wirft `NotFoundOperationalStorageError`.

Beispiel:

```python
from restalchemy.dm import models


class Foo(models.ModelWithUUID):
    pass

Foo.__operational_storage__.store("table_name", "foos")

assert Foo.__operational_storage__.get("table_name") == "foos"
```

---

## Häufige Mixins

### `ModelWithTimestamp`

Fügt `created_at` und `updated_at` Felder mit UTC-Zeit hinzu:

- Beide Felder sind Pflichtfelder, read-only und verwenden `types.UTCDateTimeZ()`.
- `update()` aktualisiert `updated_at` automatisch, wenn das Modell "dirty" ist (oder `force=True`).

```python
class TimestampedFoo(models.ModelWithUUID, models.ModelWithTimestamp):
    value = properties.property(types.Integer(), required=True)
```

### `ModelWithProject`

Fügt ein Pflichtfeld `project_id` vom Typ `types.UUID()` hinzu:

```python
class ProjectResource(models.ModelWithUUID, models.ModelWithProject):
    name = properties.property(types.String(max_length=255), required=True)
```

### `ModelWithNameDesc` und `ModelWithRequiredNameDesc`

Gemeinsame Felder `name` und `description`:

- `ModelWithNameDesc`:
  - `name`: String bis 255 Zeichen, Default `""`.
  - `description`: String bis 255 Zeichen, Default `""`.
- `ModelWithRequiredNameDesc`:
  - `name` ist Pflichtfeld.

---

## Custom Properties und Simple Views

### `CustomPropertiesMixin`

Erlaubt zusätzliche "Custom Properties" mit eigenen Typen:

- `__custom_properties__`: Mapping Name → Typ (`types.BaseType`).
- `get_custom_properties()` liefert `(name, type)` Paare.
- `get_custom_property_type(name)` gibt den Typ eines Custom-Feldes zurück.
- `_check_custom_property_value()` validiert Werte und kann statische Werte erzwingen.

### `DumpToSimpleViewMixin`

`dump_to_simple_view()` konvertiert ein Modell in eine Struktur aus einfachen Typen (für JSON, OpenAPI, Storage):

```python
result = model.dump_to_simple_view(
    skip=["internal_field"],
    save_uuid=True,
    custom_properties=False,
)
```

- Iteriert über `self.properties` und nutzt `to_simple_type()` des jeweiligen Typs.
- Bei `save_uuid=True` werden UUID-Felder als Strings ausgegeben.
- Optional werden Custom-Properties konvertiert.

### `RestoreFromSimpleViewMixin`

`restore_from_simple_view()` baut ein Modell aus einer "Simple View":

- Normalisiert Feldnamen (`-` → `_`).
- Kann unbekannte Felder ignorieren.
- Nutzt `from_simple_type()` / `from_unicode()` der Typen.

### `SimpleViewMixin`

Kombiniert beide Mixins:

```python
class User(models.ModelWithUUID, models.SimpleViewMixin):
    name = properties.property(types.String(max_length=255), required=True)
```

Round-trip Beispiel:

```python
plain = user.dump_to_simple_view()
user2 = User.restore_from_simple_view(**plain)
```

---

## Zusammenfassung

- Verwenden Sie `Model` oder seine Helferklassen als Basis für alle DM-Modelle.
- Nutzen Sie Mixins wie `ModelWithUUID`, `ModelWithTimestamp`, `ModelWithProject`, `ModelWithNameDesc`, um wiederkehrende Muster abzubilden.
- Verwenden Sie Simple-View-Mixins für die Konvertierung von Modellen in einfache Strukturen und zurück.
