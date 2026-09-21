# 08 — Error Handling

> **Where this fits:** [01-nodejs/16-error-handling.md](../01-nodejs/16-error-handling.md) built the error
> classes and the process-level guards. This chapter puts them behind HTTP: one error pipeline, one
> response contract, correct status codes, and nothing internal ever leaking to a client.

---

## 1. Two kinds of errors, one contract

Every failure in an API is one of two things:

| | **Operational errors** | **Programmer errors** |
| --- | --- | --- |
| Examples | Invalid input, missing record, expired token, duplicate email, upstream timeout | `TypeError`, undefined access, wrong SQL, logic bugs |
| Expected? | Yes — part of normal operation | No — always a defect |
| HTTP status | `400`–`499` (client's problem) or `503` (temporarily ours) | `500` |
| Message to the client | Specific and actionable | Generic ("Something went wrong") |
| Logged at | `warn` | `error`, with a stack |
| Action | Return a documented error code | Alert, fix, deploy |

Mixing them up causes the two classic failures: leaking internals on a 500, or hiding a bug behind a
vague 400.

**The contract every failure path in this API will use:**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [{ "field": "title", "message": "must not be empty" }],
    "requestId": "6a1f3e2b-8f4a-4b1e-9a3d-5b2c9e0f1a77"
  }
}
```

| Field | Always present | Purpose |
| --- | --- | --- |
| `code` | ✅ | Stable, machine-readable identifier a client can branch on. **Never** change it between deploys |
| `message` | ✅ | Human-readable, safe to display, no internals |
| `details` | Only for operational errors | Field-level validation failures, allowed values, conflict info |
| `requestId` | ✅ | Correlates the response with the server log line — the single most useful debugging aid |

The envelope is deliberately stable: **every** 4xx/5xx response — including body-parser failures, 404s
and 405s — uses it, so the client needs one parser and one error component.

---

## 2. How errors travel in Express

```text
throw new Error() / Promise.reject() / next(err)
        │
        ▼
Express looks for the next error-handling middleware registered AFTER the failing layer
        │
        ├─ ▶ found  → runs (err, req, res, next)
        │              ├─ responds  → done
        │              └─ next(err) → the next error middleware (or the default one)
        │
        └─ ▶ none   → Express's DEFAULT handler: HTML page with the stack in development
```

Three rules make this work:

| Rule | Detail |
| --- | --- |
| An error handler has **exactly four** parameters | `(err, req, res, next)`. With three, it is a normal middleware and will never be called with an error |
| It must be registered **after** the routes | Express scans forward from the failure point; an early error handler never sees later errors |
| `throw` and `next(err)` are equivalent inside handlers | Synchronous throws are caught by Express; **rejections are caught in Express 5** (not in v4) |

```js
// File: how-errors-flow.js
import express from 'express';

const app = express();

// 1. Synchronous throw — caught by Express.
app.get('/throw', (req, res) => {
  throw new Error('sync failure');
});

// 2. Async rejection — caught automatically in Express 5.
app.get('/reject', async (req, res) => {
  await Promise.reject(new Error('async failure'));
});

// 3. Explicit forwarding — the portable style (works in Express 4 and 5).
app.get('/forward', async (req, res, next) => {
  try {
    await Promise.reject(new Error('forwarded failure'));
  } catch (error) {
    next(error);
  }
});

// 4. Errors from callbacks that Express CANNOT catch — you must forward them yourself.
app.get('/callback', (req, res, next) => {
  setTimeout(() => {
    try {
      throw new Error('failure inside a timer');
    } catch (error) {
      next(error);            // without this, the process would crash
    }
  }, 10);
});

// 5. A stream error is also invisible to Express's promise handling.
app.get('/stream', (req, res, next) => {
  const stream = createFailingReadStream();
  stream.on('error', next);          // forward the error
  stream.pipe(res);
});

app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

app.use((error, req, res, next) => {
  console.log('handled:', error.message);
  res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: error.message } });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
for path in throw reject forward callback stream; do
  printf '%-9s → ' "$path"
  curl -s "localhost:3000/$path"
  echo
done
```

```text
throw     → {"error":{"code":"INTERNAL_ERROR","message":"sync failure"}}
reject    → {"error":{"code":"INTERNAL_ERROR","message":"async failure"}}
forward   → {"error":{"code":"INTERNAL_ERROR","message":"forwarded failure"}}
callback  → {"error":{"code":"INTERNAL_ERROR","message":"failure inside a timer"}}
stream    → {"error":{"code":"INTERNAL_ERROR","message":"stream failure"}}
```

### What Express 5 does **not** catch

| Situation | Why | What to do |
| --- | --- | --- |
| `setTimeout(() => { throw … })` | Outside the promise chain and the call stack | Wrap in `try/catch` and call `next(error)` |
| `stream.on('error', …)` | Event-emitter errors are not rejections | Attach a handler that calls `next` |
| `process.nextTick(() => { throw … })` | Runs after the handler returned | Treat as an uncaught exception; keep such code out of request paths |
| A rejected promise inside a **detached** async function | The handler returned before the rejection | `void doWork().catch(next)` — and think hard about whether to detach at all |
| `next('a string')` | Not an `Error` (verified in ch. 07) | Always pass `Error` instances |
| Non-`Error` rejection values (`throw 'oops'`) | No stack, no `message` | Normalise: `throw new Error(String(value))` |

```js
// File: detached-work.js
import express from 'express';

const app = express();

