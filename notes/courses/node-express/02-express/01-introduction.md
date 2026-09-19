# 01 — Introduction to Express

> **Where this fits:** You have built an HTTP server by hand and know exactly what that costs. This
> chapter introduces Express — what it is, what it actually does for you, how its request lifecycle
> works, and the honest limitations. Everything after this is detail on `app`, `req`, `res` and
> `next`.

---

## 1. What is Express?

> **Express is a minimal, unopinionated web framework for Node.js. It adds routing and a middleware
> pipeline to `node:http` — and nothing else.**

Decompose that definition:

| Word | Meaning |
| --- | --- |
| **Minimal** | The core is small: routing + middleware + request/response helpers. No ORM, no CLI, no conventions imposed |
| **Unopinionated** | You choose the folder structure, the database, the validation library, the template engine |
| **Web framework** | It serves HTTP — it is not a general-purpose toolkit |
| **Adds to `node:http`** | Express *is* built on the `http` module. `app.listen()` eventually calls `server.listen()` |

```js
// File: hello-express.js
import express from 'express';

// express() returns the application object.
const app = express();

// Define a route: GET / → run this function.
app.get('/', (req, res) => {
  res.send('Hello from Express!');
});

// Start listening on all interfaces.
app.listen(3000, '0.0.0.0', () => {
  console.log('Server running at http://localhost:3000');
});
```

```bash
npm install express
node hello-express.js
curl -i http://localhost:3000/
```

```http
HTTP/1.1 200 OK
X-Powered-By: Express
Content-Type: text/html; charset=utf-8
ETag: W/"12-9f9cLd2fFnUvfETVYgOmHc4XxOY"
Content-Length: 19

Hello from Express!
```

Notice `X-Powered-By: Express` — a header that advertises your framework and version to attackers.
Disable it in production:

```js
app.disable('x-powered-by');   // or app.set('x-powered-by', false)
```

---

## 2. Why Express exists (the honest version)

In [01-nodejs/11-http-module.md](../01-nodejs/11-http-module.md) we wrote a server by hand: ~150 lines
of plumbing for a five-endpoint API. Those lines had nothing to do with the application; they were the
*tax* of talking HTTP.

Express removes that tax:

| You wrote by hand | Express |
| --- | --- |
| A router with `:param` matching | `app.get('/notes/:id', handler)` |
| Reading + parsing + limiting the body | `express.json({ limit: '100kb' })` |
| `sendJson(res, status, payload)` | `res.status(201).json(payload)` |
| Try/catch around every handler | Errors forwarded to one error middleware (Express 5 handles async) |
| `readJson` content-type checks | `express.json()` returns `415`/`400` appropriately |
| Manual 404/405 logic | A `app.use()` at the end + optional 405 handling |
| Middleware by hand | `app.use(fn)` with `next()` |
| Static file serving | `express.static('public')` |

**What it does *not* provide:** validation, authentication, authorisation, database access, logging,
caching, rate limiting, security headers, or error *classification*. Those come from the ecosystem or
from you — which is why this section is 21 chapters long, not 3.

### Why Express 5 (and not 4)?

Express 5.2.x is `latest` on npm. The changes that matter in this section:

| Express 5 | Consequence |
| --- | --- |
| **Async errors are forwarded automatically** | An `async` handler that rejects reaches your error middleware without a wrapper (Express 4 needed `express-async-errors` or manual `try/catch`) |
| `path-to-regexp@8` | Wildcards must be *named*: `'*splat'`, not `'*'`. `'/*'` and `app.use('*')` now throw |
| `req.query` uses a simple parser by default | `?a[b]=1` no longer becomes a nested object unless you opt into a parser |
| Removed: `res.sendfile`, `res.json(status, obj)`, `app.del`, `express.static`'s `fallthrough` quirks | Old tutorials will not work verbatim |
| `req.body` is `undefined` (not `{}`) when no body parser ran | Guard with `req.body ?? {}` |
| Minimum Node 18 | Fine for everything in these notes |

