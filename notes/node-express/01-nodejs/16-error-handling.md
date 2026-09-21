# 16 — Error Handling

> **Where this fits:** In production, roughly a third of your code is about what happens when things go wrong. This chapter builds the error system you will reuse in every project: custom error classes, operational vs programmer errors, async error propagation, retries, and process-level safety nets. It is the foundation of [02-express/08-error-handling.md](../02-express/08-error-handling.md).

***

## 1. What an error actually is

An `Error` object carries four things:

```js
// File: error-anatomy.mjs
const error = new Error('Payment provider rejected the charge');

error.name = 'PaymentError';                                  // the constructor's name
error.code = 'CARD_DECLINED';                                 // machine-readable identifier
error.statusCode = 402;                                       // HTTP status (our convention)
error.details = [{ field: 'card', message: 'expired' }];      // structured extra data
error.cause = new Error('upstream returned 402');             // the original error

console.log(error.name);         // PaymentError
console.log(error.message);      // Payment provider rejected the charge
console.log(error.code);         // CARD_DECLINED
console.log(error.stack.split('\n').slice(0, 3).join('\n'));
// Error: Payment provider rejected the charge
//     at file:///…/error-anatomy.mjs:2:15
//     at …
console.log('cause:', error.cause.message);

// Errors are also thrown and caught by identity:
class NotFoundError extends Error {}
try {
  throw new NotFoundError('user 42 does not exist');
} catch (caught) {
  console.log(caught instanceof NotFoundError);   // true
  console.log(caught instanceof Error);           // true
  console.log(caught instanceof TypeError);       // false
}
```

### What the message is (and is not) for

The **message is for humans**: developers reading logs, and — for `4xx` errors — end users. It is **not** an interface: never parse a message string to decide behaviour, because someone will reword it. That is what `code` is for.

```js
// ❌ Fragile: breaks the moment someone edits the wording.
if (error.message.includes('duplicate key')) { /* … */ }

// ✅ Stable: the code is part of the contract (and comes from the driver).
if (error.code === 'ER_DUP_ENTRY' || error.code === '23505' || error.code === 11000) { /* … */ }
```

***

## 2. Operational vs programmer errors

The most useful distinction in error handling:

|              | **Operational (expected)**                                                       | **Programmer (bug)**                                                                                |
| ------------ | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Examples     | User not found, invalid input, DB unreachable, upstream timeout, duplicate email | `TypeError: cannot read property of undefined`, wrong argument order, `undefined is not a function` |
| Predictable? | Yes                                                                              | No                                                                                                  |
| Recoverable? | Usually — respond with a 4xx/5xx and continue                                    | Not safely — the process state is unknown                                                           |
| Response     | Structured error to the client                                                   | Generic `500`, log the stack, alert                                                                 |
| Counts as    | A normal event                                                                   | A defect to fix                                                                                     |

```js
// File: error-kinds.mjs
class AppError extends Error {
  constructor(message, { statusCode = 500, code = 'INTERNAL_ERROR', details, cause } = {}) {
    super(message, { cause });
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.isOperational = statusCode < 500;      // 4xx = the caller's problem: expected
    Error.captureStackTrace(this, new.target);
  }
}

class ValidationError extends AppError {
  constructor(details, message = 'Validation failed') {
    super(message, { statusCode: 422, code: 'VALIDATION_ERROR', details });
  }
}

class NotFoundError extends AppError {
  constructor(resource, id) {
    super(`${resource} ${id} not found`, { statusCode: 404, code: 'NOT_FOUND' });
    this.resource = resource;
    this.resourceId = id;
  }
}

class ConflictError extends AppError {
  constructor(message, details) {
    super(message, { statusCode: 409, code: 'CONFLICT', details });
  }
}

class UnauthorizedError extends AppError {
  constructor(message = 'Authentication required') {
    super(message, { statusCode: 401, code: 'UNAUTHENTICATED' });
  }
}

class ForbiddenError extends AppError {
  constructor(message = 'You do not have permission to do this') {
    super(message, { statusCode: 403, code: 'FORBIDDEN' });
  }
}

class RateLimitError extends AppError {
  constructor(retryAfterSeconds) {
    super('Too many requests', { statusCode: 429, code: 'RATE_LIMITED' });
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

class ServiceUnavailableError extends AppError {
  constructor(dependency, cause) {
    super(`${dependency} is unavailable`, {
      statusCode: 503,
      code: 'SERVICE_UNAVAILABLE',
      cause,
    });
    this.dependency = dependency;
  }
}

// How the status code choice maps to the distinction:
const errors = [
  new ValidationError([{ field: 'email', message: 'invalid format' }]),
  new NotFoundError('User', 42),
  new ConflictError('Email already registered', [{ field: 'email' }]),
  new UnauthorizedError(),
  new ForbiddenError(),
  new RateLimitError(30),
  new ServiceUnavailableError('payment-gateway', new Error('ECONNREFUSED')),
];

for (const error of errors) {
  console.log(
    `${error.name.padEnd(24)} status=${String(error.statusCode).padEnd(4)} code=${error.code.padEnd(20)} operational=${error.isOperational}`
  );
}
```

