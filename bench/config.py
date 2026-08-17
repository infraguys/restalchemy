"""Everything the benchmark needs to know to run twice the same way."""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
# The repository this benchmark lives in: the RestAlchemy it measures is
# the one next to it, unless RESTALCHEMY_PATH says otherwise -- which is
# how a branch is measured against the commit it started from.
RESTALCHEMY_PATH = os.environ.get("RESTALCHEMY_PATH", os.path.dirname(HERE))

# A database of its own, so a re-run is not at the mercy of what else
# lives on the machine. Point DATABASE_URL somewhere else to use yours.
PORT = int(os.environ.get("BENCH_PG_PORT", "55433"))
DATA_DIR = os.environ.get("BENCH_PG_DATA", os.path.join(HERE, ".pgdata"))
USER = "bench"
DATABASE = "bench"
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://%s@127.0.0.1:%d/%s" % (USER, PORT, DATABASE)
)

ROWS = int(os.environ.get("BENCH_ROWS", "1000"))
PAGE = int(os.environ.get("BENCH_PAGE", "100"))
ROUNDS = int(os.environ.get("BENCH_ROUNDS", "10"))
# Calls per round, per scenario: the round reports the best of them, so a
# stray scheduling hiccup does not become the round's answer.
CALLS = int(os.environ.get("BENCH_CALLS", "20"))
WARMUP = float(os.environ.get("BENCH_WARMUP", "1.0"))