```js
// File: express5-changes.js
import express from 'express';

const app = express();

// ❌ Express 4 style — throws on Express 5: TypeError: Missing parameter name
// app.get('*', (req, res) => res.send('catch all'));

// ✅ Express 5: named wildcard
app.get('/*splat', (req, res) => {
  res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } });
});

// ✅ Also fine — middleware with no path matches everything
// app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

app.listen(0, '127.0.0.1', () => {
  console.log('listening on a random port');
});
```

---

## 3. The mental model: everything is middleware

Express has one central idea: **a request flows through an ordered list of functions.** Each function
can end the request, or call `next()` to pass control on.

```text
Request
   │
   ├─▶ app.use(express.json())            parse the body
   ├─▶ app.use(requestLogger)             log it
   ├─▶ app.use('/api/notes', noteRouter)  route it
   │        ├─▶ router.use(authenticate)  check the token
   │        ├─▶ router.get('/:id', ...)   handle it
   │        └─▶ (no match) ─────────────▶ next()
   ├─▶ app.use(notFoundHandler)           404
   └─▶ app.use(errorHandler)              4 arguments → error handler
                                              │
                                              ▼
                                          Response
```

Three consequences that explain almost all Express behaviour:

1. **Order matters.** `express.json()` must come before any handler that reads `req.body`;
   `authenticate` must come before the routes it protects; the 404 handler must be last.
2. **`next()` is the only way forward.** A handler that neither responds nor calls `next()` hangs the
   request until it times out.
3. **The error handler is just middleware with four parameters.** That arity is how Express identifies
   it.

We go deep on middleware in [07 — Middleware](07-middleware.md); this is the shape you need now.

---

## 4. The four things you must understand

### `app` — the application

```js
// File: app-object.js
import express from 'express';

const app = express();

// Configuration via app.set / app.get
app.set('trust proxy', 1);            // behind a proxy: read X-Forwarded-* (see ch. 20)
app.set('case sensitive routing', true);
app.set('strict routing', false);     // /users and /users/ are equivalent
app.disable('x-powered-by');

console.log('trust proxy  :', app.get('trust proxy'));
console.log('env          :', app.get('env'));           // from NODE_ENV
console.log('disabled     :', app.disabled('x-powered-by'));
```

`app` is also a router: it has `use`, `get`, `post`, `param`, and so on. That is why `app.use('/x',
router)` works — a router is just a middleware.

### `req` — the request (extended `http.IncomingMessage`)

```js
// File: req-shape.js
import express from 'express';

const app = express();

app.get('/demo/:id', (req, res) => {
  res.json({
    method: req.method,                     // 'GET'
    url: req.url,                           // '/demo/42?x=1'
    originalUrl: req.originalUrl,           // unchanged even inside a router
    baseUrl: req.baseUrl,                   // the router's mount path
    path: req.path,                         // '/demo/42' — no query
    params: req.params,                     // { id: '42' }   ← from the path
    query: req.query,                       // { x: '1' }     ← from the query string
    headers: req.headers,                   // lower-cased names
    hostname: req.hostname,                 // 'localhost'
    protocol: req.protocol,                 // 'http' or 'https' (honours trust proxy)
    ip: req.ip,                             // with trust proxy configured
    secure: req.secure,                     // protocol === 'https'
    cookies: req.cookies,                   // requires cookie-parser
    body: req.body,                         // requires express.json()/urlencoded()
    file: req.file,                          // requires multer (single file)
    files: req.files,                        // requires multer (multiple)
    get: typeof req.get,                     // req.get('content-type') — case-insensitive
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

### `res` — the response (extended `http.ServerResponse`)

```js
// File: res-shape.js
import express from 'express';

const app = express();

app.get('/json', (req, res) => {
  res.status(201).json({ ok: true });                       // sets Content-Type + JSON body
});

app.get('/send', (req, res) => {
  res.send('text or html');                                 // content type inferred
});

app.get('/status-only', (req, res) => {
  res.sendStatus(204);                                      // sets the status AND sends its name as body
});

app.get('/redirect', (req, res) => {
  res.redirect(302, '/json');                               // sets Location and ends
});

