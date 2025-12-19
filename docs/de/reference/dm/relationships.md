# Relationships

Modul: `restalchemy.dm.relationships`

Relationships verbinden DM-Modelle miteinander.

---

## Relationship-Fabriken

### `relationship(property_type, *args, **kwargs)`

Hauptfabrik für Beziehungen innerhalb von DM-Modellen.

Argumente:

- `property_type`: Zielmodellklasse (Subklasse von `models.Model`).
- `*args`: typischerweise Modellklassen zur Validierung.
- `**kwargs`:
  - `prefetch`: bei `True` wird `PrefetchRelationship` verwendet.
  - `required`, `read_only`, `default`, usw.

### `required_relationship(property_type, *args, **kwargs)`

Wie `relationship()`, setzt aber zusätzlich `required=True`.

### `readonly_relationship(property_type, *args, **kwargs)`

Wie `required_relationship()`, setzt zusätzlich `read_only=True`.

---

## Relationship-Klassen

### `Relationship`

Property, das eine einzelne verbundene Modellinstanz repräsentiert.

Verhalten:

- Akzeptiert `None` oder eine Instanz von `property_type`.
- Respektiert `required` und `read_only`.
- `is_dirty()` vergleicht aktuellen und ursprünglichen Wert.
- `get_property_type()` gibt die Modellklasse zurück.

Falscher Typ führt zu `TypeError`.

### `PrefetchRelationship`

Unterklasse von `Relationship`:

- `is_prefetch()` gibt `True` zurück.
- Sonst identisch zu `Relationship`.

---

## Beispiel: One-to-Many über DM + API

Vereinfachtes Foo/Bar-Beispiel:

```python
from restalchemy.dm import models, properties, relationships, types


class FooModel(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)


class BarModel(models.ModelWithUUID):
    name = properties.property(types.String(max_length=10), required=True)
    foo = relationships.relationship(FooModel)
```

Verwendung:

```python
foo = FooModel(value=10)
bar = BarModel(name="test", foo=foo)

assert bar.foo is foo
```

In Kombination mit Storage (siehe DM+SQL-Beispiele) können Relationships für Foreign Keys und Joins verwendet werden.

---

## Beispiel: required + read-only Relationship

```python
class ReadOnlyBar(models.ModelWithUUID):
    foo = relationships.readonly_relationship(FooModel)
```

- `foo` ist Pflichtfeld.
- Das Feld ist nach der Initialisierung read-only (außer bei Verwendung von `set_value_force()`).

---

## Best Practices

- Verwenden Sie Relationships für DM-Level-Beziehungen; Foreign Keys und Joins sind Aufgabe der Storage-Schicht.
- Halten Sie Beziehungen einfach: ein Feld pro logischer Beziehung.
- Nutzen Sie `prefetch=True` nur dort, wo Prefetching wirklich notwendig ist.