app.post('/reports', (req, res, next) => {
  // Respond immediately, then continue working — but never lose the error.
  res.status(202).json({ data: { status: 'queued' } });

  // `void` makes the intent explicit: this promise is deliberately not awaited,
  // and its rejection is still handled.
  void generateReport(req.body)
    .then(() => console.log('report finished'))
    .catch((error) => {
      // There is no response to send any more, so log and alert instead.
      console.error(JSON.stringify({ level: 'error', message: 'report failed', error: error.message }));
    });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

---

## 3. The error classes

```js
// File: src/utils/AppError.js
/**
 * Application error hierarchy.
 * `isOperational` is the switch that decides whether a client sees the real message.
 */
export class AppError extends Error {
  constructor(message, { statusCode = 500, code = 'INTERNAL_ERROR', details, cause, isOperational = true } = {}) {
    super(message, { cause });
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.isOperational = isOperational;
    Error.captureStackTrace?.(this, new.target);
  }
}

/* ── 400 ─────────────────────────────────────────────────────────────────────── */
export class BadRequestError extends AppError {
  constructor(message = 'Bad request', details) {
    super(message, { statusCode: 400, code: 'BAD_REQUEST', details });
  }
}

/* ── 401 ─────────────────────────────────────────────────────────────────────── */
export class UnauthorizedError extends AppError {
  constructor(message = 'Authentication required', details) {
    super(message, { statusCode: 401, code: 'UNAUTHENTICATED', details });
  }
}

/* ── 403 ─────────────────────────────────────────────────────────────────────── */
export class ForbiddenError extends AppError {
  constructor(message = 'You do not have permission to perform this action', details) {
    super(message, { statusCode: 403, code: 'FORBIDDEN', details });
  }
}

/* ── 404 ─────────────────────────────────────────────────────────────────────── */
export class NotFoundError extends AppError {
  constructor(message = 'Resource not found', details) {
    super(message, { statusCode: 404, code: 'NOT_FOUND', details });
  }
}

/* ── 409 ─────────────────────────────────────────────────────────────────────── */
export class ConflictError extends AppError {
  constructor(message = 'Resource conflict', details) {
    super(message, { statusCode: 409, code: 'CONFLICT', details });
  }
}

/* ── 413 ─────────────────────────────────────────────────────────────────────── */
export class PayloadTooLargeError extends AppError {
  constructor(message = 'Request payload is too large', details) {
    super(message, { statusCode: 413, code: 'PAYLOAD_TOO_LARGE', details });
  }
}

/* ── 415 ─────────────────────────────────────────────────────────────────────── */
export class UnsupportedMediaTypeError extends AppError {
  constructor(message = 'Unsupported media type', details) {
    super(message, { statusCode: 415, code: 'UNSUPPORTED_MEDIA_TYPE', details });
  }
}

/* ── 422 ─────────────────────────────────────────────────────────────────────── */
export class ValidationError extends AppError {
  constructor(details, message = 'Request validation failed') {
    super(message, { statusCode: 422, code: 'VALIDATION_ERROR', details });
  }
}

/* ── 429 ─────────────────────────────────────────────────────────────────────── */
export class TooManyRequestsError extends AppError {
  constructor(message = 'Too many requests', { retryAfterSeconds, ...details } = {}) {
    super(message, { statusCode: 429, code: 'RATE_LIMITED', details: { ...details, retryAfterSeconds } });
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

/* ── 503 ─────────────────────────────────────────────────────────────────────── */
export class ServiceUnavailableError extends AppError {
  constructor(message = 'Service temporarily unavailable', { retryAfterSeconds, cause } = {}) {
    super(message, { statusCode: 503, code: 'SERVICE_UNAVAILABLE', cause });
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

/* ── 500 (programmer error) ──────────────────────────────────────────────────── */
export class InternalError extends AppError {
  constructor(message = 'Internal server error', { cause } = {}) {
    super(message, { statusCode: 500, code: 'INTERNAL_ERROR', cause, isOperational: false });
  }
}
```

| Class | Status | Code | Typical cause |
| --- | --- | --- | --- |
| `BadRequestError` | 400 | `BAD_REQUEST` | Malformed request that is not a validation failure (bad base64, bad cursor) |
| `UnauthorizedError` | 401 | `UNAUTHENTICATED` | Missing/invalid credentials |
| `ForbiddenError` | 403 | `FORBIDDEN` | Authenticated but not permitted |
| `NotFoundError` | 404 | `NOT_FOUND` | The addressed resource does not exist |
| `ConflictError` | 409 | `CONFLICT` | Unique-constraint violation, concurrent modification |
| `PayloadTooLargeError` | 413 | `PAYLOAD_TOO_LARGE` | Body over the limit |
| `UnsupportedMediaTypeError` | 415 | `UNSUPPORTED_MEDIA_TYPE` | Wrong `Content-Type` |
| `ValidationError` | 422 | `VALIDATION_ERROR` | Well-formed request, invalid values — carries `details` |
| `TooManyRequestsError` | 429 | `RATE_LIMITED` | Rate limiter |
| `ServiceUnavailableError` | 503 | `SERVICE_UNAVAILABLE` | Dependency down, DB pool exhausted, draining |
| `InternalError` | 500 | `INTERNAL_ERROR` | A bug (`isOperational: false`) |

> **Why 422 and not 400 for validation?** Both are defensible. Teams that use both need a rule, and the
> rule used throughout these notes is: **400 = the request could not be understood; 422 = it was
> understood and the values are wrong.** A malformed JSON body is a 400 (the parser cannot even read
> it); `{"title": ""}` is a 422.

---

## 4. Translating foreign errors

Errors from libraries arrive in their own shapes. Translate them at the boundary — once — instead of
scattering `if (error.code === '23505')` through the codebase.

```js
// File: src/utils/errorMapping.js
import {
  AppError,
  BadRequestError,
  ConflictError,
  InternalError,
  PayloadTooLargeError,
  ServiceUnavailableError,
  UnsupportedMediaTypeError,
  ValidationError,
} from './AppError.js';

/**
 * Map a database error onto an application error.
 * Codes are grouped by driver so this file stays the single place that knows them.
 */
export function fromDatabaseError(error, { resource = 'resource' } = {}) {
  switch (error.code) {
    // PostgreSQL
    case '23505':                                     // unique_violation
      return new ConflictError(`${resource} already exists`, { constraint: error.constraint });
    case '23503':                                     // foreign_key_violation
      return new BadRequestError('Referenced record does not exist', { constraint: error.constraint });
    case '23502':                                     // not_null_violation
      return new BadRequestError('A required field is missing', { column: error.column });
    case '22P02':                                     // invalid_text_representation (bad uuid/int)
      return new BadRequestError('Invalid value format');

    // MySQL / MariaDB
    case 'ER_DUP_ENTRY':
      return new ConflictError(`${resource} already exists`);
    case 'ER_NO_REFERENCED_ROW_2':
      return new BadRequestError('Referenced record does not exist');
    case 'ER_DATA_TOO_LONG':
      return new BadRequestError('A value is too long for its column');

    // MongoDB
    case 11000:
      return new ConflictError(`${resource} already exists`, { field: Object.keys(error.keyPattern ?? {})[0] });
    case 'CastError':
      return new BadRequestError('Invalid identifier format');

    // Connection problems — the client may retry later.
    case 'ECONNREFUSED':
    case 'ETIMEDOUT':
    case 'PROTOCOL_CONNECTION_LOST':
      return new ServiceUnavailableError('Database unavailable', { cause: error, retryAfterSeconds: 5 });

    default:
      return new InternalError('Database operation failed', { cause: error });
  }
}

/** Validation libraries (Zod) already produce field-level issues. */
export function fromZodError(error, message = 'Request validation failed') {
  return new ValidationError(
    error.issues.map((issue) => ({
      field: issue.path.length > 0 ? issue.path.join('.') : 'body',
      message: issue.message,
      code: issue.code,
    })),
    message,
  );
}

/** Errors thrown by express.json()/express.urlencoded() (chapter 06). */
export function fromBodyParserError(error) {
  switch (error.type) {
    case 'entity.parse.failed':
      return new BadRequestError('Request body is not valid JSON', { type: error.type });
    case 'entity.too.large':
      return new PayloadTooLargeError('Request body is too large');
    case 'charset.unsupported':
      return new UnsupportedMediaTypeError('Unsupported charset');
    case 'encoding.unsupported':
      return new UnsupportedMediaTypeError('Unsupported content encoding');
    default:
      return null;
  }
}

/** Errors from an outbound HTTP call (fetch, axios). */
export async function fromUpstreamError(response, { service = 'upstream' } = {}) {
  if (response.status >= 500) {
    return new ServiceUnavailableError(`${service} is unavailable`, { retryAfterSeconds: 5 });
  }
  if (response.status === 401 || response.status === 403) {
    return new InternalError(`${service} rejected our credentials — configuration problem`);
  }
  const body = await response.text().catch(() => '');
  return new BadRequestError(`${service} rejected the request`, { status: response.status, body: body.slice(0, 200) });
}

/** The single normalisation point: any thrown value becomes an AppError-shaped object. */
export function normalizeError(error) {
  if (error instanceof AppError) return error;

  const fromParser = fromBodyParserError(error);
  if (fromParser) return fromParser;

  // Errors thrown by Node core carry a string `code`.
  if (typeof error?.code === 'string') {
    const mapped = fromDatabaseError(error);
    if (mapped.statusCode !== 500) return mapped;
  }

  // JSON syntax errors from manual JSON.parse calls.
  if (error instanceof SyntaxError && error.message.includes('JSON')) {
    return new BadRequestError('Request body is not valid JSON', { type: 'entity.parse.failed' });
  }

  // Anything else is a bug: 500, message hidden from the client.
  return new InternalError(error?.message ?? 'Unknown error', { cause: error });
}

/** Everything above is exercised by tests/error-layer.test.js (exercise 8.1). */
```

The mapping table in one view:

| Source error | Mapped to | Why |
| --- | --- | --- |
| Postgres `23505`, MySQL `ER_DUP_ENTRY`, Mongo `11000` | `ConflictError` → 409 | A uniqueness rule was violated — the client can fix it |
| Postgres `22P02`, Mongo `CastError` | `BadRequestError` → 400 | A malformed identifier reached the query: validate earlier (ch. 06) |
| `ECONNREFUSED`/`ETIMEDOUT` to the DB | `ServiceUnavailableError` → 503 | Not the client's fault; retry is reasonable |
| body-parser `entity.parse.failed` | `BadRequestError` → 400 | Malformed JSON |
| body-parser `entity.too.large` | `PayloadTooLargeError` → 413 | Body limit exceeded |
| Zod issues | `ValidationError` → 422 with `details` | Field-level client errors |
| Anything unrecognised | `InternalError` → 500 | Assume a bug and hide the details |

> **Where this file lives:** everything above imports only from `AppError.js`, so there are no circular
> imports and no surprises. `normalizeError` is the *only* function the error middleware needs — the
> rest are called at the boundary where the foreign error appears (the route, the service, the client).

---

## 5. The error middleware

This is the file that decides what every client sees. It has four responsibilities: **normalise**,
**log**, **respond**, and **never leak**.

```js
// File: src/middleware/errorHandler.js
import { AppError } from '../utils/AppError.js';
import { normalizeError } from '../utils/errorMapping.js';

/** Fields that must never be echoed to a client, whatever the error says. */
const REDACTED_KEYS = new Set(['password', 'passwordHash', 'token', 'accessToken', 'refreshToken', 'authorization', 'cookie', 'secret']);

function redact(value, depth = 0) {
  if (value === null || typeof value !== 'object' || depth > 3) return value;
  if (Array.isArray(value)) return value.slice(0, 20).map((item) => redact(item, depth + 1));

  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      REDACTED_KEYS.has(key) ? '[redacted]' : redact(item, depth + 1),
    ]),
  );
}

export function createErrorHandler({ config, logger = console }) {
  const isProduction = config?.nodeEnv === 'production' || config?.isProduction === true;

  return function errorHandler(error, req, res, next) {
    // 1. Normalise: after this line, `appError` always has statusCode/code/isOperational.
    const appError = normalizeError(error);
    const { statusCode, code, isOperational } = appError;

    // 2. Log with everything needed to debug, and nothing that must not be stored.
    const logRecord = {
      level: statusCode >= 500 ? 'error' : 'warn',
      message: appError.message,
      code,
      statusCode,
      method: req.method,
      path: req.originalUrl,
      requestId: req.id,
      userId: req.user?.id,
      clientIp: req.ip,
      userAgent: req.get('user-agent'),
      details: appError.details ? redact(appError.details) : undefined,
      stack: statusCode >= 500 ? appError.stack : undefined,
      cause: appError.cause ? { message: appError.cause.message, code: appError.cause.code } : undefined,
    };

    (logger[logRecord.level] ?? logger.error).call(logger, logRecord);

    // 3. The response already started (streaming, file transfer): let Express finish it.
    if (res.headersSent) return next(error);

    // 4. Protocol-level headers that belong with certain statuses.
    if (statusCode === 401) res.set('WWW-Authenticate', 'Bearer realm="api"');
    if (appError.retryAfterSeconds) res.set('Retry-After', String(appError.retryAfterSeconds));

    // 5. Build the payload. The client sees details ONLY for operational errors.
    const exposeMessage = isOperational || !isProduction;
    return res.status(statusCode).json({
      error: {
        code,
        message: exposeMessage ? appError.message : 'Something went wrong',
        details: isOperational ? appError.details : undefined,
        requestId: req.id,
      },
    });
  };
}
```

| Decision | Reason |
| --- | --- |
| Normalise **first** | Everything downstream can assume a single shape |
| 4xx logged at `warn`, 5xx at `error` | An error dashboard must reflect *bugs*, not bad client input |
| `stack` only for 5xx | Stacks on client errors are noise; stacks on 500s are essential |
| `cause` logged but never sent | Underlying driver messages are for engineers |
| `details` only when `isOperational` | A bug's internal state must not describe your schema to an attacker |
| 500 messages hidden in production | Attackers learn a lot from driver and ORM messages |
| `WWW-Authenticate` on 401 | Required by the HTTP spec for a `401` with a scheme |
| `Retry-After` on 429/503 | Turns a failure into an actionable instruction |
| `headersSent` check with `next(error)` | Delegating lets Express destroy the socket cleanly |

---

## 6. Wiring it together

```js
// File: src/app.js
import express from 'express';
import { requestId } from './middleware/requestId.js';
import { notFound } from './middleware/notFound.js';
import { createErrorHandler } from './middleware/errorHandler.js';
import { createApiRouter } from './routes/index.js';
import { env } from './config/env.js';
import { logger } from './utils/logger.js';

export function createApp({ config = env, log = logger } = {}) {
  const app = express();

  app.disable('x-powered-by');
  app.use(requestId);
  app.use(express.json({ limit: config.bodyLimit }));

  app.use('/api/v1', createApiRouter({ config, logger: log }));

  // Terminal middleware: 404 for unmatched routes…
  app.use(notFound);

  // …then the ONE error handler, last of all.
  app.use(createErrorHandler({ config, logger: log }));

  return app;
}
```

```js
// File: src/routes/index.js (excerpt) — how services signal failures
import { Router } from 'express';
import { NotFoundError, ConflictError } from '../utils/AppError.js';
import { fromDatabaseError } from '../utils/errorMapping.js';

export function createNoteRouter({ noteService }) {
  const router = Router();

  router.get('/:id', async (req, res, next) => {
    try {
      const note = await noteService.getById(req.params.id);
      if (!note) throw new NotFoundError(`Note ${req.params.id} not found`);
      res.json({ data: note });
    } catch (error) {
      next(error);                       // ← the only error handling in the path
    }
  });

  router.post('/', async (req, res, next) => {
    try {
      const note = await noteService.create(req.validated.body);
      res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: note });
    } catch (error) {
      if (error.code === '23505') {
        return next(new ConflictError('A note with that title already exists', { field: 'title' }));
      }
      if (error.code === 'ECONNREFUSED') {
        return next(fromDatabaseError(error, { resource: 'note' }));
      }
      return next(error);
    }
  });

  return router;
}
```

```bash
# Every failure path, seen from the client:
curl -s localhost:3000/api/v1/notes/00000000-0000-0000-0000-000000000000
# 404 {"error":{"code":"NOT_FOUND","message":"Note … not found","requestId":"…"}}

curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: application/json' -d '{"title":""}'
# 422 {"error":{"code":"VALIDATION_ERROR","details":[{"field":"title","message":"must not be empty"}],"requestId":"…"}}

curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: application/json' -d '{bad'
# 400 {"error":{"code":"BAD_REQUEST","message":"Request body is not valid JSON","requestId":"…"}}

curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: text/plain' -d 'x'
# 415 {"error":{"code":"UNSUPPORTED_MEDIA_TYPE","message":"Unsupported media type","requestId":"…"}}

curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: application/json' -d '{"title":"duplicate"}'
curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: application/json' -d '{"title":"duplicate"}'
# second call → 409 {"error":{"code":"CONFLICT","message":"A note with that title already exists",…}}

curl -s localhost:3000/nope
# 404 {"error":{"code":"ROUTE_NOT_FOUND","message":"GET /nope not found","requestId":"…"}}

# And when a genuine bug occurs in production, the client sees nothing internal:
# 500 {"error":{"code":"INTERNAL_ERROR","message":"Something went wrong","requestId":"…"}}
# while the log line contains the stack and the same requestId.
```

---

## 7. Testing error paths

Error paths are code, and code without tests is broken. Every status in your taxonomy deserves at least
one test asserting **the status, the code, and the absence of leaks**.

```js
// File: tests/error-handling.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { requestId } from '../src/middleware/requestId.js';
import { notFound } from '../src/middleware/notFound.js';
import { createErrorHandler } from '../src/middleware/errorHandler.js';
import { ValidationError, NotFoundError, ConflictError, ForbiddenError } from '../src/utils/AppError.js';

let server;
let baseUrl;
const captured = [];

before(async () => {
  const app = express();
  app.disable('x-powered-by');
  app.use(requestId);
  app.use(express.json({ limit: '1kb' }));

  app.post('/echo', (req, res) => res.json({ ok: true, bytes: JSON.stringify(req.body).length }));
  app.get('/validation', () => { throw new ValidationError([{ field: 'title', message: 'required' }]); });
  app.get('/not-found', () => { throw new NotFoundError('Note 42 not found'); });
  app.get('/conflict', () => { throw new ConflictError('Email already registered', { field: 'email' }); });
  app.get('/forbidden', () => { throw new ForbiddenError(); });
  app.get('/bug', () => {
    // Simulates a database driver error with a secret in the message.
    const error = new Error('connect ECONNREFUSED 10.0.3.7:5432 user=admin password=hunter2');
    error.code = 'ECONNREFUSED';
    throw error;
  });
  app.get('/unexpected', () => { throw new TypeError('x.y is not a function'); });
  app.get('/headers-sent', (req, res, next) => {
    res.write('partial');
    next(new Error('failure after the response started'));
  });

  app.use(notFound);
  app.use(createErrorHandler({
    config: { nodeEnv: 'production' },                 // ← the strict case
    logger: {
      error: (record) => captured.push(record),
      warn: (record) => captured.push(record),
    },
  }));

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const get = async (path) => {
  const response = await fetch(baseUrl + path);
  return { status: response.status, body: await response.json() };
};

test('404 from a route that throws NotFoundError', async () => {
  const { status, body } = await get('/not-found');
  assert.equal(status, 404);
  assert.equal(body.error.code, 'NOT_FOUND');
  assert.equal(body.error.message, 'Note 42 not found');
  assert.match(body.error.requestId, /^[0-9a-f-]{36}$/);
});

test('422 with field-level details', async () => {
  const { status, body } = await get('/validation');
  assert.equal(status, 422);
  assert.equal(body.error.code, 'VALIDATION_ERROR');
  assert.deepEqual(body.error.details, [{ field: 'title', message: 'required' }]);
});

test('409 keeps its details', async () => {
  const { status, body } = await get('/conflict');
  assert.equal(status, 409);
  assert.deepEqual(body.error.details, { field: 'email' });
});

test('403 hides nothing but reveals nothing extra', async () => {
  const { status, body } = await get('/forbidden');
  assert.equal(status, 403);
  assert.equal(body.error.code, 'FORBIDDEN');
  assert.equal(body.error.details, undefined);
});

test('a database outage becomes 503 and never leaks the connection string', async () => {
  const { status, body } = await get('/bug');
  assert.equal(status, 503);
  assert.equal(body.error.code, 'SERVICE_UNAVAILABLE');

  const serialised = JSON.stringify(body);
  assert.ok(!serialised.includes('hunter2'), 'password leaked to the client');
  assert.ok(!serialised.includes('10.0.3.7'), 'internal host leaked to the client');
  assert.ok(!serialised.includes('ECONNREFUSED'), 'driver error leaked to the client');
});

test('an unexpected TypeError is a 500 with a generic message in production', async () => {
  const { status, body } = await get('/unexpected');
  assert.equal(status, 500);
  assert.equal(body.error.code, 'INTERNAL_ERROR');
  assert.equal(body.error.message, 'Something went wrong');
  assert.ok(!JSON.stringify(body).includes('is not a function'));
});

test('the request id in the response matches the one in the logs', async () => {
  const { body } = await get('/not-found');
  const logged = captured.at(-1);

  assert.equal(logged.requestId, body.error.requestId);
  assert.equal(logged.code, 'NOT_FOUND');
  assert.equal(logged.level, 'warn');            // 4xx is a warning, not a bug
});

test('the stack is logged for 500s but never sent', async () => {
  captured.length = 0;
  const { body } = await get('/unexpected');

  const logged = captured.at(-1);
  assert.equal(logged.level, 'error');
  assert.ok(logged.stack.includes('TypeError'));
  assert.equal(body.error.stack, undefined);
});

test('an error after the response started does not crash the process', async () => {
  const response = await fetch(`${baseUrl}/headers-sent`);
  assert.equal(response.status, 200);
  assert.equal(await response.text(), 'partial');     // the partial body arrives, then the socket closes
});

test('a body over the parser limit is a 413, not a 500', async () => {
  const tooBig = await fetch(`${baseUrl}/echo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ blob: 'x'.repeat(5000) }),          // limit is 1kb
  });
  assert.equal(tooBig.status, 413);
  assert.equal((await tooBig.json()).error.code, 'PAYLOAD_TOO_LARGE');

  const smallEnough = await fetch(`${baseUrl}/echo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ok: true }),
  });
  assert.equal(smallEnough.status, 200);

  const malformed = await fetch(`${baseUrl}/echo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{not json',
  });
  assert.equal(malformed.status, 400);
  assert.equal((await malformed.json()).error.code, 'BAD_REQUEST');
});
```

```bash
node --test tests/error-handling.test.js
```

```text
✔ 404 from a route that throws NotFoundError
✔ 422 with field-level details
✔ 409 keeps its details
✔ 403 hides nothing but reveals nothing extra
✔ a database outage becomes 503 and never leaks the connection string
✔ an unexpected TypeError is a 500 with a generic message in production
✔ the request id in the response matches the one in the logs
✔ the stack is logged for 500s but never sent
✔ an error after the response started does not crash the process
✔ a body over the parser limit is a 413, not a 500
pass 10
fail 0
```

**The three assertions that catch most real leaks:**

```js
assert.ok(!JSON.stringify(body).includes(secret));   // no secret in the payload
assert.equal(body.error.stack, undefined);           // no stack in the payload
assert.equal(logged.requestId, body.error.requestId); // logs and responses are correlated
```

---

## 8. Process-level guards (the last line of defence)

Even with a perfect middleware, something can escape: an error thrown in a `setTimeout`, an event
emitter, a background job. The process then has two options: crash loudly, or continue in an unknown
state. **Crash loudly, after draining.**

```js
// File: src/server.js (excerpt)
import { createApp } from './app.js';
import { env } from './config/env.js';
import { logger } from './utils/logger.js';

