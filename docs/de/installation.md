# Installation

In diesem Abschnitt wird erklärt, wie man RESTAlchemy und typische Abhängigkeiten installiert.

---

## Voraussetzungen

- Unterstützte CPython-Version (siehe RESTAlchemy auf PyPI für Details).
- Ein virtuelles Environment wird dringend empfohlen.
- Für SQL-Storage-Beispiele:
  - Eine laufende Datenbank (z. B. MySQL oder PostgreSQL).
  - Passende Python-Treiber (z. B. `mysql-connector-python`, `psycopg`).

---

## Installation von RESTAlchemy

Optional, aber empfohlen: ein virtuelles Environment erstellen und aktivieren:

```bash
python -m venv .venv
source .venv/bin/activate
```

Bibliothek von PyPI installieren:

```bash
pip install restalchemy
```

Um alle Beispiele aus diesem Repository zu nutzen, installieren Sie zusätzliche Abhängigkeiten aus `requirements.txt` (im Repository-Root):

```bash
pip install -r requirements.txt
```

---

## Installation überprüfen

Python starten und Folgendes ausführen:

```python
import restalchemy
from restalchemy import version

print(version.__version__)
```

Wenn eine Versionsnummer ohne Fehler ausgegeben wird, ist die Basisinstallation erfolgreich.

---

## Optional: Datenbank-Treiber

Wenn Sie SQL-Storage nutzen möchten:

- **MySQL**:
  - Installieren Sie einen MySQL-Treiber, z. B.:
    ```bash
    pip install mysql-connector-python
    ```
- **PostgreSQL**:
  - Installieren Sie einen PostgreSQL-Treiber, z. B.:
    ```bash
    pip install psycopg[binary]
    ```

Achten Sie darauf, dass Ihre Verbindungs-URLs zu den installierten Treibern und der verwendeten Datenbank passen.
