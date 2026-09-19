# 03 — Routing

> **Where this fits:** Routing is the framework's core job: deciding *which function runs for which URL*.
> Everything else in Express — middleware, controllers, error handling — hangs off the routing table.
> This chapter covers every path syntax Express 5 supports, how matching actually works, and the
> mistakes that make routes silently unreachable.

---

## 1. What routing is

> **Routing is the mapping from `(HTTP method, URL path)` to a handler function.**

In [01-nodejs/11-http-module.md](../01-nodejs/11-http-module.md) you wrote the mapping by hand:
a `match()` function that split paths on `/`, compared segments, and extracted `:params`. Express does
the same thing, with far more syntax and far fewer bugs.

```js
// File: routing-basics.js
import express from 'express';

const app = express();

//        method   path          handler (controller)
app.get('/api/v1/notes', (req, res) => {
  res.json({ data: [] });
});

app.post('/api/v1/notes', (req, res) => {
  res.status(201).json({ data: { id: '1' } });
});

app.listen(3000, '0.0.0.0', () => console.log('http://localhost:3000'));
```

Line by line:

| Line | What it does |
| --- | --- |
| `app.get(...)` | Registers a route: *if a request is `GET` and its path matches, run this function* |
| `'/api/v1/notes'` | The path pattern — matched against the URL path only (the query string is not part of it) |
| `(req, res) => {}` | The route handler. Receives the request and response; it must end the response |
| `res.json({...})` | Serialises to JSON, sets `Content-Type: application/json`, ends the response |

**Key point:** registration order is the matching order. A route's position in the file is behaviour,
not style.

---

## 2. The registration API

| Form | Meaning |
| --- | --- |
| `app.get(path, handler)` | One method, one path |
| `app.post(path, handler)` | Same, different verb |
| `app.all(path, handler)` | Every HTTP method |
| `app.route(path).get(h).post(h)` | Group handlers for one path (avoids repeating the path) |
| `app.use(path, fn)` | Middleware, not a route: matches a *prefix*, runs for any method |
| `router.get(path, handler)` | Same API on an `express.Router()` — mount it later (ch. 09) |

```js
// File: registration-forms.js
import express from 'express';

const app = express();

// 1. One at a time
app.get('/health', (req, res) => res.json({ status: 'ok' }));

// 2. Chained on a shared path — reads like a resource definition
app
  .route('/api/v1/notes/:id')
  .get((req, res) => res.json({ data: { id: req.params.id } }))
  .patch((req, res) => res.json({ data: { id: req.params.id, patched: true } }))
  .delete((req, res) => res.status(204).end());

// 3. Several paths sharing one handler
const healthHandler = (req, res) => res.json({ ok: true });
app.get(['/healthz', '/health', '/_health'], healthHandler);

// 4. Several handlers for one path (middleware + handler) — see §6
app.get(
  '/api/v1/reports',
  (req, res, next) => { req.reportScope = 'all'; next(); },
  (req, res) => res.json({ scope: req.reportScope }),
);

// 5. Any method
app.all('/api/v1/echo', (req, res) => res.json({ method: req.method }));

app.listen(0, '127.0.0.1', () => console.log('routes registered'));
```

### `app.use` versus `app.get`

This distinction causes a lot of confusion:

| | `app.get('/api/notes', fn)` | `app.use('/api/notes', fn)` |
| --- | --- | --- |
| Matches | Exactly `/api/notes` | `/api/notes`, `/api/notes/1`, `/api/notes/1/tags`, … (prefix) |
| Methods | GET only | All methods |
| Trailing `/` | Tolerated by default (`strict routing` off) | Irrelevant — it is a prefix |
| Typical use | A route | Mounting a router, or middleware |