const app = createApp({ config: env, log: logger });
const server = app.listen(env.port, env.host, () => logger.info('server started', { port: env.port }));

let shuttingDown = false;

function shutdown(reason, exitCode = 0) {
  if (shuttingDown) return;
  shuttingDown = true;

  logger.info('shutdown initiated', { reason, exitCode });

  // Stop accepting new connections; existing requests get time to finish.
  server.close((error) => {
    if (error) {
      logger.error('error while closing', { message: error.message });
      process.exit(1);
    }
    logger.info('shutdown complete');
    process.exit(exitCode);
  });

  // Close idle keep-alive sockets immediately so the process can actually exit.
  server.closeIdleConnections?.();

  // Never hang forever waiting for a stuck connection.
  setTimeout(() => {
    logger.error('forced exit after 10s');
    process.exit(1);
  }, 10_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

// A bug escaped every other handler: log everything, then die. Do NOT keep serving.
process.on('uncaughtException', (error) => {
  logger.error('uncaughtException', { message: error.message, stack: error.stack });
  shutdown('uncaughtException', 1);
});

process.on('unhandledRejection', (reason) => {
  logger.error('unhandledRejection', {
    message: reason instanceof Error ? reason.message : String(reason),
    stack: reason instanceof Error ? reason.stack : undefined,
  });
  shutdown('unhandledRejection', 1);
});
```

| Guard | Correct response | Wrong response |
| --- | --- | --- |
| `uncaughtException` | Log, stop accepting traffic, drain, `exit(1)`; let the supervisor restart | Swallow it and keep serving — the process may be in an undefined state |
| `unhandledRejection` | Same as above | Ignoring it (silent data corruption) |
| `SIGTERM` | Graceful shutdown (this is what every orchestrator sends) | Immediate `process.exit()` mid-request |
| `SIGINT` | Same as `SIGTERM` for local Ctrl+C | — |

---

## 9. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| Error handler with 3 parameters | It never runs; clients get Express's HTML page | Four parameters, exactly |
| Error handler registered before routes | Later routes' errors are never caught | Register it last |
| Forgetting `next(error)` in a callback/stream | The process crashes or the request hangs | Forward errors from every async boundary |
| Sending the stack in the response | Schema, file paths and secrets exposed | Log the stack; send a generic 500 message |
| Echoing `error.message` for 500s | Database and driver internals leak | Only expose operational errors |
| Using `error.status` for your own errors | Inconsistent mapping (`statusCode` vs `status`) | Normalise in one `normalizeError` |
| Returning `200` with `{ error: … }` | Clients' `if (!response.ok)` logic never triggers | Use real status codes |
| Registering multiple error handlers with different formats | Clients get inconsistent shapes | Exactly one formatter; others just add context |
| `next(error)` after responding | `ERR_HTTP_HEADERS_SENT` in the error handler | Check `res.headersSent` first |
| Logging every 4xx at `error` level | Alert fatigue; real bugs get lost | 4xx → `warn`, 5xx → `error` |
| Losing the original error (`throw new Error('failed')`) | No cause, no stack, undiagnosable | `new AppError(msg, { cause: error })` |
| No `requestId` | Impossible to correlate a user report with a log line | Return and log the same id |
| Trusting `error.code` everywhere | String codes collide between libraries | Normalise once, at the boundary |
| Catching everything and returning 500 | Bugs masquerade as outages; no useful client behaviour | Map known failure modes to 4xx |
| No tests for error paths | The first leak is found in production | One test per status code, asserting no leaks |

---

## Exercise 8.1 — Build the error layer and prove it does not leak

Implement the error layer in your own project and satisfy these requirements:

1. One `AppError` hierarchy with at least: 400, 401, 403, 404, 409, 413, 415, 422, 429, 500, 503.
2. One `normalizeError` that maps: unknown errors → 500, body-parser failures → 400/413/415,
   Postgres `23505` → 409, `ECONNREFUSED` → 503.
3. One error middleware producing `{ error: { code, message, details?, requestId } }`.
4. In production: 500 responses say `"Something went wrong"` and never contain `stack`, `cause`, the
   error `message`, or any secret from `details`.
5. Write one test per status code, plus a "leak test" that greps the serialised body for known secrets.

<details>
<summary>Solution</summary>

```js
// File: src/utils/AppError.js — see §3 for the full hierarchy
export class AppError extends Error {
  constructor(message, { statusCode = 500, code = 'INTERNAL_ERROR', details, cause, isOperational = true, retryAfterSeconds } = {}) {
    super(message, { cause });
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.isOperational = isOperational;
    this.retryAfterSeconds = retryAfterSeconds;
    Error.captureStackTrace?.(this, new.target);
  }
}

const define = (statusCode, defaultCode) => class extends AppError {
  constructor(message, options = {}) {
    super(message ?? `HTTP ${statusCode}`, { statusCode, code: options.code ?? defaultCode, ...options });
  }
};

export const BadRequestError = define(400, 'BAD_REQUEST');
export const UnauthorizedError = define(401, 'UNAUTHENTICATED');
export const ForbiddenError = define(403, 'FORBIDDEN');
export const NotFoundError = define(404, 'NOT_FOUND');
export const ConflictError = define(409, 'CONFLICT');
export const PayloadTooLargeError = define(413, 'PAYLOAD_TOO_LARGE');
export const UnsupportedMediaTypeError = define(415, 'UNSUPPORTED_MEDIA_TYPE');
export const TooManyRequestsError = define(429, 'RATE_LIMITED');
export const ServiceUnavailableError = define(503, 'SERVICE_UNAVAILABLE');

export class ValidationError extends AppError {
  constructor(details, message = 'Request validation failed') {
    super(message, { statusCode: 422, code: 'VALIDATION_ERROR', details });
  }
}

export class InternalError extends AppError {
  constructor(message = 'Internal server error', { cause } = {}) {
    super(message, { statusCode: 500, code: 'INTERNAL_ERROR', cause, isOperational: false });
  }
}
```

```js
// File: src/utils/normalizeError.js
import {
  AppError, BadRequestError, ConflictError, InternalError,
  PayloadTooLargeError, ServiceUnavailableError, UnsupportedMediaTypeError,
} from './AppError.js';

export function normalizeError(value) {
  if (value instanceof AppError) return value;

  // Non-Error throw values ('oops', 42, null).
  if (!(value instanceof Error)) {
    return new InternalError(`Non-Error thrown: ${String(value)}`, { cause: value });
  }

  // express.json()/urlencoded() failures.
  switch (value.type) {
    case 'entity.parse.failed':
      return new BadRequestError('Request body is not valid JSON', { cause: value });
    case 'entity.too.large':
      return new PayloadTooLargeError('Request body is too large', { cause: value });
    case 'charset.unsupported':
    case 'encoding.unsupported':
      return new UnsupportedMediaTypeError('Unsupported charset or encoding', { cause: value });
    default:
      break;
  }

  // Driver errors.
  switch (value.code) {
    case '23505':
    case 'ER_DUP_ENTRY':
    case 11000:
      return new ConflictError('Resource already exists', { cause: value });
    case 'ECONNREFUSED':
    case 'ETIMEDOUT':
    case 'PROTOCOL_CONNECTION_LOST':
      return new ServiceUnavailableError('Database unavailable', { cause: value, retryAfterSeconds: 5 });
    case '22P02':
    case 'CastError':
      return new BadRequestError('Invalid identifier format', { cause: value });
    default:
      break;
  }

  // JSON.parse failures thrown by hand-written code.
  if (value instanceof SyntaxError && /JSON/i.test(value.message)) {
    return new BadRequestError('Request body is not valid JSON', { cause: value });
  }

  return new InternalError(value.message, { cause: value });
}
```

```js
// File: src/middleware/errorHandler.js
import { AppError } from '../utils/AppError.js';
import { normalizeError } from '../utils/normalizeError.js';

const SECRET_KEYS = /password|secret|token|authorization|cookie|apikey|api_key/i;

function redact(input, depth = 0) {
  if (input === null || typeof input !== 'object' || depth > 4) return input;
  if (Array.isArray(input)) return input.slice(0, 20).map((item) => redact(item, depth + 1));

  return Object.fromEntries(
    Object.entries(input).map(([key, value]) => [key, SECRET_KEYS.test(key) ? '[redacted]' : redact(value, depth + 1)]),
  );
}

export function createErrorHandler({ config, logger = console }) {
  const isProduction = config?.nodeEnv === 'production' || config?.isProduction === true;

  return function errorHandler(error, req, res, next) {
    const appError = normalizeError(error);
    const statusCode = appError.statusCode ?? 500;

    const record = {
      level: statusCode >= 500 ? 'error' : 'warn',
      message: appError.message,
      code: appError.code,
      statusCode,
      method: req.method,
      path: req.originalUrl,
      requestId: req.id,
      stack: statusCode >= 500 ? appError.stack : undefined,
      cause: appError.cause ? { message: appError.cause.message, code: appError.cause.code } : undefined,
      details: appError.isOperational ? redact(appError.details) : undefined,
    };
    (record.level === 'error' ? logger.error : logger.warn).call(logger, record);

    if (res.headersSent) return next(error);
    if (statusCode === 401) res.set('WWW-Authenticate', 'Bearer realm="api"');
    if (appError.retryAfterSeconds) res.set('Retry-After', String(appError.retryAfterSeconds));

    const safeToExpose = appError.isOperational !== false && appError instanceof AppError;
    return res.status(statusCode).json({
      error: {
        code: appError.code ?? 'INTERNAL_ERROR',
        message: statusCode >= 500 && isProduction ? 'Something went wrong' : appError.message,
        details: safeToExpose ? appError.details : undefined,
        requestId: req.id,
      },
    });
  };
}
```

```js
// File: tests/error-layer.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { requestId } from '../src/middleware/requestId.js';
import { createErrorHandler } from '../src/middleware/errorHandler.js';
import {
  BadRequestError, UnauthorizedError, ForbiddenError, NotFoundError, ConflictError,
  PayloadTooLargeError, UnsupportedMediaTypeError, TooManyRequestsError, ServiceUnavailableError, ValidationError,
} from '../src/utils/AppError.js';

const SECRET = 'hunter2-should-never-leak';
const logs = [];

let server;
let baseUrl;

before(async () => {
  const app = express();
  app.use(requestId);
  app.use(express.json({ limit: '200b' }));

  const throws = (error) => () => { throw error; };

  app.get('/400', throws(new BadRequestError('Bad cursor format')));
  app.get('/401', throws(new UnauthorizedError()));
  app.get('/403', throws(new ForbiddenError()));
  app.get('/404', throws(new NotFoundError('Note missing')));
  app.get('/409', throws(new ConflictError('Email taken', { field: 'email' })));
  app.get('/413', throws(new PayloadTooLargeError()));
  app.get('/415', throws(new UnsupportedMediaTypeError()));
  app.get('/422', throws(new ValidationError([{ field: 'title', message: 'required' }])));
  app.get('/429', throws(new TooManyRequestsError('Slow down', { retryAfterSeconds: 30 })));
  app.get('/503', throws(new ServiceUnavailableError('Database unavailable', { retryAfterSeconds: 5 })));

  app.get('/leak', throws(Object.assign(
    new Error(`connect ECONNREFUSED 10.0.3.7:5432 user=admin password=${SECRET}`),
    { code: 'ECONNREFUSED' },
  )));

  app.get('/bug', throws(new TypeError(`Cannot read properties of undefined (reading 'id') token=${SECRET}`)));

  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND', requestId: req.id } }));
  app.use(createErrorHandler({
    config: { nodeEnv: 'production' },
    logger: { error: (record) => logs.push(record), warn: (record) => logs.push(record) },
  }));

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const cases = [
  ['/400', 400, 'BAD_REQUEST'],
  ['/401', 401, 'UNAUTHENTICATED'],
  ['/403', 403, 'FORBIDDEN'],
  ['/404', 404, 'NOT_FOUND'],
  ['/409', 409, 'CONFLICT'],
  ['/413', 413, 'PAYLOAD_TOO_LARGE'],
  ['/415', 415, 'UNSUPPORTED_MEDIA_TYPE'],
  ['/422', 422, 'VALIDATION_ERROR'],
  ['/429', 429, 'RATE_LIMITED'],
  ['/503', 503, 'SERVICE_UNAVAILABLE'],
  ['/leak', 503, 'SERVICE_UNAVAILABLE'],
  ['/bug', 500, 'INTERNAL_ERROR'],
];

for (const [path, status, code] of cases) {
  test(`${path} → ${status} ${code}`, async () => {
    const response = await fetch(baseUrl + path);
    const body = await response.json();

    assert.equal(response.status, status);
    assert.equal(body.error.code, code);
    assert.equal(typeof body.error.message, 'string');
    assert.match(body.error.requestId, /^[0-9a-f-]{36}$/);

    // The leak test, applied to EVERY case.
    const serialised = JSON.stringify(body);
    assert.ok(!serialised.includes(SECRET), 'a secret leaked');
    assert.ok(!serialised.includes('10.0.3.7'), 'an internal host leaked');
    assert.ok(!serialised.includes('.js:'), 'a stack frame leaked');
    assert.equal(body.error.stack, undefined);
    assert.equal(body.error.cause, undefined);
  });
}

test('protocol headers are present where they belong', async () => {
  const unauthorised = await fetch(`${baseUrl}/401`);
  assert.match(unauthorised.headers.get('www-authenticate'), /Bearer/);

  const limited = await fetch(`${baseUrl}/429`);
  assert.equal(limited.headers.get('retry-after'), '30');

  const unavailable = await fetch(`${baseUrl}/503`);
  assert.equal(unavailable.headers.get('retry-after'), '5');
});

test('details are exposed for operational errors only', async () => {
  assert.deepEqual((await (await fetch(`${baseUrl}/422`)).json()).error.details, [
    { field: 'title', message: 'required' },
  ]);
  assert.equal((await (await fetch(`${baseUrl}/409`)).json()).error.details.field, 'email');
  assert.equal((await (await fetch(`${baseUrl}/bug`)).json()).error.details, undefined);
});

test('404 route-not-found uses the same envelope', async () => {
  const response = await fetch(`${baseUrl}/definitely-not-a-route`);
  const body = await response.json();
  assert.equal(response.status, 404);
  assert.equal(body.error.code, 'ROUTE_NOT_FOUND');
});

test('logs are structured, correlated, and levelled correctly', async () => {
  logs.length = 0;

  await fetch(`${baseUrl}/404`);
  const warn = logs.at(-1);
  assert.equal(warn.level, 'warn');
  assert.equal(warn.code, 'NOT_FOUND');
  assert.ok(warn.requestId);

  await fetch(`${baseUrl}/bug`);
  const error = logs.at(-1);
  assert.equal(error.level, 'error');
  assert.ok(error.stack.includes('TypeError'));
  assert.ok(!JSON.stringify(error.details ?? {}).includes(SECRET));
});

test('a non-Error thrown value becomes a 500, not a crash', async () => {
  const app = express();
  app.get('/string-throw', () => { throw 'plain string'; });     // eslint-disable-line no-throw-literal
  app.use(createErrorHandler({ config: { nodeEnv: 'production' }, logger: { error() {}, warn() {} } }));

  const isolated = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => isolated.once('listening', resolve));

  const response = await fetch(`http://127.0.0.1:${isolated.address().port}/string-throw`);
  assert.equal(response.status, 500);
  assert.equal((await response.json()).error.code, 'INTERNAL_ERROR');

  await new Promise((resolve) => isolated.close(resolve));
});
```

```bash
node --test tests/error-layer.test.js
```

```text
✔ /400 → 400 BAD_REQUEST
✔ /401 → 401 UNAUTHENTICATED
✔ /403 → 403 FORBIDDEN
✔ /404 → 404 NOT_FOUND
✔ /409 → 409 CONFLICT
✔ /413 → 413 PAYLOAD_TOO_LARGE
✔ /415 → 415 UNSUPPORTED_MEDIA_TYPE
✔ /422 → 422 VALIDATION_ERROR
✔ /429 → 429 RATE_LIMITED
✔ /503 → 503 SERVICE_UNAVAILABLE
✔ /leak → 503 SERVICE_UNAVAILABLE
✔ /bug → 500 INTERNAL_ERROR
✔ protocol headers are present where they belong
✔ details are exposed for operational errors only
✔ 404 route-not-found uses the same envelope
✔ logs are structured, correlated, and levelled correctly
✔ a non-Error thrown value becomes a 500, not a crash
pass 17
fail 0
```

**Why this solution is trustworthy**

| Property | How it is achieved |
| --- | --- |
| One shape everywhere | A single formatter; the 404 middleware uses the same envelope |
| No leaks, proven | The leak assertions run against **every** case, including the ones that carry secrets |
| The client learns the right things | 4xx carries actionable `details`; 5xx carries only a `requestId` |
| Operators can debug | `requestId` is in both the response and the log; stacks and causes are logged, never sent |
| Failures are actionable | `WWW-Authenticate` and `Retry-After` tell clients what to do next |

</details>

---

## Exercise 8.2 — Find the ten leaks

```js
// File: leaky.js
import express from 'express';
import { db } from './db.js';

const app = express();
app.use(express.json());

app.get('/api/v1/users/:id', async (req, res) => {
  const user = await db.query(`SELECT * FROM users WHERE id = '${req.params.id}'`);
  res.json(user.rows[0]);
});

app.post('/api/v1/users', async (req, res) => {
  try {
    const user = await db.query('INSERT INTO users (email, password) VALUES ($1, $2) RETURNING *', [
      req.body.email, req.body.password,
    ]);
    res.status(200).send(JSON.stringify(user.rows[0]));
  } catch (error) {
    res.status(500).json({ error: error.message, stack: error.stack });
  }
});

app.get('/api/v1/admin/stats', async (req, res) => {
  if (req.query.token !== process.env.ADMIN_TOKEN) {
    res.status(200).json({ locked: true });
  }
  const stats = await db.query('SELECT count(*) FROM users');
  res.json({ stats });
});

app.use((error, req, res, next) => {
  console.log('error', error);
  res.end('Something failed');
});

app.listen(3000);
```

Ten security and correctness problems — find them all.

<details>
<summary>Solution</summary>

| # | Problem | Impact |
| --- | --- | --- |
| 1 | **String interpolation into SQL** (`'${req.params.id}'`) | SQL injection — the single most severe class of bug in this file |
| 2 | `res.json(user.rows[0])` with **no existence check** | A missing user returns `200` with an empty body instead of `404` |
| 3 | `SELECT *` returned straight to the client | Mass data exposure — `password_hash`, internal flags, deleted markers |
| 4 | **Passwords stored unhashed** (`req.body.password` inserted directly) | Total credential compromise on any database leak |
| 5 | `res.status(200).send(JSON.stringify(...))` | Wrong status for a creation (`201`), and `Content-Type` becomes `text/html` |
| 6 | `{ error: error.message, stack: error.stack }` | Leaks driver internals, table names, and stack frames to any client |
| 7 | `if (req.query.token !== ADMIN_TOKEN)` with **no `return`** | The guard does nothing: execution continues and the stats are returned anyway |
| 8 | Admin token compared with `!==` | Timing-attack-friendly and the token is in a query string (logged everywhere); use a header + constant-time compare |
| 9 | The error middleware is **registered before the routes** | It never runs; Express's default handler answers with an HTML stack page in development |
| 10 | `res.end('Something failed')` — plain text, no status, no envelope | Clients cannot parse it; `200` is implied only if nothing set otherwise (here the status would default to `200`) |
| 11 | No body-size limit, no validation of `email` | Arbitrary payloads persisted; invalid data reaches the database |
| 12 | Hard-coded `app.listen(3000)`, no host | Not deployable, and it collides with other services on the box |

```js
// File: fixed.js
import express from 'express';
import { z } from 'zod';
import { hash } from 'bcryptjs';
import { timingSafeEqual } from 'node:crypto';
import { db } from './db.js';
import { requestId } from './middleware/requestId.js';
import { createErrorHandler } from './middleware/errorHandler.js';
import { NotFoundError, UnauthorizedError, ConflictError, ValidationError } from './utils/AppError.js';

const app = express();
app.disable('x-powered-by');
app.use(requestId);
app.use(express.json({ limit: '100kb', strict: true }));

const UuidSchema = z.string().uuid();
const CreateUserSchema = z.object({
  email: z.string().trim().toLowerCase().email().max(254),
  password: z.string().min(8).max(200),
}).strict();

/** 3 + 6: one place that decides what a client may see. */
const toUserDto = (row) => ({
  id: row.id,
  email: row.email,
  createdAt: row.created_at,
});

/** 8: constant-time token comparison. */
function safeEqual(a, b) {
  const left = Buffer.from(String(a ?? ''), 'utf8');
  const right = Buffer.from(String(b ?? ''), 'utf8');
  return left.length === right.length && timingSafeEqual(left, right);
}

// 1: parameterised query; 2: explicit 404; 3: DTO projection.
app.get('/api/v1/users/:id', async (req, res, next) => {
  try {
    const parsed = UuidSchema.safeParse(req.params.id);
    if (!parsed.success) {
      throw new ValidationError([{ field: 'id', message: 'must be a UUID' }]);
    }

    const result = await db.query('SELECT id, email, created_at FROM users WHERE id = $1', [parsed.data]);
    if (result.rowCount === 0) throw new NotFoundError(`User ${parsed.data} not found`);

    return res.json({ data: toUserDto(result.rows[0]) });
  } catch (error) {
    return next(error);
  }
});

// 4: hash the password; 5: correct status + Location; 10: the standard envelope on failure.
app.post('/api/v1/users', async (req, res, next) => {
  try {
    const parsed = CreateUserSchema.safeParse(req.body ?? {});
    if (!parsed.success) {
      throw new ValidationError(
        parsed.error.issues.map((issue) => ({ field: issue.path.join('.') || 'body', message: issue.message })),
      );
    }

    const { email, password } = parsed.data;
    const passwordHash = await hash(password, 12);

    const result = await db.query(
      'INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id, email, created_at',
      [email, passwordHash],
    );

    const user = toUserDto(result.rows[0]);
    return res.status(201).location(`/api/v1/users/${user.id}`).json({ data: user });
  } catch (error) {
    if (error.code === '23505') {
      return next(new ConflictError('That email is already registered', { field: 'email' }));
    }
    return next(error);
  }
});

// 7 + 8: auth via header, constant-time compare, and an early return that actually returns.
app.get('/api/v1/admin/stats', async (req, res, next) => {
  try {
    const token = req.get('x-admin-token');
    if (!token || !safeEqual(token, process.env.ADMIN_TOKEN)) {
      throw new UnauthorizedError('Admin token required');
    }

    const result = await db.query('SELECT count(*)::int AS total FROM users');
    return res.json({ data: { total: result.rows[0].total } });
  } catch (error) {
    return next(error);
  }
});

// 9 + 10: 404 then the single error handler, both last, both JSON.
app.use((req, res) => {
  res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND', message: `${req.method} ${req.originalUrl} not found`, requestId: req.id } });
});
app.use(createErrorHandler({ config: { nodeEnv: process.env.NODE_ENV ?? 'development' } }));

const port = Number(process.env.PORT ?? 3000);
app.listen(port, '0.0.0.0', () => console.log(`listening on http://localhost:${port}`));
```

```bash
# Verify each fix:
curl -s -i localhost:3000/api/v1/users/1%27%20OR%20%271%27=%271 | head -1     # 422 — injection is impossible
curl -s localhost:3000/api/v1/users/00000000-0000-0000-0000-000000000000      # 404, not 200 with a null body
curl -s -X POST localhost:3000/api/v1/users -H 'Content-Type: application/json' \
  -d '{"email":"bad","password":"x"}'                                          # 422 with field details
curl -s localhost:3000/api/v1/admin/stats                                      # 401 (the guard now returns)
curl -s -H 'x-admin-token: wrong' localhost:3000/api/v1/admin/stats            # 401
curl -s -X POST localhost:3000/api/v1/users -H 'Content-Type: application/json' \
  -d '{"email":"same@example.com","password":"longenough"}'
curl -s -X POST localhost:3000/api/v1/users -H 'Content-Type: application/json' \
  -d '{"email":"same@example.com","password":"longenough"}'                    # 409, not a leaked 500
# Force an unexpected error and confirm the response:
# 500 {"error":{"code":"INTERNAL_ERROR","message":"Something went wrong","requestId":"…"}}
```

**The pattern behind all ten fixes:** every one of them *removes information or authority from the
client* — no raw SQL, no raw rows, no stack traces, no unchecked guard, and no plain-text responses.

</details>

---

## What's next

One error contract, everywhere. Next: organising the routes of a real API into routers that can be
composed, mounted and tested in isolation.

→ [09 — Routers](09-routers.md)
