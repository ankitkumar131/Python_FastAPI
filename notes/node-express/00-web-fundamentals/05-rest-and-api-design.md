# 05 — REST and API Design

> **Where this fits:** You know HTTP (the transport) and URLs (the addressing). This chapter is about _style_: how to shape resources, responses, errors, pagination and versioning so that your API is predictable enough that a stranger can use it without reading your source code.

***

## 1. What REST actually is

**REST (Representational State Transfer)** is an architectural _style_ described by Roy Fielding in his 2000 doctoral dissertation. It is not a specification, not a library, and not something you can "install".

Fielding's constraints, and what they mean in practice:

| Constraint                      | Meaning                                                                                                         | Do you follow it?                                                    |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Client–server**               | UI and data storage are separated                                                                               | Almost always ✅                                                      |
| **Stateless**                   | Each request carries everything the server needs; the server keeps no per-client session state between requests | Usually ✅ (JWT) — but sessions with cookies are technically stateful |
| **Cacheable**                   | Responses declare whether they can be cached                                                                    | Often ignored, easy to add ✅                                         |
| **Uniform interface**           | Resources identified by URLs; manipulation via representations; self-descriptive messages; HATEOAS              | Partially — most APIs stop after the first two                       |
| **Layered system**              | A client cannot tell if it talks to the origin server or a proxy                                                | ✅ automatically (CDNs, load balancers)                               |
| **Code on demand** _(optional)_ | Server can send code to the client (e.g. JS)                                                                    | N/A for APIs                                                         |

**The honest truth:** the "REST API" you will write and that almost every company writes is really **HTTP + JSON with resource-oriented URLs**. It ignores HATEOAS (responses containing links that tell the client what it can do next) and often uses sessions.

That is completely fine — but know the difference, because an interviewer may ask. The short answer:

> "Strict REST includes HATEOAS-driven hypermedia and complete statelessness. Most production APIs implement the resource-oriented, HTTP-verb, JSON subset, which is why they are more accurately called RESTful HTTP APIs."

### HATEOAS in one example

```json
{
  "id": 42,
  "status": "paid",
  "_links": {
    "self":   { "href": "/api/v1/orders/42" },
    "cancel": { "href": "/api/v1/orders/42/cancel", "method": "POST" },
    "refund": { "href": "/api/v1/orders/42/refund", "method": "POST" }
  }
}
```

The idea: clients discover capabilities from the response instead of hardcoding URLs. In practice almost nobody does this, because it is verbose and clients hardcode anyway. (Related ideas that _are_ widely used: pagination links in headers or `meta`, and OpenAPI documents.)

***

## 2. Resources, and why nouns matter

A **resource** is any thing worth naming: a user, an order, a shopping cart, a payment.

REST's central idea: **the URL identifies the resource; the HTTP method expresses the operation.** That gives you a small, uniform vocabulary instead of an infinite list of endpoint names.

```
✅ Resource-oriented                       ❌ RPC-style
GET    /users                             POST /getUsers
POST   /users                             POST /createUser
GET    /users/42                          POST /getUserById        { "id": 42 }
PATCH  /users/42                          POST /updateUser         { "id": 42, "name": … }
DELETE /users/42                          POST /deleteUser         { "id": 42 }
```

RPC-style is not _wrong_ — gRPC and JSON-RPC are legitimate, and they are excellent for internal service-to-service calls where operations genuinely are commands. But for a public API consumed by browsers and mobile apps, resource-oriented URLs are far more learnable, cacheable and tool-friendly.

### Representing relationships

```
/users/42/orders                  orders belonging to user 42 (a collection)
/users/42/orders/987              a specific order (usually reachable as /orders/987 too)
/users/42/manager                 a to-one relationship — singular!
/users/42/roles                   a to-many relationship — plural
```

Sub-resources are how REST expresses foreign keys in URLs. The rule: **the path mirrors the relationship graph.**

***

## 3. The CRUD mapping table

This table is the backbone of every REST API you will ever write:

| Operation | Method   | Path                | Success | Body sent        | Body returned                      |
| --------- | -------- | ------------------- | ------- | ---------------- | ---------------------------------- |
| List      | `GET`    | `/users`            | `200`   | —                | array/object of users + pagination |
| Read      | `GET`    | `/users/42`         | `200`   | —                | the user                           |
| Create    | `POST`   | `/users`            | `201`   | the new resource | the created resource (+`Location`) |
| Replace   | `PUT`    | `/users/42`         | `200`   | **all** fields   | the updated resource               |
| Update    | `PATCH`  | `/users/42`         | `200`   | **some** fields  | the updated resource               |
| Delete    | `DELETE` | `/users/42`         | `204`   | —                | — (empty)                          |
| Bulk read | `GET`    | `/users?ids=1,2,3`  | `200`   | —                | the matching users                 |
| Search    | `GET`    | `/users/search?q=…` | `200`   | —                | matching users                     |

Consistency beats cleverness. If `DELETE /users/42` returns `204`, then `DELETE /orders/9` must too.

***

## 4. Response design

### Always return an object, never a bare array

```json
// ❌ Never do this on a list endpoint
[ { "id": 1 }, { "id": 2 } ]

// ✅ Always this
{
  "data": [ { "id": 1 }, { "id": 2 } ],
  "meta": { "page": 1, "limit": 20, "total": 137, "totalPages": 7 }
}
```

Why: adding pagination metadata, a `total`, warnings, or a deprecation notice to a bare array is a breaking change. Wrapping from day one costs one line and saves a migration.

### Pick a field-naming convention and enforce it

`camelCase` (JS idiom) or `snake_case` (SQL idiom) — either is fine, mixing them is not. The most common approach: **camelCase in the API, snake\_case in the database**, with an explicit mapping layer. That keeps your SQL conventional and your JSON conventional, at the cost of a mapping function. (Exposing `user.first_name` while `user.firstName` exists in the DB is a real source of bugs.)

### Dates, times and numbers in JSON

JSON has no date type. Send **ISO 8601 strings, always in UTC, with an explicit marker**:

```json
{
  "createdAt": "2026-09-18T10:15:30.000Z",
  "birthday": "1995-04-02",
  "durationSeconds": 3600,
  "priceInCents": 1499
}
```

| Rule                         | Why                                                                          |
| ---------------------------- | ---------------------------------------------------------------------------- |
| ISO 8601 with `Z`            | Unambiguous; every language parses it; `new Date(str)` works                 |
| UTC, not local time          | The server and client are in different time zones                            |
| Money as integer minor units | Avoids floating-point rounding (`0.1 + 0.2 !== 0.3`)                         |
| Durations in explicit units  | `timeoutMs` beats `timeout`                                                  |
| IDs as strings               | 64-bit ids exceed JavaScript's safe integer range; also keeps id type stable |

That last one surprises people: a MongoDB ObjectId or a big MySQL `BIGINT` is often serialised as a _string_ because `Number.MAX_SAFE_INTEGER` is only 9,007,199,254,740,991.

### The envelope question

Two schools:

```json
// A. Plain resource
{ "id": 42, "name": "Ankit" }

// B. Envelope
{ "success": true, "data": { "id": 42, "name": "Ankit" } }
```

Recommendation: **no envelope for single resources, `{data, meta}` for collections.** The HTTP status code already says whether the request succeeded. Repeating it in a body field (`{"success": true}`) adds noise and creates two sources of truth that will eventually disagree. Collections are the exception because they carry pagination.

### Error shape

