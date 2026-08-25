# Same three requests, 6 stacks, one PostgreSQL

2026-08-26 10:39 UTC · 15 rounds × best of 20 calls, after 1.0s of warm-up per
scenario · 1000 rows in the table, 100 per page · Python 3.12.3

Each stack is called at its own interface in the same process — WSGI
applications directly, ASGI ones through a bare event loop — so what is
timed is the framework and its database work, not a web server. Each is
written the way its own documentation writes it. Every stack answers with
the same rows, checked field by field before anything is timed and checked
again after the last round. Rounds are interleaved and the order rotates,
so drift lands on everyone at once.

Three things the numbers do not say. **Django reads in autocommit** — one
statement a request, where every other stack here sends `BEGIN`, the query,
and `COMMIT` or `ROLLBACK`; on this machine's socket those two extra round
trips are 86 µs, which is most of Django's edge on the single-row requests.
**Everything talks psycopg 3**, sync or async, so the driver is a constant;
asyncpg would be a different benchmark. And **the async stacks pay for the
loop** with nothing to overlap: this benchmark asks about one request at a
time, and concurrency is a different question.

## GET a collection of 100

| Stack | Median | 95% CI | × fastest | × RestAlchemy |
| --- | ---: | :---: | ---: | ---: |
| raw psycopg + orjson | 1276 µs | 1270 … 1288 | 1.00× | 0.75× |
| RestAlchemy | 1706 µs | 1700 … 1771 | 1.34× | 1.00× |
| Flask + SQLAlchemy | 2269 µs | 2256 … 2273 | 1.78× | 1.33× |
| FastAPI + SQLAlchemy | 2397 µs | 2373 … 2449 | 1.88× | 1.41× |
| Litestar + SQLAlchemy | 2527 µs | 2517 … 2538 | 1.98× | 1.48× |
| Django + DRF | 5331 µs | 5259 … 5363 | 4.18× | 3.13× |

## GET one resource by id

| Stack | Median | 95% CI | × fastest | × RestAlchemy |
| --- | ---: | :---: | ---: | ---: |
| raw psycopg + orjson | 174 µs | 173 … 175 | 1.00× | 0.55× |
| RestAlchemy | 317 µs | 316 … 321 | 1.82× | 1.00× |
| Flask + SQLAlchemy | 636 µs | 632 … 646 | 3.65× | 2.00× |
| Litestar + SQLAlchemy | 852 µs | 845 … 858 | 4.89× | 2.68× |
| FastAPI + SQLAlchemy | 892 µs | 887 … 896 | 5.12× | 2.81× |
| Django + DRF | 942 µs | 932 … 960 | 5.41× | 2.97× |

## POST one resource

| Stack | Median | 95% CI | × fastest | × RestAlchemy |
| --- | ---: | :---: | ---: | ---: |
| raw psycopg + orjson | 232 µs | 230 … 233 | 1.00× | 0.59× |
| RestAlchemy | 396 µs | 394 … 402 | 1.71× | 1.00× |
| Flask + SQLAlchemy | 604 µs | 601 … 612 | 2.61× | 1.53× |
| Litestar + SQLAlchemy | 795 µs | 792 … 815 | 3.43× | 2.01× |
| FastAPI + SQLAlchemy | 821 µs | 815 … 825 | 3.54× | 2.07× |
| Django + DRF | 895 µs | 889 … 916 | 3.86× | 2.26× |

## What is fixed and what a row costs

The single-row request is what a stack spends before it looks at any data;
the rest of the collection, spread over the other 99 rows, is what each
row costs it.

| Stack | Fixed, per request | Per row | × fastest per row |
| --- | ---: | ---: | ---: |
| raw psycopg + orjson | 174 µs | 11.1 µs | 1.00× |
| RestAlchemy | 317 µs | 14.0 µs | 1.26× |
| FastAPI + SQLAlchemy | 892 µs | 15.2 µs | 1.37× |
| Flask + SQLAlchemy | 636 µs | 16.5 µs | 1.48× |
| Litestar + SQLAlchemy | 852 µs | 16.9 µs | 1.52× |
| Django + DRF | 942 µs | 44.3 µs | 3.98× |
