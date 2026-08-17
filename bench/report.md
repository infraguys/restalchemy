# Same three requests, {stacks} stacks, one PostgreSQL

{stamp} · {rounds} rounds × best of {calls} calls, after {warmup:.1f}s of warm-up per
scenario · {rows} rows in the table, {page} per page · Python {python}

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

## GET a collection of {page}

{collection}

## GET one resource by id

{resource}

## POST one resource

{create}

## What is fixed and what a row costs

The single-row request is what a stack spends before it looks at any data;
the rest of the collection, spread over the other {rest} rows, is what each
row costs it.

{rowcost}
