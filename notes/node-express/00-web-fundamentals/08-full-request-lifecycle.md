# 08 — The Full Request Lifecycle

> **Where this fits:** This chapter is the summary of everything in
> `00-web-fundamentals`. It follows one realistic request from a button click to a
> rendered row, naming every component it touches. Come back to this chapter whenever
> something "doesn't work" — it is the map you use to find out *which* layer is lying to
> you.

---

## 1. The scenario

Our application: an employee management system.

- Frontend SPA on `https://app.acme.com` (Vite + React, or plain JS — it does not
  matter).
- Backend API on `https://api.acme.com` (Node.js + Express, behind nginx/Cloudflare).
- PostgreSQL (or MongoDB) behind the API, not exposed to the internet.
- Redis for sessions/caching/rate limiting.

The user, **Priya**, a manager, opens the "Employees" page and clicks **Page 2**. Her
browser must fetch `GET /api/v1/employees?page=2&limit=20&sort=-createdAt`.

We will follow that request in 12 stages.

---

## 2. Stage by stage

### Stage 1 — The click (frontend)

```js
// File: client/employees.js (runs in Priya's browser)
async function loadPage(page) {
  const response = await fetch(`/api/v1/employees?page=${page}&limit=20&sort=-createdAt`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include', // send the HttpOnly session/refresh cookie
  });

  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw new Error(problem?.error?.message ?? `Request failed: ${response.status}`);
  }

  const { data, meta } = await response.json();
  renderTable(data, meta);
}

loadPage(2).catch((error) => showToast(error.message));
```

Three details that matter:

- `credentials: 'include'` — without it, cross-origin cookies are not sent (see
  [Exercise 7.2](07-cookies-sessions-and-state.md)).
- The frontend checks `response.ok`. **Fetch does not reject on 4xx/5xx** — a very common
  beginner assumption.
- The URL is relative (`/api/v1/...`). In production an nginx/CDN rule maps `/api/*` to
  the backend; in development Vite's proxy does the same. This keeps the browser
  same-origin (so `SameSite` cookies work) and avoids CORS entirely.

### Stage 2 — Browser → network

The browser:

1. Checks the HTTP cache (`Cache-Control`, `ETag`). A cached `200` can be reused —
   in that case the story ends here with a **200 from disk/memory cache**.
2. Resolves `app.acme.com` via DNS (cached for the record's TTL).
3. Opens or reuses a TCP connection (keep-alive) and, for HTTPS, a TLS session.
4. Builds the request and adds headers it owns: `Host`, `User-Agent`, `Accept`,
   `Accept-Encoding`, `Cookie`, and — because it is a `GET` from the same origin —
   nothing else.

```http
GET /api/v1/employees?page=2&limit=20&sort=-createdAt HTTP/1.1
Host: app.acme.com
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) …
Accept: application/json
Cookie: sessionId=9f3c1d2a…; csrfToken=…
```

### Stage 3 — The reverse proxy / edge

The request hits Cloudflare or an nginx container — not your Node process.

The proxy:

1. Accepts the TLS connection and decrypts it (TLS termination).
2. May serve the response from its cache if the response was cacheable and this is a
   `GET` (our per-user response will be `Cache-Control: private`, so no).
3. Applies edge rules: WAF, IP allow/deny, rate limits, bot protection.
4. Adds/propagates the client's real IP in `X-Forwarded-For` and `X-Forwarded-Proto`.
5. Selects an upstream (one of your Node instances) via round-robin/least-connections.
6. Forwards plain HTTP to `http://10.0.1.7:3000/api/v1/employees?…` and waits, with a
   timeout (e.g. `proxy_read_timeout 30s`).

```text
Cloudflare / nginx
      │  X-Forwarded-For: 203.0.113.42
      │  X-Forwarded-Proto: https
      ▼
Node.js instance #3 (10.0.1.7:3000)
```

This is why production code contains:

```js
// File: src/app.js (fragment — the whole file comes in the Express section)
app.set('trust proxy', 1);
```

Without it, `req.ip` is the proxy's IP (so rate limiting would throttle *everyone*), and
`req.protocol` is `http`, so `req.secure` is `false` and secure-cookie logic misbehaves.

### Stage 4 — Node.js accepts the connection

Node's `net` layer has the socket. `http` parses the bytes into `IncomingMessage`.

> **Internally:** Node's event loop is notified that the socket has data (via `epoll`/
> `kqueue`/`IOCP`), the request is parsed incrementally as bytes arrive, and once the
> headers (and body, if any) are complete, Node emits a `request` event that Express
> listens for. Nothing blocks; thousands of other sockets are handled by the same thread
> between these steps. Full mechanics:
> [01-nodejs/14-event-loop.md](../01-nodejs/14-event-loop.md).

