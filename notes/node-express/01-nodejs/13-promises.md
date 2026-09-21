# 13 — Promises, async and await

> **Where this fits:** [12](12-async-programming.md) showed _why_ asynchronous code exists and how callbacks became promises. This chapter is the precise mechanics: what a promise guarantees, how `async`/`await` works underneath, the mistakes that cause unhandled rejections, and the patterns you will use in every Express handler and service.

***

## 1. What is a promise?

A **promise** is an object representing the eventual result of an asynchronous operation. It has exactly three states, and moves in exactly one direction:

```
                 ┌─────────────┐
                 │   pending   │   the operation is in flight
                 └──────┬──────┘
            fulfil      │      reject
        (with a value)  │   (with a reason)
                 ┌──────▼──────┐
                 │  fulfilled  │   success — has a value
                 └─────────────┘
                        or
                 ┌─────────────┐
                 │  rejected   │   failure — has a reason (usually an Error)
                 └─────────────┘

Settled = fulfilled or rejected. A settled promise never changes again.
```

Three guarantees that make promises usable:

1. **Settled once, forever.** The first `resolve`/`reject` wins; later calls are ignored.
2. **Callbacks are asynchronous.** `.then()` callbacks never run before the current synchronous code finishes, even if the promise is already settled.
3. **Handlers are queued in order.** Multiple `.then()` calls run in registration order.

```js
// File: promise-basics.mjs
// Guarantee 1: only the first settlement counts.
const once = new Promise((resolve, reject) => {
  resolve('first');
  reject(new Error('too late — ignored'));
  resolve('also ignored');
});

console.log(await once);                    // first

// Guarantee 2: handlers always run asynchronously, even for a resolved promise.
const alreadyResolved = Promise.resolve('value');
console.log('A: synchronous code before .then');
alreadyResolved.then((value) => console.log(`C: then handler with ${value}`));
console.log('B: synchronous code after .then');
// Output order: A, B, C — never A, C, B.

// Guarantee 3: registration order is preserved.
Promise.resolve(1)
  .then((v) => console.log('handler 1:', v))
  .then((v) => console.log('handler 3:', v));
```

### Creating promises

```js
// File: creating-promises.mjs
import { setTimeout as sleep } from 'node:timers/promises';

// 1. The constructor (the "executor" runs synchronously, immediately).
function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

// 2. Promise.resolve / Promise.reject — for already-known values.
const fast = Promise.resolve({ ok: true });
const failed = Promise.reject(new Error('immediate failure'));

// 3. Most commonly: you do not create promises by hand.
//    Async APIs already return them.
import { readFile } from 'node:fs/promises';
const filePromise = readFile('./package.json', 'utf8');   // already a promise

// 4. The executor runs SYNCHRONOUSLY — a common surprise.
console.log('before');
new Promise((resolve) => {
  console.log('inside the executor (synchronous!)');
  resolve();
});
console.log('after');
// before → inside the executor → after

// 5. Promisifying a callback API.
import { promisify } from 'node:util';
import { exec } from 'node:child_process';
const execAsync = promisify(exec);

const { stdout } = await execAsync('node --version');
console.log('node version via exec:', stdout.trim());

await delay(10);
console.log('fast resolved:', await fast);
await failed.catch((error) => console.log('rejected as expected:', error.message));
await filePromise.then((raw) => console.log('package name:', JSON.parse(raw).name));
await sleep(1);
```

> **Note:** `node:util` exports the promise version of many callback APIs via `util.promisify`, but modern code should use the `*Sync`-free promise APIs directly: `node:fs/promises`, `node:timers/promises`, `node:stream/promises`, `node:dns/promises`.

***

## 2. `then`, `catch`, `finally` and chaining

```js
// File: chaining.mjs
import { readFile } from 'node:fs/promises';

// A chain: each .then receives the previous return value.
await readFile('./package.json', 'utf8')
  .then((raw) => JSON.parse(raw))                    // returns an object → next then gets it
  .then((pkg) => pkg.name)                           // returns a string
  .then((name) => console.log('project name:', name))
  .catch((error) => console.error('chain failed:', error.message))
  .finally(() => console.log('chain finished (success or failure)'));
```

### The rule that matters: what you return becomes the next value

