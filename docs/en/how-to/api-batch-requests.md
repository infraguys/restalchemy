<!--
Copyright 2026 Genesis Corporation

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

# Batch requests

This guide explains how to let clients bundle several logical operations
(create/get/update/delete, and controller actions) into a single HTTP call,
using `restalchemy.api.batch`.

Each item in a batch is replayed as its own request through the *unmodified*
routing/controller/packer stack, so nothing about your existing `Controller`
or `Route` subclasses has to change to support batching.

---

## 1. Enabling the endpoint

Mount `batch.BatchRoute` on your root route, the same way you attach any
other route:

```python
from restalchemy.api import batch
from restalchemy.api import routes


class Root(routes.RootRoute):
    v1 = routes.route(V1Route)
    batch = routes.route(batch.BatchRoute)
```

This exposes a single `POST /batch/` endpoint that can address any resource
reachable from `Root` — no per-resource opt-in is needed.

---

## 2. Request format

```json
{
  "requests": [
    {"method": "POST", "path": "/v1/vms/", "body": {"name": "vm-a"}},
    {"method": "GET",  "path": "/v1/vms/<uuid>"},
    {"method": "PUT",  "path": "/v1/vms/<uuid>", "body": {"name": "vm-b"}},
    {"method": "DELETE", "path": "/v1/vms/<uuid>"},
    {"method": "POST", "path": "/v1/vms/<uuid>/actions/poweron/invoke"}
  ]
}
```

Each item in `requests` is:

| field     | required | description                                              |
|-----------|----------|-----------------------------------------------------------|
| `method`  | yes      | `GET`, `POST`, `PUT` or `DELETE` — same as a real request. |
| `path`    | yes      | The path you would normally call, including query string (`?field=value`) if you need filtering. |
| `body`    | no       | JSON body, same shape as the real endpoint expects.        |
| `headers` | no       | Extra headers to apply to that item only.                  |

---

## 3. Each item runs independently, through the full middleware stack

Every item is best-effort: one item failing does not stop or roll back the
others. The response is always `200 OK` with a per-item `status`/`body`
pair, even if some items failed — check each item's own `status`, don't
assume success from the outer HTTP status.

Each item is dispatched through the *whole* WSGI middleware chain wrapping
the `/batch` endpoint (auth, per-route authorization/policy, rate limiting,
retry-on-deadlock, ...) — not just the innermost routing/controller layer.
A batch item is therefore held to exactly the same rules a direct call to
that same path would be: if a middleware would reject or rate-limit a
direct `POST /v1/vms/`, it rejects that same request when it arrives as a
batch item too.

One consequence of going through the full stack per item: if the deploying
app's `ContextMiddleware` opens a DB transaction per request, each item gets
its *own* transaction — there is no cross-item atomicity. A batch of five
writes is five independent transactions, exactly as if you'd made five
separate direct calls; a failure in item 3 has no effect on items 1, 2, 4 or
5. If you need several writes to succeed or fail together, that has to be
implemented as an operation on the target resource itself (a single
endpoint that performs all of them in one transaction), not by batching
independent calls.

---

## 4. Response format

```json
[
  {"status": 201, "body": {"uuid": "...", "name": "vm-a", "...": "..."}},
  {"status": 200, "body": {"uuid": "...", "name": "vm-a", "...": "..."}},
  {"status": 200, "body": {"uuid": "...", "name": "vm-b", "...": "..."}},
  {"status": 204, "body": null},
  {"status": 200, "body": {"uuid": "...", "state": "on", "...": "..."}}
]
```

The response is a JSON array, one entry per request, **in the same order as
submitted**. Each entry mirrors what a direct call to that endpoint would
have returned: the real HTTP status code and the parsed response body (or
`null` for empty bodies). A failed item looks the same as any other
RestAlchemy error body:

```json
{"status": 404, "body": {"type": "RecordNotFound", "code": 404, "message": "..."}}
```

---

## 5. Limits and validation errors

- `requests` must be a JSON array; anything else raises `ParseError`
  (HTTP 400) for the whole call.
- `BatchController.__max_batch_size__` (default `100`) caps how many items a
  single call may contain; exceeding it raises `BatchSizeLimitExceeded`
  (HTTP 400) for the whole call, before any item runs. Override it on a
  subclass if you need a different limit.
- A batch item may not target the batch endpoint itself
  (`NestedBatchNotAllowed`, HTTP 400) — this is rejected instead of
  recursing.

---

## Summary

- `batch.BatchRoute`/`batch.BatchController` reuse the existing route tree,
  controllers and packers unchanged — batching is purely additive.
- Every item is best-effort and independent: check each item's own
  `status`.
- Items are dispatched through the full middleware stack, so auth/policy/
  rate-limiting/retry behave exactly like a direct call — at the cost of no
  cross-item transaction: each item gets its own.
- Actions (`.../actions/<name>/invoke`) work inside a batch exactly like a
  direct call, since a batch item is just a path/method/body replay.
