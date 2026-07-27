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

- `validate(value) -> bool`: prüft, ob der Wert zulässig ist.
- `to_simple_type(value)`: konvertiert einen Wert in einen einfachen Python-Typ (String, Zahl, Dict, Liste …).
- `from_simple_type(value)`: konvertiert aus einem einfachen Typ zurück.
- `from_unicode(value)`: parst eine String-Darstellung.
- `to_openapi_spec(prop_kwargs)`: erzeugt das OpenAPI-Schema-Fragment.

Viele konkrete Typen basieren auf `BasePythonType`, der Python-Typen wie `int` oder `str` kapselt.

---

## Skalare Typen

### `Boolean`

- Kapselt `bool`.
- Akzeptiert in `from_simple_type()` beliebige truthy/falsy Werte und in `from_unicode()` String-Darstellungen.

### `String`

- Kapselt `str` mit Längenbeschränkungen.
- Parameter: `min_length`, `max_length`.
- `to_openapi_spec()` ergänzt `minLength`/`maxLength`.

Gängige Subklassen:

- `Email` — validiert E-Mail-Adressen (optional mit Zustellbarkeitsprüfung).

### `Integer`

- Kapselt `int` mit `min_value` und `max_value`.
- `Int8`, `Int16` usw. sind spezialisierte Varianten.

### `Float`

- Kapselt `float` mit Grenzwerten.

### `Decimal`

- Kapselt `decimal.Decimal` mit optionalem `max_decimal_places`.
- Wird als String serialisiert und deserialisiert, um Genauigkeitsverluste zu vermeiden.

### `UUID`

- Kapselt `uuid.UUID`.
- Wird als String serialisiert.

### `Enum`

- Schränkt Werte auf eine vorgegebene Menge ein.

Beispiel:

```python
from restalchemy.dm import types

status_type = types.Enum(["pending", "active", "disabled"])
```

Verwendung in Properties:

```python
status = properties.property(status_type, default="pending")
```

---

## Datums- und Zeittypen

### `UTCDateTime` (deprecated) und `UTCDateTimeZ`

- Beide kapseln `datetime.datetime`.
- `UTCDateTimeZ` erzwingt `tzinfo == datetime.timezone.utc` und ist empfohlen.
- Serialisierung als String im MySQL- bzw. RFC3339-ähnlichen Format.

### `TimeDelta`

- Kapselt `datetime.timedelta`.
- Serialisierung als Sekunden (Float).

### `DateTime`

- Legacy-Zeitstempeltyp, serialisiert als Unix-Timestamp.

---

## Collection-Typen

### `List` und `TypedList`

- `List` prüft, dass der Wert eine Python-Liste ist.
- `TypedList(nested_type)` stellt sicher, dass jedes Element für `nested_type` gültig ist.

Beispiel:

```python
from restalchemy.dm import types


tags_type = types.TypedList(types.String(max_length=32))
```

### `Dict` und strukturierte Dicts

- `Dict` prüft, dass der Wert ein `dict` mit String-Keys ist.
- `TypedDict(nested_type)` erzwingt, dass alle Werte `nested_type` entsprechen.

Schema-basierte Dicts:

- `SoftSchemeDict(scheme)` — Dict, dessen Keys eine Teilmenge des Schemas sind.
- `SchemeDict(scheme)` — Dict, das dem Schema exakt entsprechen muss.

Beispiel:

```python
from restalchemy.dm import types


settings_scheme = {
    "retries": types.Integer(min_value=0),
    "timeout": types.Float(min_value=0.0),
}

settings_type = types.SoftSchemeDict(settings_scheme)
```

Verwendung in einer Property:

```python
settings = properties.property(settings_type, default=dict)
```

---

## Nullable und Wrapper

### `AllowNone(nested_type)`

- Erlaubt `None` oder einen gültigen Wert für `nested_type`.
- `to_simple_type()` und `from_simple_type()` reichen an `nested_type` durch, sofern der Wert nicht `None` ist.
- `to_openapi_spec()` fügt `nullable: true` hinzu.

Beispiel:

```python
maybe_uuid = types.AllowNone(types.UUID())

uuid_or_none = properties.property(maybe_uuid)
```

---

## Regexp- und URL-Typen

### `BaseRegExpType` und `BaseCompiledRegExpTypeFromAttr`

Low-Level-Basisklassen für regexp-basierte Typen.

Konkrete Typen:

- `Uri` — validiert URI-Pfade, die auf eine UUID enden.
- `Mac` — validiert MAC-Adressen.
- `Hostname` (deprecated) — siehe `types_network`.
- `Url` — Validator für HTTP/FTP-URLs.

Diese Typen sind für Netzwerk- und Ressourcenbezeichner nützlich.

---

## Dynamische und Netzwerk-Typen

Weitere spezialisierte Typen liegen in:

- `restalchemy.dm.types_dynamic`
- `restalchemy.dm.types_network`

Beispiele dafür sind:

- Fortgeschrittene Hostnames, IP-Netzwerke, CIDR-Bereiche.
- Dynamische Strukturen mit zur Laufzeit definierten Schemata.

Diese Referenz listet sie nicht vollständig auf, das Verwendungsmuster ist aber immer dasselbe:

1. Typ instanziieren.
2. In `properties.property()` verwenden.
3. DM übernimmt Validierung und Konvertierung.

---

## Best Practices

- Bevorzugen Sie DM-Types (`types.String`, `types.Integer` usw.) gegenüber rohen Python-Typen; sie kodieren Validierung und OpenAPI-Metadaten.
- Nutzen Sie `AllowNone`, statt `None` von Hand in der Geschäftslogik zuzulassen.
- Verwenden Sie `Enum` bei kleinen, abgeschlossenen Wertemengen.
- Für komplexe JSON-artige Strukturen verwenden Sie `SoftSchemeDict`, `SchemeDict` oder `TypedDict` statt eines nackten `Dict`.