A single, consistent error body makes clients simple. Recommend a format close to [RFC 9457 (Problem Details for HTTP APIs)](https://www.rfc-editor.org/rfc/rfc9457.html):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request body is invalid",
    "details": [
      { "field": "email", "message": "must be a valid email address" },
      { "field": "password", "message": "must be at least 8 characters" }
    ],
    "requestId": "8f3c1d2a-4b5e-4c6d-8e7f-1a2b3c4d5e6f"
  }
}
```

Why each part exists:

| Field       | Purpose                                                                                   |
| ----------- | ----------------------------------------------------------------------------------------- |
| `code`      | **Machine-readable**, stable, for client branching (`if (code === 'INSUFFICIENT_STOCK')`) |
| `message`   | Human-readable, may change, may be translated                                             |
| `details[]` | Field-level errors so a form can highlight inputs                                         |
| `requestId` | The support engineer's superpower: "give me the request id" → find the log line           |

Rules: never leak stack traces, SQL errors, or internal hostnames in `message`. Log them with the `requestId`; return the correlation id to the client.

***

## 5. Pagination, filtering, sorting

### Pagination

| Strategy          | Request                         | Pros                                    | Cons                                                                                |
| ----------------- | ------------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------- |
| **Offset/limit**  | `?page=3&limit=20`              | Simple, jump to any page, shows a total | Skips/duplicates if rows are inserted/deleted while paging; `OFFSET 100000` is slow |
| **Cursor/keyset** | `?cursor=eyJpZCI6NDJ9&limit=20` | Stable and fast at any depth            | No random page access; needs an ordered, unique key                                 |
| Offset as skip    | `?skip=40&limit=20`             | Direct match with SQL/Mongo             | Same pitfalls                                                                       |

**Use offset pagination for admin/dashboard UIs** (users want to jump to page 7 and see "137 results"). **Use cursor pagination for infinite-scroll feeds** (users only go forward, and stability matters).

```json
// Offset style response
{
  "data": [ /* … */ ],
  "meta": { "page": 3, "limit": 20, "total": 137, "totalPages": 7,
            "links": { "self": "/users?page=3", "next": "/users?page=4", "prev": "/users?page=2" } }
}
```

Always cap `limit`:

```js
const limit = Math.min(Number(req.query.limit) || 20, 100); // snippet: partial
```

Without a cap, `?limit=1000000` is a denial-of-service attack that makes the database serialise your entire table into memory.

### Filtering

```
GET /products?category=shoes&minPrice=1000&maxPrice=5000&inStock=true
GET /products?tags=red,sale            → comma-separated OR
GET /products?createdAfter=2026-01-01
```

Keep names self-describing (`minPrice`, not `p1`) and document the operators. For very expressive querying, an explicit syntax (`?filter[price][gte]=1000`) is clearer, at the cost of more parsing — and **never pass raw query strings into your query language**, or you have built an injection vulnerability ([02-express/18-security.md](../02-express/18-security.md)).

### Sorting

```
GET /products?sort=-createdAt,price
```

Convention: a leading `-` means descending (this is what Django, DRF and many JS libraries use). **Whitelist the sortable fields** — an unvalidated `sort=; DROP TABLE` is an injection, and `sort=password` leaks ordering information.

```js
// Whitelist approach
const SORTABLE = new Set(['createdAt', 'name', 'price']); // snippet: partial
```

### Field selection and expansion

```
GET /users/42?fields=id,name,email          → return only these fields
GET /orders/987?expand=customer,items       → embed related resources inline
```

These are optional niceties; add them when a client asks, not on day one. Their main value is reducing mobile payload size and eliminating N+1 requests.

***

## 6. Practical hardening of every endpoint

| Concern                 | What to do                                                                    |
| ----------------------- | ----------------------------------------------------------------------------- |
| **Auth**                | Require a token on everything except explicitly public routes                 |
| **Authorisation**       | Check ownership _per resource_, not per route: `order.userId === req.user.id` |
| **Validation**          | Validate body, params **and** query with a schema (Zod/Joi)                   |
| **Rate limiting**       | Per IP and per user; stricter on auth endpoints                               |
| **Idempotency**         | Support `Idempotency-Key` on payment-like POSTs                               |
| **Timeouts**            | Never let a request hang: set DB/query and HTTP timeouts                      |
| **Payload size limits** | `express.json({ limit: '100kb' })` — the default is 100kb for a reason        |
| **Pagination cap**      | `limit ≤ 100`                                                                 |
| **Caching**             | `Cache-Control` for public GETs; `no-store` for anything user-specific        |
| **Correlation ids**     | Generate/propagate `X-Request-Id` in every log line                           |
| **Consistent errors**   | One error middleware, one error shape                                         |
| **CORS**                | Explicit allowlist, never `*` with credentials                                |

***

## 7. REST vs GraphQL vs gRPC

|                     | REST                           | GraphQL                             | gRPC                                   |
| ------------------- | ------------------------------ | ----------------------------------- | -------------------------------------- |
| Transport           | HTTP/1.1 or /2, JSON           | Usually HTTP POST, JSON             | HTTP/2, Protobuf (binary)              |
| Endpoints           | Many (`/users`, `/orders`)     | One (`/graphql`)                    | Many, defined by `.proto`              |
| Over/under-fetching | Common (fixed shapes)          | Solved (client picks fields)        | Fixed but compact                      |
| Caching             | ✅ Awesome (`GET` + CDN + ETag) | ❌ Hard with POST + ad-hoc queries   | ⚠️ Manual                              |
| Browser-friendly    | ✅                              | ✅                                   | ❌ (needs a proxy, e.g. grpc-web)       |
| Best for            | Public APIs, CRUD, caching     | Aggregating many sources for one UI | Internal service-to-service, streaming |
| Learning cost       | Low                            | Medium-high                         | Medium                                 |

**Default recommendation for a beginner backend: REST.** It is the lowest-friction, best-tooled choice, and the skills transfer (HTTP, status codes, auth, validation).

Choose **GraphQL** when many different clients (web, iOS, Android, watch) need different slices of the same graph and you are drowning in bespoke endpoints. Choose **gRPC** for high-throughput internal communication where schema evolution and performance matter more than browser compatibility.

***

## 8. Documenting the API

An undocumented API does not exist. Options, cheapest first:

1. **A `README.md`** with a table of endpoints — start here, always.
2. **OpenAPI (Swagger) spec** — a YAML/JSON description that generates docs _and_ clients _and_ tests.
3. **Swagger UI / Scalar** — an interactive page generated from the spec. Great for frontend teams and for manual testing.
4. **Postman/Bruno collections** — shareable, executable examples.

Minimal OpenAPI fragment:

```yaml
openapi: 3.0.3
info:
  title: Shop API
  version: 1.0.0