```js
// File: use-vs-get.js
import express from 'express';

const app = express();

app.use('/api/notes', (req, res, next) => {
  console.log('runs for every path under /api/notes:', req.originalUrl);
  next();
});

app.get('/api/notes', (req, res) => res.json({ data: [] }));          // ✔ matched after the middleware
app.get('/api/notes/:id', (req, res) => res.json({ id: req.params.id })); // ✔

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

---

## 3. Path patterns — the complete Express 5 syntax

Express 5 uses `path-to-regexp` **v8**, which changed several things from Express 4. The table below is
what you should memorise; every row was verified against `express@5.2.1`.

| Pattern | Matches | `req.params` | Notes |
| --- | --- | --- | --- |
| `/notes` | `/notes` | `{}` | Exact path (case-insensitive, trailing `/` tolerated by default) |
| `/notes/:id` | `/notes/42` | `{ id: '42' }` | Named parameter, URL-decoded |
| `/notes/:id/tags` | `/notes/42/tags` | `{ id: '42' }` | Parameters can appear anywhere in the path |
| `/files/*splat` | `/files/a/b.txt` | `{ splat: ['a', 'b.txt'] }` | **Named** wildcard → an **array** of segments |
| `/files{/*splat}` | `/files`, `/files/a/b.txt` | `{}` or `{ splat: [...] }` | Braces make the segment optional |
| `/opt{/:id}` | `/opt`, `/opt/42` | `{}` or `{ id: '42' }` | Optional parameter — `?` is **gone** in Express 5 |
| `/:file{.:ext}` | `/report.pdf`, `/report` | `{ file, ext? }` | Optional suffix |
| `['/a', '/b']` | `/a` or `/b` | — | Array of paths, one handler |
| `/^\/re\/(\d+)$/` | `/re/42` | `{ 0: '42' }` | A real `RegExp` is still supported |

### Parameters

```js
// File: params.js
import express from 'express';

const app = express();

// Single parameter: /notes/42 → { id: '42' }
app.get('/notes/:id', (req, res) => {
  res.json({ id: req.params.id, type: typeof req.params.id });   // always a string
});

// Parameters mixed with literals: /notes/42/comments/7
app.get('/notes/:noteId/comments/:commentId', (req, res) => {
  const { noteId, commentId } = req.params;
  res.json({ noteId, commentId });
});

// Optional parameter with braces: matches /search and /search/node
app.get('/search{/:term}', (req, res) => {
  res.json({ term: req.params.term ?? null });
});

// Optional suffix: matches /report.pdf and /report
app.get('/report/:file{.:ext}', (req, res) => {
  res.json({ file: req.params.file, ext: req.params.ext ?? 'none' });
});

// Wildcard: matches /files/a/b/c.txt → splat is an ARRAY
app.get('/files/*splat', (req, res) => {
  const segments = req.params.splat;             // ['a', 'b', 'c.txt']
  res.json({ segments, joined: segments.join('/') });
});

// Literal characters can be used as separators in a pattern too
app.get('/range/:from-:to', (req, res) => {
  res.json(req.params);                          // /range/1-9 → { from: '1', to: '9' }
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

> **Parameters are always strings.** `req.params.id` for `/notes/42` is `'42'`, not `42`. Never do
> arithmetic on it before validating — `'42' + 1` is `'421'`. Coercion and validation belong in a
> validator ([15 — Validation](12-validation.md) uses Zod for exactly this).

### What param values can contain

```js
// File: params-values.js
import express from 'express';

const app = express();

/** Parameters are URL-decoded before you see them. */
app.get('/decode/:value', (req, res) => {
  res.json({
    raw: req.originalUrl,            // '/decode/a%2Fb'
    decoded: req.params.value,       // 'a/b'  ← the '/' was encoded as %2F
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

| Request | `req.params.value` |
| --- | --- |
| `/decode/a%20b` | `a b` |
| `/decode/a%2Fb` | `a/b` |
| `/decode/%E2%9C%93` | `✓` |

**Consequence:** a parameter can contain `/` even though it was one URL segment. Any code that builds a
file path from a parameter must re-validate it — see the traversal defence in
[01-nodejs/07-path.md](../01-nodejs/07-path.md).

### Paths that throw at startup

path-to-regexp v8 rejects patterns Express 4 accepted. These are startup errors, not request errors —
which is good: you find them immediately.

```text
app.get('*', ...)          → TypeError: Missing parameter name at index 1: *
app.get('/*', ...)         → TypeError: Missing parameter name at index 2: /*
app.get('/foo?', ...)      → TypeError: Unexpected ? at index 4: /foo?
app.get('/x/:y?', ...)     → TypeError: Unexpected ? at index 5: /x/:y?
```

Fixes:

```js
// File: express4-to-5-paths.js
import express from 'express';

const app = express();

// ❌ app.get('*', handler)

// ✅ catch-all as a middleware (recommended — no pattern at all)
// app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

// ✅ explicit wildcard, matches any path EXCEPT the root
app.get('/*splat', (req, res) => {
  res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND', path: req.path } });
});

// ❌ app.get('/api/*', handler)

// ✅ named wildcard, and braces when the bare prefix must match too
app.get('/api{/*path}', (req, res) => {
  res.json({ segments: req.params.path ?? [] });
});

// ❌ app.get('/x/:y?', handler)

// ✅ optional parameters use braces in Express 5
app.get('/x{/:y}', (req, res) => {
  res.json({ y: req.params.y ?? null });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

> **Trap worth knowing:** `/ab*cd` does **not** throw — `*cd` is parsed as a wildcard *named* `cd`
> (because `cd` is a valid identifier). If you meant a literal asterisk, escape it: `'/ab\\*cd'`.
> Reserved characters in v8 are `{ } : * + ? ( ) [ ]` — escape them with a backslash, or avoid them
> in paths entirely. Reserved characters belong in path *parameters*, not in literal paths.

---

## 4. How matching actually works

Express tries routes **in registration order** and runs the first one that matches. There is no
"most specific wins" algorithm — which means order is a design decision.

### Three rule changes that surprise people

| Behaviour | Default | Control | Effect when changed |
| --- | --- | --- | --- |
| Case sensitivity | **Insensitive** — `/Case` matches `/case` | `app.set('case sensitive routing', true)` | `/Case` and `/case` become different routes |
| Trailing slash | **Tolerated** — `/a/` matches `/a` | `app.set('strict routing', true)` | `/a/` and `/a` become different routes |
| Precedence | **Order**, not specificity | Reorder your registrations | `/users/me` can be swallowed by `/users/:id` |

Verified behaviour of the defaults:

```text
GET /case      → 200   (registered as '/Case'; default is case-INSENSITIVE)
GET /trail/    → 200   (registered as '/trail'; default tolerates the trailing slash)
```

```js
// File: shadowing.js
import express from 'express';

const app = express();

// ❌ WRONG ORDER: ':id' swallows 'me' — /users/me returns a user with id "me"
app.get('/users/:id', (req, res) => res.json({ byId: req.params.id }));
app.get('/users/me', (req, res) => res.json({ me: true }));
// GET /users/me → { "byId": "me" }

// ✅ RIGHT ORDER: literal paths first, parameters after
const app2 = express();
app2.get('/users/me', (req, res) => res.json({ me: true }));
app2.get('/users/:id', (req, res) => res.json({ byId: req.params.id }));
// GET /users/me → { "me": true }

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

### A wildcard is greedy about *what it matches*, but only after literal segments

```text
'/files/*splat'  matches  /files/a/b/c.txt   ✔
                 does NOT match  /files       ✘   (needs at least one segment)
                 does NOT match  /files/      ✘
```

That last pair is the most common "why is my SPA fallback 404 on the root?" bug. Use braces —
`'/files{/*splat}'` — to make the wildcard optional so `/files` matches too.

### Methods are matched too, but 405 is your job

If a path matches but the method does not, Express falls through and eventually 404s. A correct API
should return `405 Method Not Allowed` **with an `Allow` header**. Express provides no built-in way, so
here is a small helper — resolved *after* all real handlers for the same path, which is exactly what you
want:

```js
// File: src/middleware/methodNotAllowed.js
/**
 * Respond with 405 (and a correct Allow header) for methods that are not allowed
 * on a path that DOES exist. Register it after the real handlers for that path.
 */
export function methodNotAllowed(allowedMethods) {
  const allowed = [...new Set(allowedMethods.map((method) => method.toUpperCase()))];
  const allowHeader = [...allowed, 'HEAD', 'OPTIONS'].join(', ');

  return function methodNotAllowedHandler(req, res) {
    res.set('Allow', allowHeader);

    // OPTIONS asks "what can I do here?" — answer it properly instead of failing.
    if (req.method === 'OPTIONS') {
      return res.status(204).end();
    }

    return res.status(405).json({
      error: {
        code: 'METHOD_NOT_ALLOWED',
        message: `${req.method} is not allowed for ${req.originalUrl}`,
        allowed,
      },
    });
  };
}
```

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { methodNotAllowed } from '../middleware/methodNotAllowed.js';

export function createNoteRouter({ controller }) {
  const router = Router();

  router.get('/', controller.list);
  router.post('/', controller.create);
  router.get('/:id', controller.getOne);
  router.patch('/:id', controller.update);
  router.delete('/:id', controller.remove);

  // After the real handlers: anything else on these paths is a 405, not a 404.
  router.all('/', methodNotAllowed(['GET', 'POST']));
  router.all('/:id', methodNotAllowed(['GET', 'PATCH', 'DELETE']));

  return router;
}
```

Verified behaviour of that router:

```text
PUT     /api/v1/notes/7   → 405  Allow: GET, PATCH, DELETE, HEAD, OPTIONS
PUT     /api/v1/notes     → 405  Allow: GET, POST, HEAD, OPTIONS
OPTIONS /api/v1/notes/7   → 204  Allow: GET, PATCH, DELETE, HEAD, OPTIONS
HEAD    /api/v1/notes/7   → 200  (Express answers HEAD automatically for GET routes)
POST    /api/v1/notes/7   → 405
GET     /api/v1/notes/7/x → 404  (a different path, so 404 is correct)
```

> `router.all` matches **every** method, including `OPTIONS` — which is why the helper answers
> `OPTIONS` itself instead of leaving it to Express's default OPTIONS handler.

---

## 5. `req.params`, `req.query` and `req.path` inside routers

When a router is mounted, Express rewrites the request in a way that trips up almost everyone:

```js
// File: mounted-values.js
import express, { Router } from 'express';

const router = Router();

router.get('/', (req, res) => {
  res.json({
    baseUrl: req.baseUrl,        // '/api/v1/notes'  ← the mount path
    path: req.path,              // '/'               ← path INSIDE the router
    url: req.url,                // '/?sort=asc'      ← url INSIDE the router (includes query)
    originalUrl: req.originalUrl,// '/api/v1/notes?sort=asc' ← the real, full URL
    query: req.query,            // { sort: 'asc' }
  });
});

const app = express();
app.use('/api/v1/notes', router);
app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

| Property | Inside a mounted router | Use it for |
| --- | --- | --- |
| `req.baseUrl` | `/api/v1/notes` | Building links, logging the resource |
| `req.path` | `/` (relative to the mount) | Route-local decisions |
| `req.url` | `/?sort=asc` (relative) | Rarely — usually you want `originalUrl` |
| `req.originalUrl` | `/api/v1/notes?sort=asc` | Logging, error messages, request ids |
| `req.params` | Merged: mount params + route params | Path values |

**Rule of thumb: log and report with `req.originalUrl`; match with `req.path`/`req.params`.**

Mounted-path matching details (verified):

```text
app.use('/api/v1/notes', router)
  /api/v1/notes        → matches, req.path === '/'
  /api/v1/notes/       → matches, req.path === '/'
  /api/v1/notes/7      → matches, router sees '/7'
  /API/v1/notes        → matches (mount is case-insensitive by default; req.baseUrl keeps the original casing)
  /api/v1/notes/7/8    → matches the router; the router then 404s if it has no such route
```

---

## 6. Several handlers per route

A route can take an array of functions (or several arguments). They run in order until one responds —
this is the mechanism behind "middleware inside a route".

```js
// File: route-handlers.js
import express from 'express';

const app = express();

/** 1. Authorisation middleware, then the handler. */
const requireAuth = (req, res, next) => {
  const token = req.get('authorization');
  if (!token) {
    return res.status(401).json({ error: { code: 'UNAUTHENTICATED', message: 'Missing Authorization header' } });
  }
  req.user = { id: 'u1', token };
  return next();       // ← without next() the request hangs forever
};

app.get('/api/v1/me', requireAuth, (req, res) => {
  res.json({ data: req.user });
});

/** 2. The same thing as an array (useful when generated). */
const requireAdmin = (req, res, next) => {
  if (req.user?.role !== 'admin') {
    return res.status(403).json({ error: { code: 'FORBIDDEN' } });
  }
  return next();
};

app.get('/api/v1/admin/users', [requireAuth, requireAdmin], (req, res) => {
  res.json({ data: [] });
});

/** 3. next('route') — abandon THIS route and try the next matching one. */
app.get(
  '/api/v1/search',
  (req, res, next) => {
    if (req.query.engine === 'legacy') return next('route');  // skip to the next route definition
    return res.json({ engine: 'default', results: [] });
  },
  (req, res) => res.json({ note: 'this handler is skipped when next("route") ran' }),
);

app.get('/api/v1/search', (req, res) => {
  res.json({ engine: 'legacy', results: [] });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

| Call | Effect |
| --- | --- |
| `next()` | Continue to the next handler **in this route**, then the next matching route |
| `next('route')` | Skip the remaining handlers **of this route**; continue matching from the next route definition |
| `next('router')` | Leave the current router entirely; continue in the parent |
| `next(error)` | Jump to the error middleware (ch. 08), skipping normal middleware |
| Nothing | The request hangs until the client or server timeout — always respond or call `next()` |

`next('route')` is verified behaviour: with a query flag, the second handler of the *same* route is
skipped and the *separate* `/api/v1/search` registration runs.

---

## 7. `app.param` — loading a resource once per parameter

Instead of repeating "fetch the note, 404 if missing" in five handlers, declare it once with
`router.param` (or `app.param`).

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { NotFoundError } from '../utils/AppError.js';

export function createNoteRouter({ noteService, controller }) {
  const router = Router();

  /**
   * Runs ONCE per request for any route that has :id — but only when the route matches.
   * Attach the loaded resource to req so handlers never repeat the lookup.
   */
  router.param('id', async (req, res, next, id) => {
    try {
      const note = await noteService.getById(id);
      if (!note) return next(new NotFoundError(`Note ${id} not found`));
      req.note = note;
      return next();
    } catch (error) {
      return next(error);              // async: you must catch and forward manually
    }
  });

  router.get('/:id', controller.getOne);        // can use req.note directly
  router.patch('/:id', controller.update);      // same, no lookup repeated
  router.delete('/:id', controller.remove);

  return router;
}
```

Verified semantics: `param` callbacks run **once per request**, in the order the parameters were
declared, and only for routes that actually match (the test counted one call for `GET /notes/7` and a
second for `GET /notes/7/extra`).

| Use `param` for | Avoid it for |
| --- | --- |
| Loading a resource by id across several routes | Heavy work used by only one route |
| Validating an id format consistently | Anything that changes the response shape |
| Access checks that depend on the resource | Side effects (it runs even for a 405 fallthrough) |

---

## 8. Organising routes for a real API

Three levels of structure, in increasing order of seriousness.

### Level 1 — prefixes and versions

```js
// File: src/app.js (excerpt)
import express from 'express';

const app = express();

// Versioned base path — one line changes the whole API version.
const API_PREFIX = '/api/v1';

app.get(`${API_PREFIX}/notes`, listNotes);
// …later: app.use(`${API_PREFIX}/notes`, noteRouter);

export default app;
```

### Level 2 — one router per resource (see [09 — Routers](09-routers.md))

```js
// File: src/routes/index.js
import { Router } from 'express';
import { createNoteRouter } from './noteRoutes.js';
import { createUserRouter } from './userRoutes.js';

export function createApiRouter({ noteController, userController }) {
  const api = Router();

  api.use('/notes', createNoteRouter({ controller: noteController }));
  api.use('/users', createUserRouter({ controller: userController }));

  return api;
}
```

```js
// File: src/app.js (excerpt)
import { createApiRouter } from './routes/index.js';

export function createApp({ config }) {
  const app = express();
  app.use('/api/v1', createApiRouter({ /* … */ }));
  return app;
}
```

### Level 3 — a route table (data, not code)

For a large API, declaring routes as data makes them auditable: you can print them, test them, and
generate documentation from them.

```js
// File: src/routes/routeTable.js
import { methodNotAllowed } from '../middleware/methodNotAllowed.js';

/**
 * One place that answers "what does this API expose?".
 * Each entry: { method, path, handlers }.
 */
export function createRouteTable({ noteController, userController }) {
  return [
    { method: 'get', path: '/health', handlers: [(req, res) => res.json({ status: 'ok' })] },

    { method: 'get', path: '/notes', handlers: [noteController.list] },
    { method: 'post', path: '/notes', handlers: [noteController.create] },
    { method: 'get', path: '/notes/:id', handlers: [noteController.getOne] },
    { method: 'patch', path: '/notes/:id', handlers: [noteController.update] },
    { method: 'delete', path: '/notes/:id', handlers: [noteController.remove] },

    { method: 'get', path: '/users', handlers: [userController.list] },
    { method: 'get', path: '/users/:id', handlers: [userController.getOne] },

    // 405 guards: one entry per path shape, resolved last within its router.
    { method: 'all', path: '/notes', handlers: [methodNotAllowed(['GET', 'POST'])] },
    { method: 'all', path: '/notes/:id', handlers: [methodNotAllowed(['GET', 'PATCH', 'DELETE'])] },
    { method: 'all', path: '/users', handlers: [methodNotAllowed(['GET'])] },
    { method: 'all', path: '/users/:id', handlers: [methodNotAllowed(['GET'])] },
  ];
}
```

```js
// File: src/routes/applyRouteTable.js
import { Router } from 'express';

/** Turn data into Express registrations. Order of the table IS the matching order. */
export function applyRouteTable(router, routeTable) {
  for (const { method, path, handlers } of routeTable) {
    router[method](path, ...handlers);
  }
  return router;
}

export function createRouterFromTable(routeTable) {
  return applyRouteTable(Router(), routeTable);
}
```

```js
// File: src/routes/printRoutes.js
/**
 * Debugging aid: print the route table. Because we hold the table as data,
 * no framework internals are involved — this always reflects reality.
 */
export function printRoutes(routeTable, { prefix = '/api/v1', write = console.log } = {}) {
  const rows = routeTable
    .filter((route) => route.method !== 'all')                    // hide 405 guards by default
    .map((route) => ({ method: route.method.toUpperCase(), path: prefix + route.path }));

  const methodWidth = Math.max(...rows.map((row) => row.method.length));
  for (const row of rows) write(`${row.method.padEnd(methodWidth)}  ${row.path}`);
  write(`\n${rows.length} routes registered`);
  return rows;
}
```

```js
// File: src/server.js (excerpt) — print the table at startup in development
import { createRouteTable } from './routes/routeTable.js';
import { printRoutes } from './routes/printRoutes.js';

const routeTable = createRouteTable({ noteController, userController });
if (env.nodeEnv !== 'production') printRoutes(routeTable);
```

```text
GET    /api/v1/health
GET    /api/v1/notes
POST   /api/v1/notes
GET    /api/v1/notes/:id
PATCH  /api/v1/notes/:id
DELETE /api/v1/notes/:id
GET    /api/v1/users
GET    /api/v1/users/:id

8 routes registered
```

> **Do not reach into `app._router.stack` to list routes.** Express 5 removed `app._router` (there is
> an `app.router` getter, but its internal layer structure — and mounted-prefix information — is not
> part of the public API and changes between minor versions). Keep your own table; it cannot break.

---

## 9. Debugging "my route doesn't work"

Work through this checklist in order. It resolves almost every routing bug.

| # | Check | How |
| --- | --- | --- |
| 1 | Is the method right? | `curl -i -X POST ...` — a `GET` to a `POST` route is a 404, not a 405, unless you added the guard |
| 2 | Is the path exactly right? | Compare with the startup route print (`printRoutes`) |
| 3 | Is a parameter swallowing a literal? | `/users/:id` before `/users/me` — reorder |
| 4 | Is the router mounted at the right prefix? | `req.originalUrl` in a log line tells you what actually arrived |
| 5 | Is the middleware above it calling `next()`? | A log statement inside each `app.use` proves it |
| 6 | Is `express.json()` registered before the route? | Bodies are `undefined` in handlers when it is not |
| 7 | Is the pattern Express-5-legal? | `*`/`?` in a pattern throws at startup — read the error message |
| 8 | Is a wildcard swallowing the path? | `'/*splat'`-style catch-alls must be registered last |
| 9 | Does the response get sent? | A handler that neither responds nor calls `next()` hangs — look for a request timeout in logs |
| 10 | Is the trailing slash / case different? | Defaults tolerate both; a `strict routing`/`case sensitive routing` flag may not |

```js
// File: src/middleware/traceRoutes.js
/** Temporary debugging middleware: log what actually arrives, before matching. */
export function traceRoutes(req, res, next) {
  console.log(
    JSON.stringify({
      method: req.method,
      originalUrl: req.originalUrl,
      path: req.path,
      host: req.get('host'),
      contentType: req.get('content-type'),
    }),
  );
  next();
}
```

```bash
# Prove the route exists at the HTTP level, independent of your client code:
curl -i -X POST http://localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' -d '{"title":"from curl"}'

# See exactly which method/path reached the server:
# run with traceRoutes registered first, then re-run the curl above
```

---

## 10. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| `app.get('*', …)` on Express 5 | App crashes at startup: `Missing parameter name` | `app.use(handler)` or `'/*splat'` |
| `'/x/:y?'` for an optional param | Startup crash: `Unexpected ?` | `'/x{/:y}'` |
| `/files/*splat` expected to match `/files` | 404 on the bare prefix | `'/files{/*splat}'` |
| Literal path after a parameter path | The literal route never runs | Literal first, parameter second |
| Catch-all registered before routes | Every request hits the catch-all | Register 404/wildcard handlers last |
| `*splat` treated as a string | `segments.join is not a function` | It is an **array** in Express 5 |
| Arithmetic on `req.params.id` | `"2" + 1 === "21"` | Validate and coerce explicitly |
| Trusting `req.params.id` as a filename | Path traversal (`../../etc/passwd`) | Validate against an allowlist; use `path.basename` |
| Forgetting `next()` in a route middleware | The request hangs and eventually times out | Respond or call `next()` on every path |
| Same path registered twice by accident | The first silently wins for matching methods | Use a route table; print it at startup |
| `app.use('/api', router)` then `/api` unmatched | Router sees `/` and has no `'/'` route | Add a `router.get('/')` or a redirect |
| Testing with only one case (`/users/me`) | Case-insensitive routing hides missing routes | Use `app.set('case sensitive routing', true)` if your API contract is case-sensitive |
| Relying on `app._router.stack` | Breaks on an Express minor release | Keep your own route table |

---

## Exercise 3.1 — Fix the route file

```js
// File: broken-routes.js
import express from 'express';
const app = express();

app.use((req, res) => {
  res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } });
});

app.get('/api/notes', (req, res) => res.json({ data: [] }));
app.get('/api/notes/:id', (req, res) => res.json({ id: Number(req.params.id) + 1 }));
app.get('/api/notes/stats', (req, res) => res.json({ total: 42 }));
app.get('/api/notes/*', (req, res) => res.json({ fallback: req.params[0] }));
app.post('/api/notes', (req, res) => res.status(201).json({ title: req.body.title }));

app.listen(3000);
```

Six problems. Find them all.

<details>
<summary>Solution</summary>

| # | Problem | Effect | Fix |
| --- | --- | --- | --- |
| 1 | The 404 middleware is registered **first** | It ends every request; nothing below ever runs | Move it to the bottom |
| 2 | `/api/notes/:id` comes before `/api/notes/stats` | `/api/notes/stats` is unreachable — `id` becomes `'stats'` and `Number('stats') + 1` is `NaN` | Register `/api/notes/stats` first |
| 3 | `/api/notes/*` — bare wildcard | Startup crash on Express 5: `Missing parameter name` | `'/api/notes/*splat'`, and use `req.params.splat` (an array) |
| 4 | `express.json()` is never registered | `req.body` is `undefined` → `TypeError` on `POST /api/notes` | `app.use(express.json())` before the routes |
| 5 | No error handler | A thrown error returns Express's default HTML page | Add a 4-argument error middleware last |
| 6 | `app.listen(3000)` with no host and no `PORT` | Cannot inject a port in production; binds implicitly | `const port = Number(process.env.PORT ?? 3000); app.listen(port, '0.0.0.0')` |

```js
// File: fixed-routes.js
import express from 'express';

const app = express();
app.disable('x-powered-by');

// 1. Parsers and middleware first.
app.use(express.json({ limit: '100kb' }));

// 2. Literal paths before parameterised ones.
app.get('/api/notes/stats', (req, res) => res.json({ total: 42 }));

app.get('/api/notes', (req, res) => res.json({ data: [] }));
app.post('/api/notes', (req, res) => {
  const body = req.body ?? {};
  if (typeof body.title !== 'string' || body.title.trim() === '') {
    return res.status(422).json({
      error: { code: 'VALIDATION_ERROR', details: [{ field: 'title', message: 'required' }] },
    });
  }
  return res.status(201).json({ data: { id: '1', title: body.title.trim() } });
});

app.get('/api/notes/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id < 1) {
    return res.status(422).json({
      error: { code: 'VALIDATION_ERROR', details: [{ field: 'id', message: 'must be a positive integer' }] },
    });
  }
  return res.json({ data: { id } });
});

// 3. Named wildcard; splat is an array in Express 5.
app.get('/api/notes/*splat', (req, res) => {
  res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND', segments: req.params.splat } });
});

// 4. Terminal middleware, in order.
app.use((req, res) => {
  res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND', path: req.originalUrl } });
});

app.use((error, req, res, next) => {
  const statusCode = error.statusCode ?? 500;
  console.error(JSON.stringify({ level: 'error', message: error.message, path: req.originalUrl }));
  if (res.headersSent) return next(error);
  return res.status(statusCode).json({
    error: {
      code: error.code ?? 'INTERNAL_ERROR',
      message: statusCode >= 500 ? 'Something went wrong' : error.message,
    },
  });
});

const port = Number(process.env.PORT ?? 3000);
app.listen(port, '0.0.0.0', () => console.log(`listening on http://localhost:${port}`));
```

```bash
curl -s localhost:3000/api/notes/stats                  # {"total":42}   (no longer NaN)
curl -s localhost:3000/api/notes/7                       # {"data":{"id":7}}
curl -s localhost:3000/api/notes/abc                     # 422
curl -s -X POST localhost:3000/api/notes -H 'Content-Type: application/json' -d '{"title":"ok"}'
curl -s -X POST localhost:3000/api/notes -H 'Content-Type: application/json' -d '{}'   # 422
curl -s localhost:3000/api/notes/1/comments | head -1     # splat fallback (404 JSON)
curl -s localhost:3000/elsewhere                         # generic 404
```

</details>

---

## Exercise 3.2 — Design a versioned route table

Design and implement the routing for a bookmarks API:

```text
GET    /api/v1/bookmarks                 list (filter ?tag=, search ?q=, paginate)
POST   /api/v1/bookmarks                 create
GET    /api/v1/bookmarks/:id             read one
PATCH  /api/v1/bookmarks/:id             partial update
DELETE /api/v1/bookmarks/:id             delete
GET    /api/v1/bookmarks/stats           counts (must NOT be interpreted as an :id)
POST   /api/v1/bookmarks/:id/archive     action on a sub-resource
GET    /api/v1/users/:userId/bookmarks   a user's bookmarks (nested resource)
GET    /api/v1/tags                      list tags
GET    /api/v1/tags/*splat               nested tag paths, e.g. /tags/node/express
```

Requirements: 405 with the correct `Allow` header for unsupported methods on a known path, a JSON 404
for everything else, and a startup route print listing every route.

<details>
<summary>Solution</summary>

```js
// File: src/middleware/methodNotAllowed.js
export function methodNotAllowed(allowedMethods) {
  const allowed = [...new Set(allowedMethods.map((method) => method.toUpperCase()))];
  const allowHeader = [...allowed, 'HEAD', 'OPTIONS'].join(', ');

  return function methodNotAllowedHandler(req, res) {
    res.set('Allow', allowHeader);
    if (req.method === 'OPTIONS') return res.status(204).end();
    return res.status(405).json({
      error: {
        code: 'METHOD_NOT_ALLOWED',
        message: `${req.method} is not allowed for ${req.originalUrl}`,
        allowed,
      },
    });
  };
}
```

```js
// File: src/controllers/bookmarkController.js
/** Stubs — full controllers arrive in chapter 10. Every one ends the response. */
export const bookmarkController = {
  list: (req, res) => res.json({ data: [], meta: { total: 0 } }),
  create: (req, res) => res.status(201).json({ data: { id: '1' } }),
  getOne: (req, res) => res.json({ data: { id: req.params.id } }),
  update: (req, res) => res.json({ data: { id: req.params.id, updated: true } }),
  remove: (req, res) => res.status(204).end(),
  stats: (req, res) => res.json({ data: { total: 0, archived: 0 } }),
  archive: (req, res) => res.json({ data: { id: req.params.id, archived: true } }),
  listForUser: (req, res) => res.json({ data: [], meta: { userId: req.params.userId } }),
};

export const tagController = {
  list: (req, res) => res.json({ data: [] }),
  nested: (req, res) => res.json({ data: [], segments: req.params.splat }),
};
```

```js
// File: src/routes/routeTable.js
import { methodNotAllowed } from '../middleware/methodNotAllowed.js';

export function createRouteTable({ bookmarkController, tagController, healthHandler }) {
  return [
    { method: 'get', path: '/health', handlers: [healthHandler] },

    // Literal before parameterised — 'stats' must be reached before ':id'.
    { method: 'get', path: '/bookmarks/stats', handlers: [bookmarkController.stats] },
    { method: 'get', path: '/bookmarks', handlers: [bookmarkController.list] },
    { method: 'post', path: '/bookmarks', handlers: [bookmarkController.create] },
    { method: 'get', path: '/bookmarks/:id', handlers: [bookmarkController.getOne] },
    { method: 'patch', path: '/bookmarks/:id', handlers: [bookmarkController.update] },
    { method: 'delete', path: '/bookmarks/:id', handlers: [bookmarkController.remove] },
    { method: 'post', path: '/bookmarks/:id/archive', handlers: [bookmarkController.archive] },

    // Nested resource: a different :param name keeps the two routers independent.
    { method: 'get', path: '/users/:userId/bookmarks', handlers: [bookmarkController.listForUser] },

    // Wildcards must be named and are arrays of segments.
    { method: 'get', path: '/tags', handlers: [tagController.list] },
    { method: 'get', path: '/tags{/*splat}', handlers: [tagController.nested] },

    // 405 guards last within each path shape.
    { method: 'all', path: '/bookmarks', handlers: [methodNotAllowed(['GET', 'POST'])] },
    { method: 'all', path: '/bookmarks/:id', handlers: [methodNotAllowed(['GET', 'PATCH', 'DELETE'])] },
    { method: 'all', path: '/bookmarks/:id/archive', handlers: [methodNotAllowed(['POST'])] },
    { method: 'all', path: '/tags', handlers: [methodNotAllowed(['GET'])] },
  ];
}
```

```js
// File: src/routes/index.js
import { Router } from 'express';
import { createRouteTable } from './routeTable.js';

export function createApiRouter(dependencies) {
  const router = Router();
  const routeTable = createRouteTable(dependencies);

  for (const { method, path, handlers } of routeTable) {
    router[method](path, ...handlers);         // order of the table IS the matching order
  }

  return { router, routeTable };
}

/** Print route data without touching framework internals. */
export function printRouteTable(routeTable, { prefix = '/api/v1', write = console.log } = {}) {
  const rows = routeTable
    .filter((route) => route.method !== 'all')
    .map((route) => ({ method: route.method.toUpperCase(), path: prefix + route.path }));

  const width = Math.max(...rows.map((row) => row.method.length));
  for (const row of rows) write(`${row.method.padEnd(width)}  ${row.path}`);
  write(`\n${rows.length} routes registered`);
  return rows;
}
```

```js
// File: src/app.js
import express from 'express';
import { createApiRouter } from './routes/index.js';
import { bookmarkController, tagController } from './controllers/bookmarkController.js';

export function createApp({ config = {} } = {}) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: config.bodyLimit ?? '100kb' }));

  const { router, routeTable } = createApiRouter({
    bookmarkController,
    tagController,
    healthHandler: (req, res) => res.json({ status: 'ok' }),
  });

  app.use('/api/v1', router);

  // JSON 404 for everything the router did not handle.
  app.use((req, res) => {
    res.status(404).json({
      error: { code: 'ROUTE_NOT_FOUND', message: `${req.method} ${req.originalUrl} not found` },
    });
  });

  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    const statusCode = error.statusCode ?? 500;
    return res.status(statusCode).json({
      error: { code: error.code ?? 'INTERNAL_ERROR', message: error.message },
    });
  });

  return { app, routeTable };
}
```

```bash
# Verify every requirement
curl -s localhost:3000/api/v1/bookmarks/stats                 # {"data":{"total":0,"archived":0}}
curl -s localhost:3000/api/v1/bookmarks/abc                   # {"data":{"id":"abc"}} — not NaN
curl -s -X PUT localhost:3000/api/v1/bookmarks/1 -i | head -4 # 405 with Allow: GET, PATCH, DELETE, HEAD, OPTIONS
curl -s -X GET localhost:3000/api/v1/bookmarks/1/archive -i | head -4   # 405 with Allow: POST, HEAD, OPTIONS
curl -s localhost:3000/api/v1/tags/node/express               # {"data":[],"segments":["node","express"]}
curl -s localhost:3000/api/v1/tags                            # {"data":[]}
curl -s localhost:3000/api/v1/nope                            # JSON 404
```

**Why this is the right design**

| Decision | Reason |
| --- | --- |
| `/bookmarks/stats` before `/bookmarks/:id` | Otherwise `stats` is captured as an id — the single most common Express routing bug |
| Route table as data | Printing, testing and documenting routes needs no framework internals |
| 405 guards registered after real handlers | They must only see requests that everything else declined |
| `/tags{/*splat}` with braces | Makes the bare `/tags` route reachable by the wildcard entry as well |
| Distinct param names (`:userId`) | Mounted routers merge params; distinct names make ownership obvious |
| Wildcard segments read as an array | `req.params.splat` is `['node','express']` in Express 5 |

</details>

---

## What's next

You know how URLs map to handlers. Next: what each HTTP method *promises*, and which verb belongs in
which situation.

→ [04 — HTTP Methods](04-http-methods.md)