app.get('/headers', (req, res) => {
  res.set('X-Custom', 'value').status(200).type('application/json').send('{"ok":true}');
});

app.get('/cookie', (req, res) => {
  res.cookie('sessionId', 'abc', { httpOnly: true, sameSite: 'lax', maxAge: 86_400_000 });
  res.json({ set: true });
});

app.get('/download', (req, res) => {
  res.download('./package.json', 'package-copy.json');       // sets Content-Disposition
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

### `next` — pass control

```js
// File: next-shape.js
import express from 'express';

const app = express();

// Middleware: does something, then continues.
app.use((req, res, next) => {
  req.startedAt = process.hrtime.bigint();
  next();                                   // → the next middleware or route
});

// Middleware that stops the chain with a response (no next()).
app.use((req, res, next) => {
  if (req.headers['x-api-key'] !== 'secret') {
    return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
  }
  return next();
});

// next('route') skips the remaining handlers for THIS route only.
app.get(
  '/special',
  (req, res, next) => {
    if (!req.query.mode) return next('route');   // fall through to the next matching route
    return res.json({ mode: req.query.mode });
  }
);

app.get('/special', (req, res) => {
  res.json({ mode: 'default' });
});

// next(error) jumps straight to the error middleware, skipping normal middleware.
app.get('/boom', (req, res, next) => {
  next(new Error('deliberate failure'));
});

// The error middleware — identified by its FOUR parameters.
app.use((error, req, res, next) => {
  console.error('handled:', error.message);
  res.status(500).json({ error: { code: 'INTERNAL_ERROR' } });
});

app.get('/timed', (req, res) => {
  const ms = Number(process.hrtime.bigint() - req.startedAt) / 1e6;
  res.json({ durationMs: Number(ms.toFixed(3)) });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

---

## 5. A realistic first application

```js
// File: src/server.js
import express from 'express';

const app = express();
const PORT = process.env.PORT ?? 3000;

// ---------------------------------------------------------------------------
// 1. Global middleware (order matters)
// ---------------------------------------------------------------------------
app.disable('x-powered-by');
app.use(express.json({ limit: '100kb' }));

app.use((req, res, next) => {
  const startedAt = process.hrtime.bigint();
  res.on('finish', () => {
    const ms = Number(process.hrtime.bigint() - startedAt) / 1e6;
    console.log(`${req.method} ${req.originalUrl} → ${res.statusCode} (${ms.toFixed(1)}ms)`);
  });
  next();
});

// ---------------------------------------------------------------------------
// 2. Routes
// ---------------------------------------------------------------------------
const notes = new Map();
let nextId = 1;

app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.get('/api/v1/notes', (req, res) => {
  res.json({ data: [...notes.values()] });
});

app.post('/api/v1/notes', (req, res) => {
  const { title, content } = req.body ?? {};
  if (typeof title !== 'string' || title.trim() === '') {
    return res.status(422).json({
      error: { code: 'VALIDATION_ERROR', details: [{ field: 'title', message: 'required' }] },
    });
  }
  const note = { id: String(nextId++), title: title.trim(), content: content ?? '', createdAt: new Date().toISOString() };
  notes.set(note.id, note);
  res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: note });
});

app.get('/api/v1/notes/:id', (req, res) => {
  const note = notes.get(req.params.id);
  if (!note) {
    return res.status(404).json({ error: { code: 'NOT_FOUND', message: `Note ${req.params.id} not found` } });
  }
  res.json({ data: note });
});

app.patch('/api/v1/notes/:id', (req, res) => {
  const note = notes.get(req.params.id);
  if (!note) return res.status(404).json({ error: { code: 'NOT_FOUND' } });

  const body = req.body ?? {};
  const updated = { ...note, ...(typeof body.title === 'string' ? { title: body.title.trim() } : {}) };
  notes.set(note.id, updated);
  res.json({ data: updated });
});

app.delete('/api/v1/notes/:id', (req, res) => {
  if (!notes.delete(req.params.id)) return res.status(404).json({ error: { code: 'NOT_FOUND' } });
  res.status(204).end();
});

