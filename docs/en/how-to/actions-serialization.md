<!--
Copyright 2025 Genesis Corporation

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

# Nuances of action result serialization

This document describes an important RESTAlchemy nuance: **how the serializer (packer) and the set of resource fields are selected when processing `actions`**, and why an action declared on a controller for resource `A` is, by default, serialized *as resource `A`*, even if it actually returns model `B`.

It also provides a practical workaround (without changing the library) and links to a working example in functional tests.

---

## TL;DR

- An action is executed **in the context of the controller** it is declared on / bound to.
- **The packer and the serialization schema are taken from that controller's `__resource__`.**
- If an action returns a model of a different type, the packer will try to read “foreign” fields and fail with `AttributeError`.
- A practical workaround without modifying RESTAlchemy: **bind the action to a dedicated controller** whose `__resource__` matches the returned model type.

---

## 1. Why it happens

### 1.1. High-level action processing flow

Simplified, for a URL like:

- `/v1/vms/<uuid>/actions/ip_addresses`

the following happens:

1. The router resolves the route tree (e.g. `v1 → vms → actions/ip_addresses`).
2. VM is loaded by `<uuid>` (this is the **input** to the action).
3. The action class (`routes.Action`) is resolved and its `__controller__` is selected.
4. The controller method decorated with `@actions.get` / `@actions.post` is invoked.
5. The result is passed to `controller.process_result()`.
6. `process_result()` builds an HTTP response via `controller.get_packer()`.
7. The packer serializes the object using **resource fields from `controller.__resource__`**.

### 1.2. The key nuance

The packer does not “infer” the model type from the returned value at runtime (and OpenAPI annotations are not used for runtime packing). Instead, it serializes the response **as the resource bound to the controller**.

If the controller declares:

- `__resource__ = ResourceByRAModel(models.VM)`

then the packer expects that the returned objects contain VM fields (e.g. `state`, `name`, ...).

---

## 2. Problem symptoms

### 2.1. Typical error stack

If an action on the VM controller returns `IpAddress`, the packer (serializing “as VM”) will try to access the `state` field on `IpAddress`:

- `AttributeError: IpAddress object has no attribute state`

This looks like “broken model serialization in actions”, but in fact it is **a mismatch between the controller `__resource__` type and the actual action result type**.

---

## 3. Practical example from functional tests (VM → IpAddress)

### 3.1. Goal

Implement an action endpoint:

- `GET /v1/vms/<uuid>/actions/ip_addresses`

that returns **a list of `IpAddress`** for the given VM.

### 3.2. Why returning `IpAddress` directly from `VMController` is not enough

If `ip_addresses()` is implemented directly on `VMController`, serialization will still be performed as `VM` and will fail (see section 2).

### 3.3. Fix without modifying the library (approach 1)

The fix consists of two parts:

- **(A) A dedicated controller for the action result** with the correct `__resource__`.
- **(B) Bind `routes.Action` to that controller**.

#### A) Result controller

File:

- `restalchemy/tests/functional/restapi/ra_based/microservice/controllers.py`

Class:

- `VMIpAddressesController`

Idea: the input parameter `resource` is still VM (the parent resource), but **`__resource__` is set to IpAddress**, so the packer serializes the result correctly.

Additional nuance: RESTAlchemy maintains a global mapping `model → resource`.

- If you create another `ResourceByRAModel(models.IpAddress)`, you will get a duplicate mapping error.
- Therefore the resource is **reused**: `IpAddressController.__resource__`.

#### B) Action route

File:

- `restalchemy/tests/functional/restapi/ra_based/microservice/routes.py`

Class:

- `VMIPAddressesAction`

It must point to `VMIpAddressesController`, and in `VMRoute` it is declared as:

- `ip_addresses = routes.action(VMIPAddressesAction, invoke=False)`

### 3.4. Test that validates correct behavior

File:

- `restalchemy/tests/functional/restapi/ra_based/test_resources.py`

Test:

- `TestRetryOnErrorMiddlewareBaseResourceTestCase.test_vm_get_ip_addresses_action_returns_success`

It asserts:

- HTTP 200
- JSON response is a list of IpAddress objects with:
  - `uuid`
  - `ip`
  - `port` (URI of the port)

---

## 4. Recommendations

### 4.1. When to use a dedicated controller (recommended)

Use a dedicated controller when:

- the action returns **a different model type** (or a list of such models),
- you want to keep an action endpoint (instead of introducing an additional nested route),
- you do not want to modify RESTAlchemy.

This provides:

- the correct packer,
- the correct set of fields,
- predictable behavior.

### 4.2. When to return `dict` / primitives

If the result is not a resource/model (e.g. `{"state": "on"}`), returning plain structures (`dict`, `list[dict]`, strings) is a good fit, because they do not depend on `__resource__` fields.

### 4.3. What if one action must return multiple types

If an action can return different types (sometimes VM, sometimes IpAddress), that is a poor contract:

- one `__resource__` cannot pack both types correctly.

In that case prefer:

- separate endpoints/controllers,
- or extend the library (e.g. “action-specific resource type”).

---

## 5. See also

- How-to about nested resources and actions:
  - `docs/en/how-to/api-nested-resources-and-actions.md`
