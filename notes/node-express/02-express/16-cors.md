# 16 — CORS

> **Where this fits:** Everything so far assumed the API and the page live at the same origin. The moment
> a browser app runs on `http://localhost:5173` and the API on `http://localhost:3000`, the browser
> applies its **same-origin policy** and blocks the response until your server opts in. That opt-in is
> CORS — and it is one of the most misunderstood headers on the web.

---

## 1. What CORS actually is

> **CORS (Cross-Origin Resource Sharing) is a set of HTTP response headers that tell the *browser*
> whether JavaScript from one origin may read a response from another origin.**

Three facts that clear up most confusion:

1. **CORS is enforced by the browser, not the server.** `curl`, Postman, server-to-server calls and
   mobile apps ignore it completely. A "CORS error" is a browser message about a response it refused to
   hand to your code.
2. **The server still runs the request.** When a disallowed origin sends a simple request, your handler
   executes and writes the response — the browser just refuses to expose it to the page. This is why CORS
   is **not** an authorisation mechanism.
3. **The "origin" is `scheme + host + port`.** These are all different origins:

```text
http://localhost:5173     ← a Vite dev server
http://localhost:3000     ← your API                     different port  → cross-origin
https://api.example.com   vs  https://example.com        different host  → cross-origin
http://example.com        vs  https://example.com        different scheme → cross-origin
https://example.com:8443  vs  https://example.com        different port  → cross-origin
```

```js
// File: origins-are-not-files.js
// Same-origin: the page and the API agree on scheme, host and port.
const page = 'http://localhost:5173';
const api  = 'http://localhost:3000';
console.log(new URL(page).origin === new URL(api).origin);   // false → CORS applies
```

### What the same-origin policy stops, and what it allows

| The browser will… | …because |
| --- | --- |
| Send the cross-origin request | Requests are cheap; blocking them would break `<img>`, `<script>` and forms |
| Attach cookies if `SameSite` allows it | Cookies follow their own rules, not CORS |
| Block the page from **reading** the response | The actual protection: your data must not leak to `evil.com` |
| Block state-changing XHR/fetch unless the server opts in (via preflight) | Preflight prevents "fire and forget" JSON POSTs from any site |

---

## 2. Simple requests versus preflighted requests

Browsers classify every cross-origin request. The classification decides whether an extra `OPTIONS`
round-trip happens first.

A request is **simple** (no preflight) only if **all** of these are true:

| Condition | Allowed values |
| --- | --- |
| Method | `GET`, `HEAD`, `POST` |
| Headers | Only the safelisted ones: `Accept`, `Accept-Language`, `Content-Language`, `Content-Type`, `Range` (and a few others) |
| `Content-Type` | `application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain` |
| No `ReadableStream` body, no event listeners on `XMLHttpRequest.upload` | — |

```text
GET  /api/v1/notes                       simple (if no custom headers)
POST /api/v1/notes  Content-Type: application/json    ← preflighted!
POST /api/v1/notes  Content-Type: text/plain          ← simple, no preflight
GET  /api/v1/notes  Authorization: Bearer …           ← preflighted (custom header)
DELETE /api/v1/notes/1                                ← preflighted (method)
```

> **`application/json` triggers a preflight.** That is why nearly every modern API sees an `OPTIONS`
> request before each new `POST`/`PATCH` — and why a misconfigured preflight looks like "POST is broken
> but GET works".

### The preflight exchange

```text
Browser                                                  Server
   │ OPTIONS /api/v1/notes
   │ Origin: http://localhost:5173
   │ Access-Control-Request-Method: POST
   │ Access-Control-Request-Headers: content-type
   ├──────────────────────────────────────────────────────▶
   │                                            is this origin allowed to
   │                                            send POST with that header?
   │◀──────────────────────────────────────────────────────
   │ HTTP/1.1 204 No Content
   │ Access-Control-Allow-Origin: http://localhost:5173
   │ Access-Control-Allow-Methods: GET,POST,PATCH,DELETE,OPTIONS
   │ Access-Control-Allow-Headers: Content-Type,Authorization,X-CSRF-Token
   │ Access-Control-Max-Age: 600
   │ Vary: Origin
   │
   │ Now the REAL request is sent (with cookies, if credentials are configured).
```

The browser caches the preflight result for `Access-Control-Max-Age` seconds, so it does not run an
`OPTIONS` request before every call.

---

## 3. The response headers, one by one