paths:
  /api/v1/users/{id}:
    get:
      summary: Fetch one user
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string }
      responses:
        '200': { description: The user }
        '404': { description: Not found }
```

Note the YAML block above is inside a \`\`\`yaml fence — that is why it is not checked as JavaScript by `scripts/verify-docs.mjs`.

***

## 9. Common mistakes

| Mistake                                               | Why it hurts                                 | Do this instead                             |
| ----------------------------------------------------- | -------------------------------------------- | ------------------------------------------- |
| Returning `200` with `{"error": …}`                   | Breaks caching, retries, monitoring          | Use real status codes                       |
| Different error shapes per endpoint                   | Every client needs special cases             | One error contract                          |
| Exposing the database schema directly                 | Table/column renames become breaking changes | A mapping layer; API names are your own     |
| `GET /users` unbounded                                | One request can return 4 million rows        | Always paginate, always cap `limit`         |
| Sending `password`, `passwordHash`, or internal flags | A single leak in logs or a client error      | Explicit response serialisers / DTOs        |
| Auto-increment integer ids everywhere                 | Enumeration ("user 5's data is public!")     | UUIDs/ULIDs for public resources            |
| Trusting the client's `role`/`userId`                 | Trivial privilege escalation                 | Read identity from the verified token       |
| No `Content-Type` check                               | 500s instead of a helpful `415`              | Validate the media type                     |
| Breaking changes without a version bump               | Outages for every consumer                   | URI versioning + deprecation headers        |
| "We'll add tests/docs later"                          | They never happen                            | Test and document as you write the endpoint |

***

## Exercise 5.1 — Review this contract

```http
GET /api/getProductsByCategory?cat=5&num=9999
→ 200 OK
{ "ok": true, "products": [ ... 9999 items ... ], "err": null }
```

Then:

```http
POST /api/deleteProduct
{ "id": 12 }
→ 200 OK
{ "ok": false, "err": "not found" }
```

List every problem and rewrite both.

<details>

<summary>Solution</summary>

**Problems:**

1. **Verb in the URL** (`getProductsByCategory`, `deleteProduct`) — should be nouns + HTTP methods.
2. **No version prefix** — you cannot evolve it.
3. **Unbounded collection** (`num=9999`, no cap) — a performance and memory hazard; also no pagination metadata at all.
4. **`ok: true` duplicating the status code** — two sources of truth.
5. **`err: null` on success** — noise; and a string error is not machine-readable.
6. **`DELETE` implemented as `POST`** — non-idempotent deletion; a retried request could delete the wrong thing later, and caches/proxies will not understand it.
7. **`200 OK` on failure** — the biggest problem: a client must parse bodies to know whether anything worked. Monitoring sees 100% success while the feature is broken.
8. **No `Location`, no resource returned on create** — not shown here, but the same pattern usually omits it.
9. **`cat=5` as an opaque number** — a filter should be a readable name, and multi-value filters should be supported (`?category=shoes&category=boots` or a comma list).
10. **No sorting / field selection** — clients will over-fetch.

**Rewritten:**

```http
GET /api/v1/products?category=shoes&page=1&limit=20&sort=-createdAt
→ 200 OK
{
  "data": [ { "id": "p_5", "name": "Runner", "priceInCents": 12999 } ],
  "meta": { "page": 1, "limit": 20, "total": 1432, "totalPages": 72 }
}
```

```http
DELETE /api/v1/products/12
→ 204 No Content
```

```http
DELETE /api/v1/products/12          (already deleted → idempotent)
→ 404 Not Found
{ "error": { "code": "PRODUCT_NOT_FOUND", "message": "Product 12 does not exist",
             "requestId": "…" } }
