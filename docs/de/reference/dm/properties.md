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

# Properties

Modul: `restalchemy.dm.properties`

Properties sind der zentrale Mechanismus, mit dem DM-Modelle Felder definieren und Werte speichern.

---

## Basisklassen

### `AbstractProperty`

Abstrakte Basisklasse für alle Properties:

- `value` (Property): aktueller Wert.
- `set_value_force(value)`: Wert setzen unter Umgehung von read-only/ID-Regeln.
- `is_dirty()`: zeigt an, ob sich der Wert seit der Initialisierung geändert hat.
- `is_prefetch()` (classmethod): ob das Property für Prefetching markiert ist.

### `Property`

Standard-Implementierung für skalare und strukturierte Felder.

Konstruktor:

```python
Property(
    property_type,
    default=None,
    required=False,
    read_only=False,
    value=None,
    mutable=False,
    example=None,
)
```

Wesentliche Punkte:

- `property_type` muss eine Instanz von `types.BaseType` sein.
- `default` kann ein Wert oder ein Callable sein.
- Falls `value` gesetzt ist, überschreibt es `default`.
- Bei `mutable=False` wird der Startwert für `is_dirty()` tief kopiert.
- Ungültige Werte führen zu Exceptions aus `restalchemy.common.exceptions`.

### `IDProperty`

Spezialfall von `Property` für ID-Felder:

- `is_id_property()` gibt `True` zurück.
- Wird mit `ModelWithID`/`ModelWithUUID` kombiniert.

---

## PropertyCreator und Fabriken

### `PropertyCreator`

Speichert, wie ein konkretes Property erstellt wird:

- Property-Klasse (`Property` oder `IDProperty`).
- DM-Typinstanz (`types.String()`, `types.Integer()`, ...).
- Argumente und Keyword-Argumente.
- `prefetch`-Flag.

Auf Klassenebene weisen Sie `PropertyCreator`-Instanzen den Attributen zu.

### `property()`

Hauptfabrik für Properties in Modellen:

```python
from restalchemy.dm import properties, types


class Foo(models.Model):
    value = properties.property(types.Integer(), required=True)
```

Argumente:

- `property_type`: Instanz von `types.BaseType`.
- `id_property`: wenn `True`, wird `IDProperty` verwendet.
- `property_class`: eigene Property-Klasse (muss von `AbstractProperty` erben).
- Weitere Keyword-Argumente werden an den Property-Konstruktor weitergegeben.

Hilfsfunktionen:

- `required_property(property_type, *args, **kwargs)` — setzt `required=True`.
- `readonly_property(property_type, *args, **kwargs)` — setzt `read_only=True` und `required=True`.

---

## PropertyCollection und PropertyManager

### `PropertyCollection`

- Hält Mapping Name → `PropertyCreator` (oder verschachtelte `PropertyCollection`).
- Implementiert Mapping-Protokoll.
- `sort_properties()` sortiert Keys alphabetisch.
- `instantiate_property(name, value=None)` erzeugt eine konkrete Property-Instanz.

### `PropertyManager`

Laufzeit-Container für Properties auf Instanzebene:

- Baut konkrete Property-Objekte aus einer `PropertyCollection` und Keyword-Argumenten.
- `properties`: read-only Mapping Name → Property.
- `value`: Dict mit "rohen" Werten (lesen/schreiben).

`Model.pour()` verwendet `PropertyManager`, um den Zustand des Modells zu initialisieren.

---

## Container und verschachtelte Strukturen

### `container()`

Erzeugt eine verschachtelte `PropertyCollection` für gruppierte Felder:

```python
address_container = properties.container(
    city=properties.property(types.String()),
    zip_code=properties.property(types.String()),
)


class User(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)
    address = address_container
```

Zur Laufzeit ist `address` ein `PropertyManager`, z.B.:

```python
user.address.value["city"]
user.address.value["zip_code"]
```

---

## Dirty Tracking

`Property` und `Relationship` unterstützen `is_dirty()`:

- `Property` vergleicht aktuellen und initialen Wert.
- `Relationship` vergleicht aktuelle und ursprüngliche Relation.

`Model.is_dirty()` iteriert über alle Properties und gibt `True` zurück, sobald eines "dirty" ist.

---

## Best Practices

- Verwenden Sie DM-Typen (`types.String`, `types.Integer` etc.) statt roher Python-Typen.
- Markieren Sie ID-Felder mit `id_property=True` oder nutzen Sie `ModelWithUUID`.
- Nutzen Sie `required_property()` / `readonly_property()` für bessere Lesbarkeit.
- Verwenden Sie `container()` für logisch gruppierte Felder oder verschachtelte JSON-Strukturen.
