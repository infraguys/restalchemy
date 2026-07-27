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

# SQL ORM Mixins und Collections

Modul: `restalchemy.storage.sql.orm`

Bietet ORM-ähnliche Funktionalität für DM-Modelle:

- `ObjectCollection` — Collection-API, verfügbar als `Model.objects`.
- `SQLStorableMixin` — Mixin, das `save()`, `update()`, `delete()` und die Anbindung an SQL-Tabellen ergänzt.
- `SQLStorableWithJSONFieldsMixin` — Spezialisierung für Modelle mit JSON-Feldern.

---

## ObjectCollection

`ObjectCollection` implementiert die Collection-Schnittstelle für SQL-gestützte Modelle.

Wichtigste Methoden:

- `get_all(filters=None, session=None, cache=False, limit=None, order_by=None, locked=False)`
  - Liefert eine Liste von Modellinstanzen.
  - Nutzt `filters` (DM-Filterstrukturen), um WHERE-Bedingungen zu bauen.
  - Kann mit `cache=True` den Query-Cache der Session verwenden.
- `get_one(filters=None, session=None, cache=False, locked=False)`
  - Liefert genau eine Modellinstanz.
  - Wirft `RecordNotFound` ohne Treffer und `HasManyRecords` bei mehr als einem Treffer.
- `get_one_or_none(filters=None, session=None, cache=False, locked=False)`
  - Liefert eine einzelne Instanz oder `None`, wenn nichts gefunden wurde.
- `query(where_conditions, where_values, session=None, cache=False, limit=None, order_by=None, locked=False)`
  - Führt eine benutzerdefinierte WHERE-Bedingung aus.
- `count(session=None, filters=None)`
  - Liefert die Anzahl der Zeilen, die den Filtern entsprechen.

`ObjectCollection` verwendet:

- Den SQL-Dialekt über `engine.dialect`.
- Die Methode `restore_from_storage()` des Modells, um Zeilen in DM-Modelle zu überführen.

---

## SQLStorableMixin

`SQLStorableMixin` ist dafür gedacht, mit DM-Modellen kombiniert zu werden, um sie in SQL speicherbar zu machen.

### Voraussetzungen

- Das DM-Modell muss einen gültigen `__tablename__`-String besitzen.
- Es muss mindestens eine ID-Property geben (`id_property=True`).

### Kernaufgaben

- `get_table()`
  - Liefert eine `SQLTable`-Instanz für das Modell, zwischengespeichert in `__operational_storage__`.
- `insert(session=None)`
  - Fügt das Modell mit den aktuellen Property-Werten in die Tabelle ein.
  - Übersetzt dialektspezifische Exceptions in Storage-Exceptions (z. B. Konflikte).
- `save(session=None)`
  - Ruft `insert()` auf, wenn die Instanz noch nicht gespeichert ist.
  - Andernfalls ruft es `update()` auf.
- `update(session=None, force=False)`
  - Aktualisiert die Zeile, wenn das Modell verändert wurde oder `force=True` gesetzt ist.
  - Validiert das Modell vor dem Update.
  - Stellt sicher, dass genau eine Zeile aktualisiert wird (sonst wird eine Exception geworfen).
- `delete(session=None)`
  - Löscht die Zeile, die den ID-Properties des Modells entspricht.
- `restore_from_storage(**kwargs)` (Klassenmethode)
  - Konvertiert Zeilenwerte der Datenbank (einfache Typen) in DM-Property-Werte.
  - Erzeugt eine Modellinstanz, die als gespeichert markiert ist.

### Anbindung der Object Collection

`SQLStorableMixin` definiert `_ObjectCollection = ObjectCollection`. In Kombination mit den Basis-Storage-Klassen ergibt das:

- `Model.objects` — eine Collection, die Abfragen über `ObjectCollection` ausführt.

### Hilfsfunktionen zur Typkonvertierung

- `to_simple_type(value)` (Klassenmethode)
  - Konvertiert Modellinstanzen oder rohe ID-Werte in eine für Filter geeignete Form.
- `from_simple_type(value)` (Klassenmethode)
  - Konvertiert rohe ID-Werte oder Prefetch-Ergebnisse in Modellinstanzen.

Diese Helfer erlauben es Storage- und API-Schicht, transparent mit IDs und Prefetch-Strukturen zu arbeiten.

---

## SQLStorableWithJSONFieldsMixin

`SQLStorableWithJSONFieldsMixin` erweitert `SQLStorableMixin` für Datenbanken, die JSON-Felder nicht nativ unterstützen.

Verwendungsmuster:

- Erben Sie von `SQLStorableWithJSONFieldsMixin` statt von `SQLStorableMixin`.
- Definieren Sie `__jsonfields__` als Iterable der Feldnamen, die JSON-Daten enthalten.

Verhalten:

- `restore_from_storage()`
  - Für Felder aus `__jsonfields__`:
    - Ist der gespeicherte Wert ein String, wird er als JSON geparst.
- `_get_prepared_data(properties=None)`
  - Für Felder aus `__jsonfields__` werden Python-Datenstrukturen als kompakte JSON-Strings serialisiert.

So können Sie JSON-Felder in Ihren DM-Modellen behalten und sie in Datenbanken ohne native JSON-Unterstützung als Text persistieren.