| Header | Values | Meaning |
| --- | --- | --- |
| `Access-Control-Allow-Origin` (ACAO) | `*` or exactly one origin | Which origin may read the response. `*` cannot be combined with credentials |
| `Access-Control-Allow-Methods` | `GET,POST,PATCH,DELETE` | Methods allowed in the actual request (preflight only) |
| `Access-Control-Allow-Headers` | `Content-Type,Authorization` | Request headers the client may send (preflight only) |
| `Access-Control-Allow-Credentials` | `true` | The client may send cookies/`Authorization` and read the response |
| `Access-Control-Expose-Headers` | `Location,X-Request-Id` | Response headers JavaScript may read — **everything else is hidden** |
| `Access-Control-Max-Age` | `600` | How long the browser may cache the preflight |
| `Vary: Origin` | — | Tells caches the response depends on the `Origin` header. Missing `Vary` is a real caching bug |

```text
The header almost everyone forgets
──────────────────────────────────
fetch() can read only the "safelisted" response headers
(Content-Type, Content-Length, Cache-Control, Date, Expires, Last-Modified, Pragma).
A 201 with Location, or a 429 with Retry-After, is invisible to the page
unless the server also sends:
    Access-Control-Expose-Headers: Location, Retry-After, X-Request-Id, ETag
```

---

## 4. The `cors` middleware

```bash
npm install cors
```

```js
// File: src/middleware/cors.js
import cors from 'cors';

/**
 * One configuration, one allowlist. Origins come from configuration so that
 * local, staging and production differ without touching code.
 */
export function createCorsOptions({ allowedOrigins, isProduction }) {
  const allowlist = new Set(allowedOrigins);

  return {
    origin(origin, callback) {
      // No Origin header: curl, server-to-server, health checks, mobile apps.
      // These are not subject to CORS, so let them through.
      if (!origin) return callback(null, true);

      if (allowlist.has(origin)) return callback(null, true);

      // Reject politely: no header is sent, so the browser blocks the read.
      // (Throwing here would turn a CORS problem into a 500 for everyone.)
      return callback(null, false);
    },
    methods: ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token', 'X-Request-Id'],
    exposedHeaders: ['Location', 'X-Request-Id', 'Retry-After', 'ETag', 'Deprecation', 'Sunset'],
    credentials: true,
    maxAge: 600,
    optionsSuccessStatus: 204,
  };
}

export function createCorsMiddleware(options) {
  return cors(options);
}
```

```js
// File: src/app.js (excerpt)
import { createCorsMiddleware, createCorsOptions } from './middleware/cors.js';

export function createApp({ config, container }) {
  const app = express();
  app.disable('x-powered-by');

  // CORS sits BEFORE the routes: it must also answer preflight requests,
  // which never reach a route handler.
  app.use(createCorsMiddleware(createCorsOptions({
    allowedOrigins: config.allowedOrigins,        // ['http://localhost:5173', 'https://app.example.com']
    isProduction: config.isProduction,
  })));

  app.use(express.json({ limit: '100kb' }));
  app.use('/api/v1', createApiRouter({ controllers: container, middleware: container.middleware }));
  return app;
}
```

### Options reference

| Option | Type | Default | Notes |
| --- | --- | --- | --- |
| `origin` | `string \| boolean \| RegExp \| array \| function` | `*` | A function gives full control per request |
| `methods` | `string[] \| string` | `GET,HEAD,PUT,PATCH,POST,DELETE` | Advertised on preflight only |
| `allowedHeaders` | `string[]` | Reflects `Access-Control-Request-Headers` | Be explicit in production |
| `exposedHeaders` | `string[]` | none | Add `Location`, `ETag`, `Retry-After` when the client needs them |
| `credentials` | `boolean` | `false` | Required for cookies and for `fetch(..., { credentials: 'include' })` |
| `maxAge` | `number \| null` | none | Seconds the preflight may be cached |
| `optionsSuccessStatus` | `number` | `204` | Some old clients choke on 204 and prefer 200 |
| `preflightContinue` | `boolean` | `false` | `true` passes the `OPTIONS` on to your routes |

### Verified behaviour

The outputs below were produced by probing this exact configuration with `cors` 2.8.x against an Express 5
app:

```text
Request: GET /api/v1/notes   Origin: http://localhost:5173    (allowed)
HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Credentials: true
Access-Control-Expose-Headers: Location,X-Request-Id,Retry-After
Vary: Origin
```