### Stage 5 — Express routing

```text
GET /api/v1/employees?page=2&limit=20&sort=-createdAt
        │
        ├── app-level middleware (in registration order)
        │     ├── requestId()        → req.id = uuid
        │     ├── requestLogger()    → start timer, log "→ GET /api/v1/employees"
        │     ├── helmet()           → security headers
        │     ├── cors()             → CORS headers (no-op for same-origin)
        │     ├── rateLimiter()      → 100 req/min per IP; 429 if exceeded
        │     ├── express.json()     → parse body (none here — GET)
        │     └── cookieParser()     → req.cookies
        │
        └── router mounted at /api/v1
              └── employees router
                    └── route: GET '/'  → authenticate → authorise('employee:read') → validateQuery → controller
```

Routing itself is a match on **method + path pattern**; query parameters do not affect
matching. See [00-web-fundamentals/04](04-urls-endpoints-and-routing.md).

If no route matches, control reaches the 404 handler at the bottom of `app.js` — and if
the request produces a `404` in **production**, that fact alone means the URL is wrong,
not your logic.

### Stage 6 — Middleware does its job

In order:

```js
// File: src/middleware/authenticate.js
export function authenticate(req, res, next) {
  const sessionId = req.cookies?.sessionId;
  if (!sessionId) {
    return res.status(401).json({
      error: { code: 'UNAUTHENTICATED', message: 'Sign in to continue' },
    });
  }
  req.user = { id: 'u_17', email: 'priya@acme.com', role: 'manager' }; // look up in the store
  return next();
}
```

```js
// File: src/middleware/validate.js
import { z } from 'zod';

const listQuerySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  sort: z.enum(['createdAt', '-createdAt', 'name', '-name']).default('-createdAt'),
});

export const validateQuery = (schema) => (req, res, next) => {
  const result = schema.safeParse(req.query); // ← note: req.query is all STRINGS
  if (!result.success) {
    return res.status(422).json({
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid query parameters',
        details: result.error.issues.map((issue) => ({
          field: issue.path.join('.'),
          message: issue.message,
        })),
      },
    });
  }
  req.validatedQuery = result.data; // validated + typed: { page: 2, limit: 20, sort: '-createdAt' }
  return next();
};
```

Two lessons embedded here:

- `?page=2` arrives as the **string** `"2"`; `z.coerce.number()` converts it. Without
  coercion, `page + 1` would produce `"21"`.
- Validation failures are `422` with a structured body — not a `500`.

### Stage 7 — Controller: HTTP in, service call out

```js
// File: src/controllers/employeeController.js
import * as employeeService from '../services/employeeService.js';

export async function listEmployees(req, res, next) {
  try {
    const { page, limit, sort } = req.validatedQuery;

    const { rows, total } = await employeeService.list({
      page,
      limit,
      sort,
      requester: req.user, // authorisation context — never from the request body
    });

    res.status(200).json({
      data: rows.map(toEmployeeDto),
      meta: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (error) {
    next(error); // async errors MUST be forwarded — see the Express error chapter
  }
}

function toEmployeeDto(employee) {
  return {
    id: String(employee.id),
    name: employee.name,
    department: employee.department,
    createdAt: employee.created_at.toISOString(),
  };
}
```

The controller's only jobs: read the request, call the service, shape the response,
forward errors. **No SQL, no business rules.**

### Stage 8 — Service: the business rules

```js
// File: src/services/employeeService.js
import * as employeeRepo from '../repositories/employeeRepository.js';

export async function list({ page, limit, sort, requester }) {
  // Business rule: a manager sees only their department; admins see everything.
  const filters = requester.role === 'admin' ? {} : { departmentId: requester.departmentId };

  const offset = (page - 1) * limit;

  // Run count and page in parallel — two independent queries, one await.
  const [rows, total] = await Promise.all([
    employeeRepo.findMany({ ...filters, limit, offset, sort }),
    employeeRepo.count(filters),
  ]);

  return { rows, total };
}
```

This is where authorisation-as-a-rule lives ("managers see their department"), where
workflow lives ("an employee cannot approve their own leave"), and where you decide
transaction boundaries.

### Stage 9 — Repository: the query