```js
// File: return-values.mjs
import { setTimeout as sleep } from 'node:timers/promises';

// ✅ Returning a promise WAITS for it.
await Promise.resolve()
  .then(() => sleep(50).then(() => 'A'))
  .then((value) => console.log('received:', value));      // received: A

// ❌ NOT returning it: the chain continues immediately, with undefined.
await Promise.resolve()
  .then(() => {
    sleep(50).then(() => 'B');                            // fire-and-forget, and unawaitable
  })
  .then((value) => console.log('received:', value));      // received: undefined

// The equivalent async/await bug — forgetting `await`:
async function missingAwait() {
  sleep(50).then(() => console.log('this may fire after the function returns'));
  return 'returned immediately';
}
console.log(await missingAwait());                        // returned immediately
```

**Rule: inside a `.then()` callback, return the promise. Inside an `async` function, `await` it.** Forgetting turns sequential logic into a race.

### `catch` and error propagation

```js
// File: error-propagation.mjs
import { readFile } from 'node:fs/promises';

// A rejection skips every subsequent .then until a .catch is found.
await readFile('./definitely-missing.txt', 'utf8')
  .then((raw) => {
    console.log('never runs');
    return raw;
  })
  .then(() => console.log('never runs either'))
  .catch((error) => console.log('caught:', error.code));   // caught: ENOENT

// Throwing inside a .then behaves exactly like a rejection.
await Promise.resolve('start')
  .then(() => {
    throw new Error('thrown in a then');
  })
  .catch((error) => console.log('caught from then:', error.message));

// A .catch can RECOVER by returning a value — the chain continues as fulfilled.
const recovered = await Promise.reject(new Error('boom'))
  .catch((error) => `recovered from ${error.message}`);
console.log('recovered value:', recovered);                // recovered from boom

// The subtle async/await equivalent: `return await` vs `return` inside try/catch.
import { setTimeout as sleep } from 'node:timers/promises';

async function noAwaitInsideTry() {
  try {
    return sleep(10).then(() => {
      throw new Error('escapes the try block');
    });
  } catch {
    return 'caught';                                       // never reached
  }
}

async function awaitInsideTry() {
  try {
    return await sleep(10).then(() => {
      throw new Error('caught correctly');
    });
  } catch (error) {
    return `caught: ${error.message}`;
  }
}

console.log(await noAwaitInsideTry().catch((error) => `escaped: ${error.message}`));  // escaped
console.log(await awaitInsideTry());                                                  // caught: caught correctly
```

`finally` is for cleanup and does not change the value:

```js
// File: finally-usage.mjs
import { setTimeout as sleep } from 'node:timers/promises';

let connectionOpen = false;

async function query({ fail = false } = {}) {
  connectionOpen = true;
  try {
    await sleep(10);
    if (fail) throw new Error('query failed');
    return 'rows';
  } finally {
    // Runs on success, on failure, and on early return — the correct place for cleanup.
    connectionOpen = false;
    console.log('connection released');
  }
}

console.log(await query());
try {
  await query({ fail: true });
} catch (error) {
  console.log('handled:', error.message);
}
console.log('connection open?', connectionOpen);

// ⚠️ `return` inside finally overrides the value and swallows errors — do not do this.
async function badFinally() {
  try {
    throw new Error('important');
  } finally {
    return 'swallowed';                     // the error disappears
  }
}
console.log(await badFinally());             // swallowed
```

***

## 3. `async` functions and `await`

```js
// File: async-function.mjs
import { setTimeout as sleep } from 'node:timers/promises';

// An async function ALWAYS returns a promise — even if it returns a plain value.
async function returnValue() {
  return 42;                                // equivalent to Promise.resolve(42)
}
async function throwError() {
  throw new Error('boom');                  // equivalent to Promise.reject(new Error('boom'))
}
async function returnPromise() {
  return Promise.resolve('wrapped');        // the promise is adopted (not double-wrapped)
}

console.log(returnValue() instanceof Promise);      // true
console.log(await returnValue());                   // 42
console.log(await returnPromise());                 // wrapped
await throwError().catch((error) => console.log('rejected:', error.message));

// `await` pauses THIS function only — the thread keeps serving other work.
async function demonstrateYield() {
  console.log('1 (synchronous start)');
  await sleep(0);                                    // yields to the event loop
  console.log('3 (after the await)');
}
const pending = demonstrateYield();
console.log('2 (outside — runs while demonstrateYield is paused)');
await pending;
```

