# 03 — HTTP Basics

> **Where this fits:** HTTP is the language your backend speaks. Every Express
> feature — `req.params`, `res.status()`, middleware — is a thin wrapper over the HTTP
> concepts in this chapter. If you understand HTTP properly, Express becomes obvious
> instead of magical.

---

## 1. What is HTTP?

**HTTP (HyperText Transfer Protocol)** is a **text-based request/response protocol**.

- **Text-based**: the messages are human-readable (`GET /users HTTP/1.1`). You can read
  a raw request with your own eyes. (HTTP/2 and HTTP/3 use a binary framing layer
  underneath, but the semantics — methods, status codes, headers — are unchanged.)
- **Request/response**: the client always starts. A server never spontaneously sends
  data to a client over plain HTTP. (Real-time pushes need WebSockets or SSE — see
  §9.)
- **Stateless**: each request is independent. The server keeps no memory of previous
  requests *at the protocol level*. If you need continuity (who is logged in?), you
  implement it yourself with sessions or tokens
  ([07-cookies-sessions-and-state.md](07-cookies-sessions-and-state.md)).

### Why HTTP is designed this way

Being stateless is not a limitation, it is a scaling strategy. Because request #2 does
not depend on request #1 still being handled by the same machine, you can put 20
identical servers behind a load balancer and route each request to whichever is free.
The trade-off is that *you* must carry the state (in a cookie, a token, or a database)
and send it with every request.

---

## 2. Anatomy of a request

```http
POST /api/v1/users?sendWelcome=true HTTP/1.1     ← request line: METHOD PATH VERSION
Host: api.shop.example.com                        ┐
Content-Type: application/json                    │
Content-Length: 61                                │ headers
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...     │
Accept: application/json                          │
User-Agent: curl/8.7.1                            ┘
                                                  ← empty line: "headers end here"
{"name":"Ankit","email":"ankit@example.com"}      ← body (optional, usually JSON)
```

Four parts:

| Part | Example | Notes |
| --- | --- | --- |
| **Method** (verb) | `POST` | *What* kind of action |
| **Path** (+ query string) | `/api/v1/users?sendWelcome=true` | *What* resource |
| **Headers** | `Content-Type: application/json` | *Metadata* about the request |
| **Body** | `{"name":"Ankit"}` | The *data*, only on some methods |

Notice what is *not* in the path: parameters like `page`, `limit`, `sort` — those go in
the query string. Data that creates or modifies a resource goes in the **body**. This
separation is one of the most common review comments on beginner PRs.

### Why an empty line?

HTTP was designed to be parseable line by line. The blank line is the terminator for the
header section: everything after it is the body, and `Content-Length` tells the parser
how many bytes to read. This is literally how you parse HTTP by hand (you will do it in
[01-nodejs/11-http-module.md](../01-nodejs/11-http-module.md), where Node does the
parsing for you).

---

## 3. Anatomy of a response

```http
HTTP/1.1 201 Created                              ← status line: VERSION CODE REASON
Content-Type: application/json; charset=utf-8     ┐
Location: /api/v1/users/64f1a2b3c4d5e6f7a8b9c0d1   │ headers
X-Request-Id: 8f3c1d2a-...                         │
Cache-Control: no-store                            ┘
                                                   ← empty line
{"id":"64f1a2b3c4d5e6f7a8b9c0d1","name":"Ankit"}    ← body
```

The **status code** is a machine-readable outcome, and the **reason phrase** is just
decoration (a modern client ignores `Created`, it only reads `201`).

---

## 4. HTTP methods (verbs)

| Method | Purpose | Body? | Safe? | Idempotent? |
| --- | --- | --- | --- | --- |
| `GET` | Retrieve a representation | No | ✅ | ✅ |
| `HEAD` | Like GET but headers only | No | ✅ | ✅ |
| `POST` | Create a resource / trigger an action | Yes | ❌ | ❌ |
| `PUT` | Replace a resource entirely | Yes | ❌ | ✅ |
| `PATCH` | Partially modify a resource | Yes | ❌ | ❌* |
| `DELETE` | Remove a resource | Usually no | ❌ | ✅ |
| `OPTIONS` | Ask what is allowed (used by CORS preflight) | No | ✅ | ✅ |

Definitions that matter:

- **Safe**: the method must not change state on the server. `GET` must never delete or
  modify anything. This is why search-engine crawlers can follow links without breaking
  your data.
- **Idempotent**: calling it once or ten times has the same effect. `DELETE /users/42`
  is idempotent — the resource ends up deleted either way. The *second* call returns
  `404`, but the state is unchanged. `POST /users` is **not** idempotent — call it five
  times and you may create five users (or get five "duplicate email" errors).
- **`PATCH` and idempotency**: `PATCH` is defined as non-idempotent in general (a patch
  like "increment view count by 1" is not idempotent), but a specific patch such as
  `{"email": "new@x.com"}` happens to be idempotent. That is why the table marks it ❌*
  — the *method* makes no guarantee.

### Why idempotency matters more than you think

Mobile network drops a response? The client retries. If your endpoint was
`POST /payments`, a retry could charge the customer twice. This is why payment APIs
require an **idempotency key** header:

```http
POST /api/v1/payments
Idempotency-Key: 9f3c1d2a-4b5e-4c6d-8e7f-1a2b3c4d5e6f
```

The server stores that key with the result; a retry with the same key returns the
original response instead of charging again. You will implement exactly this pattern in
the production project.

### The PUT vs PATCH question (full answer)

```text
Existing user: { "name": "Ankit", "email": "a@x.com", "role": "user" }

PUT /users/42   { "name": "Ankit Kumar" }
→ Replaces the whole resource. Under strict REST the missing fields are removed
  or reset to defaults → { "name": "Ankit Kumar" }. Dangerous with partial data.

PATCH /users/42 { "name": "Ankit Kumar" }
→ Applies only the given fields → { "name": "Ankit Kumar", "email": "a@x.com", "role": "user" }
```

In practice many teams use `PUT` to mean "update what I sent you, leave the rest"
(technically more like PATCH). That is a **documented deviation**, not a disaster — but
you must decide and document it, because clients depend on it.

---

## 5. Status codes

The first digit is the category:

- **1xx** Informational — rare in application code (`101 Switching Protocols` for
  WebSockets).
- **2xx** Success — the request was understood and completed.
- **3xx** Redirection — you need to look elsewhere.
- **4xx** Client error — *you* (the client) did something wrong.
- **5xx** Server error — *I* (the server) broke.

Memorising the categories means you can reason about a code you have never seen:
`422` is a client error about semantics; `503` is the server being unavailable.

### The codes you will actually use

| Code | Name | Use it when | Gotcha |
| --- | --- | --- | --- |
| `200` | OK | Successful GET, PUT, PATCH, DELETE with a body | — |
| `201` | Created | A new resource was created (POST) | Send `Location: /users/42` header |
| `204` | No Content | Success with nothing to return (often DELETE) | Must not include a body |
| `301`/`308` | Moved Permanently | Permanent redirect | `308` preserves the method and body |
| `302`/`307` | Found / Temporary Redirect | Temporary redirect | `307` preserves the method |
| `304` | Not Modified | Conditional GET, client cache is still valid | Requires `ETag`/`Last-Modified` |
| `400` | Bad Request | Malformed syntax, invalid query params | Do not use for "not found" |
| `401` | Unauthorized | **Not authenticated** — who are you? | Must add `WWW-Authenticate` in strict HTTP |
| `403` | Forbidden | Authenticated but **not allowed** | The classic 401/403 confusion |
| `404` | Not Found | No such resource | Often also used to hide existence of private resources |
| `405` | Method Not Allowed | `PATCH /users` where only GET/POST exist | Include an `Allow` header |
| `409` | Conflict | Duplicate email, version clash | Very common with unique indexes |
| `410` | Gone | Resource existed and was permanently deleted | |
| `413` | Payload Too Large | Body exceeds the parser/upload limit | Your first file-upload bug |
| `415` | Unsupported Media Type | `Content-Type: text/plain` sent to a JSON endpoint | |
| `422` | Unprocessable Content | Syntactically valid JSON, semantically invalid | Zod/Joi validation failures |
| `429` | Too Many Requests | Rate limited | Send `Retry-After` |
| `500` | Internal Server Error | Unhandled exception | Never leak stack traces to clients |
| `502` | Bad Gateway | Proxy could not reach your app | App crashed / wrong port |
| `503` | Service Unavailable | Overloaded or in maintenance | Send `Retry-After` |
| `504` | Gateway Timeout | Proxy waited too long for your app | Slow query, blocking code |