```js
// File: src/repositories/employeeRepository.js
import { pool } from '../database/pool.js';

const SORT_MAP = {
  createdAt: 'created_at ASC',
  '-createdAt': 'created_at DESC',
  name: 'name ASC',
  '-name': 'name DESC',
};

export async function findMany({ departmentId, limit, offset, sort }) {
  const orderBy = SORT_MAP[sort] ?? 'created_at DESC'; // whitelist → never interpolate user input
  const params = [];
  let where = '';

  if (departmentId) {
    params.push(departmentId);
    where = `WHERE department_id = $${params.length}`; // parameterised, always
  }

  params.push(limit, offset);
  const sql = `
    SELECT id, name, department_id, created_at
    FROM employees
    ${where}
    ORDER BY ${orderBy}
    LIMIT $${params.length - 1} OFFSET $${params.length}
  `;

  const { rows } = await pool.query(sql, params);
  return rows;
}

export async function count({ departmentId }) {
  const params = departmentId ? [departmentId] : [];
  const where = departmentId ? 'WHERE department_id = $1' : '';
  const { rows } = await pool.query(`SELECT COUNT(*)::int AS total FROM employees ${where}`, params);
  return rows[0].total;
}
```

Note the two security patterns: **values are parameterised** (`$1`, `$2`) and **`ORDER BY`
comes from a whitelist** — because column names cannot be parameterised.

### Stage 10 — The database does the work

```text
PostgreSQL receives:
  SELECT id, name, department_id, created_at
  FROM employees WHERE department_id = 4
  ORDER BY created_at DESC LIMIT 20 OFFSET 20;

  1. Parse → 2. Plan (is there an index on department_id? on created_at?) →
  3. Execute → 4. Return rows over the connection

  With an index on (department_id, created_at DESC) this is a fast index scan.
  Without one it is a sequential scan of the whole table plus a sort — the classic
  "it worked with 1,000 rows and died at 1,000,000" story.
```

The connection is not new: it comes from the **pool**
(03-databases/03-mysql/12-connection-pooling.md *(not available in this published source revision)*).
Opening a connection costs milliseconds; pooling makes it ~microseconds.

### Stage 11 — Response is built and sent

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Cache-Control: private, max-age=30
X-Request-Id: 8f3c1d2a-4b5e-4c6d-8e7f-1a2b3c4d5e6f
Content-Length: 412

{"data":[{"id":"41","name":"Ravi Sharma","department":"Engineering","createdAt":"2026-08-02T09:12:00.000Z"}],"meta":{"page":2,"limit":20,"total":137,"totalPages":7}}
```

Then:

- The logger middleware writes one line: `← 200 GET /api/v1/employees 18ms`.
- Metrics record the latency and status code for dashboards.
- The proxy streams the bytes back to the client, possibly compressing them.
- Node keeps the TCP connection open for the next request (keep-alive).

### Stage 12 — Back in the browser

`fetch` resolves, `response.ok` is `true`, `res.json()` parses the body, and
`renderTable(data, meta)` paints 20 rows. Priya sees page 2 of her employees.

If *any* stage failed, the client would see a status code and an error body — and the
`X-Request-Id` is the thread that leads support straight to the exact log line on the
server.

---

## 3. The whole thing in one diagram

```text
 Priya clicks "Page 2"
        │
        ▼
┌───────────────────────────────┐
│ BROWSER                       │
│  fetch('/api/v1/employees…')  │  ① relative URL, credentials: include
│  cookies attached automatically│
└──────────────┬────────────────┘
               │ DNS → TCP → TLS → HTTP/1.1 request
               ▼
┌───────────────────────────────┐
│ EDGE / REVERSE PROXY (nginx)  │  ② TLS termination, WAF, rate limit,
│                               │     X-Forwarded-* headers, upstream choice
└──────────────┬────────────────┘
               │ plain HTTP to a private IP
               ▼
┌───────────────────────────────┐
│ NODE.JS + EXPRESS             │
│  ③ routing                    │  ④ middleware: id, log, helmet, cors,
│  ⑤ authenticate + validate    │     json, cookies, rate limit
│  ⑥ controller                 │     ── reads req, calls service
│  ⑦ service                    │     ── business rules, authorisation
│  ⑧ repository                 │     ── builds a parameterised query
└──────────────┬────────────────┘
               │ pooled connection (never per-request)
               ▼
┌───────────────────────────────┐
│ DATABASE (PostgreSQL/Mongo)   │  ⑨ index scan, 20 rows, total count
└──────────────┬────────────────┘
               │
               ▼
   ⑩ rows → DTO → JSON → status 200 + Cache-Control + X-Request-Id
               │
               ▼
       proxy → browser → renderTable() → Priya sees 20 rows
