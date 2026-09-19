# 11 — The `http` Module: Building a Server by Hand

> **Where this fits:** This is the chapter that makes Express understandable. We build a real HTTP
> server with nothing but Node's built-in `http` module — routing, body parsing, JSON responses,
> status codes, error handling — and then look at exactly how much of that work Express removes.
> After this, `app.get('/users/:id', handler)` is a convenience, not magic.

---

## 1. The simplest possible server

```js
// File: server-basic.mjs
import { createServer } from 'node:http';

// createServer takes a request listener: called once per incoming request.
const server = createServer((req, res) => {
  console.log(`${req.method} ${req.url}`);

  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.end('Hello from a bare Node.js server\n');
});

const PORT = process.env.PORT ?? 3000;
const HOST = '0.0.0.0';   // listen on all interfaces, not only localhost

server.listen(PORT, HOST, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
```

```bash
node server-basic.mjs
curl -i http://localhost:3000/anything
```

```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Date: Thu, 18 Sep 2026 10:15:30 GMT
Connection: keep-alive
Keep-Alive: timeout=5
Content-Length: 30

Hello from a bare Node.js server
```

Four lines of real work: create the server, listen on a port, read the request, write the response.
Everything else in this chapter is the detail that a production server needs.

---

## 2. The `req` object

`req` is an `http.IncomingMessage` — a **readable stream** plus request metadata.

```js
// File: inspect-request.mjs
import { createServer } from 'node:http';

const server = createServer((req, res) => {
  const details = {
    method: req.method,                     // 'GET', 'POST', 'PUT', 'PATCH', 'DELETE' …
    url: req.url,                           // '/users/42?page=2' — path + query, not the host
    httpVersion: req.httpVersion,           // '1.1'
    headers: req.headers,                   // lower-cased names, joined duplicate values
    rawHeaders: req.rawHeaders,             // original casing and order, as an array
    socket: {
      remoteAddress: req.socket.remoteAddress,  // '::1' or '127.0.0.1' locally
      remotePort: req.socket.remotePort,
    },
  };

  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(details, null, 2));
});

server.listen(3000, '0.0.0.0', () => console.log('listening on 3000'));
```

```bash
curl -s http://localhost:3000/users/42?page=2 -H "X-Demo: yes"
```

```json
{
  "method": "GET",
  "url": "/users/42?page=2",
  "httpVersion": "1.1",
  "headers": { "host": "localhost:3000", "x-demo": "yes", "accept": "*/*", "user-agent": "curl/8.7.1" },
  "rawHeaders": ["Host", "localhost:3000", "X-Demo", "yes", "Accept", "*/*"],
  "socket": { "remoteAddress": "127.0.0.1", "remotePort": 53230 }
}
```

Key observations:

- **`req.url` is only the path and query** — the host is in the `Host` header. That is why virtual
  hosting works (one IP, many domains).
- **Header names are lower-cased** in `req.headers`. `req.headers['content-type']` is the reliable
  access pattern.
- **Duplicate headers are joined**: two `Cookie` headers become `"a=1; b=2"`.

### Reading the request body

`req` is a stream. There is no `req.body` — you must collect the chunks and parse them yourself.

```js
// File: parse-body.mjs
import { createServer } from 'node:http';

/** Collect a request body with a hard size limit, honouring backpressure. */
function readBody(req, { limitBytes = 1_000_000 } = {}) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;

    req.on('data', (chunk) => {
      size += chunk.length;

      // Never let a client exhaust your memory (an easy DoS otherwise).
      if (size > limitBytes) {
        const error = new Error('Payload too large');
        error.statusCode = 413;
        req.destroy(error);              // stop reading and close the connection
        return;
      }

      chunks.push(chunk);
    });

    req.on('end', () => resolve(Buffer.concat(chunks)));

    req.on('error', reject);

    // A client that disconnects mid-body must not leave this promise pending forever.
    req.on('aborted', () => reject(new Error('Client aborted the request')));
  });
}

const server = createServer(async (req, res) => {
  if (req.method !== 'POST') {
    res.writeHead(405, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Only POST is supported' }));
    return;
  }

  try {
    const raw = await readBody(req, { limitBytes: 100_000 });
    const contentType = req.headers['content-type'] ?? '';

    if (!contentType.includes('application/json')) {
      res.writeHead(415, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Content-Type must be application/json' }));
      return;
    }

    let parsed;
    try {
      parsed = JSON.parse(raw.toString('utf8'));
    } catch {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Body is not valid JSON' }));
      return;
    }

    res.writeHead(201, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ received: parsed, bytes: raw.length }));
  } catch (error) {
    const status = error.statusCode ?? 500;
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: error.message }));
  }
});

server.listen(3000, '0.0.0.0', () => console.log('listening on 3000'));
```