### 401 vs 403 — the interview classic

```text
401 Unauthorized   = "I don't know who you are."  → send credentials (or a valid token)
403 Forbidden      = "I know who you are, and you may not do this."
```

Confusingly, `401` is named "Unauthorized" but means "Unauthenticated". A missing or
expired token → `401`. A valid token belonging to a non-admin hitting an admin endpoint →
`403`.

Design rule: **client errors (4xx) must not be silent successes.** Returning `200` with
`{"error": "not found"}` forces every client to parse bodies to detect failure, and
breaks caching, logging and monitoring. Use the status line for the outcome and the body
for the details.

---

## 6. Headers

Headers are `Name: value` metadata. They are case-insensitive (`Content-Type` ==
`content-type`). Two directions, overlapping names.

### Request headers you will read

| Header | Meaning | Backend use |
| --- | --- | --- |
| `Host` | Which domain the client wanted | Virtual hosting/routing |
| `Content-Type` | Format of the **request body** | Reject non-JSON with `415` |
| `Content-Length` | Body size in bytes | Body parser limits |
| `Authorization` | Credentials, e.g. `Bearer <jwt>` | Auth middleware |
| `Accept` | Formats the client can handle | Content negotiation |
| `Accept-Encoding` | Compression the client supports (gzip, br) | Compression middleware |
| `Cookie` | Cookies the browser stored for this domain | Session lookup |
| `User-Agent` | Client software | Analytics, blocking abusive bots |
| `X-Forwarded-For` | Original client IP when behind a proxy | Rate limiting (with `trust proxy`) |
| `If-None-Match` | Cache validation with an `ETag` | Serving `304` |
| `Origin` | Where the request came from (browsers set it) | **CORS** decisions |

### Response headers you will set

| Header | Meaning | Example |
| --- | --- | --- |
| `Content-Type` | Format of the **response body** | `application/json; charset=utf-8` |
| `Content-Length` | Body size | set automatically by Node |
| `Location` | Where the created/redirected resource is | `/api/v1/users/42` |
| `Set-Cookie` | Ask the browser to store a cookie | `token=…; HttpOnly; Secure; SameSite=Lax` |
| `Cache-Control` | Who may cache and for how long | `private, max-age=60` |
| `ETag` | Fingerprint of the body for caching | `W/"1a2b3c"` |
| `Access-Control-Allow-Origin` | CORS permission | `https://app.example.com` |
| `Retry-After` | Seconds to wait (429/503) | `30` |
| `X-Request-Id` | Correlation id for logs | a UUID you generate per request |

### Custom headers and the `X-` convention

Headers like `X-Request-Id`, `X-RateLimit-Remaining` are application-specific. The `X-`
prefix was a convention for experimental/non-standard headers (RFC 6648 deprecated the
practice, but the ecosystem still uses it heavily).

> **Security note:** a client can send *any* header, including `X-Admin: true`. Never
> authorise based on a client-supplied header. Only `Authorization`/`Cookie` values that
> you cryptographically verify are trustworthy.

---

## 7. Content types and bodies

The body is just bytes. `Content-Type` says how to interpret them:

| Content-Type | Meaning | Typical use |
| --- | --- | --- |
| `application/json` | JSON | 99% of modern REST APIs |
| `application/x-www-form-urlencoded` | `a=1&b=2` | Classic HTML forms |
| `multipart/form-data` | Mixed parts with boundaries | File uploads |
| `text/plain` | Unstructured text | Health checks, debugging |
| `text/html` | HTML | Server-rendered pages |
| `application/octet-stream` | Raw bytes | File downloads |
| `application/xml` | XML | Legacy/SOAP integrations |

If a client sends `text/plain` to an endpoint that only understands JSON, the correct
answer is **`415 Unsupported Media Type`**, not a confusing `400`. Express's
`express.json()` silently ignores non-JSON bodies by default, which is why middleware
that validates `Content-Type` exists.

### Why JSON won (and not XML)

