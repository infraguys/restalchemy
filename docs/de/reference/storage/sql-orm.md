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

- `ObjectCollection` — Collection-API (`Model.objects`).
- `SQLStorableMixin` — Mixin für SQL-Persistenz.
- `SQLStorableWithJSONFieldsMixin` — Erweiterung für JSON-Felder.

---

## ObjectCollection

- `get_all(...)` — Liste von Modellen.
- `get_one(...)` — genau ein Modell oder Exception.
- `get_one_or_none(...)` — ein Modell oder `None`.
- `query(...)` — benutzerdefinierter WHERE-Ausdruck.
- `count(...)` — Anzahl der Zeilen.

---

## SQLStorableMixin

- Erwartet `__tablename__` und ID-Property.
- `get_table()` — `SQLTable` für das Modell.
- `insert()`, `save()`, `update()`, `delete()` — CRUD auf Tabellenebene.
- `restore_from_storage()` — Row → DM-Modell.

`Model.objects` verwendet intern `ObjectCollection`.

---

## SQLStorableWithJSONFieldsMixin

- `__jsonfields__` definiert JSON-Felder.
- Überschreibt `restore_from_storage()` und `_get_prepared_data()`, um JSON korrekt zu (de)serialisieren.