```
1 (synchronous start)
2 (outside — runs while demonstrateYield is paused)
3 (after the await)
```

### What `await` really does (the mental model)

```
async function f() {
  const a = await g();     ← 1. call g(), get a promise
  console.log(a);          ← 3. resume here, later
}
                           ← 2. f() returns a pending promise to its caller;
                                the event loop runs other work;
                                when g()'s promise settles, `console.log(a)` is
                                scheduled as a MICROTASK and runs before timers/I/O.
```

Two consequences worth remembering:

* **`await` does not block the thread.** It suspends one function and returns control to the event loop.
* **Code after `await` runs on the microtask queue**, which has priority over timers and I/O callbacks ([14 — The Event Loop](14-event-loop.md)).

### Sequential vs concurrent, one more time — because it is the main performance lever

```js
// File: sequential-vs-concurrent-await.mjs
import { setTimeout as sleep } from 'node:timers/promises';
import { performance } from 'node:perf_hooks';

const fetchUser = (id) => sleep(50).then(() => ({ id, name: `User ${id}` }));

// ❌ Sequential: 3 × 50ms = 150ms
async function getUserNamesSequential(ids) {
  const names = [];
  for (const id of ids) {
    const user = await fetchUser(id);       // waits before starting the next
    names.push(user.name);
  }
  return names;
}

// ✅ Concurrent: ~50ms
async function getUserNamesConcurrent(ids) {
  const users = await Promise.all(ids.map((id) => fetchUser(id)));
  return users.map((user) => user.name);
}

let start = performance.now();
await getUserNamesSequential([1, 2, 3]);
console.log(`sequential: ${(performance.now() - start).toFixed(0)}ms`);

start = performance.now();
await getUserNamesConcurrent([1, 2, 3]);
console.log(`concurrent: ${(performance.now() - start).toFixed(0)}ms`);
```

**Where `await` is legitimate:** these are the top three causes of slow endpoints, and none of them are algorithmic — they are missing parallelism.

| Anti-pattern                               | Fix                                                                                   |
| ------------------------------------------ | ------------------------------------------------------------------------------------- |
| Awaiting independent queries in a loop     | `Promise.all`                                                                         |
| Awaiting a count and a page separately     | `Promise.all([count, find])`                                                          |
| Awaiting per-item enrichment one at a time | `Promise.all` with bounded concurrency, or a single batched query (`$in`, `IN (...)`) |

**Where sequential is&#x20;**_**required**_**:** when step 2 needs step 1's output, when order matters, when you must respect a rate limit, or when the operations share a resource that cannot handle concurrency (a single transaction, a file handle being appended to).

***

## 4. Rejections, unhandled rejections, and why they crash your process

```js
// File: unhandled-rejection.mjs
// A rejected promise with no handler is an UNHANDLED REJECTION.
// Since Node 15, the default behaviour is to terminate the process with a non-zero exit code.

Promise.reject(new Error('nobody is listening'));
// → UnhandledPromiseRejection … this would crash the process at the end of the tick.

// Handle it (even if only to log):
await sleep(1).then(() => {}); // keep this example harmless
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection:', reason);
});
```

### Why the process crashes (and why that is often correct)

A rejected promise means an operation failed and **nobody knows what state the application is in**. A payment may have been charged with no record, a write may be half-applied. Continuing to serve requests from an unknown state is how you get corrupted data.

The production policy for a web server:

```js
// File: rejection-policy.mjs
// 1. Log with full context (with a structured logger in real code).
process.on('unhandledRejection', (reason) => {
  console.error(
    JSON.stringify({
      level: 'fatal',
      message: 'unhandled promise rejection — shutting down',
      reason: reason instanceof Error ? reason.message : String(reason),
      stack: reason instanceof Error ? reason.stack : undefined,
    })
  );

  // 2. Stop accepting new work, let in-flight requests finish, then exit.
  //    The supervisor (systemd, Docker, Kubernetes, PM2) restarts a clean process.
  process.exitCode = 1;
  setTimeout(() => process.exit(1), 5_000).unref();
});

// 3. The same for synchronous escapes.
process.on('uncaughtException', (error) => {
  console.error(JSON.stringify({ level: 'fatal', message: 'uncaught exception', error: error.message }));
  process.exitCode = 1;
  setTimeout(() => process.exit(1), 5_000).unref();
});
```