JSON is a subset of JavaScript object literal syntax, so in a JavaScript backend it is a
direct mapping: parse to an object, manipulate, stringify. Compared to XML it is
shorter, has no namespace/attribute complexity, and has native browser support via
`JSON.parse`/`JSON.stringify`. It is also trivially embeddable in other languages.
(JSON's weaknesses — no dates, no comments, no schema — are discussed in
[06-json-and-data-formats.md](06-json-and-data-formats.md).)

---

## 8. HTTP versions, briefly

| Version | Transport | Key characteristics | Practical impact |
| --- | --- | --- | --- |
| HTTP/1.0 | TCP | One connection per request | Slow: a handshake for every asset |
| HTTP/1.1 | TCP | **Keep-alive** by default, pipelining (unused in practice) | Reuses connections; head-of-line blocking at the TCP level |
| HTTP/2 | TCP + TLS (usually) | Binary framing, multiplexing many streams per connection, header compression (HPACK), server push (deprecated) | One connection, many parallel requests |
| HTTP/3 | **QUIC over UDP** | No TCP head-of-line blocking, faster connection setup (0-RTT) | Better on lossy mobile networks |

You rarely choose this — your client and the proxy negotiate it via the `ALPN` TLS
extension. What matters for backend code:

- **Behind HTTP/2 or HTTP/3, `req.protocol` and `req.ip` come from proxy headers**, which
  is why `app.set('trust proxy', …)` exists.
- **Streaming responses are natural on HTTP/1.1 (chunked) and HTTP/2**, which is how
  Server-Sent Events work.

### Keep-alive: the single biggest performance lever you get for free

Creating a TCP connection costs a round trip plus (for HTTPS) a TLS handshake — easily
100ms+ on a mobile network. Reusing one connection for many requests removes that cost.
This is why:

- HTTP clients use **connection pooling** (Node's `fetch`/`undici` does this by default).
- Databases use **connection pools** instead of connecting per query.
- Your server should not close the connection after each response unless it must.

---

## 9. Beyond request/response: WebSockets and SSE

REST is pull-based. For chat, live notifications, or progress bars you need push:

| | Server-Sent Events (SSE) | WebSockets | Polling (REST) |
| --- | --- | --- | --- |
| Direction | Server → client only | Bi-directional | Client asks repeatedly |
| Protocol | Plain HTTP (`text/event-stream`) | `ws://` / `wss://` upgrade from HTTP | HTTP |
| Complexity | Very low | Medium | Lowest |
| Auto-reconnect | Built in | You implement | N/A |
| Use for | Notifications, feeds, progress | Chat, games, collaboration | Simple, infrequent updates |

**Start with polling.** It is trivially debuggable and often good enough. Move to SSE for
one-way push and WebSockets only when you need low-latency two-way traffic.

---

## 10. Reading raw HTTP with your own hands

The fastest way to stop being confused by HTTP is to look at it directly.

```bash
# Full request/response dump
curl -v https://jsonplaceholder.typicode.com/posts/1

# Send your own headers and a JSON body
curl -X POST https://jsonplaceholder.typicode.com/posts \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: demo-123" \
  -d '{"title":"hello","userId":1}'

# Talk raw HTTP to a local server with netcat — no library involved
printf 'GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' | nc localhost 3000
```

The `nc` example is worth doing once: it proves the request really is just text, and it
will help enormously when you write the raw Node HTTP server chapter.

### Inspecting from the browser

Open DevTools → **Network** tab → click any request. You see:

- **Headers** — request and response headers, exactly as sent.
- **Payload** — what the browser sent (`req.body` on the server).
- **Response** — what the server returned.
- **Timing** — DNS, TCP, TLS, waiting (TTFB), download. `Waiting (TTFB)` is your
  *server processing time* — if it is 2 seconds, the problem is your backend, not the
  network.

---

## 11. Common mistakes

| Mistake | Why it is wrong | Correct approach |
| --- | --- | --- |
| `GET /deleteUser/42` | GET must be safe; crawlers/prefetchers will delete data | `DELETE /users/42` |
| Returning `200` for errors | Clients, caches and monitors cannot detect failure | Use real 4xx/5xx codes |
| Using `400` for everything | Hides whether the syntax or the semantics were bad | `400` syntax, `422` validation, `404` missing |
| Putting data in the wrong place | `POST /users/42?name=x` mixes concerns | Params in the path, filters in the query, data in the body |
| Sending a body with `GET` | Undefined behaviour; some proxies drop it | Use query params or switch to `POST` |
| Forgetting `Content-Type` on a JSON response | Clients may guess, browsers may download the file | `res.json()` sets it; do the same with `res.send` |
| Leaking stack traces in `500` responses | Reveals file paths, dependencies, sometimes secrets | Log internally, return a generic message |
| Trusting `X-Forwarded-For` blindly | Anyone can spoof it unless your proxy overwrites it | Configure `trust proxy` for your exact topology |
| Inventing status codes (`299`) | Nobody knows what it means | Use standard codes |

---

## Exercise 3.1 — Choose the status code

For each scenario, pick the code and say why:

1. `GET /api/v1/orders/999` — no order with that id exists.
2. `POST /api/v1/users` — the email is already registered.
3. `GET /api/v1/admin/stats` — the caller has no `Authorization` header.
4. `GET /api/v1/admin/stats` — the caller has a valid token for a non-admin user.
5. `POST /api/v1/users` — body is `{"email": "not-an-email"}`.
6. `DELETE /api/v1/orders/42` — deleted successfully, nothing to return.
7. `GET /api/v1/products` — this IP has made 400 requests in the last minute.
8. `POST /api/v1/orders` — the payment provider is down.

<details>
<summary>Solution</summary>

1. **404 Not Found** — the resource does not exist.
2. **409 Conflict** — the request conflicts with the current state of the resource (a
   unique constraint). `400` is acceptable but loses information.
3. **401 Unauthorized** — no credentials were supplied. Include `WWW-Authenticate: Bearer`.
4. **403 Forbidden** — identity is known, permission is not granted.
5. **422 Unprocessable Content** — valid JSON, invalid semantics. (Many teams use `400`
   with a field-level error list; both are defensible, be consistent.)
6. **204 No Content** — success with no body. (Returning `200 {"success":true}` is also
   common; `204` is the cleaner contract.)
7. **429 Too Many Requests** — include `Retry-After: 60`.
8. **503 Service Unavailable** — a dependency is unavailable. **Do not** return `500`:
   `503` tells clients and load balancers "this is temporary, retry later", and prevents
   a retry storm from being read as your own bug. Include `Retry-After`.

Bonus: in case 8, if you *can* accept the order and process payment asynchronously, the
better answer is **202 Accepted** plus a job queue — that is a real architecture decision
covered in 03-databases/05-redis/03-rate-limiting-queues-pubsub.md *(not available in this published source revision)*.

</details>

## Exercise 3.2 — Fix the API design

A team exposes these endpoints. List the problems and give a corrected design.

```text
POST   /getAllUsers
POST   /createNewUser
GET    /deleteUser?id=42
POST   /updateUserEmail/42?email=x@y.com
GET    /user/42
```

<details>
<summary>Solution</summary>

**Problems:**

1. `POST /getAllUsers` uses a verb in the URL and a non-safe method for a read. Should be
   `GET /users`.
2. `POST /createNewUser` — verb, and "New" is implied by POST. Should be `POST /users`.
3. `GET /deleteUser` — **dangerous**: GET must be safe. Browsers, crawlers and prefetch
   proxies will happily trigger it.
4. `POST /updateUserEmail/42?email=…` — verb in the URL, and mixing a resource
   identifier (path) with the new value (should be the body).
5. `GET /user/42` vs `/getAllUsers` — inconsistent pluralisation (`user` vs `Users`).
   Pick one convention (plural nouns).

**Corrected:**

```text
GET    /api/v1/users             → list
POST   /api/v1/users             → create  (201 + Location: /api/v1/users/42)
GET    /api/v1/users/42          → read one
PATCH  /api/v1/users/42          → partial update   (body: {"email":"x@y.com"})
DELETE /api/v1/users/42          → delete   (204)
```

The rule of thumb: **URLs name things, methods say what to do with them.**

</details>

---

## What's next

HTTP gives you methods, headers and status codes. Now we look at the *addressing* part in
detail: the pieces of a URL, and how to organise endpoints into a coherent API.

→ [04 — URLs, Endpoints and Routing](04-urls-endpoints-and-routing.md)