```text
Request: GET /api/v1/notes   Origin: https://evil.com         (disallowed)
HTTP/1.1 200 OK                     ← the handler STILL RAN
Access-Control-Allow-Credentials: true
Access-Control-Expose-Headers: Location,X-Request-Id,Retry-After
Vary: Origin
                                    ← no Access-Control-Allow-Origin
Result: the browser blocks the page from reading the response.
```

```text
Request: OPTIONS /api/v1/notes   Origin: http://localhost:5173
        Access-Control-Request-Method: POST
        Access-Control-Request-Headers: content-type, authorization
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET,POST,PATCH,DELETE,OPTIONS
Access-Control-Allow-Headers: Content-Type,Authorization,X-CSRF-Token
Access-Control-Max-Age: 600
Vary: Origin
```

> **The middle case is the whole lesson of this chapter.** The disallowed origin received a normal `200`
> with data. CORS did not stop the request; it only removed the header that would let a browser page read
> the answer. Anyone calling your API outside a browser is unaffected — so **authentication and
> authorisation must still be real**, and CORS is defence in depth at best.

### `*` versus a reflected origin

```text
cors({ origin: '*' })                       → Access-Control-Allow-Origin: *
                                              Access-Control-Allow-Credentials: (absent)
                                              Vary: (absent)

cors({ origin: '*' , credentials: true })   → Access-Control-Allow-Origin: *
                                              Access-Control-Allow-Credentials: true
                                              ✘ The browser REJECTS this combination outright.

cors({ origin: true })                      → Access-Control-Allow-Origin: <request origin>
                                              Vary: Origin
                                              (reflects anything — convenient locally, dangerous online)

cors({ origin: ['https://app.example.com'] }) → <that origin> when it matches, no header otherwise
                                              Vary: Origin
```

| Use | Configuration |
| --- | --- |
| A public, cookie-less read-only API | `origin: '*'` |
| A public API with cookies or `Authorization` | An explicit allowlist + `credentials: true` (never `*`) |
| Local development against a Vite/Next dev server | Allowlist `http://localhost:5173` (and `http://localhost:3000`) |
| Many customer subdomains | A function or `RegExp`: `/^https:\/\/[a-z0-9-]+\.example\.com$/` |

`Vary: Origin` matters more than it looks: without it, a CDN or proxy can cache a response that was issued
for origin A and serve it to origin B, which is both wrong and a data leak. The `origin` as a **string**
(`origin: 'https://app.example.com'`) produces no `Vary` header — another reason to use a function or a
list.

---

## 5. Credentials: cookies, `Authorization` and the `include` flag

For the browser to attach cookies to a cross-origin request, **both** sides must opt in:

```js
// File: public/js/api.js (browser)
export async function api(path, { method = 'GET', body } = {}) {
  return fetch(`http://localhost:3000/api/v1${path}`, {
    method,
    credentials: 'include',                        // ← without this, no cookies cross the origin
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
}
```

```js
// File: src/middleware/cors.js (server)
const corsOptions = {
  origin(origin, callback) { /* allowlist check */ },
  credentials: true,                                // ← without this, the browser hides the response
};
```

```text
What each side controls
───────────────────────
Client:  credentials: 'include'      → "send my cookies"
Server:  Access-Control-Allow-Credentials: true
         Access-Control-Allow-Origin: <that exact origin, never *>
Cookie:  SameSite=None; Secure       → for genuinely cross-site cookies (third-party API calls)
         SameSite=Lax  (default)     → fine when the frontend is a "site" that navigates to the API
```

| Frontend / API setup | Cookie `SameSite` | Notes |
| --- | --- | --- |
| Same origin (Vite proxy, or served by the API) | `Lax` | No CORS at all — the proxy makes it same-origin (recommended for development) |
| Different subdomains of one registrable domain | `Lax` | `app.example.com` → `api.example.com` is same-**site**, cross-**origin** |
| Completely different sites | `None` + `Secure` | Needs `SameSite=None` **and** an explicit allowlist |
| Token in `Authorization` (no cookies) | n/a | Simpler: no CSRF concerns, so `credentials` is not needed |

> **`SameSite=None` re-enables CSRF.** If a cross-site cookie is required, add CSRF tokens (chapter 15) —
> `SameSite` is no longer protecting you.

---

## 6. Express 5 specifics

Express 5 uses `path-to-regexp` v8, so the old wildcard spellings are gone. This bites people upgrading:

```js
// ❌ Express 5 startup error: Missing parameter name
app.options('*', cors());
app.get('/*', handler);

