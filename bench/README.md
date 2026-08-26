# How fast is RestAlchemy?

The same three requests, answered by RestAlchemy, by the Python stacks
people reach for instead, and by the floor: a hand-written query and
`orjson.dumps`, no framework at all, which is what the database and the
JSON cost before anything else runs.

15 rounds × best of 20 calls, 1000 rows in the table, 100 per page,
Python 3.12, PostgreSQL 16 on a local socket, one AMD EPYC 7742 with
DDR4-2666. In
parentheses: the same number as a multiple of RestAlchemy's. Microseconds
are only comparable against the same machine — `results/results.md`
records which one it was, and how busy.

| Stack | Collection of 100 | One resource | POST one | Per row |
| --- | ---: | ---: | ---: | ---: |
| raw psycopg + orjson | 1272 µs (0.7×) | 174 µs (0.5×) | 229 µs (0.6×) | 11.1 µs (0.8×) |
| **RestAlchemy** | **1705 µs** | **317 µs** | **397 µs** | **14.0 µs** |
| Flask + SQLAlchemy | 2267 µs (1.3×) | 636 µs (2.0×) | 606 µs (1.5×) | 16.5 µs (1.2×) |
| FastAPI + SQLAlchemy | 2417 µs (1.4×) | 894 µs (2.8×) | 829 µs (2.1×) | 15.4 µs (1.1×) |
| Litestar + SQLAlchemy | 2524 µs (1.5×) | 857 µs (2.7×) | 811 µs (2.0×) | 16.8 µs (1.2×) |
| Django + DRF | 5276 µs (3.1×) | 943 µs (3.0×) | 895 µs (2.3×) | 43.8 µs (3.1×) |

**First in this table on all three request patterns, because of how little
it adds to the floor.** The bare single-row query costs 174 µs;
RestAlchemy serves it as a REST resource — routed, fetched through its
ORM, packed, answered — for 143 µs more. The bare insert costs 229 µs;
served, 168 µs more. A row of a collection costs the floor 11.1 µs and
RestAlchemy 14.0: under three microseconds of framework per row. On every
request it stands nearer to the floor than to any framework behind it.

Two numbers are worth separating. The **fixed part** of a request — what a
stack spends before it looks at any data — is the single-resource column:
317 µs. **A row** is the rest of the collection spread over its other 99
rows: 14.0 µs, and it is the number that decides a page, because a
collection is one fixed part and a hundred rows.

## Why it is light

Nothing here is a trick, and none of it changed what the library is. What
a declaration settles is answered once and kept: the columns and aliases
of a `SELECT`, the escaped names of a table, what filling a model in needs
to know per property, which fields a request may see. What a row does not
ask for is not built: a model keeps its values and builds a property
object when something wants one, and its id properties when something
writes it. A relationship is fetched once per page rather than once per
row. And what another library writes faster is handed to it — UUIDs and
UTC timestamps go to orjson, which writes them in C.

## Run it

```bash
bench/run.sh                          # everything
bench/run.sh --rounds 20 --calls 30   # longer
bench/run.sh --only RestAlchemy Flask
bench/run.sh --stop                   # put the database away
```

The first run creates a virtualenv under `bench/.venv` from
`requirements.txt`, brings up a PostgreSQL of its own under `bench/.pgdata`
and seeds it; every later run reuses both. `DATABASE_URL` points it
somewhere else if you would rather, and `RESTALCHEMY_PATH` measures a
RestAlchemy other than the one this file sits in. Results land in
`results/results.md`, the raw per-round samples beside it in JSON.

The report names the machine it ran on. It reads what it can; the speed of
the DIMMs only `dmidecode` knows and only root may ask, so
`BENCH_MEMORY_SPEED="2666 MT/s"` says it where nobody can.

## What is compared

| Stack | What answers the request |
| --- | --- |
| raw psycopg + orjson | no framework at all: a query and `orjson.dumps` |
| RestAlchemy | its own ORM, its own resources and packer, WSGI |
| Django + DRF | the Django ORM and a `ModelSerializer` |
| Flask + SQLAlchemy | the SQLAlchemy ORM, dictionaries by hand, orjson |
| FastAPI + SQLAlchemy | async SQLAlchemy, pydantic response models |
| Litestar + SQLAlchemy | async SQLAlchemy, msgspec serialisation |