```bash
curl -s -X POST http://localhost:3000/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ankit"}' -i | head -3
```

```http
HTTP/1.1 201 Created
Content-Type: application/json
{"received":{"name":"Ankit"},"bytes":16}
```

Notice how much *manual* work protecting the server required: a size limit, a content-type check, a
JSON parse try/catch, an abort handler, an error status mapping. **All of that is what
`express.json()` does for you** — and knowing it is there is why you will configure its `limit`
rather than ignore it.

---

## 3. The `res` object

`res` is an `http.ServerResponse` — a **writable stream** plus response helpers.

```js
// File: response-api.mjs
import { createServer } from 'node:http';

const server = createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  switch (url.pathname) {
    case '/status-only': {
      // 204 must have NO body.
      res.writeHead(204);
      res.end();
      return;
    }

    case '/headers': {
      res.writeHead(200, {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'public, max-age=60',
        'X-Request-Id': 'req_12345',
      });
      res.end(JSON.stringify({ ok: true }));
      return;
    }

    case '/redirect': {
      res.writeHead(302, { Location: '/target' });
      res.end();                       // 302 responses have no body requirement, but end() is needed
      return;
    }

    case '/stream': {
      // Chunked response: send data as it is produced.
      res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
      let count = 0;
      const interval = setInterval(() => {
        count += 1;
        res.write(`chunk ${count}\n`);
        if (count === 3) {
          clearInterval(interval);
          res.end('finished\n');
        }
      }, 100);
      return;
    }

    case '/cookie': {
      // Multiple Set-Cookie headers require an array — setHeader would overwrite.
      res.writeHead(200, {
        'Content-Type': 'text/plain',
        'Set-Cookie': [
          'sessionId=abc123; HttpOnly; SameSite=Lax; Path=/',
          'theme=dark; Path=/',
        ],
      });
      res.end('cookies set');
      return;
    }

    default: {
      res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Try /status-only, /headers, /redirect, /stream or /cookie');
    }
  }
});

server.listen(3000, '0.0.0.0', () => console.log('listening on 3000'));
```

### The response API

| Method / property | Purpose |
| --- | --- |
| `res.statusCode = 404` | Set the status (default `200`) |
| `res.setHeader(name, value)` | Set one header (overwrites); pass an array for `Set-Cookie` |
| `res.writeHead(status, headers?)` | Set status and headers, then send — **must be called before the body** |
| `res.write(chunk)` | Write part of the body (enables chunked transfer) |
| `res.end([chunk])` | Finish the response; always call it, even with no body |
| `res.headersSent` | `true` once headers are flushed — you cannot change them after |
| `res.getHeader(name)` | Read a header you set (or one Node will send) |
| `res.removeHeader(name)` | Remove a header before sending |
| `res.flushHeaders()` | Send headers immediately (before the first body chunk) |
| `res.writableEnded` | `true` after `end()` |
| `res.destroy([error])` | Abort the response and the connection |

### The three mistakes everyone makes

```js
// ❌ 1. Setting a header AFTER writing the body — silently ignored, and it throws in some setups.
res.write('hello');
res.setHeader('X-Late', 'nope');   // headers were already sent

// ❌ 2. Calling end() twice — ERR_STREAM_WRITE_AFTER_END
res.end('first');
res.end('second');

// ❌ 3. Forgetting end() — the request hangs until the client times out.
if (someCondition) {
  res.writeHead(200);
  // no res.end() on this path
}
```