// ---------------------------------------------------------------------------
// 3. 404 handler — after all routes, before the error handler
// ---------------------------------------------------------------------------
app.use((req, res) => {
  res.status(404).json({
    error: { code: 'ROUTE_NOT_FOUND', message: `${req.method} ${req.originalUrl} not found` },
  });
});

// ---------------------------------------------------------------------------
// 4. Error handler — LAST, with four parameters
// ---------------------------------------------------------------------------
app.use((error, req, res, next) => {
  const statusCode = error.statusCode ?? 500;
  console.error(JSON.stringify({ level: 'error', message: error.message, path: req.originalUrl }));

  if (res.headersSent) return next(error);           // delegate to Express's default handler
  return res.status(statusCode).json({
    error: {
      code: error.code ?? 'INTERNAL_ERROR',
      message: statusCode >= 500 && process.env.NODE_ENV === 'production' ? 'Something went wrong' : error.message,
    },
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`API ready on http://localhost:${PORT}`);
});
```

Compare this with the raw-`http` version from the last chapter: the same features, roughly half the
code, and no hand-written router, body parser or error plumbing.

---

## 6. When not to use Express

| Situation | Better choice | Why |
| --- | --- | --- |
| Maximum throughput, schema-validated routes | **Fastify** | Faster routing, built-in schema validation and serialisation |
| Serverless edge functions | Hono, itty-router | Tiny footprint, runs on Workers/Deno/Bun |
| Full TypeScript, opinionated structure | **NestJS** | Dependency injection, decorators, modules (built on Express or Fastify) |
| One endpoint, no routing | plain `node:http` | No dependency is the best dependency |
| You want batteries included (ORM, auth, admin) | NestJS, AdonisJS | Express leaves all of that to you |

Express's advantages remain: it is the most widely used Node framework (so every tutorial, Stack
Overflow answer and middleware exists), it is stable across a decade, and it teaches the middleware
model that every other JS framework borrows. **Learn Express first; migrate later if you need to.**

---

## 7. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| Forgetting `express.json()` | `req.body` is `undefined` → 500s | Register it before routes that read bodies |
| Calling `express.json()` *after* routes | Same, for matching routes | Middleware order is registration order |
| Not calling `next()` or responding | The request hangs until timeout | Every path must respond or call `next` |
| Express 4 wildcards on Express 5 | `TypeError: Missing parameter name` at startup | Use `'*splat'` or a path-less `app.use` |
| `app.listen` inside a module that tests import | Port conflicts between tests | Split `app.js` (build) from `server.js` (listen) |
| Trusting `req.query` / `req.params` types | `"2" + 1 === "21"` | Validate and coerce |
| Assuming `req.body` exists | `Cannot read properties of undefined` | `req.body ?? {}` and validate |
| Leaving `X-Powered-By` on | Version disclosure | `app.disable('x-powered-by')` |
| Putting business logic in route handlers | Untestable, duplicated | Controller → service → repository |
| One giant `app.js` | Unmaintainable at 500 lines | Routers per resource (ch. 09) |

---

## Exercise 1.1 — Identify the errors

```js
import express from 'express';
const app = express();

app.get('/users/:id', (req, res) => {
  res.json({ id: req.params.id, page: req.query.page + 1 });
});

app.post('/users', (req, res) => {
  res.json({ received: req.body.name });
});

app.use(express.json());

app.use((req, res) => {
  res.status(404).send('Cannot GET ' + req.url);
});

app.listen(3000);
```

Find every problem and fix it.

<details>
<summary>Solution</summary>

1. **`express.json()` is registered after the routes that need it.** Middleware runs in registration
   order, so for `POST /users` the body parser never runs → `req.body` is `undefined` → `TypeError:
   Cannot read properties of undefined (reading 'name')` → an unhandled error.
2. **`req.query.page + 1` is string concatenation.** `GET /users/1?page=2` returns `"21"`. Worse,
   without `?page=2` it returns `"undefined1"`. Query values are strings and must be coerced and
   validated.
3. **`req.body.name` is unguarded** even after fixing the order: a `POST` with an empty or
   non-object body (`null`, `[]`) throws. Use `req.body ?? {}` plus validation.
4. **`res.status(404).send('Cannot GET ...')` sends HTML to a JSON API.** Clients expecting JSON
   will fail to parse it. Return a JSON error contract.
5. **No error handler.** Any thrown error falls through to Express's default handler, which returns
   an HTML page including the stack in development and a bare `Internal Server Error` in production.
   Add a 4-argument error middleware.
6. **`Cannot GET` is Express's wording, not a real message.** Writing it manually is fine, but the
   message should describe *your* API's contract.
7. **`app.listen(3000)` with no host** binds to all interfaces by default in Express — acceptable, but
   be explicit (`'0.0.0.0'`) so it is a decision, not an accident.
8. **The 404 handler is installed after the routes but before the error handler** — that part is
   correct, and worth noting as the one thing done right.
9. **No `x-powered-by` disabled**, no logging, no `PORT` from the environment (hard-coded 3000 breaks
   most platforms).

**Fixed version:**

```js
// File: server-fixed.js
import express from 'express';

const app = express();
app.disable('x-powered-by');

// 1. Parser FIRST, so every route below can rely on req.body.
app.use(express.json({ limit: '100kb' }));

// 2. Request logging.
app.use((req, res, next) => {
  const startedAt = process.hrtime.bigint();
  res.on('finish', () => {
    const ms = Number(process.hrtime.bigint() - startedAt) / 1e6;
    console.log(`${req.method} ${req.originalUrl} → ${res.statusCode} ${ms.toFixed(1)}ms`);
  });
  next();
});

app.get('/users/:id', (req, res) => {
  // 3. Coerce and validate query values.
  const page = req.query.page === undefined ? 1 : Number(req.query.page);
  if (!Number.isInteger(page) || page < 1) {
    return res.status(422).json({
      error: { code: 'VALIDATION_ERROR', details: [{ field: 'page', message: 'must be an integer >= 1' }] },
    });
  }
  return res.json({ id: req.params.id, page: page + 1 });
});

app.post('/users', (req, res) => {
  // 4. Guard the body and validate the shape.
  const body = req.body ?? {};
  if (typeof body.name !== 'string' || body.name.trim() === '') {
    return res.status(422).json({
      error: { code: 'VALIDATION_ERROR', details: [{ field: 'name', message: 'required' }] },
    });
  }
  return res.status(201).json({ data: { name: body.name.trim() } });
});

// 5. JSON 404, matching the rest of the API.
app.use((req, res) => {
  res.status(404).json({
    error: { code: 'ROUTE_NOT_FOUND', message: `${req.method} ${req.originalUrl} not found` },
  });
});

// 6. One error handler, last.
app.use((error, req, res, next) => {
  const statusCode = error.statusCode ?? 500;
  console.error(JSON.stringify({ level: 'error', message: error.message, path: req.originalUrl }));
  if (res.headersSent) return next(error);
  return res.status(statusCode).json({
    error: {
      code: error.code ?? 'INTERNAL_ERROR',
      message: statusCode >= 500 && process.env.NODE_ENV === 'production' ? 'Something went wrong' : error.message,
    },
  });
});

// 7. Port from the environment.
const port = Number(process.env.PORT ?? 3000);
app.listen(port, '0.0.0.0', () => console.log(`listening on http://localhost:${port}`));
```

**Verify the fixes with `curl`:**

```bash
curl -s 'localhost:3000/users/1?page=2'          # {"id":"1","page":3}
curl -s 'localhost:3000/users/1'                 # {"id":"1","page":1}
curl -s 'localhost:3000/users/1?page=abc'        # 422
curl -s -X POST localhost:3000/users -H 'Content-Type: application/json' -d '{"name":"Ankit"}'
curl -s -X POST localhost:3000/users -H 'Content-Type: application/json' -d '{}'    # 422
curl -s localhost:3000/nope                      # JSON 404 (not HTML)
```

</details>

---

## What's next

Next: setting the project up properly — structure, scripts, environment handling, and the `app.js` /
`server.js` split that makes everything testable.

→ [02 — Project Setup](02-project-setup.md)