```
ValidationError          status=422  code=VALIDATION_ERROR     operational=true
NotFoundError            status=404  code=NOT_FOUND            operational=true
ConflictError            status=409  code=CONFLICT             operational=true
UnauthorizedError        status=401  code=UNAUTHENTICATED      operational=true
ForbiddenError           status=403  code=FORBIDDEN            operational=true
RateLimitError           status=429  code=RATE_LIMITED         operational=true
ServiceUnavailableError  status=503  code=SERVICE_UNAVAILABLE  operational=false
```

Notice `ServiceUnavailableError.isOperational` is `false` — it is a 5xx, so by the rule above it is "not the caller's fault". But it _is_ expected and recoverable, which shows the two axes are independent:

|         | Expected                              | Unexpected                                           |
| ------- | ------------------------------------- | ---------------------------------------------------- |
| **4xx** | `ValidationError`, `NotFoundError`    | — (a 4xx caused by a bug usually means wrong status) |
| **5xx** | `ServiceUnavailableError`, DB timeout | `TypeError`, `ReferenceError`                        |

Both axes matter: the **status code** drives the HTTP response, and **expectedness** drives whether you log at `warn` or `error`, whether you page a human, and whether you keep serving.

***

## 3. `try`/`catch`/`finally` — the rules

```js
// File: try-catch-rules.mjs
import { readFile } from 'node:fs/promises';
import { setTimeout as sleep } from 'node:timers/promises';

// 1. Catch ONLY what you can handle. Log-and-rethrow is usually right; log-and-ignore is a bug.
async function loadOrDefault(filePath, fallback) {
  try {
    return await readFile(filePath, 'utf8');
  } catch (error) {
    if (error.code === 'ENOENT') {
      console.warn(`[config] ${filePath} not found, using fallback`);
      return fallback;                       // handled: a missing optional file is expected
    }
    throw error;                             // everything else is not mine to swallow
  }
}

console.log(await loadOrDefault('./missing.txt', 'default'));

// 2. Add context, keep the cause — never create a brand-new error and drop the original.
async function readUserConfig(userId) {
  try {
    return await loadOrDefault(`./configs/${userId}.json`, '{}');
  } catch (error) {
    throw new Error(`Failed to read config for user ${userId}`, { cause: error });
  }
}

console.log(await readUserConfig('u_1'));

// 3. Validate inputs BEFORE the try, so genuine bugs are not masked as operational errors.
function parsePort(raw) {
  const port = Number(raw);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new RangeError(`Invalid port: ${raw}`);        // programmer input error → propagate
  }
  return port;
}
console.log('port:', parsePort('3000'));

// 4. Do not use exceptions for normal control flow in hot paths.
//    (Exceptions are relatively expensive: stack capture on throw.)
const userExists = (users, id) => users.some((user) => user.id === id);
console.log('exists:', userExists([{ id: 'a' }], 'a'));

// 5. finally for cleanup — never for returning a value.
async function withTempResource(fn) {
  let closed = false;
  try {
    return await fn();
  } finally {
    closed = true;
    console.log('resource released (closed =', closed, ')');
  }
}
await withTempResource(async () => {
  await sleep(5);
  return 'work done';
});

// 6. Rethrowing non-Error values: always normalise.
async function normaliseExample() {
  try {
    // Someone threw a string — which does happen in third-party code.
    throw 'something went wrong';
  } catch (caught) {
    const error = caught instanceof Error ? caught : new Error(String(caught));
    console.log('normalised:', error.name, '-', error.message);
  }
}
await normaliseExample();
```

### The five rules, condensed

1. **Catch only what you can handle.** Otherwise let it propagate.
2. **Preserve the cause.** `new Error('context', { cause: originalError })`.
3. **Never swallow silently.** `catch {}` hides outages.
4. **Fail fast on programmer errors.** Do not convert a bug into a friendly message.
5. **`finally` is for cleanup only.**

***

## 4. Asynchronous errors

This section is the source of most production incidents, so read it carefully.