```js
// ✅ The correct order
res.writeHead(200, { 'Content-Type': 'application/json' });
res.write('{"partial":');
res.end('true}');
```

---

## 4. Routing by hand

Routing is matching `(method, path)` to a function. Here it is, implemented from scratch:

```js
// File: manual-router.mjs
import { createServer } from 'node:http';

/**
 * A minimal router: registers handlers as pattern → method → fn, then matches by
 * splitting the path into segments. Demonstrates exactly what Express does internally.
 */
function createRouter() {
  const routes = [];

  function add(method, pattern, handler) {
    const segments = pattern.split('/').filter(Boolean);
    routes.push({ method, segments, handler });
  }

  function match(method, pathname) {
    const parts = pathname.split('/').filter(Boolean);

    for (const route of routes) {
      if (route.method !== method) continue;
      if (route.segments.length !== parts.length) continue;

      const params = {};
      let matched = true;

      for (let i = 0; i < route.segments.length; i += 1) {
        const patternSegment = route.segments[i];
        if (patternSegment.startsWith(':')) {
          params[patternSegment.slice(1)] = decodeURIComponent(parts[i]);
        } else if (patternSegment !== parts[i]) {
          matched = false;
          break;
        }
      }

      if (matched) return { handler: route.handler, params };
    }

    return null;
  }

  return {
    get: (pattern, handler) => add('GET', pattern, handler),
    post: (pattern, handler) => add('POST', pattern, handler),
    patch: (pattern, handler) => add('PATCH', pattern, handler),
    delete: (pattern, handler) => add('DELETE', pattern, handler),
    match,
  };
}

// ---------------------------------------------------------------------------
// A toy in-memory "database"
// ---------------------------------------------------------------------------
const users = new Map([
  ['1', { id: '1', name: 'Ankit', role: 'admin' }],
  ['2', { id: '2', name: 'Priya', role: 'user' }],
]);

// ---------------------------------------------------------------------------
// Helpers, because raw Node requires them
// ---------------------------------------------------------------------------
const sendJson = (res, status, payload) => {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),      // avoids chunked encoding for known sizes
  });
  res.end(body);
};

const readJson = (req) =>
  new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > 100_000) {
        req.destroy();
        reject(Object.assign(new Error('Payload too large'), { statusCode: 413 }));
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8');
      if (raw.length === 0) return resolve({});
      try {
        return resolve(JSON.parse(raw));
      } catch {
        return reject(Object.assign(new Error('Invalid JSON body'), { statusCode: 400 }));
      }
    });
    req.on('error', reject);
  });

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
const router = createRouter();

router.get('/health', (req, res) => sendJson(res, 200, { status: 'ok' }));

router.get('/users', (req, res, ctx) => {
  const role = ctx.query.get('role');
  const all = [...users.values()];
  sendJson(res, 200, { data: role ? all.filter((u) => u.role === role) : all });
});

router.get('/users/:id', (req, res, ctx) => {
  const user = users.get(ctx.params.id);
  if (!user) return sendJson(res, 404, { error: { code: 'USER_NOT_FOUND' } });
  return sendJson(res, 200, { data: user });
});

router.post('/users', async (req, res) => {
  const body = await readJson(req);
  if (typeof body.name !== 'string' || body.name.trim() === '') {
    return sendJson(res, 422, {
      error: { code: 'VALIDATION_ERROR', details: [{ field: 'name', message: 'required' }] },
    });
  }
  const id = String(users.size + 1);
  const user = { id, name: body.name.trim(), role: body.role === 'admin' ? 'admin' : 'user' };
  users.set(id, user);
  res.setHeader('Location', `/users/${id}`);
  return sendJson(res, 201, { data: user });
});

router.delete('/users/:id', (req, res, ctx) => {
  if (!users.has(ctx.params.id)) return sendJson(res, 404, { error: { code: 'USER_NOT_FOUND' } });
  users.delete(ctx.params.id);
  res.writeHead(204);
  return res.end();
});

// ---------------------------------------------------------------------------
// The server: parse the URL, match, run, handle errors
// ---------------------------------------------------------------------------
const server = createServer(async (req, res) => {
  const startedAt = process.hrtime.bigint();

  // Parse the URL properly — never hand-split the query string.
  const url = new URL(req.url, `http://${req.headers.host ?? 'localhost'}`);
  const requestId = crypto.randomUUID();

  res.setHeader('X-Request-Id', requestId);

  // CORS would need explicit handling here too (another thing Express does for you).
  const ctx = {
    params: {},
    query: url.searchParams,       // a real URLSearchParams instance
    requestId,
  };

  try {
    const matched = router.match(req.method, url.pathname);

    if (!matched) {
      // Distinguish "no such path" from "wrong method for this path".
      const allowed = ['GET', 'POST', 'PATCH', 'DELETE'].filter((method) =>
        router.match(method, url.pathname)
      );

      if (allowed.length > 0) {
        res.setHeader('Allow', allowed.join(', '));
        return sendJson(res, 405, { error: { code: 'METHOD_NOT_ALLOWED', allowed } });
      }

      return sendJson(res, 404, {
        error: { code: 'ROUTE_NOT_FOUND', message: `${req.method} ${url.pathname} not found` },
      });
    }

    ctx.params = matched.params;
    await matched.handler(req, res, ctx);
    return undefined;
  } catch (error) {
    // Central error handler — the ONE place that decides how failures look.
    const status = error.statusCode ?? 500;
    const durationMs = Number(process.hrtime.bigint() - startedAt) / 1e6;

    console.error(
      JSON.stringify({
        level: 'error',
        requestId,
        method: req.method,
        path: url.pathname,
        status,
        durationMs: Number(durationMs.toFixed(2)),
        message: error.message,
      })
    );

    if (res.headersSent) return res.destroy();     // too late to send a JSON error body

    return sendJson(res, status, {
      error: {
        code: status === 500 ? 'INTERNAL_ERROR' : error.code ?? 'REQUEST_ERROR',
        // Never leak internal messages on a 500.
        message: status === 500 ? 'Something went wrong' : error.message,
        requestId,
      },
    });
  }
});