Each is written the way its own documentation writes it, which is the
comparison worth having: not the same code six times, but the same request
answered six ways.

The three requests: **GET a collection** of 100 rows ordered, **GET one
resource** by id, and **POST one resource**, which writes a row.

## How it is measured

- **In the same process, at each stack's own interface.** WSGI
  applications are called directly, ASGI ones through a bare event loop.
  A web server would measure the web server.
- **Nobody is timed without answering the same as the table.** Every
  stack's output is parsed and compared against the rows themselves, field
  by field, before any timing starts — and compared again after the last
  round, so a stack that broke mid-run cannot be timed answering something
  cheaper than the work. Timestamps are compared as instants: the stacks
  spell them differently (`Z` against `+00:00`), and that is a formatting
  difference, not less work.
- **Everything is warmed first.** Each stack runs every scenario for a
  second before timing — compiled statements, validators built per model,
  routes resolved, a pool opened, and the pages the query reads land in the
  database's cache. `--warmup 0` turns it off, which is a good way to see
  how much it was worth.
- **Rounds are interleaved** and the order rotates each round, so a machine
  that drifts does it to everyone at once and being first is not an
  advantage anyone keeps.
- **A round reports the best of its calls; the table reports the median of
  the rounds** with a bootstrap 95% interval. The best of a round is the
  repeatable part of a latency — noise on a shared machine only ever adds —
  and the median across fifteen rounds keeps any one round from being the
  story.
- **Rows created by the POSTs are swept after every stack's turn**, so
  every stack in a round reads the same table.

## The guard in the suite

This benchmark is a report: run by hand, on a machine somebody trusts,
and it publishes a table. The functional suite carries a smaller relative
of it, `restalchemy/tests/functional/perf/`, which runs on every push and
fails when a request of ours costs more of the floor than it may — 2.5×
for a collection, 3× for a resource, 3× for a create, against 1.6×, 2.1×
and 1.9× measured today. PostgreSQL only: the floor is a raw psycopg one,
so the MySQL run skips it.

A ratio is what a build machine can be held to, where microseconds are
not: a runner that is slow or busy is slow for the floor too, and under a
fully loaded machine every ratio above *falls*. What that buys is a wall
against losing a factor rather than a tenth — on the requests where our
own work is the smaller part of the whole, a regression under about half
again lands inside the room the wall leaves for the machine. That is what
running the benchmark is for.

Beside it a second guard serves two thousand requests and counts what the
process kept: no objects at all, and under 32 bytes each. Measured, after
the caches settle: nothing and about a byte. Both run in a process of
their own — RestAlchemy keeps one application per process, and what a
request keeps cannot be counted in a process other tests allocate in.

```bash
tox -e py312-functional          # both, with the rest of the suite
DATABASE_URI=postgresql://user@host/db python -m \
    restalchemy.tests.functional.perf.probe --mode speed   # or --mode memory
```

## What the numbers do not say

**Transactions are not the same across stacks.** Counted from the server's
own log, per request: Django sends one statement, everyone else sends three
(`BEGIN`, the query, `COMMIT` or `ROLLBACK`) because Django reads in
autocommit by default. On this machine's local socket that is **86 µs** a
request — measured, not guessed — which is most of Django's edge on the
single-row requests and none of its cost on the collection.

**One driver everywhere.** Everything that talks SQL talks it through
psycopg 3 — sync or async — so the driver is a constant, not a variable.
The async stacks are also often run over asyncpg; that is a different
driver with different numbers, and comparing drivers is a different
benchmark.

**Async stacks pay for the loop.** FastAPI and Litestar are driven through
an event loop for a single request at a time, which is the honest cost of
the model when there is nothing to overlap. Under concurrency the picture
would be a different one; this benchmark asks about one request.

**One machine, one PostgreSQL, one Python.** The numbers are the shape of
the difference, not a universal constant. Run it yourself; that is what it
is for.
