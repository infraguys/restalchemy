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