server.listen(3000, '0.0.0.0', () => console.log('listening on http://localhost:3000'));
```

```bash
# Happy paths
curl -s localhost:3000/health
curl -s "localhost:3000/users?role=admin"
curl -s localhost:3000/users/2
curl -s -X POST localhost:3000/users -H 'Content-Type: application/json' -d '{"name":"Meera"}'

# Failure paths — the part that matters
curl -s localhost:3000/users/999                                   # 404 USER_NOT_FOUND
curl -s -X PATCH localhost:3000/users/1                            # 405 with Allow: GET, DELETE
curl -s -X POST localhost:3000/users -d '{"name":""}' \
     -H 'Content-Type: application/json'                           # 422 with field details
curl -s -X DELETE localhost:3000/users/2 -o /dev/null -w '%{http_code}\n'   # 204
```

Look at how much code this took: **the router, the body reader with a limit, the query parser, the
error handler, the 404/405 logic, the logging, the request id plumbing.** Around 150 lines that have
nothing to do with user management. That is the honest answer to "why Express?".

---

## 5. Why Express exists

Here is the same application in Express:

```js
// File: express-version.mjs
import express from 'express';

const app = express();
const users = new Map([
  ['1', { id: '1', name: 'Ankit', role: 'admin' }],
  ['2', { id: '2', name: 'Priya', role: 'user' }],
]);

app.use(express.json({ limit: '100kb' }));
app.use((req, res, next) => {
  req.id = crypto.randomUUID();
  res.setHeader('X-Request-Id', req.id);
  next();
});

app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.get('/users', (req, res) => {
  const all = [...users.values()];
  const { role } = req.query;
  res.json({ data: role ? all.filter((u) => u.role === role) : all });
});

app.get('/users/:id', (req, res, next) => {
  const user = users.get(req.params.id);
  if (!user) return next(Object.assign(new Error('User not found'), { statusCode: 404 }));
  return res.json({ data: user });
});

