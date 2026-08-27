"""What a run must not do to a database it was pointed at.

DATABASE_URL exists so the benchmark can be run against a database
someone chose. Setting up a run recreates its table, so the checks here
are about the one thing that must never follow from that: a table the
benchmark did not create being dropped.

Runs against the benchmark's own cluster, and brings it up if it is not
already running:

    bench/.venv/bin/python -m bench.tests.test_database
"""

import contextlib

import psycopg

from bench import config
from bench import database

OTHER = "items"
OTHER_ROW = ("a row that was here first",)


@contextlib.contextmanager
def _table_named(name):
    """A table of somebody else's, with a row in it to recognise."""
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as connection:
        connection.execute("DROP TABLE IF EXISTS %s" % name)
        connection.execute("CREATE TABLE %s (note text)" % name)
        connection.execute("INSERT INTO %s (note) VALUES (%%s)" % name, OTHER_ROW)
        try:
            yield connection
        finally:
            connection.execute("DROP TABLE IF EXISTS %s" % name)


def _rows(connection, name):
    return connection.execute("SELECT note FROM %s" % name).fetchall()


def test_a_run_leaves_an_unrelated_table_alone():
    """The default table is the benchmark's own; `items` is not it."""
    with _table_named(OTHER) as connection:
        database.seed(rows=1)

        assert _rows(connection, OTHER) == [OTHER_ROW]


def test_a_table_the_benchmark_did_not_create_is_refused():
    """Named at somebody's table, a run stops instead of recreating it."""
    with _table_named(OTHER) as connection:
        table, config.TABLE = config.TABLE, OTHER
        try:
            try:
                database.seed(rows=1)
            except SystemExit as refusal:
                assert OTHER in str(refusal)
                assert "BENCH_DROP_UNMARKED" in str(refusal)
            else:
                raise AssertionError("a foreign table was recreated")
            assert _rows(connection, OTHER) == [OTHER_ROW]
        finally:
            config.TABLE = table


def test_the_benchmark_recreates_its_own_table():
    """Its own mark is what lets the next run drop what it left."""
    database.seed(rows=1)
    database.seed(rows=1)

    assert len(database.expected(page=10)) == 1


def test_a_table_name_that_is_not_an_identifier_is_refused():
    table, config.TABLE = config.TABLE, "items; DROP TABLE items"
    try:
        try:
            database.seed(rows=1)
        except SystemExit as refusal:
            assert "BENCH_TABLE" in str(refusal)
        else:
            raise AssertionError("a name that is not an identifier was used")
    finally:
        config.TABLE = table


def main():
    database.start()
    for name, check in sorted(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok   %s" % name)


if __name__ == "__main__":
    main()