```js
// File: async-errors.mjs
import { setTimeout as sleep } from 'node:timers/promises';

// 1. `await` + try/catch works naturally.
async function withAwait() {
  try {
    await sleep(5).then(() => {
      throw new Error('from an awaited promise');
    });
    return 'not reached';
  } catch (error) {
    return `caught: ${error.message}`;
  }
}
console.log(await withAwait());

// 2. Without `await`, the try/catch does NOT catch it — the rejection escapes.
async function withoutAwait() {
  try {
    sleep(5).then(() => {
      throw new Error('escapes the catch');
    });
    return 'returned before the error happens';
  } catch (error) {
    return `caught: ${error.message}`;        // never runs
  }
}
console.log(await withoutAwait());

// 3. Callbacks do not throw into the caller's stack — the error arrives as an argument.
import { readFile } from 'node:fs';

function callbackStyle(callback) {
  readFile('./missing-file.txt', (error, data) => {
    // This error cannot be caught by a try/catch around the outer call.
    callback(error, data);
  });
}

await new Promise((resolve) => {
  callbackStyle((error, data) => {
    console.log('callback error:', error?.code);      // ENOENT
    resolve();
  });
});

// 4. Async function inside a constructor or an event listener: the classic escape route.
import { EventEmitter } from 'node:events';

const emitter = new EventEmitter({ captureRejections: true });
emitter.on('job', async () => {
  throw new Error('async listener failure');
});
emitter.on('error', (error) => console.log('error event:', error.message));
emitter.emit('job');

// 5. A promise chain that nobody handles → unhandled rejection.
//    (Commented out because it would crash the process — which is the point.)
// sleep(5).then(() => { throw new Error('unhandled'); });
```

### The rule that prevents most incidents

> **Every promise must have a handler.** Either `await` it inside a `try/catch`, return it to something that handles it, or explicitly attach `.catch()`.

```js
// File: promise-hygiene.mjs
import { setTimeout as sleep } from 'node:timers/promises';

async function sendEmail(to) {
  await sleep(5);
  if (!to.includes('@')) throw new Error('invalid email address');
  return { delivered: true };
}

// ❌ Fire and forget — an unhandled rejection waiting to crash the process.
// sendEmail('not-an-email');

// ✅ Deliberately detached, with a handler. The `void` documents the intent.
void sendEmail('not-an-email').catch((error) => {
  console.error('[email] delivery failed:', error.message);
});

// ✅ Inside a request handler: await it, so the failure is part of the response.
async function registerUser(email) {
  try {
    const result = await sendEmail(email);
    return { status: 'registered', welcomeEmailSent: result.delivered };
  } catch (error) {
    // The user is registered; the email failing must not fail the registration.
    console.error('[email] welcome email failed:', error.message);
    return { status: 'registered', welcomeEmailSent: false };
  }
}

console.log(await registerUser('ankit@example.com'));

await sleep(20);   // let the detached promise settle before this example exits
```

***

## 5. Database and HTTP errors — translating the outside world

External systems signal failures in their own vocabulary. Translate them **once**, at the boundary:

```js
// File: translate-errors.mjs
class AppError extends Error {
  constructor(message, { statusCode = 500, code = 'INTERNAL_ERROR', details, cause } = {}) {
    super(message, { cause });
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}
class ValidationError extends AppError {
  constructor(details, message = 'Validation failed') {
    super(message, { statusCode: 422, code: 'VALIDATION_ERROR', details });
  }
}
class NotFoundError extends AppError {
  constructor(resource, id) {
    super(`${resource} ${id} not found`, { statusCode: 404, code: 'NOT_FOUND' });
  }
}
class ConflictError extends AppError {
  constructor(message, details) {
    super(message, { statusCode: 409, code: 'CONFLICT', details });
  }
}
class ServiceUnavailableError extends AppError {
  constructor(dependency, cause) {
    super(`${dependency} is unavailable`, { statusCode: 503, code: 'SERVICE_UNAVAILABLE', cause });
  }
}

/** Map a database driver error to an application error. One place, one vocabulary. */
export function fromDatabaseError(error, context = {}) {
  // PostgreSQL SQLSTATE codes
  const pgCodes = { 23505: 'unique_violation', 23503: 'foreign_key_violation', 23502: 'not_null_violation' };
  // MySQL error numbers
  const mysqlCodes = { ER_DUP_ENTRY: 'unique_violation', ER_NO_REFERENCED_ROW_2: 'foreign_key_violation' };
  // MongoDB
  const mongoCodes = { 11000: 'unique_violation' };

  const kind = pgCodes[error.code] ?? mysqlCodes[error.code] ?? mongoCodes[error.code];

  switch (kind) {
    case 'unique_violation':
      return new ConflictError(
        context.message ?? `${context.field ?? 'A record'} already exists`,
        [{ field: context.field ?? 'unknown', message: 'must be unique' }]
      );
    case 'foreign_key_violation':
      return new ValidationError([
        { field: context.field ?? 'unknown', message: 'references a record that does not exist' },
      ]);
    case 'not_null_violation':
      return new ValidationError([{ field: context.field ?? 'unknown', message: 'is required' }]);
    default:
      // Unknown database errors are infrastructure problems: 503, not 500, and never leaked.
      return new ServiceUnavailableError('database', error);
  }
}

/** Map an HTTP client error (fetch/axios) to an application error. */
export async function fromHttpError(response, dependency) {
  if (response.status === 404) return new NotFoundError(dependency, 'resource');
  if (response.status === 429) {
    const retryAfter = Number(response.headers.get('retry-after') ?? 60);
    return new ServiceUnavailableError(`${dependency} (rate limited, retry in ${retryAfter}s)`);
  }
  if (response.status >= 500) return new ServiceUnavailableError(dependency);
  // 4xx from an upstream usually means WE sent something wrong: that is a bug on our side.
  const body = await response.text().catch(() => '');
  const error = new AppError(`${dependency} rejected the request: ${body.slice(0, 200)}`, {
    statusCode: 502,
    code: 'UPSTREAM_REJECTED',
  });
  return error;
}

// Demonstrations
const cases = [
  fromDatabaseError({ code: '23505' }, { field: 'email', message: 'Email already registered' }),
  fromDatabaseError({ code: 'ER_DUP_ENTRY' }, { field: 'email' }),
  fromDatabaseError({ code: '23503' }, { field: 'userId' }),
  fromDatabaseError({ code: 'ECONNREFUSED' }, {}),
  fromDatabaseError({ code: 11000 }, { field: 'email', message: 'Email already registered' }),
];

for (const error of cases) {
  console.log(`${String(error.statusCode).padEnd(4)} ${error.code.padEnd(22)} ${error.message}`);
}
```