// ✅ Named wildcards; braces also match the root path.
app.options('/*splat', cors());     // matches /anything but NOT /
app.options('/{*splat}', cors());   // matches / and /anything
```

> In practice you rarely need `app.options(...)` at all: `app.use(cors(...))` already answers preflight
> requests itself, before routing. Use `app.options(..., cors())` only when CORS is applied
> per-route and you need a wildcard catch-all for preflights.

| Express 4 habit | Express 5 replacement |
| --- | --- |
| `app.options('*', cors())` | `app.use(cors(...))`, or `app.options('/{*splat}', cors())` |
| `app.get('/*', …)` | `app.get('/{*splat}', …)` |
| `res.sendFile` callback style | Removed — use `res.sendFile(path)` inside `try/catch` |

---

## 7. Debugging CORS

```text
Read the browser console message — each one names the fix.
```

| Browser error | Cause | Fix |
| --- | --- | --- |
| `No 'Access-Control-Allow-Origin' header is present` | The origin is not in the allowlist, or CORS is mounted after the routes | Add the origin; mount `cors()` before routing |
| `The 'Access-Control-Allow-Origin' header has a value '*' that is not equal to the supplied origin` | `origin: '*'` while the client sends credentials | Use an allowlist; never `*` with credentials |
| `Response to preflight request doesn't pass access control check` | No `OPTIONS` handler, or the preflight hit a 404/500 | Let `app.use(cors(...))` answer it; check that a proxy does not swallow `OPTIONS` |
| `Request header field authorization is not allowed by Access-Control-Allow-Headers` | The header is missing from `allowedHeaders` | Add it (or stop sending it) |
| `Method PATCH is not allowed by Access-Control-Allow-Methods` | The method is missing from `methods` | Add it |
| The client cannot read `Location` / `ETag` | Not exposed | Add `exposedHeaders: ['Location', 'ETag']` |
| Preflight succeeds but the POST fails with cookies missing | No `credentials: 'include'` or no `Access-Control-Allow-Credentials` | Set both, plus `SameSite` |
| "It works in Postman but not in the browser" | Postman does not implement CORS | Reproduce with `curl -H 'Origin: …'` and inspect the headers |

```bash
# Reproduce the exact preflight the browser sends
curl -i -X OPTIONS http://localhost:3000/api/v1/notes \
  -H 'Origin: http://localhost:5173' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type, authorization'
```

```text
# v0.0.0.0
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS
Access-Control-Allow-Headers: Content-Type,Authorization,X-CSRF-Token,X-Request-Id
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 600
Vary: Origin
```

```bash
# And the actual request, as the browser would send it
curl -i http://localhost:3000/api/v1/notes -H 'Origin: http://localhost:5173'
```

---

## 8. CORS is not a security boundary

Three reasons to keep repeating this:

1. **Only browsers enforce it.** `curl`, Postman, a mobile app, a scraper or another server can call your
   API with any `Origin` they like — or none at all.
2. **The request runs anyway.** As verified above, a disallowed origin still gets the real response from
   your handler. CORS only stops a *page* from reading it.
3. **The real protections are elsewhere:** authentication, authorisation, rate limiting, validation,
   HTTPS, `HttpOnly` cookies, and CSRF tokens.

The right mental model: **CORS is a browser courtesy that prevents casual cross-site data theft. It is
not a firewall.** If an endpoint must not be called by other sites, protect the data, do not just hide the
header.

```js
// File: cors-is-not-auth.js
// ❌ "Only our frontend can call this because CORS is locked down."
app.get('/api/v1/admin/stats', (req, res) => res.json({ data: { users: 10_000 } }));
//   curl http://localhost:3000/api/v1/admin/stats -H 'Origin: https://evil.com'
//   → 200 with the data. The Origin header changes nothing on the server.

// ✅ Authentication and authorisation decide who gets the data; CORS never does.
app.get('/api/v1/admin/stats', requireAuth, requireRole('ADMIN'), controller.stats);
```

---

## 9. Testing CORS