app.post('/users', (req, res, next) => {
  const { name, role } = req.body ?? {};
  if (typeof name !== 'string' || name.trim() === '') {
    return next(
      Object.assign(new Error('Validation failed'), {
        statusCode: 422,
        details: [{ field: 'name', message: 'required' }],
      })
    );
  }
  const id = String(users.size + 1);
  const user = { id, name: name.trim(), role: role === 'admin' ? 'admin' : 'user' };
  users.set(id, user);
  return res.status(201).location(`/users/${id}`).json({ data: user });
});

app.delete('/users/:id', (req, res) => {
  if (!users.has(req.params.id)) {
    return res.status(404).json({ error: { code: 'USER_NOT_FOUND' } });
  }
  users.delete(req.params.id);
  return res.status(204).end();
});

// 404 for anything unmatched
app.use((req, res) => {
  res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND', message: `${req.method} ${req.path} not found` } });
});

// Central error handler: 4 arguments is what marks it as one
app.use((error, req, res, next) => {
  const status = error.statusCode ?? 500;
  console.error(JSON.stringify({ level: 'error', requestId: req.id, status, message: error.message }));
  if (res.headersSent) return res.destroy();
  return res.status(status).json({
    error: {
      code: status === 500 ? 'INTERNAL_ERROR' : error.code ?? 'REQUEST_ERROR',
      message: status === 500 ? 'Something went wrong' : error.message,
      details: error.details,
      requestId: req.id,
    },
  });
});

app.listen(3000, '0.0.0.0', () => console.log('listening on http://localhost:3000'));
```

### What Express actually did for you

| Raw `http` work | Express equivalent |
| --- | --- |
| `new URL(req.url, host)` + `searchParams` | `req.query` (parsed, with a query-string parser) |
| Hand-written `createRouter()` with segment matching | `app.get('/users/:id')` and `req.params` |
| `readJson(req)` with size limits and JSON parse errors | `express.json()` → `req.body` (and a proper 400/413) |
| `sendJson(res, status, payload)` helper | `res.json()`, `res.status()` |
| Manual `Allow` header and 405 logic | Still manual, but trivial with `app.all`/middleware |
| Manual try/catch around every handler | Express 5 forward async errors to the error handler automatically |
| Manual 404 handling at the end of a chain | One `app.use()` at the bottom |
| Ad-hoc error responses | A single 4-argument error middleware |
| Manual logging middleware | `app.use()` with `next()` |
| No static file serving | `express.static('public')` |
| No cookie parsing | `cookie-parser` |
| No CORS handling | `cors` package (or your own middleware) |
| No body parsing for forms/uploads | `express.urlencoded()`, `multer` |

**What Express did *not* do:** routing performance magic, security, validation, authentication,
authorisation, database access, logging, or error *handling* (only error *delivery*). Those are
still your job — and they are the subject of the rest of these notes.

### A fair performance note

Express adds a measurable but small overhead versus raw `http` (middleware dispatch, more objects
per request). For virtually every API this is irrelevant next to database time. If you ever truly
need more throughput, the answer is usually Fastify (which is designed around a schema-compiled
router) rather than hand-rolled `http` — you would be giving up an ecosystem for microseconds.

```bash
# Rough comparison you can run yourself once you have both implementations
npx autocannon -c 100 -d 10 http://localhost:3000/health
```

Read the numbers with suspicion: what matters is *latency under load* and *whether the event loop is
blocked*, not peak requests per second on a microbenchmark.

---

## 6. Production concerns a real server needs (previewed here, implemented later)

```js
// File: production-server.mjs — the shape of a real entry point
import { createServer } from 'node:http';
import { once } from 'node:events';

const server = createServer(handler);

// 1. Timeouts: never let a slow or malicious client hold a connection forever.
server.keepAliveTimeout = 65_000;      // slightly more than a typical proxy's 60s
server.headersTimeout = 66_000;        // must be LARGER than keepAliveTimeout
server.requestTimeout = 30_000;        // whole request (headers + body)
server.maxRequestsPerSocket = 1000;    // recycle connections to spread load

// 2. Headers: hide the implementation, mitigate some attacks.
server.on('request', (req, res) => {
  res.removeHeader('X-Powered-By');    // Node does not add this; Express does
});

// 3. Client errors must not crash the process.
server.on('clientError', (error, socket) => {
  if (socket.writable) socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
  socket.destroy();
});