```
409  CONFLICT               Email already registered
409  CONFLICT               email already exists
422  VALIDATION_ERROR       Validation failed
503  SERVICE_UNAVAILABLE    database is unavailable
409  CONFLICT               Email already registered
```

**Why this matters:** without translation, a duplicate email produces a raw SQL error string in your HTTP response (an information leak and a terrible API), or a generic `500` that tells the user nothing. With translation, it is exactly what it should be: `409 Conflict` with a field-level detail the form can highlight.

### Retries belong at the boundary too, for _transient_ errors only

```js
// File: transient-retry.mjs
import { setTimeout as sleep } from 'node:timers/promises';

/** Only these are worth retrying: they may succeed on the next attempt. */
const isTransient = (error) =>
  ['ECONNRESET', 'ETIMEDOUT', 'ECONNREFUSED', 'EPIPE'].includes(error.code) ||
  error.statusCode === 503 ||
  error.statusCode === 429 ||
  error.code === 'SERVICE_UNAVAILABLE';

/** These will never succeed without a change: retrying them is wasted time and load. */
const isPermanent = (error) =>
  error.statusCode === 400 ||
  error.statusCode === 401 ||
  error.statusCode === 403 ||
  error.statusCode === 404 ||
  error.statusCode === 422 ||
  error.code === 'VALIDATION_ERROR';

export async function retryTransient(operation, { attempts = 4, baseDelayMs = 50, signal } = {}) {
  let lastError;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await operation(attempt);
    } catch (error) {
      lastError = error;

      if (isPermanent(error) || !isTransient(error) || attempt === attempts) throw error;

      const backoff = Math.min(baseDelayMs * 2 ** (attempt - 1), 2_000);
      const jittered = backoff * (0.5 + Math.random() / 2);      // avoid retry stampedes
      await sleep(jittered, undefined, { signal });
    }
  }

  throw lastError;
}

let attempts = 0;
const flaky = async () => {
  attempts += 1;
  if (attempts < 3) {
    const error = new Error('connection reset by peer');
    error.code = 'ECONNRESET';
    throw error;
  }
  return `succeeded on attempt ${attempts}`;
};

console.log(await retryTransient(flaky));
```

**Never retry without idempotency.** Retrying a `POST /payments` that actually succeeded but whose response was lost will charge the customer twice. That is why payment APIs require an `Idempotency-Key` header — the server stores the key with the result and returns the original response for a repeat call.

***

## 6. Process-level safety nets

Even with careful error handling, surprises reach the top level. Define the policy **once**:

```js
// File: process-guards.mjs
import { once } from 'node:events';
import { createServer } from 'node:http';

let shuttingDown = false;

function shutdown(reason, error) {
  if (shuttingDown) return;
  shuttingDown = true;

  console.error(
    JSON.stringify({
      level: 'fatal',
      message: `shutting down: ${reason}`,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    })
  );

  // Stop accepting new connections; in-flight requests complete.
  server.close(() => {
    console.log('server closed cleanly');
    process.exit(1);
  });

  server.closeIdleConnections?.();

  // Safety net: never hang forever.
  setTimeout(() => {
    console.error('forced exit after 10s');
    process.exit(1);
  }, 10_000).unref();
}

process.on('uncaughtException', (error) => shutdown('uncaughtException', error));
process.on('unhandledRejection', (reason) => shutdown('unhandledRejection', reason));

// Graceful shutdown on signals: what Docker/Kubernetes send before killing the process.
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, () => {
    console.log(`${signal} received`);
    if (shuttingDown) process.exit(0);
    shuttingDown = true;
    server.close(() => process.exit(0));
    server.closeIdleConnections?.();
    setTimeout(() => process.exit(0), 10_000).unref();
  });
}

const server = createServer((req, res) => {
  if (req.url === '/crash') {
    // A programmer error: an unhandled rejection outside any request scope.
    Promise.reject(new Error('simulated bug in background work'));
    res.end('triggered an unhandled rejection\n');
    return;
  }
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', pid: process.pid }));
    return;
  }
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: { code: 'NOT_FOUND' } }));
});

server.listen(0, '127.0.0.1');
await once(server, 'listening');
const { port } = server.address();
console.log(`listening on ${port} — try /health then /crash`);

// Self-test: health, then trigger the crash path.
const health = await fetch(`http://127.0.0.1:${port}/health`).then((r) => r.json());
console.log('health before crash:', health);
try {
  await fetch(`http://127.0.0.1:${port}/crash`).then((r) => r.text());
  console.log('crash endpoint called — watch the log above/below');
} catch {
  console.log('request failed as the process exited (expected)');
}
```

**The policy, stated plainly:**

| Situation                      | Correct action                                       | Why                                          |
| ------------------------------ | ---------------------------------------------------- | -------------------------------------------- |
| Operational error in a request | Respond 4xx/5xx, log at `warn`/`error`, keep serving | It is expected; nothing is broken            |
| Unexpected error in a request  | Respond `500`, log with stack, keep serving          | The request is lost; the process may be fine |
| Uncaught exception             | Log, stop accepting, exit non-zero                   | Process state is unknown                     |
| Unhandled rejection            | Log, stop accepting, exit non-zero                   | Same                                         |
| `SIGTERM`                      | Stop accepting, finish in-flight, exit 0             | Zero-downtime deploys                        |

"Do not crash on uncaught exceptions" is a **common and dangerous** piece of advice. In a long-running server, continuing after an unknown error means serving corrupted data from an unknown state. Restart is cheap; corruption is not.

***

## 7. Logging errors usefully

The difference between a 5-minute fix and a 5-hour one is usually the log line.

```js
// File: error-logging.mjs
function logError(error, context) {
  const entry = {
    level: error.statusCode >= 500 ? 'error' : 'warn',
    timestamp: new Date().toISOString(),
    name: error.name,
    code: error.code,
    message: error.message,
    statusCode: error.statusCode,
    // Correlation: the thread from a user's report to this line.
    requestId: context.requestId,
    userId: context.userId,
    route: context.route,
    method: context.method,
    // The full chain: our context AND the original low-level error.
    cause: error.cause ? { name: error.cause.name, message: error.cause.message, code: error.cause.code } : undefined,
    stack: error.stack,
    // Business context that makes the bug reproducible.
    params: context.params,
  };

  // OK to log the body only if it is redacted — never log passwords or tokens.
  if (context.safeBody) entry.body = context.safeBody;

  process.stderr.write(`${JSON.stringify(entry)}\n`);
}

class NotFoundError extends Error {
  constructor(message) {
    super(message);
    this.name = 'NotFoundError';
    this.code = 'NOT_FOUND';
    this.statusCode = 404;
  }
}

logError(new NotFoundError('User 42 not found'), {
  requestId: 'req_8f3c1d2a',
  userId: 'u_17',
  route: '/api/v1/users/42',
  method: 'GET',
  params: { id: '42' },
});

// A 5xx with a cause chain
const dbError = Object.assign(new Error('connection terminated unexpectedly'), { code: 'ECONNRESET' });
const appError = new Error('Failed to load user profile', { cause: dbError });
appError.statusCode = 503;
appError.code = 'SERVICE_UNAVAILABLE';