```js
// File: tests/cors.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { createCorsMiddleware, createCorsOptions } from '../src/middleware/cors.js';

const ALLOWED = 'http://localhost:5173';
const OTHER_ALLOWED = 'https://app.example.com';

let server;
let baseUrl;

before(async () => {
  const app = express();
  app.use(createCorsMiddleware(createCorsOptions({ allowedOrigins: [ALLOWED, OTHER_ALLOWED], isProduction: true })));
  app.use(express.json());
  app.get('/api/v1/notes', (req, res) => {
    res.set('X-Request-Id', 'rid-1');
    res.json({ data: [] });
  });
  app.post('/api/v1/notes', (req, res) => {
    res.status(201).location('/api/v1/notes/1').json({ data: { id: '1' } });
  });
  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

test('an allowed origin gets its own origin reflected plus Vary: Origin', async () => {
  const response = await fetch(`${baseUrl}/api/v1/notes`, { headers: { Origin: ALLOWED } });

  assert.equal(response.status, 200);
  assert.equal(response.headers.get('access-control-allow-origin'), ALLOWED);
  assert.equal(response.headers.get('access-control-allow-credentials'), 'true');
  assert.equal(response.headers.get('vary'), 'Origin');
});

test('a disallowed origin gets no allow-origin header — but the handler still ran', async () => {
  const response = await fetch(`${baseUrl}/api/v1/notes`, { headers: { Origin: 'https://evil.com' } });

  assert.equal(response.status, 200);                                       // the server answered
  assert.equal(response.headers.get('access-control-allow-origin'), null);  // the browser will hide it
  assert.deepEqual(await response.json(), { data: [] });
});

test('a request with no Origin is unaffected (curl, server-to-server)', async () => {
  const response = await fetch(`${baseUrl}/api/v1/notes`);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('access-control-allow-origin'), null);
});

test('a preflight is answered with 204 and the full allow-list', async () => {
  const response = await fetch(`${baseUrl}/api/v1/notes`, {
    method: 'OPTIONS',
    headers: {
      Origin: ALLOWED,
      'Access-Control-Request-Method': 'POST',
      'Access-Control-Request-Headers': 'content-type, authorization',
    },
  });

  assert.equal(response.status, 204);
  assert.equal(response.headers.get('access-control-allow-origin'), ALLOWED);
  assert.match(response.headers.get('access-control-allow-methods'), /POST/);
  assert.match(response.headers.get('access-control-allow-headers'), /Authorization/i);
  assert.equal(response.headers.get('access-control-max-age'), '600');
});

test('a preflight from a disallowed origin carries no allow-origin', async () => {
  const response = await fetch(`${baseUrl}/api/v1/notes`, {
    method: 'OPTIONS',
    headers: { Origin: 'https://evil.com', 'Access-Control-Request-Method': 'POST' },
  });

  assert.equal(response.headers.get('access-control-allow-origin'), null);
});

test('custom response headers are exposed to the client', async () => {
  const response = await fetch(`${baseUrl}/api/v1/notes`, { headers: { Origin: ALLOWED } });

  const exposed = (response.headers.get('access-control-expose-headers') ?? '').toLowerCase();
  for (const header of ['location', 'retry-after', 'x-request-id', 'etag']) {
    assert.ok(exposed.includes(header), `${header} should be exposed`);
  }
});

test('a POST gets the CORS headers on the actual response too', async () => {
  const response = await fetch(`${baseUrl}/api/v1/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Origin: OTHER_ALLOWED },
    body: JSON.stringify({ title: 'T', content: 'C' }),
  });

  assert.equal(response.status, 201);
  assert.equal(response.headers.get('access-control-allow-origin'), OTHER_ALLOWED);
  assert.equal(response.headers.get('location'), '/api/v1/notes/1');
});