```

Both are now idempotent-safe, versioned, bounded, cache-friendly and self-describing.

</details>

## Exercise 5.2 — Is this a breaking change?

For each change to `GET /api/v1/orders/987`, say breaking or not, and why:

1. Adding `"updatedAt"` to the response.
2. Renaming `"total"` to `"totalInCents"`.
3. Changing `"total"` from `149.99` to `14999`.
4. Adding a new optional query parameter `?expand=items`.
5. Removing a field a client depends on but which is not in your docs.
6. Making the endpoint require an `X-API-Key` header it previously ignored.
7. Returning `"id": 987` instead of `"id": "987"`.
8. Making an endpoint faster (200ms → 40ms).

<details>

<summary>Solution</summary>

1. **Not breaking.** Additive; clients that ignore unknown fields are unaffected. (This is why "ignore unknown fields" is a documented rule for clients.)
2. **Breaking.** Any client reading `total` now gets `undefined` — usually rendered as `NaN` or blank. Needs a new version, or a deprecation period where _both_ fields are present.
3. **Breaking.** Same field, different unit and type. Silent 100x errors are worse than crashes. This is exactly why `priceInCents`-style naming is used from day one — the name makes the unit impossible to misinterpret.
4. **Not breaking.** Optional parameters are additive.
5. **Breaking**, and note that the word "docs" is doing a lot of work here: if a client depends on a field, it is part of your de-facto contract even if undocumented. Good APIs watch field usage before removing anything.
6. **Breaking.** Existing clients start receiving `401`. Auth changes on existing endpoints are always breaking.
7. **Breaking.** Type changes break strict clients, and it is a common source of bugs in the opposite direction too (numbers losing precision).
8. **Not breaking.** Performance is not part of the contract — unless a client depended on a delay, which it must not.

</details>

***

## What's next

Concrete representation format time: JSON in detail — syntax, types, the JS/JSON mismatches, and the patterns you will repeat in every endpoint.

→ [06 — JSON and Data Formats](06-json-and-data-formats.md)