logError(appError, { requestId: 'req_9a1b2c3d', route: '/api/v1/profile', method: 'GET' });
```

```
{"level":"warn","timestamp":"2026-09-18T10:15:30.001Z","name":"NotFoundError","code":"NOT_FOUND","message":"User 42 not found","statusCode":404,"requestId":"req_8f3c1d2a","userId":"u_17","route":"/api/v1/users/42","method":"GET","stack":"NotFoundError: User 42 not found\n    at …","params":{"id":"42"}}
{"level":"error","timestamp":"2026-09-18T10:15:30.002Z","name":"Error","code":"SERVICE_UNAVAILABLE","message":"Failed to load user profile","statusCode":503,"requestId":"req_9a1b2c3d","route":"/api/v1/profile","method":"GET","cause":{"name":"Error","message":"connection terminated unexpectedly","code":"ECONNRESET"},"stack":"Error: Failed to load user profile\n    at …"}
```

**Every error log must answer:** what failed, for whom, where, with which correlation id, and what the underlying cause was. Anything less and you are guessing during an incident.

***

## 8. Common mistakes

| Mistake                                          | Consequence                                      | Fix                                          |
| ------------------------------------------------ | ------------------------------------------------ | -------------------------------------------- |
| `try { … } catch {}` (empty catch)               | Silent failures                                  | Log, or handle, or rethrow                   |
| Losing the original error                        | Impossible to diagnose ("failed")                | `{ cause: error }`                           |
| Throwing strings                                 | No stack, no `instanceof`                        | Throw `Error` subclasses                     |
| Catch-all `catch (e) { res.status(500) }`        | Real 4xx become 500s; monitoring is meaningless  | Classify with error types/codes              |
| Leaking `error.message` and `stack` on 5xx       | Information disclosure                           | Generic message + `requestId`                |
| Trusting error messages to branch on             | Breaks on the next library upgrade               | Branch on `code`/`name`/`instanceof`         |
| Retrying non-idempotent operations               | Duplicate charges/inserts                        | Idempotency keys, retry only safe operations |
| Retrying permanent errors                        | Wasted time, extra load on a failing system      | Retry only transient codes                   |
| No `unhandledRejection` policy                   | Random crashes with useless logs, or silent loss | Log fatal, drain, exit non-zero              |
| Swallowing errors in a background job            | Jobs "succeed" while doing nothing               | Record failures; alert on repeated failures  |
| One giant error middleware with `if/else` chains | Unmaintainable classification                    | Error classes + a single translator          |
| Logging the whole request body                   | Passwords and tokens in your logs                | Redact before logging                        |

***

## Exercise 16.1 — Build the error layer

Create a small module that provides: `AppError` with subclasses, a translator for a fake "payment provider" error vocabulary, and a function that turns any thrown value into a safe HTTP response body (with the stack only in development).

<details>

<summary>Solution</summary>

```js
// File: error-layer.mjs
// ---------------------------------------------------------------------------
// Part 1: the error hierarchy
// ---------------------------------------------------------------------------
export class AppError extends Error {
  constructor(message, { statusCode = 500, code = 'INTERNAL_ERROR', details, cause, expected = false } = {}) {
    super(message, { cause });
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.expected = expected;         // "expected" → log at warn, do not page
    Error.captureStackTrace?.(this, new.target);
  }
}

export class ValidationError extends AppError {
  constructor(details, message = 'Request validation failed') {
    super(message, { statusCode: 422, code: 'VALIDATION_ERROR', details, expected: true });
  }
}

export class NotFoundError extends AppError {
  constructor(message = 'Resource not found') {
    super(message, { statusCode: 404, code: 'NOT_FOUND', expected: true });
  }
}

export class ConflictError extends AppError {
  constructor(message, details) {
    super(message, { statusCode: 409, code: 'CONFLICT', details, expected: true });
  }
}

export class UpstreamError extends AppError {
  constructor(provider, providerCode, details) {
    super(`${provider} could not complete the request`, {
      statusCode: 502,
      code: 'UPSTREAM_ERROR',
      details,
      expected: true,
    });
    this.provider = provider;
    this.providerCode = providerCode;
  }
}

// ---------------------------------------------------------------------------
// Part 2: translating a third-party vocabulary into ours
// ---------------------------------------------------------------------------
/**
 * The fake payment provider throws errors shaped like:
 *   { type: 'card_error', code: 'card_declined' | 'expired_card' | 'insufficient_funds',
 *     message: string, param?: string }
 *   { type: 'api_error', code: 'rate_limit' | 'service_unavailable' }
 */
export function translatePaymentError(providerError) {
  const { type, code, message, param } = providerError ?? {};

  // The customer's payment method is the problem → 402, and it is the client's business.
  const cardErrors = {
    card_declined: 'Your card was declined',
    expired_card: 'Your card has expired',
    insufficient_funds: 'Insufficient funds',
    incorrect_cvc: 'The security code is incorrect',
  };
  if (type === 'card_error' && cardErrors[code]) {
    return new AppError(cardErrors[code], {
      statusCode: 402,
      code: `PAYMENT_${code.toUpperCase()}`,
      details: param ? [{ field: param, message: message ?? cardErrors[code] }] : undefined,
      expected: true,
    });
  }

  // Our integration is the problem → 502/503, and it is an incident for us.
  if (code === 'rate_limit') {
    return new AppError('Payment provider rate limit reached, please retry shortly', {
      statusCode: 503,
      code: 'PAYMENT_RATE_LIMITED',
      expected: true,
    });
  }
  if (code === 'service_unavailable' || type === 'api_error') {
    return new UpstreamError('payment-provider', code, [{ message: 'temporary provider failure' }]);
  }

  // Unknown: never leak it to the client, always keep the cause.
  return new AppError('Payment could not be processed', {
    statusCode: 502,
    code: 'PAYMENT_UNKNOWN_ERROR',
    cause: providerError,
  });
}