// 4. Graceful shutdown: stop accepting, finish in-flight, then exit.
async function shutdown(reason) {
  console.log(`${reason} received: closing server`);

  server.close(() => {
    console.log('all connections closed, exiting');
    process.exit(0);
  });

  // Force-exit safety net if something refuses to finish.
  setTimeout(() => {
    console.error('forced exit after timeout');
    process.exit(1);
  }, 10_000).unref();

  // Close idle keep-alive sockets so close() can complete promptly.
  server.closeIdleConnections?.();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

function handler(req, res) {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ ok: true }));
}

server.listen(Number(process.env.PORT ?? 3000), '0.0.0.0');
await once(server, 'listening');
console.log('ready on port', server.address().port);
```

Those four concerns — **timeouts, flood protection, graceful shutdown, and not crashing on client
errors** — are exactly what separates a tutorial server from a deployable one, and they appear in
full in [02-express/20-production-architecture.md](../02-express/20-production-architecture.md).

---

## 7. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| Forgetting `res.end()` | Request hangs until timeout | Always end the response on every path |
| Setting headers after the body | Silently ignored / throws | Set headers and status first |
| No body size limit | A single request can exhaust memory | Count bytes and destroy past the limit |
| Hand-parsing the query string | Broken on encoded values, arrays, `+` | `new URL(req.url, base).searchParams` |
| Using `req.url` as a file path | Directory traversal | Resolve and containment-check ([07 §5](07-path.md)) |
| No `'error'` handler on `req` | Unhandled error, possible crash | Handle `'error'` and `'aborted'` |
| Ignoring backpressure on `res.write` | Memory growth under slow clients | Check the return value / use `pipeline` |
| Trusting `req.headers['x-forwarded-for']` | Rate limiting is bypassable | Configure trusted proxies ([20](../02-express/20-production-architecture.md)) |
| No timeouts | Slow-loris attacks keep sockets open | Set `requestTimeout`, `headersTimeout` |
| Logging every request with `console.log` at high volume | Slow, unstructured | Structured logging with levels and request ids |

---

## Exercise 11.1 — Extend the raw server

Add these endpoints to the manual router server:

1. `PATCH /users/:id` — merges a partial body, returns `200` with the updated user, `404` if missing,
   `422` if the body contains no recognised fields.
2. `GET /users/:id/posts` — returns a nested resource (`404` if the user does not exist), showing
   that `:id` plus a static segment works.
3. `GET /users?sort=name|-name&page=1&limit=2` — real (validated) pagination with metadata.

<details>
<summary>Solution</summary>

```js
// File: extend-router.mjs — only the new/changed parts, to be added to manual-router.mjs

// ---------------------------------------------------------------------------
// 1. PATCH — partial update
// ---------------------------------------------------------------------------
router.patch('/users/:id', async (req, res, ctx) => {
  const existing = users.get(ctx.params.id);
  if (!existing) return sendJson(res, 404, { error: { code: 'USER_NOT_FOUND' } });

  const body = await readJson(req);
  const allowedFields = ['name', 'role'];
  const updates = {};

  for (const field of allowedFields) {
    if (Object.hasOwn(body, field)) updates[field] = body[field];
  }

  if (Object.keys(updates).length === 0) {
    return sendJson(res, 422, {
      error: {
        code: 'VALIDATION_ERROR',
        message: `Provide at least one of: ${allowedFields.join(', ')}`,
      },
    });
  }

  if (updates.name !== undefined && (typeof updates.name !== 'string' || !updates.name.trim())) {
    return sendJson(res, 422, {
      error: { code: 'VALIDATION_ERROR', details: [{ field: 'name', message: 'must be a non-empty string' }] },
    });
  }

  if (updates.role !== undefined && !['user', 'admin'].includes(updates.role)) {
    return sendJson(res, 422, {
      error: { code: 'VALIDATION_ERROR', details: [{ field: 'role', message: 'must be user or admin' }] },
    });
  }

  const updated = { ...existing, ...updates };
  users.set(ctx.params.id, updated);
  return sendJson(res, 200, { data: updated });
});

