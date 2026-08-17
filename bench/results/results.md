# Same three requests, 6 stacks, one PostgreSQL

2026-08-17 11:46 UTC · 15 rounds × best of 20 calls, after 1.0s of warm-up per
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
| raw psycopg + orjson | 1307 µs | 1270 … 1338 | 1.00× | 0.75× |
| RestAlchemy | 1731 µs | 1699 … 1741 | 1.32× | 1.00× |
| Flask + SQLAlchemy | 2275 µs | 2229 … 2313 | 1.74× | 1.31× |
| FastAPI + SQLAlchemy | 2370 µs | 2358 … 2387 | 1.81× | 1.37× |
| Litestar + SQLAlchemy | 2491 µs | 2481 … 2537 | 1.91× | 1.44× |
| Django + DRF | 5254 µs | 5131 … 5333 | 4.02× | 3.03× |

## GET one resource by id

| Stack | Median | 95% CI | × fastest | × RestAlchemy |
| --- | ---: | :---: | ---: | ---: |
| raw psycopg + orjson | 166 µs | 165 … 167 | 1.00× | 0.54× |
| RestAlchemy | 310 µs | 305 … 315 | 1.86× | 1.00× |
| Flask + SQLAlchemy | 628 µs | 623 … 634 | 3.78× | 2.03× |
| Litestar + SQLAlchemy | 832 µs | 829 … 835 | 5.00× | 2.68× |
| FastAPI + SQLAlchemy | 872 µs | 865 … 876 | 5.24× | 2.81× |
| Django + DRF | 924 µs | 919 … 931 | 5.56× | 2.98× |

## POST one resource

| Stack | Median | 95% CI | × fastest | × RestAlchemy |
| --- | ---: | :---: | ---: | ---: |
| raw psycopg + orjson | 222 µs | 220 … 222 | 1.00× | 0.58× |
| RestAlchemy | 384 µs | 382 … 388 | 1.73× | 1.00× |
| Flask + SQLAlchemy | 588 µs | 583 … 602 | 2.65× | 1.53× |
| Litestar + SQLAlchemy | 784 µs | 778 … 788 | 3.53× | 2.04× |
| FastAPI + SQLAlchemy | 804 µs | 800 … 806 | 3.63× | 2.09× |
| Django + DRF | 868 µs | 860 … 882 | 3.91× | 2.26× |

## What is fixed and what a row costs

The single-row request is what a stack spends before it looks at any data;
the rest of the collection, spread over the other 99 rows, is what each
row costs it.

| Stack | Fixed, per request | Per row | × fastest per row |
| --- | ---: | ---: | ---: |
| raw psycopg + orjson | 166 µs | 11.5 µs | 1.00× |
| RestAlchemy | 310 µs | 14.4 µs | 1.25× |
| FastAPI + SQLAlchemy | 872 µs | 15.1 µs | 1.31× |
| Flask + SQLAlchemy | 628 µs | 16.6 µs | 1.44× |
| Litestar + SQLAlchemy | 832 µs | 16.8 µs | 1.45× |
| Django + DRF | 924 µs | 43.7 µs | 3.80× |