// ---------------------------------------------------------------------------
// Part 3: turning anything into a safe HTTP payload
// ---------------------------------------------------------------------------
export function toHttpError(error, { isProduction = true, requestId } = {}) {
  // Normalise non-Error throws.
  const normalised = error instanceof Error ? error : new Error(String(error));

  const isOperational = normalised instanceof AppError && normalised.expected;
  const statusCode =
    normalised instanceof AppError && normalised.statusCode >= 400 ? normalised.statusCode : 500;

  // A 5xx always gets a generic message in production — never the internal one.
  const message =
    statusCode >= 500 && isProduction ? 'Something went wrong' : normalised.message;

  return {
    status: statusCode,
    body: {
      error: {
        code: normalised.code ?? 'INTERNAL_ERROR',
        message,
        details: normalised.details,
        requestId,
        // Stack traces and causes are for local debugging only.
        ...(isProduction
          ? {}
          : {
              debug: {
                name: normalised.name,
                stack: normalised.stack?.split('\n').slice(0, 5),
                cause: normalised.cause?.message,
              },
            }),
      },
    },
    // What the logger should do with it.
    logLevel: statusCode >= 500 ? 'error' : 'warn',
    isExpected: isOperational,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
const scenarios = [
  ['validation', new ValidationError([{ field: 'email', message: 'invalid' }])],
  ['not found', new NotFoundError('Order 999 not found')],
  ['conflict', new ConflictError('Email already registered')],
  ['card declined', translatePaymentError({ type: 'card_error', code: 'card_declined', param: 'card' })],
  ['card expired', translatePaymentError({ type: 'card_error', code: 'expired_card' })],
  ['provider down', translatePaymentError({ type: 'api_error', code: 'service_unavailable' })],
  ['unknown payment error', translatePaymentError({ type: 'weird_error', code: 'mystery' })],
  ['programmer error', new TypeError("Cannot read properties of undefined (reading 'id')")],
  ['non-error throw', 'just a string'],
];

console.log('=== PRODUCTION (stacks hidden) ===');
for (const [label, error] of scenarios) {
  const { status, body, logLevel, isExpected } = toHttpError(error, {
    isProduction: true,
    requestId: 'req_demo',
  });
  console.log(
    `${label.padEnd(22)} ${String(status).padEnd(4)} log=${logLevel.padEnd(5)} expected=${String(isExpected).padEnd(5)} → ${body.error.code}: ${body.error.message}`
  );
}

console.log('\n=== DEVELOPMENT (one example, with debug info) ===');
const devResult = toHttpError(scenarios[7][1], { isProduction: false, requestId: 'req_dev' });
console.log(JSON.stringify(devResult.body, null, 2));
```

Expected output:

```
=== PRODUCTION (stacks hidden) ===
validation             422  log=warn  expected=true  → VALIDATION_ERROR: Request validation failed
not found              404  log=warn  expected=true  → NOT_FOUND: Order 999 not found
conflict               409  log=warn  expected=true  → CONFLICT: Email already registered
card declined          402  log=warn  expected=true  → PAYMENT_CARD_DECLINED: Your card was declined
card expired           402  log=warn  expected=true  → PAYMENT_EXPIRED_CARD: Your card has expired
provider down          502  log=error expected=true  → UPSTREAM_ERROR: payment-provider could not complete the request
unknown payment error  502  log=error expected=false → PAYMENT_UNKNOWN_ERROR: Payment could not be processed
programmer error       500  log=error expected=false → INTERNAL_ERROR: Something went wrong
non-error throw        500  log=error expected=false → INTERNAL_ERROR: Something went wrong

=== DEVELOPMENT (one example, with debug info) ===
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Cannot read properties of undefined (reading 'id')",
    "requestId": "req_dev",
    "debug": {
      "name": "TypeError",
      "stack": [ … ]
    }
  }
}
```

**Design notes worth reusing**

| Decision                                   | Why                                                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `expected` flag separate from `statusCode` | A 502 is expected (we know the provider fails) while a `TypeError` is not; logging and alerting differ |
| Translation happens at the boundary        | The rest of the app speaks one vocabulary                                                              |
| Unknown errors are never leaked            | Fail closed: generic message, full detail in logs only                                                 |
| Non-Error throws are normalised            | Third-party code does throw strings                                                                    |
| `requestId` is always in the payload       | The only practical way to support a user                                                               |
| Debug info only outside production         | Developer experience locally, safety deployed                                                          |
| `logLevel` returned with the response      | One decision point for logging, not scattered `console.error`s                                         |

**Follow-up challenges**

* Add a `details` filter that strips any field whose name looks like a secret.
* Map database errors (`23505`, `ER_DUP_ENTRY`, `11000`) into this same vocabulary.
* Write the logger that consumes `logLevel` and emits structured JSON with the cause chain.
* Add an `AggregateError` case (`Promise.any` failures) that reports all inner causes.

</details>

## Exercise 16.2 — Find the eight problems

```js
// File: bad-handler.js
app.get('/users/:id/orders/:orderId', async (req, res) => {
  try {
    const order = await db.findOrder(req.params.orderId);
    console.log('order found:', order);
    res.json(order);
  } catch (e) {
    console.log('error', e);
    res.status(500).json({ error: e.message, stack: e.stack });
  }
});
```

<details>

<summary>Solution</summary>

1. **Everything becomes a `500`.** A missing order, a malformed id, a permission failure — all reported as server errors, which breaks monitoring (you cannot distinguish "the DB is down" from "the user typed a wrong id") and lies to clients.
2. **The full stack trace is sent to the client** (`e.stack`). That leaks file paths, dependency versions and sometimes connection strings. It is an information-disclosure vulnerability.
3. **`e.message` is leaked** for 5xx errors. Internal messages ("relation orders does not exist") should never reach a client.
4. **Errors are logged with `console.log`**, which means: no level (so it cannot be filtered or alerted on), no timestamp, no request id, no user, and it goes to stdout rather than stderr — so a log aggregator may treat an incident as normal traffic.
5. **Nothing validates `req.params.orderId`.** A malformed id reaches the database and produces a driver-level `CastError`/`invalid input syntax` error — which becomes a `500`.
6. **The order is returned without checking ownership.** Any authenticated user can read any order by guessing ids — a horizontal privilege escalation (IDOR). Authorisation is missing entirely.
7. **The whole `order` document is returned**, including any internal fields (soft-delete flags, internal notes, `userId` of others, cost prices). It should pass through a DTO.
8. **`res.json(order)` when the order is `null`** sends a `200` with an empty body (`null`), not a `404`. Clients see "success" with no data.

**Additional issues:** no timeout on the database call; no `.catch`-equivalent for cancellation if the client disconnects; the `try/catch` would also swallow a bug in `res.json` (a serialisation error) and try to send a second response, producing `ERR_HTTP_HEADERS_SENT`.

**Rewritten**

```js
// File: good-handler.js
import { z } from 'zod';