```

---

## 4. The failure map — how to debug fast

This table is the practical payoff of the whole chapter. When something breaks, find the
symptom, then look at the layer. **Do not guess; the symptom usually names the layer.**

| Symptom | Most likely layer | First action |
| --- | --- | --- |
| `ERR_NAME_NOT_RESOLVED`, `ENOTFOUND` | DNS | Check the hostname, then `dig` it |
| `ERR_CONNECTION_REFUSED`, `ECONNREFUSED` | TCP | Is the process running? Right port? Bound to `0.0.0.0`? |
| `ERR_CONNECTION_TIMED_OUT`, `ETIMEDOUT` | Network/firewall | Security group, VPC, proxy upstream |
| `ERR_CERT_DATE_INVALID` | TLS | Certificate renewal |
| `404` | Routing | Compare the exact URL and method with the route table |
| `405` | Routing | The path exists, the method does not — check the `Allow` header |
| `401` | Auth | Token/cookie missing, expired, or the client is not sending credentials |
| `403` | Authorisation | Rights are too narrow for this user, or the resource belongs to someone else |
| `400` / `422` | Validation | Read the `details[]` array — it names the failing field |
| `413` | Body parser limit | Raise `express.json({ limit })` or use file uploads |
| `415` | Content-Type | Client sent a non-JSON content type |
| `429` | Rate limiting | Check limits; a shared IP/proxy may be the cause |
| HTML `Cannot GET /x` | Express 404 | No matching route, or the router is mounted at the wrong prefix |
| `500` | Your code | Read the server log with the `X-Request-Id` |
| `502` | Proxy → app | The app crashed or is not listening on the expected port |
| `504` | Proxy timeout | Your handler is too slow; check for a missing index or blocking code |
| Works locally, fails deployed | Configuration | Env vars, `NODE_ENV`, trust proxy, DB host, port binding |
| Works for 1 hour, then 401s | Tokens/clock | Access-token expiry, mismatched server clocks, session TTL |
| Works for small data, slow/500 for big | Database | Missing index, unbounded query, N+1 queries, missing pagination |
| Intermittent failures at high load | Concurrency | Connection pool exhaustion, unhandled promise rejection, memory leak |

**The single most useful debugging habit:** get the `X-Request-Id` (or the timestamp) from
the user, then read the corresponding server log line, which should contain the route,
status, duration and any error stack. Every codebase you work in should have that. If it
does not, add it — that is exactly the kind of thing the rest of these notes teaches you
to build.

---

## 5. Complete exercise: trace it yourself

Pick any public API you use. Run:

```bash
curl -v -H "Accept: application/json" "https://api.github.com/users/octocat"
```

Then write down, for your own notes:

1. The resolved IP and port.
2. The exact request line and at least four request headers.
3. The exact status line and at least four response headers.
4. Which headers tell you about caching (`Cache-Control`, `ETag`, `Age`).
5. Which headers tell you about rate limiting (`X-RateLimit-*`).
6. What a `404` looks like for that API (`/users/this-user-does-not-exist-xyz`) — the body
   shape is the API's error contract in action.

<details>
<summary>What you should observe (GitHub's API as an example)</summary>

- `* Trying 140.82.x.x:443…` → the DNS answer and the TCP attempt.
- `* Connected to api.github.com (140.82.x.x) port 443` → TCP established.
- `* Server certificate: subject: CN=*.github.com; issuer: …` → TLS verified, and the
  name matches.
- `> GET /users/octocat HTTP/2` with `> accept: application/json`, `> host: api.github.com`,
  `> user-agent: curl/…` — note `HTTP/2`: curl negotiated it via ALPN, transparently.
- `< HTTP/2 200`, `< content-type: application/json; charset=utf-8`,
  `< cache-control: public, max-age=60, s-maxage=60`,
  `< etag: W/"…"`, `< x-ratelimit-limit: 60`, `< x-ratelimit-remaining: 57`,
  `< x-github-media-type: …`.
- A `404` body from GitHub is a **JSON object with a `message` field** — a consistent error
  contract, exactly like the one designed in
  [05-rest-and-api-design.md](05-rest-and-api-design.md).

The exercise is worth doing more than once, on APIs you know. You will start to *see* the
design decisions behind them: whether they paginate with links, whether errors are
structured, whether they version in the path, whether they cap page sizes.

</details>

---

## 6. What you can now do

If everything above made sense, you are ready for Node.js. You can:

- Name every layer a request passes through and what each one is responsible for.
- Predict which status code an API should return for any situation.
- Design resource-oriented URLs and consistent response bodies.
- Explain statelessness, sessions, tokens, CSRF and CORS to another developer.
- Diagnose a failure by symptom instead of guessing.

Those five abilities are what separate "I can write a route" from "I can be trusted with a
production service".

---

## What's next

Time to build. In [01-nodejs/01-introduction.md](../01-nodejs/01-introduction.md) we meet
the runtime: what Node.js actually is, why it was created, and how its architecture makes
the "thousands of concurrent connections" story in Stage 4 possible.

→ [Node.js — 01 Introduction](../01-nodejs/01-introduction.md)