**Do not "handle" these by swallowing them.** The reason Node crashes by default is that catching an unknown error and carrying on is how a bug becomes a data corruption incident.

### The common sources of accidental unhandled rejections

| Source                              | Example                                    | Fix                                                   |
| ----------------------------------- | ------------------------------------------ | ----------------------------------------------------- |
| Fire-and-forget async call          | `sendEmail(user)` without `await`/`.catch` | `void sendEmail(user).catch(logError)` — deliberate   |
| `forEach` with async callback       | `items.forEach(async (i) => …)`            | `for...of` or `Promise.all(map)`                      |
| Missing `await` inside `try`        | `try { doAsync() } catch {}`               | `await doAsync()`                                     |
| Async event listener                | `emitter.on('x', async () => { throw … })` | `captureRejections: true`, or wrap in try/catch       |
| Async middleware without forwarding | Express 4 with `async` handlers            | Express 5 forwards automatically; or wrap             |
| A rejection in a job queue worker   | Not awaited                                | Always await the worker's promise and record failures |

***

## 5. Patterns you will use in real backends

### Pattern 1: retry with exponential backoff (and jitter)

```js
// File: retry.mjs
import { setTimeout as sleep } from 'node:timers/promises';

export async function retry(
  operation,
  { attempts = 3, baseDelayMs = 100, maxDelayMs = 5_000, signal } = {}
) {
  let lastError;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    signal?.throwIfAborted();
    try {
      return await operation({ attempt });
    } catch (error) {
      lastError = error;

      // Do not retry errors that will never succeed.
      if (error.code === 'VALIDATION_ERROR' || error.statusCode === 400 || error.statusCode === 404) {
        throw error;
      }

      if (attempt === attempts) break;

      // Exponential backoff + full jitter: avoids a synchronised retry stampede.
      const exponential = Math.min(baseDelayMs * 2 ** (attempt - 1), maxDelayMs);
      const delay = Math.random() * exponential;
      console.log(`  attempt ${attempt} failed (${error.message}); retrying in ${delay.toFixed(0)}ms`);
      await sleep(delay, undefined, { signal });
    }
  }

  throw lastError;
}

let calls = 0;
const flakyApi = async () => {
  calls += 1;
  if (calls < 3) {
    const error = new Error('upstream unavailable');
    error.statusCode = 503;
    throw error;
  }
  return { ok: true, attempts: calls };
};

console.log('result:', await retry(flakyApi, { attempts: 5, baseDelayMs: 20 }));
```

### Pattern 2: a timeout that does not leak the underlying operation

```js
// File: timeout-pattern.mjs
import { setTimeout as sleep } from 'node:timers/promises';

/**
 * Race an operation against a timeout, and cancel the operation when the
 * timeout wins (AbortSignal.timeout does not cancel your own work by itself).
 */
export async function withTimeout(operation, ms, label = 'operation') {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);

  try {
    return await operation(controller.signal);
  } catch (error) {
    if (error.name === 'AbortError') {
      const timeoutError = new Error(`${label} timed out after ${ms}ms`);
      timeoutError.code = 'ETIMEDOUT';
      timeoutError.statusCode = 504;
      throw timeoutError;
    }
    throw error;
  } finally {
    clearTimeout(timer);              // ALWAYS clear, or the timer keeps the loop alive
  }
}

// Usage
try {
  // Note how the operation cooperates with the signal — that is what makes it cancellable.
  await withTimeout(
    async (signal) => {
      await sleep(500, undefined, { signal });
      return 'never seen';
    },
    50,
    'inventory service'
  );
} catch (error) {
  console.log(error.code, '-', error.message);   // ETIMEDOUT - inventory service timed out after 50ms
}
```

### Pattern 3: a simple concurrency limiter

