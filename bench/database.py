"""The database the benchmark runs against, and the rows in it.

Brings up a cluster of its own under the project unless DATABASE_URL
says otherwise, so re-running is one command and leaves nothing behind
that a later run has to reckon with.
"""

import datetime
import glob
import os
import subprocess
import time
import uuid

import psycopg

from bench import config

SCHEMA = """
DROP TABLE IF EXISTS items;
CREATE TABLE items (
    id uuid PRIMARY KEY,
    name varchar(255) NOT NULL,
    description varchar(255) NOT NULL,
    enabled boolean NOT NULL,
    quantity integer NOT NULL,
    project_id uuid NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);
CREATE INDEX items_project_id ON items (project_id);
"""


def binaries():
    found = sorted(glob.glob("/usr/lib/postgresql/*/bin"))
    if not found:
        raise SystemExit(
            "no PostgreSQL server binaries found under /usr/lib/postgresql"
        )
    return found[-1]


def running():
    try:
        with psycopg.connect(config.DATABASE_URL, connect_timeout=2):
            return True
    except Exception:
        return False


def start():
    """Bring up the project's own cluster. Returns True if we started it."""
    if running():
        return False
    binary = binaries()
    if not os.path.exists(os.path.join(config.DATA_DIR, "PG_VERSION")):
        subprocess.run(
            [
                os.path.join(binary, "initdb"),
                "-D",
                config.DATA_DIR,
                "-U",
                config.USER,
                "--auth=trust",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    subprocess.run(
        [
            os.path.join(binary, "pg_ctl"),
            "-D",
            config.DATA_DIR,
            "-o",
            "-p %d -h 127.0.0.1 -k %s" % (config.PORT, config.DATA_DIR),
            "-l",
            os.path.join(config.DATA_DIR, "server.log"),
            "start",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    for _ in range(30):
        if _database_ready(binary):
            return True
        time.sleep(0.5)
    raise SystemExit("PostgreSQL did not come up")


def _database_ready(binary):
    try:
        subprocess.run(
            [
                os.path.join(binary, "createdb"),
                "-h",
                "127.0.0.1",
                "-p",
                str(config.PORT),
                "-U",
                config.USER,
                config.DATABASE,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return running()
    except Exception:
        return False


def stop():
    subprocess.run(
        [os.path.join(binaries(), "pg_ctl"), "-D", config.DATA_DIR, "stop"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def server_version():
    """What PostgreSQL answered the calls, as it names itself."""
    with psycopg.connect(config.DATABASE_URL) as connection:
        return connection.execute("SHOW server_version").fetchone()[0]


def seed(rows=None):
    """The same rows every time: seeded ids, seeded timestamps."""
    rows = rows or config.ROWS
    epoch = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    project = uuid.UUID(int=0x51)
    records = []
    for number in range(rows):
        records.append(
            (
                uuid.UUID(int=number + 1),
                "item %d" % number,
                "a description of item %d" % number,
                number % 3 != 0,
                number,
                project,
                epoch + datetime.timedelta(seconds=number),
                # Every third row lands exactly on a second, which is
                # where stacks spell timestamps differently.
                epoch + datetime.timedelta(seconds=number, microseconds=number % 3),
            )
        )
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as connection:
        connection.execute(SCHEMA)
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO items (id, name, description, enabled, quantity,"
                " project_id, created_at, updated_at)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                records,
            )
    return records


def expected(page=None):
    """What every stack must answer with, read straight from the table."""
    page = page or config.PAGE
    with psycopg.connect(config.DATABASE_URL) as connection:
        with connection.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            cursor.execute("SELECT * FROM items ORDER BY quantity LIMIT %s", (page,))
            collection = cursor.fetchall()
    return collection
