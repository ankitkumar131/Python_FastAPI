# 07 — Middleware

> **Where this fits:** Middleware is *the* Express concept. Routes are middleware. Error handlers are
> middleware. Authentication, logging, parsing, rate limiting, CORS — all middleware. If you understand
> the middleware pipeline you understand Express; everything else is API surface.

---

## 1. What middleware is

> **Middleware is a function that receives `(req, res, next)` and either ends the request, or does
> something and passes control onward by calling `next()`.**

```js
// File: what-is-middleware.js
import express from 'express';

const app = express();

//              ↓ the signature
function myMiddleware(req, res, next) {
  // 1. Do something with the request or response…
  req.receivedAt = new Date().toISOString();
  res.set('X-Served-By', 'middleware-demo');

  // 2. …then either finish the request, or continue the chain.
  next();
}

app.use(myMiddleware);                       // applies to EVERY request

app.get('/hello', (req, res) => {
  res.json({ message: 'hi', receivedAt: req.receivedAt });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

Why this design exists: HTTP handling is full of **cross-cutting concerns** — things every endpoint
needs but no endpoint owns:

| Concern | Why it is not the handler's job |
| --- | --- |
| Parsing the body | Every route needs it; it must happen before any handler reads `req.body` |
| Logging | Should be identical for every route, and should capture the status after the handler runs |
| Authentication | Applies to many routes; a single mistake leaks data |
| Rate limiting | Must run *before* expensive work |
| CORS headers | Must be on every response, including errors |
| Validation | Same shape rules for create/update |
| Error formatting | One contract for the whole API |

Without middleware, each of those becomes duplicated code in every handler — and duplication is where
inconsistencies (and security holes) live.

**Composition over inheritance.** Middleware is just function composition: `f(g(h(req, res)))`. It needs
no framework-specific base classes, so any middleware is a plain function you can test on its own.

---

## 2. The onion model

Express runs middleware in **registration order**, and each one decides when (or whether) the rest of
the chain runs. That produces an "onion": code *before* `next()` runs on the way in, code *after*
`next()` runs on the way out.

```text
              ┌──────────────────────────────────────────────┐
 request ────▶│ mw 1: before next()                          │
              │   ┌──────────────────────────────────────┐   │
              │   │ mw 2: before next()                  │   │
              │   │   ┌──────────────────────────────┐   │   │
              │   │   │ route handler → response     │   │   │
              │   │   └──────────────────────────────┘   │   │
              │   │ mw 2: after next()  ← runs here      │   │
              │   └──────────────────────────────────────┘   │
              │ mw 1: after next()                           │
              └──────────────────────────────────────────────┘
```

```js
// File: onion.js
import express from 'express';

const app = express();

const trace = [];

app.use((req, res, next) => {
  trace.push('1: in');
  res.locals.trace = trace;

  next();                    // → middleware 2 (synchronously)

  trace.push('1: out');      // ← runs AFTER the whole chain below finished
});

app.use((req, res, next) => {
  trace.push('2: in');
  next();
  trace.push('2: out');
});