```js
// File: pool.mjs
/** Promise-based semaphore: at most `size` tasks run at once. */
export function createPool(size) {
  let active = 0;
  const waiting = [];

  const next = () => {
    if (active >= size || waiting.length === 0) return;
    active += 1;
    const { task, resolve, reject } = waiting.shift();
    task()
      .then(resolve, reject)
      .finally(() => {
        active -= 1;
        next();
      });
  };

  return (task) =>
    new Promise((resolve, reject) => {
      waiting.push({ task, resolve, reject });
      next();
    });
}

import { setTimeout as sleep } from 'node:timers/promises';
import { performance } from 'node:perf_hooks';

const run = createPool(3);            // e.g. match your DB pool size
const start = performance.now();

await Promise.all(
  Array.from({ length: 9 }, (_, i) =>
    run(async () => {
      await sleep(50);
      return `task ${i + 1}`;
    })
  )
);

console.log(`9 tasks at 50ms each with a pool of 3 took ${(performance.now() - start).toFixed(0)}ms (~150ms)`);
```

### Pattern 4: idempotent "do once" for expensive initialisation

```js
// File: lazy-init.mjs
import { setTimeout as sleep } from 'node:timers/promises';

/** Cache the promise itself, not the resolved value, so concurrent callers share one attempt. */
export function createLazy(initialise) {
  let promise = null;
  return () => {
    promise ??= initialise().catch((error) => {
      promise = null;               // allow a retry after a failure
      throw error;
    });
    return promise;
  };
}

let connectCalls = 0;
const getConnection = createLazy(async () => {
  connectCalls += 1;
  console.log('connecting to the database…');
  await sleep(50);
  return { id: 'db-connection-1' };
});

// Ten concurrent callers → exactly ONE connection attempt.
const connections = await Promise.all(Array.from({ length: 10 }, () => getConnection()));
console.log('connect() called', connectCalls, 'time(s)');
console.log('all callers got the same connection:', connections.every((c) => c === connections[0]));
```

**Why this pattern matters:** it is the difference between one database connection and ten at startup, and it removes a whole class of race conditions in initialisation code. (This is also, by the way, how the Node module cache behaves — see [04 §2](04-modules.md).)

***

## 6. Promises vs callbacks vs events — the summary table

|                      | Callback                   | Promise                     | async/await   | EventEmitter                            |
| -------------------- | -------------------------- | --------------------------- | ------------- | --------------------------------------- |
| Outcomes             | One                        | One                         | One           | Many                                    |
| Error handling       | Error-first arg            | `.catch`                    | `try/catch`   | `'error'` event                         |
| Composition          | Manual nesting             | `.then` chains, combinators | Linear code   | Listeners                               |
| Cancellation         | Convention-specific        | `AbortSignal`               | `AbortSignal` | `removeListener`                        |
| Readability at depth | Poor                       | Fair                        | **Excellent** | N/A                                     |
| Typical modern use   | Low-level APIs, `execFile` | Combinators (`all`, `race`) | **Default**   | Servers, sockets, streams, custom buses |

The practical rule: **async/await for control flow, promises for combinators and API boundaries, events for things that happen repeatedly.**

***

## 7. Common mistakes