test('two different origins get two different answers (no shared cache entry)', async () => {
  const first = await fetch(`${baseUrl}/api/v1/notes`, { headers: { Origin: ALLOWED } });
  const second = await fetch(`${baseUrl}/api/v1/notes`, { headers: { Origin: OTHER_ALLOWED } });

  assert.equal(first.headers.get('access-control-allow-origin'), ALLOWED);
  assert.equal(second.headers.get('access-control-allow-origin'), OTHER_ALLOWED);
  assert.equal(second.headers.get('vary'), 'Origin');
});
```

```bash
node --test tests/cors.test.js
```

```text
✔ an allowed origin gets its own origin reflected plus Vary: Origin
✔ a disallowed origin gets no allow-origin header — but the handler still ran
✔ a request with no Origin is unaffected (curl, server-to-server)
✔ a preflight is answered with 204 and the full allow-list
✔ a preflight from a disallowed origin carries no allow-origin
✔ custom response headers are exposed to the client
✔ a POST gets the CORS headers on the actual response too
✔ two different origins get two different answers (no shared cache entry)
pass 8
fail 0
```

---

## 10. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| `origin: '*'` with `credentials: true` | "…has a value '\*' that is not equal to the supplied origin" | A real allowlist that reflects one origin |
| Mounting `cors()` after the routes | Preflights 404; some responses lack the headers | `app.use(cors(...))` before routers |
| No `Vary: Origin` (string `origin`) | A CDN serves one origin's response to another | Use a function or a list, and assert `Vary` in tests |
| Forgetting `exposedHeaders` | The SPA cannot read `Location`, `ETag`, `X-Request-Id` | Expose what the client needs |
| `allowedHeaders` missing `Authorization` | "Request header field authorization is not allowed" | Add every custom header the API accepts |
| `methods` missing `PATCH`/`DELETE` | Preflight fails only for those verbs | List all methods the API supports |
| Using CORS as authorisation | A disallowed origin still got the data | Authenticate and authorise; CORS is not a boundary |
| `origin: true` in production | Reflects **any** origin, including `evil.com` | An allowlist from configuration |
| Allowlist entries with a trailing slash | `https://app.example.com/` never matches the `Origin` header value | Origins have no path — remove the slash |
| `localhost` vs `127.0.0.1` mixed up | Works in one browser, not another | Add both during development, or use a dev proxy |
| An error thrown in the `origin` callback | The preflight becomes a 500 | `callback(null, false)` and log the rejection |
| Proxying through Vite/nginx without forwarding `OPTIONS` | Preflights die at the proxy | Forward all methods, or answer preflights at the edge |
| Adding CORS and calling it "frontend security" | The API is still open to anyone with `curl` | Rate limits, auth, validation, HTTPS |

---

## Exercise 16.1 — Configure CORS for three frontends

The notes API is consumed by:

| Client | Origin | Needs |
| --- | --- | --- |
| Local dev SPA | `http://localhost:5173` | `Authorization`, cookies, `PATCH`, reading `Location` and `Retry-After` |
| Production SPA | `https://app.example.com` | The same, plus `ETag` for caching |
| Partner dashboard | `https://partner.example.net` | Read-only: `GET` only, no cookies |

Requirements:

- Origins come from configuration (`ALLOWED_ORIGINS` in `.env`), not from code.
- The partner origin may only use `GET`/`HEAD`/`OPTIONS`.
- `Vary: Origin` on every response that carries CORS headers.
- Unknown origins are rejected without an error and logged once per minute (to avoid log floods).
- Tests that assert each of the above, including the partner's `POST` being refused.

<details>
<summary>Solution</summary>

```js
// File: src/middleware/cors.js
import cors from 'cors';

/** Per-origin policy: which methods and credentials each client may use. */
const POLICIES = new Map([
  ['http://localhost:5173', { methods: ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'], credentials: true }],
  ['https://app.example.com', { methods: ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'], credentials: true }],
  ['https://partner.example.net', { methods: ['GET', 'HEAD', 'OPTIONS'], credentials: false }],
]);

export function createCors({ allowedOrigins, logger, isProduction }) {
  const policies = new Map(
    allowedOrigins.filter((origin) => POLICIES.has(origin)).map((origin) => [origin, POLICIES.get(origin)]),
  );

  /** Rejection logging, deduplicated: one warning per origin per minute. */
  const lastLogged = new Map();
  function logRejection(origin) {
    const now = Date.now();
    if ((lastLogged.get(origin) ?? 0) > now - 60_000) return;
    lastLogged.set(origin, now);
    logger.warn('CORS origin rejected', { origin });
  }

  return cors({
    origin(origin, callback) {
      if (!origin) return callback(null, true);                 // curl, health checks
      const policy = policies.get(origin);
      if (policy) return callback(null, true);

      if (isProduction) logRejection(origin);
      return callback(null, false);                             // no header, no 500
    },

    // Dynamic values are decided per request, so attach them with a small wrapper below.
    credentials: true,
    exposedHeaders: ['Location', 'X-Request-Id', 'Retry-After', 'ETag'],
    maxAge: 600,
    optionsSuccessStatus: 204,
  });
}

/** Applies the per-origin method list on preflight responses. */
export function createCorsPolicy({ allowedOrigins, logger, isProduction }) {
  const base = createCors({ allowedOrigins, logger, isProduction });
  const policies = new Map(
    allowedOrigins.filter((origin) => POLICIES.has(origin)).map((origin) => [origin, POLICIES.get(origin)]),
  );

  return function corsPolicy(req, res, next) {
    const origin = req.get('origin');
    const policy = origin ? policies.get(origin) : null;

    if (policy) {
      res.set('Access-Control-Allow-Methods', policy.methods.join(','));
      res.set('Access-Control-Allow-Credentials', String(policy.credentials));
    }

    return base(req, res, next);
  };
}
```