const paramsSchema = z.object({
  id: z.string().min(1),
  orderId: z.string().uuid('orderId must be a UUID'),
});

export async function getOrder(req, res, next) {
  // 1. Validate at the boundary — malformed input is a 422/400, not a crash.
  const parsed = paramsSchema.safeParse(req.params);
  if (!parsed.success) {
    return next(
      new ValidationError(
        parsed.error.issues.map((issue) => ({ field: issue.path.join('.'), message: issue.message }))
      )
    );
  }

  const { orderId } = parsed.data;
  const abortController = new AbortController();
  req.on('close', () => abortController.abort());

  try {
    // 2. Time-box every external call.
    const order = await withTimeout(
      () => orderService.findById(orderId, { signal: abortController.signal }),
      3_000,
      'order lookup'
    );

    // 3. Missing resource is a real 404.
    if (!order) return next(new NotFoundError(`Order ${orderId} not found`));

    // 4. Authorisation: ownership is checked per resource, not per route.
    if (order.userId !== req.user.id && req.user.role !== 'admin') {
      return next(new ForbiddenError());
    }

    // 5. Return a DTO: only the fields the client should see.
    return res.json({ data: toOrderDto(order) });
  } catch (error) {
    // 6. Forward to the central error middleware — it classifies, logs and redacts.
    return next(error);
  }
}

function toOrderDto(order) {
  return {
    id: order.id,
    status: order.status,
    total: order.totalCents / 100,
    currency: order.currency,
    createdAt: order.createdAt.toISOString(),
    items: order.items.map((item) => ({ sku: item.sku, quantity: item.quantity })),
  };
}
```

**The principles**

| Principle                             | Where it appears                                     |
| ------------------------------------- | ---------------------------------------------------- |
| Validate before touching the database | `paramsSchema.safeParse`                             |
| Distinguish 4xx from 5xx              | `ValidationError`, `NotFoundError`, `ForbiddenError` |
| Check ownership per resource          | `order.userId !== req.user.id`                       |
| Never leak internals                  | `toOrderDto` + central error middleware              |
| Log structurally, once, with context  | The error middleware, not the handler                |
| Bound external calls                  | `withTimeout`                                        |
| Forward async errors to one place     | `next(error)`                                        |
| Serialise deliberately                | A DTO, not the raw document                          |

</details>

***

## What's next

You can handle failure. Next: finding out _why_ code fails — debugging techniques, logging, and the tooling (`--inspect`, breakpoints, profiling) that turns a vague bug report into a fixed line of code.

→ [17 — Debugging and Tooling](17-debugging.md)
