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

# Types

Modul: `restalchemy.dm.types`

DM-Types beschreiben zulässige Werte für Properties und wie Werte in einfache Typen (JSON, OpenAPI, Storage) konvertiert werden.

Alle Typen erben von `BaseType`.

---

## BaseType

### `BaseType`

Zentrale Schnittstelle für alle DM-Typen:

- `validate(value) -> bool`
- `to_simple_type(value)`
- `from_simple_type(value)`
- `from_unicode(value)`
- `to_openapi_spec(prop_kwargs)`

Viele konkrete Typen basieren auf `BasePythonType`, der Python-Typen wie `int` oder `str` kapselt.

---

## Skalare Typen

- `Boolean` — boolescher Typ.
- `String` — String mit `min_length`/`max_length`.
  - Subtyp `Email` für E-Mail-Adressen.
- `Integer` — Ganzzahl mit `min_value`/`max_value`.
- `Float` — Fließkommazahl mit Grenzwerten.
- `Decimal` — `decimal.Decimal`, mit optionaler Begrenzung der Nachkommastellen.
- `UUID` — `uuid.UUID` als String.
- `Enum` — eingeschränkte Menge zulässiger Werte.

Beispiel:

```python
status_type = types.Enum(["pending", "active", "disabled"])
status = properties.property(status_type, default="pending")
```

---

## Datums- und Zeittypen

- `UTCDateTime` (deprecated) und `UTCDateTimeZ` für UTC `datetime`.
- `TimeDelta` für `datetime.timedelta` (als Sekunden).
- `DateTime` (Legacy) für Unix-Timestamps.

---

## Collection-Typen

- `List` — Liste beliebiger Werte.
- `TypedList(nested_type)` — Liste von Werten, die `nested_type` entsprechen.
- `Dict` — Dictionary mit String-Keys.
- `TypedDict(nested_type)` — Dictionary mit String-Keys und Werten vom Typ `nested_type`.
- `SoftSchemeDict(scheme)` / `SchemeDict(scheme)` — strukturierte Dicts mit Schema.

Beispiel:

```python
settings_scheme = {
    "retries": types.Integer(min_value=0),
    "timeout": types.Float(min_value=0.0),
}

settings_type = types.SoftSchemeDict(settings_scheme)
settings = properties.property(settings_type, default=dict)
```

---

## Nullable und Wrapper

### `AllowNone(nested_type)`

- Erlaubt `None` oder einen gültigen Wert für `nested_type`.
- Fügt `nullable: true` zur OpenAPI-Spezifikation hinzu.

Beispiel:

```python
maybe_uuid = types.AllowNone(types.UUID())

uuid_or_none = properties.property(maybe_uuid)
```

---

## Regexp- und URL-Typen

Basistypen: `BaseRegExpType`, `BaseCompiledRegExpTypeFromAttr`.

Konkrete Typen:

- `Uri` — Pfad mit UUID.
- `Mac` — MAC-Adresse.
- `Hostname` (deprecated) — siehe `types_network`.
- `Url` — HTTP/FTP-URL.

---

## Dynamische und Netzwerk-Typen

In `restalchemy.dm.types_dynamic` und `restalchemy.dm.types_network` finden sich weitere spezialisierte Typen, z.B. für:

- Hostnames, IP-Netzwerke, CIDR-Bereiche.
- Dynamische Strukturen mit Laufzeit-Schema.

Musterschema:

1. Typ instanziieren.
2. In `properties.property()` verwenden.
3. DM übernimmt Validierung und Konvertierung.

---

## Best Practices

- Verwenden Sie DM-Types anstelle roher Python-Typen.
- Nutzen Sie `AllowNone`, wenn `None` explizit erlaubt ist.
- Verwenden Sie `Enum` bei kleinen, abgeschlossenen Wertemengen.
- Für komplexe JSON-Strukturen sind `SoftSchemeDict`, `SchemeDict` und `TypedDict` empfehlenswert.