| Mistake                                                          | Symptom                                          | Fix                                                |
| ---------------------------------------------------------------- | ------------------------------------------------ | -------------------------------------------------- |
| Using `new Promise` for code that already returns promises       | Verbose, and errors get swallowed                | Just `return thePromise`                           |
| Missing `return` inside `.then`                                  | Chain continues with `undefined`                 | Return the promise/value                           |
| Missing `await` before an async call                             | Race conditions, silent failures                 | `await`, or `void … .catch()` deliberately         |
| `try { doAsync(); } catch {}` without `await`                    | `catch` never runs                               | `await doAsync()`                                  |
| `.catch` only at the end, but an earlier error must not continue | Wrong control flow                               | Catch where you can handle it                      |
| Swallowing errors: `.catch(() => {})`                            | Invisible failures                               | Log with context; rethrow unknown errors           |
| No top-level `unhandledRejection` handler                        | Crashes with a poor log, or silent loss          | Log fatal, exit cleanly, restart                   |
| Sequential `await` in a loop                                     | Latency adds up (the #1 cause of slow endpoints) | `Promise.all` / bounded concurrency                |
| Unbounded `Promise.all` on huge arrays                           | Pool exhaustion, memory spike                    | Concurrency limiter                                |
| `return` inside `finally`                                        | Swallows errors and values                       | Do not return from `finally`                       |
| `Promise.all` where partial failure is expected                  | One failure loses all results                    | `Promise.allSettled`                               |
| Forgetting `clearTimeout` in a timeout wrapper                   | Timer keeps the process alive, leaks             | `finally { clearTimeout(timer) }`                  |
| Not returning the promise from an async Express handler          | Errors are not forwarded                         | `return`/`await` inside handlers (Express 5 helps) |

***

## Exercise 13.1 — Fix the service layer

This service loads a user's dashboard. Find all six bugs and rewrite it.

```js
// File: dashboard-before.js
import { getUser } from './userService.js';
import { getOrders } from './orderService.js';
import { getRecommendations } from './recommendationService.js';

export async function getDashboard(userId) {
  const user = getUser(userId);                       // bug 1
  const orders = getOrders(userId);
  const recommendations = getRecommendations(userId);

  const enrichedOrders = [];
  orders.forEach(async (order) => {                   // bug 2
    const items = await getOrderItems(order.id);
    enrichedOrders.push({ ...order, items });
  });

  const stats = {
    totalSpent: orders.reduce((sum, order) => sum + order.total, 0),
    orderCount: orders.length,
  };

  if (process.env.FEATURE_RECOMMENDATIONS) {          // bug 3
    recommendations.then((r) => console.log(r));
  }

  return { user, orders: enrichedOrders, stats, recommendations: [] };  // bug 4, 5
}

// called as:
getDashboard(req.params.id)
  .then((data) => res.json(data));                    // bug 6
```

<details>

<summary>Solution</summary>

**The six bugs**

1. **Missing `await` on `getUser`** — `user` is a pending promise, serialised into JSON as `{}`.
2. **`forEach` with an async callback** — nothing is awaited; `enrichedOrders` is empty when the function returns. (It also has no error handling and no concurrency control.)
3. **Unawaited promise inside an `if`** — a floating promise with no `.catch`; if it rejects, you get an unhandled rejection that can crash the process.
4. **`orders` may be a promise or an array** depending on bug 1/2, so `orders.reduce` would throw (`TypeError: orders.reduce is not a function`) the moment `getOrders` returns a promise.
5. **`recommendations: []` hardcoded** — the value that was computed is thrown away. (And the caller has no way to know the feature flag exists.)
6. **No error handling at the call site** — no `.catch`, so a rejection produces an unhandled rejection instead of a `500` response. Also the handler is `async`-shaped but not wrapped, which in Express 4 (not 5) means a rejected promise is never forwarded to the error middleware.

**Bonus problems:** no timeout on any dependency; no partial-failure handling (one slow recommendation service takes the whole dashboard down); no caching for an expensive aggregate; and `stats.totalSpent` assumes `order.total` is always a number.

**Rewritten**

```js
// File: dashboard-after.mjs
import { getUser } from './userService.js';
import { getOrders } from './orderService.js';
import { getOrderItems } from './orderItemService.js';
import { getRecommendations } from './recommendationService.js';

const CONCURRENCY = 5;

async function mapWithLimit(items, worker, limit = CONCURRENCY) {
  const results = new Array(items.length);
  let next = 0;
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const index = next;
      next += 1;
      results[index] = await worker(items[index]);
    }
  });
  await Promise.all(runners);
  return results;
}

export async function getDashboard(userId, { signal } = {}) {
  // 1. Independent work runs CONCURRENTLY, each with its own error boundary and timeout.
  const [userResult, ordersResult, recommendationsResult] = await Promise.allSettled([
    getUser(userId, { signal }),
    getOrders(userId, { signal }),
    getRecommendations(userId, { signal }),
  ]);

  // 2. The user is REQUIRED — without it there is no dashboard at all.
  if (userResult.status === 'rejected') throw userResult.reason;

  // 3. Orders are important but the dashboard can degrade.
  const orders = ordersResult.status === 'fulfilled' ? ordersResult.value : [];
  const degraded = {
    orders: ordersResult.status === 'rejected',
    recommendations: recommendationsResult.status === 'rejected',
  };

  // 4. Enrich with BOUNDED concurrency, not unbounded Promise.all.
  const enrichedOrders = await mapWithLimit(orders, async (order) => {
    const items = await getOrderItems(order.id, { signal });
    return { ...order, items };
  });

  // 5. Defensive arithmetic: a bad row must not poison the whole response.
  const totalSpent = enrichedOrders.reduce((sum, order) => {
    const total = Number.isFinite(Number(order.total)) ? Number(order.total) : 0;
    return sum + total;
  }, 0);

  return {
    user: {
      id: String(userResult.value.id),
      name: userResult.value.name,
      email: userResult.value.email,
    },
    orders: enrichedOrders,
    stats: { totalSpent, orderCount: enrichedOrders.length },
    recommendations:
      recommendationsResult.status === 'fulfilled' ? recommendationsResult.value : [],
    degraded,                                   // 6. Tell the client what is missing
  };
}
```

```js
// File: route-usage.mjs — the controller, with proper error forwarding
import { AbortSignal } from 'node:abort' /* not needed; global */;

router.get('/dashboard', async (req, res, next) => {
  const controller = new AbortController();
  req.on('close', () => controller.abort());          // stop work if the client leaves

  try {
    const dashboard = await getDashboard(req.user.id, { signal: controller.signal });
    res.json(dashboard);
  } catch (error) {
    if (error.name === 'AbortError') return res.destroy();
    return next(error);                                // → central error middleware
  }
});
```

**The principles this exercise encodes**

| Principle                                                           | Where                                                                    |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Every `await`/`Promise.all` must be awaited by _someone_            | Bugs 1, 2, 3                                                             |
| Use `allSettled` when partial failure is acceptable                 | Recommendations may fail; the dashboard still works                      |
| Fail loudly for required data, degrade gracefully for optional data | `userResult` vs `ordersResult`                                           |
| Tell the client about degradation                                   | The `degraded` flags                                                     |
| Bound concurrency                                                   | `mapWithLimit` — a user with 500 orders would otherwise open 500 queries |
| Propagate cancellation                                              | `AbortSignal`, so abandoned requests stop doing work                     |
| Forward errors to one place                                         | `next(error)`                                                            |
| Never trust arithmetic on external data                             | Defensive `Number.isFinite`                                              |

</details>

## Exercise 13.2 — Predict the output

Write down what this prints, then run it.

```js
// File: predict.mjs
import { setTimeout as sleep } from 'node:timers/promises';

console.log('1');

Promise.resolve().then(() => console.log('2'));

setTimeout(() => console.log('3'), 0);

(async () => {
  console.log('4');
  await null;
  console.log('5');
})();

queueMicrotask(() => console.log('6'));

console.log('7');

await sleep(10);
```

<details>

<summary>Solution</summary>

```
1
4
7
2
5
6
3
```

**Why, step by step:**

1. `1` — synchronous.
2. `Promise.resolve().then(...)` **schedules** a microtask; it does not run yet.
3. `setTimeout(..., 0)` schedules a **timer** — the timers phase comes after microtasks.
4. The async IIFE starts executing **synchronously** up to the first `await`, so `4` prints now. (`await null` is legal and equals one microtask tick — the same as `await Promise.resolve()`.)
5. `queueMicrotask(...)` schedules a microtask (`6`).
6. `7` — synchronous.
7.  Synchronous execution ends. The event loop drains the **microtask queue** in order:

    * `2` (the first `.then`)
    * `5` (the continuation of the async IIFE, queued when it awaited)
    * `6` (the explicit `queueMicrotask`)

    Microtasks added _while_ draining microtasks are also processed before moving on — that is why the order here is "all microtasks, then anything else".
8. Then the **timers phase**: `3`.
9. Finally the top-level `await sleep(10)` resolves and the module finishes.

**The rules to take away**

* Synchronous code always finishes first.
* Microtasks (promise callbacks, `queueMicrotask`, `process.nextTick`, `await` continuations) run before timers and I/O.
* `process.nextTick` callbacks run before promise microtasks — a detail covered in [14 — The Event Loop](14-event-loop.md).
* An `async` function's body runs synchronously until the first `await`.

</details>

***

## What's next

You now know how to _use_ the machinery. Next: how it actually works — the event loop phases, microtask queues, the libuv thread pool, and why `setTimeout(fn, 0)` does not mean "run now".

→ [14 — The Event Loop](14-event-loop.md)