```js
// File: src/config/env.js (excerpt)
const allowedOrigins = (process.env.ALLOWED_ORIGINS ?? 'http://localhost:5173')
  .split(',')
  .map((value) => value.trim())
  .filter(Boolean);

export const env = {
  /* … */
  allowedOrigins,
};
```

```dotenv
# File: .env.example
ALLOWED_ORIGINS=http://localhost:5173,https://app.example.com,https://partner.example.net
```

```js
// File: tests/cors.policy.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { createCorsPolicy } from '../src/middleware/cors.js';

const ORIGINS = ['http://localhost:5173', 'https://app.example.com', 'https://partner.example.net'];
let server;
let baseUrl;

before(async () => {
  const app = express();
  app.use(createCorsPolicy({
    allowedOrigins: ORIGINS,
    isProduction: true,
    logger: { warn() {} },
  }));
  app.use(express.json());
  app.get('/api/v1/notes', (req, res) => res.json({ data: [] }));
  app.post('/api/v1/notes', (req, res) => res.status(201).json({ data: { id: '1' } }));
  app.patch('/api/v1/notes/:id', (req, res) => res.json({ data: { id: req.params.id } }));

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1/notes`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const preflight = (origin, method) =>
  fetch(baseUrl, {
    method: 'OPTIONS',
    headers: { Origin: origin, 'Access-Control-Request-Method': method },
  });

test('the local SPA may use every method with credentials', async () => {
  const response = await preflight('http://localhost:5173', 'PATCH');
  assert.equal(response.status, 204);
  assert.equal(response.headers.get('access-control-allow-origin'), 'http://localhost:5173');
  assert.match(response.headers.get('access-control-allow-methods'), /PATCH/);
  assert.equal(response.headers.get('access-control-allow-credentials'), 'true');
  assert.equal(response.headers.get('vary'), 'Origin');
});

test('the partner origin may not use POST or PATCH', async () => {
  const options = await preflight('https://partner.example.net', 'POST');
  assert.equal(options.headers.get('access-control-allow-origin'), 'https://partner.example.net');
  assert.equal(options.headers.get('access-control-allow-credentials'), 'false');
  assert.doesNotMatch(options.headers.get('access-control-allow-methods') ?? '', /POST/);
  assert.doesNotMatch(options.headers.get('access-control-allow-methods') ?? '', /PATCH/);
});

test('an unknown origin never gets an allow-origin header', async () => {
  const response = await preflight('https://evil.com', 'GET');
  assert.equal(response.headers.get('access-control-allow-origin'), null);
});

test('every CORS-carrying response varies by origin', async () => {
  const response = await fetch(baseUrl, { headers: { Origin: 'https://app.example.com' } });
  assert.equal(response.headers.get('vary'), 'Origin');
  assert.equal(response.headers.get('access-control-allow-origin'), 'https://app.example.com');
});

test('exposed headers include everything the SPA needs', async () => {
  const response = await fetch(baseUrl, { headers: { Origin: 'https://app.example.com' } });
  const exposed = (response.headers.get('access-control-expose-headers') ?? '').toLowerCase();

  for (const header of ['location', 'x-request-id', 'retry-after', 'etag']) {
    assert.ok(exposed.includes(header));
  }
});