// ---------------------------------------------------------------------------
// 2. Nested resource: /users/:id/posts
// ---------------------------------------------------------------------------
const posts = new Map([
  ['1', [{ id: 'p1', userId: '1', title: 'Hello world' }]],
  ['2', [{ id: 'p2', userId: '2', title: 'Second post' }]],
]);

router.get('/users/:id/posts', (req, res, ctx) => {
  // The parent must exist — a nested collection of a missing parent is a 404, not [].
  if (!users.has(ctx.params.id)) {
    return sendJson(res, 404, { error: { code: 'USER_NOT_FOUND' } });
  }
  return sendJson(res, 200, { data: posts.get(ctx.params.id) ?? [] });
});

// ---------------------------------------------------------------------------
// 3. Paginated + sorted list, replacing the naive GET /users
// ---------------------------------------------------------------------------
const SORTABLE = {
  name: (a, b) => a.name.localeCompare(b.name),
  '-name': (a, b) => b.name.localeCompare(a.name),
  '-id': (a, b) => Number(b.id) - Number(a.id),
};

router.get('/users', (req, res, ctx) => {
  // 1. Validate and coerce — query values are STRINGS.
  const page = Number(ctx.query.get('page') ?? 1);
  const limit = Number(ctx.query.get('limit') ?? 20);
  const sort = ctx.query.get('sort') ?? 'name';

  const errors = [];
  if (!Number.isInteger(page) || page < 1) errors.push({ field: 'page', message: 'must be an integer >= 1' });
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
    errors.push({ field: 'limit', message: 'must be an integer between 1 and 100' });
  }
  if (!Object.hasOwn(SORTABLE, sort)) {
    errors.push({ field: 'sort', message: `must be one of: ${Object.keys(SORTABLE).join(', ')}` });
  }
  if (errors.length > 0) {
    return sendJson(res, 422, { error: { code: 'VALIDATION_ERROR', details: errors } });
  }

  // 2. Filter, sort, paginate.
  const role = ctx.query.get('role');
  const filtered = [...users.values()].filter((u) => (role ? u.role === role : true));
  const sorted = filtered.sort(SORTABLE[sort]);
  const offset = (page - 1) * limit;
  const pageItems = sorted.slice(offset, offset + limit);

  return sendJson(res, 200, {
    data: pageItems,
    meta: {
      page,
      limit,
      total: sorted.length,
      totalPages: Math.max(1, Math.ceil(sorted.length / limit)),
      sort,
    },
  });
});
```

```bash
curl -s -X PATCH localhost:3000/users/2 -H 'Content-Type: application/json' -d '{"name":"Priya S"}' | head -c 120
curl -s -X PATCH localhost:3000/users/2 -H 'Content-Type: application/json' -d '{}'          # 422
curl -s localhost:3000/users/1/posts
curl -s localhost:3000/users/999/posts                                                       # 404
curl -s 'localhost:3000/users?sort=-name&page=1&limit=2' | head -c 200
curl -s 'localhost:3000/users?limit=9999'                                                    # 422
curl -s 'localhost:3000/users?sort=password'                                                 # 422 (whitelist)
```

**What this exercise demonstrates**

| Lesson | Where it shows up |
| --- | --- |
| Nested routes need the parent check | `/users/:id/posts` returns 404 when the user is missing |
| Query values are strings and must be coerced | `Number(ctx.query.get('page'))` |
| Sort fields must be whitelisted | A `SORTABLE` map, not string interpolation |
| Partial updates need "present vs absent" checks | `Object.hasOwn(body, field)`, not `if (body.field)` |
| List endpoints cap `limit` | `limit > 100` → 422 |
| Pagination metadata belongs in the response | `{ data, meta }` |

Notice how much of this is *boilerplate you wrote by hand* — validation, coercion, whitelisting,
pagination. In Express this collapses to a schema (`zod`) plus a three-line middleware, which is
precisely the value the next section delivers.

</details>

---

## What's next

You have built a server with raw Node and seen what Express automates. Before using Express, though,
we must master the thing that trips up every Node beginner: asynchrony — callbacks, promises and the
patterns that keep code readable when everything is async.

→ [12 — Asynchronous Programming](12-async-programming.md)
