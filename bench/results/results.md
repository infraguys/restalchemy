# Same three requests, 6 stacks, one PostgreSQL

2026-08-26 11:30 UTC · 15 rounds × best of 20 calls, after 1.0s of warm-up per
scenario · 1000 rows in the table, 100 per page · Python 3.12.3

Measured on:

- **CPU**: AMD EPYC 7742 64-Core Processor, 64 cores / 128 threads
- **Frequency governor**: schedutil
- **Memory**: 504 GiB at 2666 MT/s
- **Kernel**: Linux 6.8.0-134-generic
- **PostgreSQL**: 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)
- **Load average before the first round**: 6.27, 6.23, 6.83

Microseconds are only comparable against the same machine. This benchmark
allocates and walks small objects, so it reads the memory subsystem at
least as much as the clock, and a busy machine slows every stack at once —
the load average is here so a reader can tell whether that happened. The
ratios hold up better than the absolute numbers across machines.

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
| raw psycopg + orjson | 1272 µs | 1264 … 1283 | 1.00× | 0.75× |
| RestAlchemy | 1705 µs | 1687 … 1759 | 1.34× | 1.00× |
| Flask + SQLAlchemy | 2267 µs | 2257 … 2347 | 1.78× | 1.33× |
| FastAPI + SQLAlchemy | 2417 µs | 2385 … 2429 | 1.90× | 1.42× |
| Litestar + SQLAlchemy | 2524 µs | 2509 … 2536 | 1.98× | 1.48× |
| Django + DRF | 5276 µs | 5160 … 5358 | 4.15× | 3.09× |

## GET one resource by id

| Stack | Median | 95% CI | × fastest | × RestAlchemy |
| --- | ---: | :---: | ---: | ---: |
| raw psycopg + orjson | 174 µs | 173 … 175 | 1.00× | 0.55× |
| RestAlchemy | 317 µs | 315 … 319 | 1.83× | 1.00× |
| Flask + SQLAlchemy | 636 µs | 632 … 638 | 3.66× | 2.00× |
| Litestar + SQLAlchemy | 857 µs | 848 … 902 | 4.94× | 2.70× |
| FastAPI + SQLAlchemy | 894 µs | 889 … 902 | 5.15× | 2.82× |
| Django + DRF | 943 µs | 934 … 972 | 5.43× | 2.97× |

## POST one resource

| Stack | Median | 95% CI | × fastest | × RestAlchemy |
| --- | ---: | :---: | ---: | ---: |
| raw psycopg + orjson | 229 µs | 228 … 231 | 1.00× | 0.58× |
| RestAlchemy | 397 µs | 392 … 399 | 1.73× | 1.00× |
| Flask + SQLAlchemy | 606 µs | 600 … 612 | 2.64× | 1.53× |
| Litestar + SQLAlchemy | 811 µs | 805 … 835 | 3.54× | 2.04× |
| FastAPI + SQLAlchemy | 829 µs | 825 … 843 | 3.62× | 2.09× |
| Django + DRF | 895 µs | 883 … 912 | 3.91× | 2.26× |

## What is fixed and what a row costs

The single-row request is what a stack spends before it looks at any data;
the rest of the collection, spread over the other 99 rows, is what each
row costs it.

| Stack | Fixed, per request | Per row | × fastest per row |
| --- | ---: | ---: | ---: |
| raw psycopg + orjson | 174 µs | 11.1 µs | 1.00× |
| RestAlchemy | 317 µs | 14.0 µs | 1.26× |
| FastAPI + SQLAlchemy | 894 µs | 15.4 µs | 1.39× |
| Flask + SQLAlchemy | 636 µs | 16.5 µs | 1.49× |
| Litestar + SQLAlchemy | 857 µs | 16.8 µs | 1.52× |
| Django + DRF | 943 µs | 43.8 µs | 3.94× |