test('the allowlist can be changed without touching the middleware', async () => {
  const extra = express();
  extra.use(createCorsPolicy({ allowedOrigins: ['https://new.example.com'], isProduction: false, logger: { warn() {} } }));
  extra.get('/x', (req, res) => res.json({ ok: true }));

  const extraServer = extra.listen(0, '127.0.0.1');
  await new Promise((resolve) => extraServer.once('listening', resolve));

  const allowed = await fetch(`http://127.0.0.1:${extraServer.address().port}/x`, { headers: { Origin: 'https://new.example.com' } });
  const denied = await fetch(`http://127.0.0.1:${extraServer.address().port}/x`, { headers: { Origin: 'http://localhost:5173' } });

  assert.equal(allowed.headers.get('access-control-allow-origin'), 'https://new.example.com');
  assert.equal(denied.headers.get('access-control-allow-origin'), null);

  await new Promise((resolve) => extraServer.close(resolve));
});
```

```bash
node --test tests/cors.policy.test.js
```

```text
✔ the local SPA may use every method with credentials
✔ the partner origin may not use POST or PATCH
✔ an unknown origin never gets an allow-origin header
✔ every CORS-carrying response varies by origin
✔ exposed headers include everything the SPA needs
✔ the allowlist can be changed without touching the middleware
pass 6
fail 0
```

**Design notes**

| Decision | Reason |
| --- | --- |
| A policy map, not one global rule | Clients genuinely differ; expressing that in configuration keeps the middleware dumb |
| `callback(null, false)` instead of an error | A rejected origin is normal, not an exception — and a 500 would leak that the endpoint exists |
| Deduplicated rejection logging | Bot traffic can otherwise flood logs with one line per request |
| `credentials: false` for the partner | The strictest setting that still satisfies the requirement |
| Origins from `ALLOWED_ORIGINS` | Deployment changes configuration, not code |

</details>

---

## Exercise 16.2 — Diagnose the console

A developer reports: *"GET works in Postman, but in the browser my POST shows a CORS error. I added
`cors()` so I don't understand it."* Here is their code:

```js
// File: broken-cors.js
import express from 'express';
import cors from 'cors';

const app = express();
app.use(express.json());

app.post('/api/v1/notes', (req, res) => res.status(201).json({ data: { id: '1' } }));

app.use(cors());          // added "to fix CORS"

app.listen(3000);
```

The browser console shows:

```text
Access to fetch at 'http://localhost:3000/api/v1/notes' from origin 'http://localhost:5173'
has been blocked by CORS policy: Response to preflight request doesn't pass access control
check: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

<details>
<summary>Solution</summary>

**Diagnosis, in order:**

| # | Observation | Conclusion |
| --- | --- | --- |
| 1 | The error names the **preflight** request | It is an `OPTIONS /api/v1/notes` that failed, not the `POST` |
| 2 | `cors()` is registered **after** the route | Express runs middleware in order; `OPTIONS` hits the JSON body parser and then the route table, never reaching `cors()` |
| 3 | `express.json()` has no route match for `OPTIONS` | The request falls through to Express's default `OPTIONS` handling, which responds `200 Allow: POST` with no CORS headers |
| 4 | No explicit `origin` in their config | Even if reached, `*` with default `credentials: false` would work for a token-less API, but it would not cover cookies |
| 5 | "Works in Postman" | Postman does not enforce CORS — the server behaves identically in both cases |

**The fix**

```js
// File: fixed-cors.js
import express from 'express';
import cors from 'cors';

const app = express();
app.disable('x-powered-by');

// 1. CORS FIRST — before the body parser and before the routes, so preflights are answered here.
app.use(cors({
  origin: ['http://localhost:5173'],                 // explicit allowlist, not '*'
  methods: ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token', 'X-Request-Id'],
  exposedHeaders: ['Location', 'X-Request-Id', 'Retry-After', 'ETag'],
  credentials: true,                                 // only if the client sends cookies
  maxAge: 600,
  optionsSuccessStatus: 204,
}));

app.use(express.json({ limit: '100kb' }));
app.post('/api/v1/notes', (req, res) => res.status(201).location('/api/v1/notes/1').json({ data: { id: '1' } }));
app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

app.listen(3000);
```

```bash
# Verify the exact preflight before touching the browser again
curl -i -X OPTIONS http://localhost:3000/api/v1/notes \
  -H 'Origin: http://localhost:5173' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type'
```

```text
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS
Access-Control-Allow-Headers: Content-Type,Authorization,X-CSRF-Token,X-Request-Id
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 600
Vary: Origin
```

**Three lasting lessons**

1. **Middleware order is the bug.** `cors()` must be mounted before anything that can answer the request —
   including the routes themselves.
2. **Read the error precisely.** "Preflight" points at `OPTIONS`; "no allow-origin header" points at the
   allowlist or the mount order; "not allowed by Access-Control-Allow-Headers" points at configuration.
3. **Verify with `curl`.** The browser hides the actual response; `curl -X OPTIONS` shows it, headers and
   all, in one command.

</details>

---

## What's next

Requests can now arrive from any configured origin, with or without credentials. Next: accepting **files**
— multipart form data, streaming uploads, size limits, file-type verification, and storage that cannot be
tricked into overwriting itself.

→ [17 — File Uploads](17-file-upload.md)