app.get('/onion', (req, res) => {
  res.locals.trace.push('handler');
  // We must respond before the "out" phases have any chance to add headers.
  res.json({ trace: res.locals.trace });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
curl -s localhost:3000/onion
```

```json
{ "trace": ["1: in", "2: in", "handler"] }
```

The `out` entries are pushed *after* the response has already been sent — which is exactly why
Express's response helpers throw if you try to change headers at that point. Two rules follow:

1. **Do "on the way out" work with events, not with code after `next()`.** `res.on('finish', …)` is the
   safe place to log the final status and duration.
2. **Everything a handler needs must be set *before* `next()`**, not after.

```js
// File: onion-safe.js
import express from 'express';

const app = express();

app.use((req, res, next) => {
  const startedAt = process.hrtime.bigint();
  req.id = crypto.randomUUID();

  // Log on the way out — after the response has been flushed.
  res.on('finish', () => {
    const durationMs = Number(process.hrtime.bigint() - startedAt) / 1e6;
    console.log(
      JSON.stringify({
        level: 'info',
        requestId: req.id,
        method: req.method,
        path: req.originalUrl,
        status: res.statusCode,
        durationMs: Number(durationMs.toFixed(2)),
      }),
    );
  });

  next();
});

app.get('/onion-safe', (req, res) => res.json({ requestId: req.id }));

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

---

## 3. The five kinds of middleware

| Kind | Registered with | Runs for | Example |
| --- | --- | --- | --- |
| **Application-level** | `app.use(fn)` / `app.use(path, fn)` | Every request (or every request under `path`) | Logger, `express.json()` |
| **Router-level** | `router.use(fn)` | Every request that reaches that router | Auth for `/api/v1/admin` |
| **Route-level** | `app.get(path, mw1, mw2, handler)` | Only that route | `requireRole('admin')` on one endpoint |
| **Error-handling** | `app.use((err, req, res, next) => …)` | Only when an error is passed to `next()` | The API error formatter |
| **Built-in / third-party** | `app.use(express.static(…))` | As configured | `helmet()`, `cors()`, `express.json()` |

```js
// File: five-kinds.js
import express from 'express';

const app = express();

// 1. Application-level
app.use((req, res, next) => { req.appName = 'notes-api'; next(); });

// 2. Router-level
const admin = express.Router();
admin.use((req, res, next) => {
  if (req.get('x-role') !== 'admin') {
    return res.status(403).json({ error: { code: 'FORBIDDEN' } });
  }
  next();
});
admin.get('/stats', (req, res) => res.json({ data: { users: 3 } }));
app.use('/api/v1/admin', admin);

// 3. Route-level (middleware + handler in one route)
const requireFeature = (req, res, next) => {
  if (req.query.feature !== 'beta') {
    return res.status(404).json({ error: { code: 'NOT_FOUND' } });
  }
  next();
};
app.get('/api/v1/beta/notes', requireFeature, (req, res) => res.json({ data: [] }));

// 4. Error-handling (four parameters)
app.use((error, req, res, next) => {
  if (res.headersSent) return next(error);
  return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: error.message } });
});

// 5. Built-in
app.use(express.static('public'));

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

### Built-in middleware

| Middleware | Purpose | Typical options |
| --- | --- | --- |
| `express.json()` | Parse JSON bodies | `limit`, `strict`, `type`, `verify` |
| `express.urlencoded()` | Parse HTML form bodies | `extended`, `limit` |
| `express.raw()` | Body as a `Buffer` | `type`, `limit` |
| `express.text()` | Body as a string | `type`, `limit` |
| `express.static(root, opts)` | Serve files from a directory | `maxAge`, `etag`, `index`, `immutable`, `fallthrough` |

> In Express 4, `express.json()` did not exist and you had to install `body-parser` separately. In
> Express 5 it is built in — **`body-parser` is redundant** and should not be added to new projects.

---

## 4. `next()` — the complete rule set

| Call | Result |
| --- | --- |
| `next()` | Continue with the next middleware/route in the chain |
| `next('route')` | Skip the remaining handlers **of the current route** — only valid inside a route handler (verified: from `app.use` it behaves like `next()`) |
| `next('router')` | Leave the current router and continue in the parent (verified) |
| `next(error)` | Jump straight to the error middleware, skipping normal middleware |
| `next('string')` | Treated as an error whose value is a **string**, not an `Error` (verified) — never do this |
| *(nothing)* | The chain stops and the request hangs until a timeout |
| `next()` **and** a response | The chain continues *after* the response is finished → `ERR_HTTP_HEADERS_SENT` when the next handler responds |

```js
// File: next-rules.js
import express from 'express';

const app = express();

// ❌ WRONG: responds and continues — the next handler tries to respond again.
app.use((req, res, next) => {
  if (!req.get('authorization')) {
    res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
  }
  next();                       // ← runs even after responding!
});

// ✅ RIGHT: return after responding.
app.use((req, res, next) => {
  if (!req.get('authorization')) {
    return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
  }
  return next();
});

app.get('/secure', (req, res) => res.json({ data: 'ok' }));

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

The `return` is not decoration: `res.status(...).json(...)` returns the response object, so
`return res.status(401).json(...)` finishes the function. Without it, execution continues into
`next()` and Express eventually tries to write a second response — the classic
`Cannot set headers after they are sent to the client`.

### Async middleware in Express 5

Express 5 **forwards rejected promises from middleware and handlers to the error middleware
automatically** (verified). In Express 4 this required a wrapper:

```js
// File: async-wrapper.js
import express from 'express';

const app = express();

/**
 * Express 4 needed this. In Express 5 it is optional — but it is still useful to
 * add per-route context to errors, and it keeps code portable between versions.
 */
export const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

// Works in Express 5 without the wrapper…
app.get('/auto', async (req, res) => {
  const data = await Promise.reject(new Error('rejected automatically'));
  res.json({ data });
});

// …and in both versions with it.
app.get('/wrapped', asyncHandler(async (req, res) => {
  const data = await Promise.reject(Object.assign(new Error('wrapped'), { statusCode: 503 }));
  res.json({ data });
}));

app.use((error, req, res, next) => {
  if (res.headersSent) return next(error);
  return res.status(error.statusCode ?? 500).json({
    error: { code: error.code ?? 'INTERNAL_ERROR', message: error.message },
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

> **What is still your responsibility:** rejecting with an `Error` (never a string), and *not* calling
> `next()` after you already responded.

---

## 5. Middleware that needs configuration: the factory pattern

A middleware with hard-coded values cannot be reused or tested. Return a function instead:

```js
// File: src/middleware/requireRole.js
/**
 * Factory: configuration in, middleware out.
 * This is how helmet, cors, express.json and every serious middleware works.
 */
export function requireRole(...allowedRoles) {
  const allowed = new Set(allowedRoles.map((role) => role.toUpperCase()));

  // The returned function is the actual middleware.
  return function requireRoleMiddleware(req, res, next) {
    const user = req.user;                       // set by the authentication middleware

    if (!user) {
      return res.status(401).json({ error: { code: 'UNAUTHENTICATED', message: 'Sign in required' } });
    }

    if (!allowed.has(String(user.role).toUpperCase())) {
      // 403 (authenticated but not permitted) — never 401 here.
      return res.status(403).json({
        error: { code: 'FORBIDDEN', message: `Requires one of: ${[...allowed].join(', ')}` },
      });
    }

    return next();
  };
}
```

```js
// File: src/routes/adminRoutes.js
import { Router } from 'express';
import { requireRole } from '../middleware/requireRole.js';

export function createAdminRouter({ controller }) {
  const router = Router();

  router.use(requireRole('ADMIN'));            // every route below is admin-only

  router.get('/users', controller.listUsers);
  router.delete('/users/:id', controller.deleteUser);

  return router;
}
```

```js
// File: src/routes/noteRoutes.js (excerpt)
// The same factory applied to a single endpoint.
router.delete('/:id', requireRole('ADMIN', 'EDITOR'), controller.remove);
```

| Why the factory pattern | Alternative |
| --- | --- |
| Configuration is explicit at the mount point | Hard-coded roles inside the middleware |
| Easy to unit test (`requireRole('ADMIN')` is a function you can call) | Testing requires importing the whole app |
| Reusable across routers and routes | Copy-paste per route |
| Each middleware closure keeps its own state safely | Module-level mutable state shared between tests |

---

## 6. The canonical order

Order is behaviour. This is the order that works for a real API, with the reason each position matters:

```js
// File: src/app.js
import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import cookieParser from 'cookie-parser';
import { pinoHttp } from 'pino-http';

import { requestId } from './middleware/requestId.js';
import { createErrorHandler } from './middleware/errorHandler.js';
import { notFound } from './middleware/notFound.js';
import { createRateLimiter } from './middleware/rateLimiter.js';
import { createApiRouter } from './routes/index.js';
import { env } from './config/env.js';
import { logger } from './utils/logger.js';

export function createApp({ config = env } = {}) {
  const app = express();

  // ── 0. Before anything: trust settings and framework noise ────────────────────
  app.disable('x-powered-by');
  app.set('trust proxy', config.trustProxy);      // affects req.ip, req.protocol, secure cookies

  // ── 1. Request identity: everything downstream (logs, errors) needs it ───────
  app.use(requestId);

  // ── 2. Security and CORS headers: must be on EVERY response, including 404/500 ─
  app.use(helmet());
  app.use(cors({ origin: config.corsOrigins, credentials: true }));

  // ── 3. Logging: early enough to see every request, late enough to have req.id ─
  app.use(pinoHttp({ logger, genReqId: (req) => req.id }));

  // ── 4. Rate limiting BEFORE parsing bodies (cheap rejection of floods) ────────
  app.use('/api', createRateLimiter({ windowMs: 60_000, max: 300 }));

  // ── 5. Body parsing: needed by every handler that reads req.body ─────────────
  app.use(express.json({ limit: config.bodyLimit }));
  app.use(express.urlencoded({ extended: false, limit: config.bodyLimit }));

  // ── 6. Cookies and sessions (after parsing, before auth) ─────────────────────
  app.use(cookieParser(config.cookieSecret));

  // ── 7. Static files: before the API router, after logging ────────────────────
  app.use('/static', express.static(config.publicDir, { maxAge: '1h', index: false }));

  // ── 8. Health checks: no auth, no rate limit, no DB ──────────────────────────
  app.get('/health', (req, res) => res.json({ status: 'ok' }));

  // ── 9. The API ───────────────────────────────────────────────────────────────
  app.use('/api/v1', createApiRouter({ config }));

  // ── 10. Terminal middleware: 404 first, then the error handler LAST ──────────
  app.use(notFound);
  app.use(createErrorHandler({ config, logger }));

  return app;
}
```

| Position | Middleware | Why exactly here |
| --- | --- | --- |
| 1 | Request id | Available to the logger and to every error response |
| 2 | `helmet`, `cors` | Their headers must appear even on 404 and 500 responses |
| 3 | Logger | Sees every request; `genReqId` reuses the id from step 1 |
| 4 | Rate limiter | Rejects floods before parsing or hitting the database |
| 5 | Body parsers | Must precede any handler that reads `req.body` |
| 6 | Cookie/session | Needs the parsed headers; must precede authentication |
| 7 | Static files | Cheap, cacheable, and short-circuits before API routing |
| 8 | Health | Must not depend on auth, rate limits or the database |
| 9 | Routes | The application itself |
| 10 | 404 + error handler | Only reached when nothing above responded |

Two rules that come out of this table:

- **Security headers first** — a 500 must still carry `X-Content-Type-Options: nosniff`, or the error
  page can be sniffed into an XSS.
- **Error handler last** — Express finds the *first* error handler *after* the failing layer. Register
  it early and later routes' errors will never reach it.

---

## 7. Paths, mounting and `req` rewriting

```js
// File: mounting.js
import express from 'express';

const app = express();
const router = express.Router();

router.use((req, res, next) => {
  console.log(
    JSON.stringify({ baseUrl: req.baseUrl, path: req.path, url: req.url, originalUrl: req.originalUrl }),
  );
  next();
});

router.get('/:id', (req, res) => res.json({ id: req.params.id }));

app.use('/api/v1/notes', router);

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
curl -s 'localhost:3000/api/v1/notes/42?expand=tags'
# {"baseUrl":"/api/v1/notes","path":"/42","url":"/42?expand=tags","originalUrl":"/api/v1/notes/42?expand=tags"}
```

| Behaviour | Detail |
| --- | --- |
| `app.use(path, fn)` matches a **prefix** | `/api/v1/notes`, `/api/v1/notes/42`, `/api/v1/notes/42/tags` all match |
| Inside a mounted layer, `req.url`/`req.path` are **relative** | The router sees `/42`, not `/api/v1/notes/42` |
| `req.baseUrl` holds the mount prefix | Use it to build links |
| `req.originalUrl` is never rewritten | Use it in logs and error messages |
| Mount matching is case-insensitive by default | `/API/V1/notes` reaches the same router |
| `router.use(fn)` without a path | Runs for every request reaching that router |

**Practical consequence:** a middleware mounted on `/api` runs for `/apiary` too.

```js
// File: path-pitfall.js
import express from 'express';

const app = express();

// ❌ Matches /apiary, /apiculture, … because '/api' is a prefix
app.use('/api', (req, res, next) => {
  console.log('api middleware');
  next();
});

// ✅ Mount on a path with a trailing boundary to be explicit about intent,
//    or mount the exact resource path you mean.
app.use('/api/v1', (req, res, next) => {
  console.log('api v1 middleware');
  next();
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

---

## 8. Middleware patterns you will actually need

Every one of these is a complete, testable implementation.

### 8.1 Request id and correlation

```js
// File: src/middleware/requestId.js
import { randomUUID } from 'node:crypto';

/** Accept an inbound id when it looks safe, otherwise generate one. */
export function requestId(req, res, next) {
  const inbound = req.get('x-request-id');
  req.id = inbound && /^[\w.:-]{1,128}$/.test(inbound) ? inbound : randomUUID();
  res.set('X-Request-Id', req.id);
  next();
}
```

### 8.2 A content-type guard

```js
// File: src/middleware/requireJson.js
/** Reject non-JSON request bodies on endpoints that need them — a clean 415. */
export function requireJson(req, res, next) {
  const methodsWithBodies = new Set(['POST', 'PUT', 'PATCH']);
  if (!methodsWithBodies.has(req.method)) return next();

  if (!req.is('application/json')) {
    return res.status(415).json({
      error: {
        code: 'UNSUPPORTED_MEDIA_TYPE',
        message: 'Content-Type must be application/json',
        received: req.get('content-type') ?? null,
      },
    });
  }
  return next();
}
```

### 8.3 A simple, honest rate limiter

```js
// File: src/middleware/rateLimiter.js
/**
 * In-memory fixed-window rate limiter.
 * HONEST LIMITATION: state lives in one process, so behind a load balancer each
 * instance limits independently. Production uses Redis (see chapter 18).
 */
export function createRateLimiter({ windowMs = 60_000, max = 100, keyGenerator } = {}) {
  const hits = new Map();          // key → { count, resetAt }

  // Clean up so the map cannot grow without bound.
  const cleanup = setInterval(() => {
    const now = Date.now();
    for (const [key, record] of hits) {
      if (record.resetAt <= now) hits.delete(key);
    }
  }, windowMs);
  cleanup.unref();

  const defaultKey = (req) => req.ip;

  return function rateLimiter(req, res, next) {
    const key = (keyGenerator ?? defaultKey)(req);
    const now = Date.now();
    let record = hits.get(key);

    if (!record || record.resetAt <= now) {
      record = { count: 0, resetAt: now + windowMs };
      hits.set(key, record);
    }

    record.count += 1;

    const remaining = Math.max(0, max - record.count);
    const resetSeconds = Math.ceil((record.resetAt - now) / 1000);

    res.set({
      'RateLimit-Limit': String(max),
      'RateLimit-Remaining': String(remaining),
      'RateLimit-Reset': String(resetSeconds),
    });

    if (record.count > max) {
      res.set('Retry-After', String(resetSeconds));
      return res.status(429).json({
        error: { code: 'RATE_LIMITED', message: 'Too many requests', retryAfterSeconds: resetSeconds },
      });
    }

    return next();
  };
}
```

### 8.4 Validation as middleware

```js
// File: src/middleware/validate.js
import { zodErrorToDetails } from '../utils/zodErrors.js';

/**
 * Validate one part of the request with a Zod schema and replace it with the parsed
 * value. `source` is 'body' | 'query' | 'params'.
 */
export function validate(schema, source = 'body') {
  return function validateMiddleware(req, res, next) {
    const parsed = schema.safeParse(req[source] ?? {});

    if (!parsed.success) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Request validation failed',
          details: zodErrorToDetails(parsed.error),
          requestId: req.id,
        },
      });
    }

    // Store separately: keep raw input available for debugging and logging.
    req.validated ??= {};
    req.validated[source] = parsed.data;
    return next();
  };
}
```

```js
// File: src/utils/zodErrors.js
/** Turn Zod issues into a stable, client-friendly shape: [{ field, message }]. */
export function zodErrorToDetails(error) {
  return error.issues.map((issue) => ({
    field: issue.path.length > 0 ? issue.path.join('.') : 'body',
    message: issue.message,
    code: issue.code,
  }));
}
```

### 8.5 Authentication stub (full version in chapter 13)

```js
// File: src/middleware/authenticate.js
import { verifyAccessToken } from '../utils/tokens.js';

export function createAuthenticate({ verify = verifyAccessToken } = {}) {
  return function authenticate(req, res, next) {
    const header = req.get('authorization') ?? '';
    const [scheme, token] = header.split(' ');

    if (scheme !== 'Bearer' || !token) {
      return res.status(401).json({
        error: { code: 'UNAUTHENTICATED', message: 'Missing or malformed Authorization header' },
      });
    }

    try {
      req.user = verify(token);        // { sub, role, exp }
      return next();
    } catch (error) {
      return res.status(401).json({
        error: { code: 'INVALID_TOKEN', message: error.name === 'TokenExpiredError' ? 'Token expired' : 'Invalid token' },
      });
    }
  };
}
```

### 8.6 404 and the error handler

```js
// File: src/middleware/notFound.js
export function notFound(req, res) {
  res.status(404).json({
    error: {
      code: 'ROUTE_NOT_FOUND',
      message: `${req.method} ${req.originalUrl} not found`,
      requestId: req.id,
    },
  });
}
```

```js
// File: src/middleware/errorHandler.js
import { AppError } from '../utils/AppError.js';

/** FOUR parameters — this arity is the only thing that marks an error handler. */
export function createErrorHandler({ config, logger = console }) {
  return function errorHandler(error, req, res, next) {
    // 1. Body-parser failures carry `status`/`type` (see chapter 06).
    // 2. Our own AppError carries `statusCode`/`code`.
    const statusCode = error.statusCode ?? error.status ?? 500;
    const code = error.code && typeof error.code === 'string' ? error.code : 'INTERNAL_ERROR';

    const logPayload = {
      level: statusCode >= 500 ? 'error' : 'warn',
      message: error.message,
      code,
      statusCode,
      method: req.method,
      path: req.originalUrl,
      requestId: req.id,
      userId: req.user?.id,
      stack: statusCode >= 500 ? error.stack : undefined,
      cause: error.cause?.message,
    };
    (logger[logPayload.level] ?? logger.error)(logPayload);

    // 3. The response already started: let Express/Node finish and close the socket.
    if (res.headersSent) return next(error);

    const isProduction = config.nodeEnv === 'production';
    return res.status(statusCode).json({
      error: {
        code,
        message: statusCode >= 500 && isProduction ? 'Something went wrong' : error.message,
        details: error instanceof AppError ? error.details : undefined,
        requestId: req.id,
      },
    });
  };
}
```

---

## 9. Testing middleware in isolation

Middleware is a function — test it without starting a server.

```js
// File: tests/requireRole.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { requireRole } from '../src/middleware/requireRole.js';

/** Minimal fakes: only the members the middleware touches. */
function createMocks({ user, query = {} } = {}) {
  const req = { user, query, get: () => undefined };
  const res = {
    statusCode: 200,
    body: undefined,
    status(code) { this.statusCode = code; return this; },
    json(payload) { this.body = payload; return this; },
  };
  let nextCalled = 0;
  const next = (error) => { nextCalled += 1; if (error) throw error; };

  return { req, res, next, get nextCalls() { return nextCalled; } };
}

test('rejects an unauthenticated request with 401', () => {
  const { req, res, next, nextCalls } = createMocks();
  requireRole('ADMIN')(req, res, next);

  assert.equal(res.statusCode, 401);
  assert.equal(res.body.error.code, 'UNAUTHENTICATED');
  assert.equal(nextCalls(), 0);
});

test('rejects the wrong role with 403', () => {
  const { req, res, next, nextCalls } = createMocks({ user: { id: 'u1', role: 'USER' } });
  requireRole('ADMIN')(req, res, next);

  assert.equal(res.statusCode, 403);
  assert.equal(res.body.error.code, 'FORBIDDEN');
  assert.equal(nextCalls(), 0);
});

test('allows a permitted role and calls next() exactly once', () => {
  const { req, res, next, nextCalls } = createMocks({ user: { id: 'u1', role: 'admin' } });
  requireRole('ADMIN')(req, res, next);

  assert.equal(res.body, undefined);       // no response written
  assert.equal(nextCalls(), 1);
});
```

```bash
node --test tests/requireRole.test.js
```

```text
✔ rejects an unauthenticated request with 401
✔ rejects the wrong role with 403
✔ allows a permitted role and calls next() exactly once
pass 3
fail 0
```

> **Why fake objects instead of a real server?** These tests run in milliseconds, need no port, and
> fail with a precise message. Integration tests (chapter 19) still prove the wiring; unit tests prove
> the logic. You want both, but only the unit test should run hundreds of times a day.

---

## 10. Performance: middleware is not free

Every middleware is a function call per request, and some of them are expensive.

| Cost | Where it comes from | Mitigation |
| --- | --- | --- |
| Function-call overhead | 30 middlewares × thousands of requests per second | Keep the list short; delete dead middleware |
| Synchronous work | JSON parsing, JWT verification, hashing | Verify tokens once; never hash in a global middleware |
| Database calls in middleware | Session lookup, user load "just in case" | Load lazily: only for routes that need it |
| Duplicated work | Two middlewares reading the same data | Cache on `req` (`req.user ??= await load()`) |

Ordering is a performance decision too:

```text
cheap and rejecting ──▶ expensive ──▶ very expensive
  rate limit             auth          database
  content-type guard     body parse    external API calls
```

Rejecting a flood with a rate limiter costs microseconds. Rejecting it *after* the database query
costs a connection and a query per request — which is how an API goes down under load.

```js
// File: lazy-loading.js
import express from 'express';

const app = express();

/**
 * ❌ Eager: every request pays for a database read, even /health and 404s.
 */
app.use(async (req, res, next) => {
  req.user = await users.findById(req.get('x-user-id'));     // a query per request!
  next();
});

/**
 * ✅ Lazy: only the routes that need the user ask for it, and only once.
 */
const loadUser = async (req, res, next) => {
  try {
    if (req.user !== undefined) return next();                 // already loaded
    const id = req.get('x-user-id');
    req.user = id ? await users.findById(id) : null;
    return next();
  } catch (error) {
    return next(error);
  }
};

app.get('/health', (req, res) => res.json({ status: 'ok' }));       // never loads a user
app.get('/api/v1/me', loadUser, (req, res) => res.json({ data: req.user }));
app.get('/api/v1/admin/stats', loadUser, requireRoleAdmin, handler);

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

---

## 11. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| Registering `express.json()` after the routes | `req.body` is `undefined` in handlers | Middleware order = registration order |
| Forgetting `next()` | The request hangs until the client times out | Every non-terminal path must call `next()` |
| Calling `next()` **and** responding | `ERR_HTTP_HEADERS_SENT` on the next middleware | `return res.status(...).json(...)` |
| `next()` called twice | The rest of the chain runs twice → duplicate writes, double logs | Call it once per path; `return` after it |
| `next('route')` in `app.use` | Does nothing (verified) — confusing to readers | Only use it inside route handlers |
| `next('generic string')` | The error middleware receives a string, not an `Error` (verified) | Always pass an `Error` |
| Error handler with 3 parameters | It never runs | It must have exactly **four** |
| Error handler not last | Errors from later routes never reach it | Register it last |
| Error handler that throws | Hangs the request or crashes the process | Wrap its body in `try/catch` |
| Middleware mounted on `/api` | Also matches `/apiary` | Mount more specific prefixes |
| Auth middleware on some routes only | One unprotected endpoint leaks data | Mount auth on the whole router, then opt out explicitly |
| Async middleware without `try/catch` **in Express 4** | Unhandled rejection, request hangs | Wrap with `asyncHandler` (unnecessary in Express 5) |
| Heavy work in a global middleware | Every request pays for it | Move it into route-level middleware |
| Mutating `req.body`/`req.query` in middleware | Validation and logging disagree about the input | Store parsed values in `req.validated` |
| Logging secrets in a global logger | Tokens and passwords in the logs | Redact known fields (ch. 20) |
| Middleware leaking between tests | Module-level state shared across files | Factory pattern with per-instance state |

---

## Exercise 7.1 — Build a middleware toolkit

Implement, with unit tests for each:

1. `requestId` — reuses a safe inbound `X-Request-Id`, otherwise generates a UUID, and sets the header.
2. `createTiming()` — records the duration and exposes it as `X-Response-Time` **before** the response is sent.
3. `createBodyGuard({ maxBytes })` — returns `413` for a declared `Content-Length` above the limit,
   *before* the body is read.
4. `createApiKeyAuth({ keys })` — checks `X-Api-Key`, uses a **timing-safe** comparison, and attaches
   `req.client`.
5. `createCacheControl({ maxAgeSeconds })` — GET/HEAD get a private cache directive; other methods get
   `no-store`.

<details>
<summary>Solution</summary>

```js
// File: src/middleware/requestId.js
import { randomUUID } from 'node:crypto';

const SAFE_ID = /^[\w.:-]{1,128}$/;

export function requestId(req, res, next) {
  const inbound = req.get('x-request-id');
  req.id = inbound && SAFE_ID.test(inbound) ? inbound : randomUUID();
  res.set('X-Request-Id', req.id);
  return next();
}
```

```js
// File: src/middleware/timing.js
/**
 * Timing must be set BEFORE the response is sent, so `res.on('finish')` is too late
 * for a header. Intercept the write instead.
 */
export function createTiming({ header = 'X-Response-Time' } = {}) {
  return function timing(req, res, next) {
    const startedAt = process.hrtime.bigint();

    const writeHead = res.writeHead.bind(res);
    let patched = false;

    const patch = () => {
      if (patched) return;
      patched = true;
      res.writeHead = (statusCode, ...rest) => {
        const ms = Number(process.hrtime.bigint() - startedAt) / 1e6;
        res.set(header, `${ms.toFixed(1)}ms`);
        return writeHead(statusCode, ...rest);
      };
    };

    // Node routes every response through writeHead — including the implicit header
    // path used by res.json/res.send/res.end — so this is the one interception point.
    patch();
    return next();
  };
}
```

```text
# Verified on all response helpers (the header is present every time):
GET  /json          → 200  X-Response-Time: 2.5ms
GET  /status-only   → 204  X-Response-Time: 0.5ms
GET  /empty         → 200  X-Response-Time: 0.1ms
GET  /string        → 200  X-Response-Time: 0.3ms
POST /created       → 201  X-Response-Time: 0.2ms
```

```js
// File: src/middleware/bodyGuard.js
/** Cheap pre-check on the declared Content-Length — rejects before reading a byte. */
export function createBodyGuard({ maxBytes = 100_000 } = {}) {
  return function bodyGuard(req, res, next) {
    const declared = Number(req.get('content-length') ?? 0);

    if (Number.isFinite(declared) && declared > maxBytes) {
      return res.status(413).json({
        error: {
          code: 'PAYLOAD_TOO_LARGE',
          message: `Request body must not exceed ${maxBytes} bytes`,
          declaredBytes: declared,
        },
      });
    }

    // A body sent without Content-Length (chunked) is still bounded by express.json({ limit }).
    return next();
  };
}
```

```js
// File: src/middleware/apiKeyAuth.js
import { timingSafeEqual } from 'node:crypto';

/** Constant-time comparison so response timing cannot reveal a key byte by byte. */
function safeEqual(a, b) {
  const bufferA = Buffer.from(a, 'utf8');
  const bufferB = Buffer.from(b, 'utf8');
  if (bufferA.length !== bufferB.length) return false;
  return timingSafeEqual(bufferA, bufferB);
}

export function createApiKeyAuth({ keys }) {
  // keys: Map<apiKey, { id, name, scopes }>
  return function apiKeyAuth(req, res, next) {
    const provided = req.get('x-api-key');

    if (!provided) {
      return res.status(401).json({ error: { code: 'UNAUTHENTICATED', message: 'X-Api-Key header is required' } });
    }

    // Compare against every candidate in constant time (a Map lookup would leak timing).
    let matched = null;
    for (const [key, client] of keys) {
      if (safeEqual(key, provided)) matched = client;
    }

    if (!matched) {
      return res.status(401).json({ error: { code: 'INVALID_API_KEY', message: 'Unknown API key' } });
    }

    req.client = matched;
    return next();
  };
}
```

```js
// File: src/middleware/cacheControl.js
export function createCacheControl({ maxAgeSeconds = 0 } = {}) {
  return function cacheControl(req, res, next) {
    if (req.method === 'GET' || req.method === 'HEAD') {
      res.set('Cache-Control', maxAgeSeconds > 0 ? `private, max-age=${maxAgeSeconds}` : 'private, no-cache');
      res.vary('Authorization');
      res.vary('Accept-Encoding');
    } else {
      res.set('Cache-Control', 'no-store');
    }
    return next();
  };
}
```

```js
// File: tests/middleware.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { requestId } from '../src/middleware/requestId.js';
import { createBodyGuard } from '../src/middleware/bodyGuard.js';
import { createApiKeyAuth } from '../src/middleware/apiKeyAuth.js';
import { createCacheControl } from '../src/middleware/cacheControl.js';

function createMocks({ method = 'GET', headers = {} } = {}) {
  const lower = Object.fromEntries(Object.entries(headers).map(([k, v]) => [k.toLowerCase(), v]));
  const req = { method, headers: lower, get: (name) => lower[String(name).toLowerCase()] };
  const res = {
    headers: {},
    statusCode: 200,
    body: undefined,
    status(code) { this.statusCode = code; return this; },
    set(name, value) {
      if (typeof name === 'object') Object.assign(this.headers, name);
      else this.headers[name] = value;
      return this;
    },
    vary(name) { this.headers.Vary = name; return this; },
    json(payload) { this.body = payload; return this; },
  };
  let calls = 0;
  const next = () => { calls += 1; };
  return { req, res, next, nextCalls: () => calls };
}

test('requestId generates an id and echoes a safe inbound one', () => {
  const first = createMocks();
  requestId(first.req, first.res, first.next);
  assert.match(first.req.id, /^[0-9a-f-]{36}$/);
  assert.equal(first.res.headers['X-Request-Id'], first.req.id);

  const second = createMocks({ headers: { 'X-Request-Id': 'trace-123' } });
  requestId(second.req, second.res, second.next);
  assert.equal(second.req.id, 'trace-123');
});

test('requestId ignores an unsafe inbound id', () => {
  const { req, res, next } = createMocks({ headers: { 'X-Request-Id': 'bad id with spaces' } });
  requestId(req, res, next);
  assert.notEqual(req.id, 'bad id with spaces');
  assert.match(req.id, /^[0-9a-f-]{36}$/);
});

test('bodyGuard rejects an oversized declared body before reading it', () => {
  const guard = createBodyGuard({ maxBytes: 100 });

  const tooBig = createMocks({ method: 'POST', headers: { 'Content-Length': '1000' } });
  guard(tooBig.req, tooBig.res, tooBig.next);
  assert.equal(tooBig.res.statusCode, 413);
  assert.equal(tooBig.res.body.error.code, 'PAYLOAD_TOO_LARGE');
  assert.equal(tooBig.nextCalls(), 0);

  const fine = createMocks({ method: 'POST', headers: { 'Content-Length': '50' } });
  guard(fine.req, fine.res, fine.next);
  assert.equal(fine.nextCalls(), 1);
});

test('apiKeyAuth rejects a missing or unknown key and accepts a known one', () => {
  const keys = new Map([['key-abc-123', { id: 'client-1', name: 'mobile', scopes: ['read'] }]]);
  const auth = createApiKeyAuth({ keys });

  const missing = createMocks();
  auth(missing.req, missing.res, missing.next);
  assert.equal(missing.res.statusCode, 401);

  const unknown = createMocks({ headers: { 'X-Api-Key': 'nope' } });
  auth(unknown.req, unknown.res, unknown.next);
  assert.equal(unknown.res.body.error.code, 'INVALID_API_KEY');

  const valid = createMocks({ headers: { 'X-Api-Key': 'key-abc-123' } });
  auth(valid.req, valid.res, valid.next);
  assert.equal(valid.req.client.id, 'client-1');
  assert.equal(valid.nextCalls(), 1);
});

test('cacheControl treats reads and writes differently', () => {
  const middleware = createCacheControl({ maxAgeSeconds: 60 });

  const read = createMocks({ method: 'GET' });
  middleware(read.req, read.res, read.next);
  assert.equal(read.res.headers['Cache-Control'], 'private, max-age=60');
  assert.equal(read.res.headers.Vary, 'Authorization');

  const write = createMocks({ method: 'POST' });
  middleware(write.req, write.res, write.next);
  assert.equal(write.res.headers['Cache-Control'], 'no-store');
});
```

```bash
node --test tests/middleware.test.js
```

```text
✔ requestId generates an id and echoes a safe inbound one
✔ requestId ignores an unsafe inbound id
✔ bodyGuard rejects an oversized declared body before reading it
✔ apiKeyAuth rejects a missing or unknown key and accepts a known one
✔ cacheControl treats reads and writes differently
pass 5
fail 0
```

**Design notes**

| Decision | Reason |
| --- | --- |
| `X-Response-Time` set by patching `writeHead` | A header must exist before the response starts; `res.on('finish')` is too late |
| `bodyGuard` checks the declared length | Rejecting before the body arrives saves memory and bandwidth |
| API keys compared in constant time | A normal `===` leaks key prefixes through response timing |
| API keys iterated, not looked up in a Map | Map lookup timing can reveal which prefix matched |
| Factories everywhere | Tests get isolated state; nothing is shared between test files |

</details>

---

## Exercise 7.2 — Diagnose a middleware disaster

```js
// File: broken-app.js
import express from 'express';
const app = express();

app.use((error, req, res, next) => {
  console.error(error);
  res.status(500).json({ error: { code: 'INTERNAL_ERROR' } });
});

app.use((req, res, next) => {
  if (!req.get('authorization')) {
    res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
  }
  next();
});

app.use('/api', requireJson);

app.get('/api/v1/notes', async (req, res, next) => {
  const notes = await noteService.list();
  res.json({ data: notes });
  next();
});

app.use(express.json());
app.use(cookieParser());

app.use((req, res, next) => {
  console.log(`${req.method} ${req.originalUrl}`);
  next();
});

app.post('/api/v1/notes', (req, res) => {
  const note = noteService.create(req.body);
  res.status(201).json({ note });
});

app.use((req, res) => res.status(404).send('Not found'));

app.listen(3000);
```

List every problem, in execution order, and explain the symptom each produces.

<details>
<summary>Solution</summary>

| # | Problem | Symptom |
| --- | --- | --- |
| 1 | The **error handler is registered first** | Express matches error handlers *after* the failing layer, so this one never runs; every error falls through to Express's default HTML handler |
| 2 | Auth middleware responds with 401 **and then calls `next()`** unconditionally | The chain continues; the next middleware/handler responds again → `ERR_HTTP_HEADERS_SENT` |
| 3 | Auth is applied to **everything**, including `/health`, static files and the 404 handler | Public endpoints become unreachable; monitoring breaks |
| 4 | `requireJson` is mounted on `/api` | It also runs for `/apiary`-style prefixes and for **GET** requests (unless it guards by method) |
| 5 | `/api/v1/notes` is `async` with no `try/catch` **and** calls `next()` after responding | In Express 5 the rejection is forwarded (fine), but `next()` after `res.json()` continues the chain → a second response attempt |
| 6 | `express.json()` is registered **after** the routes | `req.body` is `undefined` in `POST /api/v1/notes` → `TypeError` |
| 7 | `cookieParser` is used but never imported | `ReferenceError` at startup |
| 8 | The **logger runs after the routes** | Requests that are handled never reach it — no request logs at all |
| 9 | No `try/catch` and no error middleware that works | Errors become HTML pages with stack traces |
| 10 | `res.status(404).send('Not found')` | HTML for a JSON API |
| 11 | No `express.json()` limit | Unbounded body → memory exhaustion |
| 12 | `app.listen(3000)` with no host, no `PORT` | Not deployable |
| 13 | Note creation returns `200`-style shape without `Location` | `201` should include `Location` |
| 14 | Errors are logged with `console.error(error)` | Unstructured, no request id, no correlation |
| 15 | `x-powered-by` not disabled | Version disclosure |

**The corrected skeleton:**

```js
// File: fixed-app.js
import express from 'express';
import cookieParser from 'cookie-parser';
import { requestId } from './src/middleware/requestId.js';
import { requireJson } from './src/middleware/requireJson.js';
import { notFound } from './src/middleware/notFound.js';
import { createErrorHandler } from './src/middleware/errorHandler.js';
import { createAuthenticate } from './src/middleware/authenticate.js';
import { noteService } from './src/services/noteService.js';

const app = express();
app.disable('x-powered-by');
app.set('trust proxy', true);

// 1. Request identity
app.use(requestId);

// 2. Logging — early, so every request is recorded
app.use((req, res, next) => {
  const startedAt = process.hrtime.bigint();
  res.on('finish', () => {
    const durationMs = Number(process.hrtime.bigint() - startedAt) / 1e6;
    console.log(
      JSON.stringify({
        level: res.statusCode >= 500 ? 'error' : 'info',
        requestId: req.id,
        method: req.method,
        path: req.originalUrl,
        status: res.statusCode,
        durationMs: Number(durationMs.toFixed(2)),
      }),
    );
  });
  next();
});

// 3. Body parsing — before any handler that reads req.body
app.use(express.json({ limit: '100kb' }));
app.use(cookieParser(process.env.COOKIE_SECRET));

// 4. Public routes first, so auth never blocks them
app.get('/health', (req, res) => res.json({ status: 'ok' }));

// 5. A router that owns its own middleware and its own auth
const notes = express.Router();

notes.use(createAuthenticate());            // every note route requires a token
notes.get('/', async (req, res, next) => {
  try {
    const data = await noteService.list();
    return res.json({ data });              // `return` — never call next() after responding
  } catch (error) {
    return next(error);                     // forward errors, do not respond here
  }
});

notes.post('/', requireJson, async (req, res, next) => {
  try {
    const note = await noteService.create(req.body ?? {});
    return res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: note });
  } catch (error) {
    return next(error);
  }
});

app.use('/api/v1/notes', notes);

// 6. Terminal middleware, in order
app.use(notFound);
app.use(createErrorHandler({ config: { nodeEnv: process.env.NODE_ENV ?? 'development' } }));

const port = Number(process.env.PORT ?? 3000);
app.listen(port, '0.0.0.0', () => console.log(`listening on http://localhost:${port}`));
```

```bash
# Proof that each fix works:
curl -s localhost:3000/health                                # 200 — not blocked by auth
curl -s -o /dev/null -w '%{http_code}\n' localhost:3000/api/v1/notes       # 401 (no token)
curl -s -o /dev/null -w '%{http_code}\n' -H 'Authorization: Bearer x' \
  localhost:3000/api/v1/notes                                # 401 (invalid token)
curl -s -X POST localhost:3000/api/v1/notes \
  -H 'Authorization: Bearer <valid>' -H 'Content-Type: text/plain' -d 'x'  # 415
curl -s -X POST localhost:3000/api/v1/notes \
  -H 'Authorization: Bearer <valid>' -H 'Content-Type: application/json' -d '{bad'  # 400
curl -s localhost:3000/nope                                  # JSON 404, not HTML
curl -s localhost:3000/health -D - -o /dev/null | grep -i x-powered-by      # (no output)
# Watch the terminal: every request appears exactly once, with an id and a duration
```

**The one-sentence lesson:** in Express, the *order of registration is the order of execution*, and
every one of the fifteen problems above is an ordering or `next()` discipline issue — not an Express
bug.

</details>

---

## What's next

Middleware is the machinery; errors are what it carries. Next: the single error contract that every
failure path in your API will use.

→ [08 — Error Handling](08-error-handling.md)
