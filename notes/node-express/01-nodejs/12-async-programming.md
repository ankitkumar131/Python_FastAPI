# 12 — Asynchronous Programming

> **Where this fits:** Everything in Node is asynchronous: file reads, database queries, HTTP calls.
> This chapter covers *why* asynchrony exists, callbacks and their problems, and the patterns that
> make async code correct. [13 — Promises](13-promises.md) then covers the modern syntax in depth,
> and [14 — The Event Loop](14-event-loop.md) explains the machinery underneath.

---

## 1. The problem: slow operations and one thread

Imagine a single-threaded server that handles requests one at a time, waiting for each database
query to finish:

```text
Request A arrives ──▶ query database (20ms) ──▶ respond
                                                Request B arrives ──▶ query (20ms) ──▶ respond
                                                                                        Request C …
```

Each request waits for the previous one. With 100 concurrent users, the last one waits 2 seconds —
doing nothing but waiting.

The fix is not "more threads". JSON serialisation, string manipulation and routing logic take
*microseconds*; the waiting takes *milliseconds to seconds*. Spending resources on waiting is the
waste.

### Blocking vs non-blocking

| | Blocking (synchronous) | Non-blocking (asynchronous) |
| --- | --- | --- |
| What happens | The thread stops until the operation completes | The operation is handed off; the thread continues |
| Other requests during the wait | Blocked | Served normally |
| Code shape | Read top to bottom | Callbacks, promises, `async`/`await` |
| Example | `fs.readFileSync`, `JSON.parse` of 50 MB, a tight `for` loop | `fs.readFile`, `fetch`, `db.find({})` |

```js
// File: blocking-vs-nonblocking.mjs
import { readFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { performance } from 'node:perf_hooks';

// Two "requests" being handled at the same time.
async function handleRequestSync(id) {
  const start = performance.now();
  const content = readFileSync('./package.json', 'utf8');   // blocks the whole thread
  const elapsed = performance.now() - start;
  console.log(`[sync  req ${id}] read ${content.length} bytes in ${elapsed.toFixed(2)}ms`);
}

async function handleRequestAsync(id) {
  const start = performance.now();
  const content = await readFile('./package.json', 'utf8'); // yields to the event loop
  const elapsed = performance.now() - start;
  console.log(`[async req ${id}] read ${content.length} bytes in ${elapsed.toFixed(2)}ms`);
}

async function main() {
  console.log('--- synchronous (serialised) ---');
  const s1 = performance.now();
  await Promise.all([1, 2, 3].map((id) => handleRequestSync(id)));
  console.log(`total sync: ${(performance.now() - s1).toFixed(2)}ms`);

  console.log('\n--- asynchronous (concurrent) ---');
  const s2 = performance.now();
  await Promise.all([1, 2, 3].map((id) => handleRequestAsync(id)));
  console.log(`total async: ${(performance.now() - s2).toFixed(2)}ms`);
}

await main();
```

Typical output (your numbers will vary with disk caching):

```text
--- synchronous (serialised) ---
[sync  req 1] read 1204 bytes in 0.42ms
[sync  req 2] read 1204 bytes in 0.31ms
[sync  req 3] read 1204 bytes in 0.28ms
total sync: 1.01ms

--- asynchronous (concurrent) ---
[async req 3] read 1204 bytes in 1.31ms
[async req 2] read 1204 bytes in 1.35ms
[async req 1] read 1204 bytes in 1.38ms
total async: 1.90ms
```

**Read that result honestly.** With three tiny local-file reads, the *synchronous* version is
faster in wall-clock terms — the async version pays overhead per operation. The lesson is not
"async is always faster on a microbenchmark". The lesson is:

- Async wins when the operation involves **waiting** for an external system (network, disk under
  load, a database), because the wait is overlapped with other work.
- Async **starves** under CPU-bound work — there is nothing to overlap.
- The real reason to use async in a server is not speed for one request; it is that **one slow
  operation must not block every other concurrent request**.

```js
// File: why-it-matters.mjs
import { readFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { performance } from 'node:perf_hooks';
import { createServer } from 'node:http';

// A simulation of "some request does blocking work while others wait".
async function demonstrateBlocking() {
  const timer = setInterval(() => {
    console.log('  [heartbeat] the event loop is still responsive');
  }, 50);

  const start = performance.now();
  readFileSync('./package.json', 'utf8');
  // Simulate a slow synchronous operation (a big JSON parse, a CPU loop, a sync hash).
  const spinUntil = performance.now() + 300;
  while (performance.now() < spinUntil) {
    // intentional busy-wait
  }

  console.log(`  [blocker] blocked the loop for ${(performance.now() - start).toFixed(0)}ms`);
  await new Promise((resolve) => setTimeout(resolve, 200));
  clearInterval(timer);
}

console.log('With a blocking operation in a handler:');
await demonstrateBlocking();
```

Notice the missing heartbeats during the busy-wait: **the event loop stopped**, so timers, other
requests and even `console.log` scheduling all waited. That is the single most important thing to
internalise about Node.

---

## 2. The callback pattern

Before promises, async results were delivered by calling a function you supplied.

```js
// File: callbacks.mjs
import { readFile } from 'node:fs';

// The Node convention: "error-first callback" (aka Node-style callback).
readFile('./package.json', 'utf8', (error, data) => {
  if (error) {
    console.error('failed:', error.message);
    return;                              // ALWAYS return after handling an error
  }
  const pkg = JSON.parse(data);
  console.log('package:', pkg.name);
});

console.log('this prints BEFORE the file contents — the read is asynchronous');
```

### The error-first convention

```js
// File: error-first.mjs
function divideAsync(a, b, callback) {
  // Simulate async delivery of the result.
  queueMicrotask(() => {
    if (b === 0) {
      // The error is the FIRST argument, and the callback is still called exactly once.
      return callback(new RangeError('Cannot divide by zero'));
    }
    return callback(null, a / b);
  });
}

divideAsync(10, 2, (error, result) => {
  if (error) return console.error('error:', error.message);
  console.log('10 / 2 =', result);
  return undefined;
});

divideAsync(10, 0, (error, result) => {
  if (error) return console.error('error:', error.message);
  console.log('10 / 0 =', result);
  return undefined;
});
```

Rules that every well-behaved async function follows:

1. **Call the callback exactly once.**
2. **Call it asynchronously** — never before the function returns (prevents "Zalgo" bugs where
   behaviour depends on whether a cached result exists).
3. **Error first, data second.** On success, `error` is `null`/`undefined`.
4. **Callbacks are the last parameter.**

### Callback hell

Real operations have sequences and branches. In callbacks that becomes nesting:

```js
// File: callback-hell.mjs
import { readFile } from 'node:fs';

// ❌ The pyramid. Hard to read, hard to refactor, error handling duplicated.
function loadConfigThenData(callback) {
  readFile('./package.json', 'utf8', (error1, pkgRaw) => {
    if (error1) return callback(error1);
    let pkg;
    try {
      pkg = JSON.parse(pkgRaw);
    } catch (parseError) {
      return callback(parseError);
    }

    readFile('./package.json', 'utf8', (error2, dataRaw) => {
      if (error2) return callback(error2);

      readFile('./package.json', 'utf8', (error3, extraRaw) => {
        if (error3) return callback(error3);

        // Actual work buried five levels deep, four error checks up the stack.
        callback(null, {
          name: pkg.name,
          sizes: [dataRaw.length, extraRaw.length],
        });
      });
    });
  });
}

loadConfigThenData((error, result) => {
  if (error) return console.error('failed:', error.message);
  console.log('result:', result);
  return undefined;
});
```

The problems, precisely:

| Problem | Consequence |
| --- | --- |
| Nesting grows with each step | Indentation; logic far from its context |
| Error handling repeated at every level | Easy to forget one → swallowed errors |
| Control flow is implicit | Sequential vs parallel is hard to see; loops are awkward |
| No composition | You cannot "wait for two of these and combine the results" cleanly |
| Stack traces are fragmented | Debugging jumps between anonymous callbacks |

That is why promises were added to the language — not cosmetic preference, but to make async
control flow *composable*.

---

## 3. The same code with promises

```js
// File: promises-intro.mjs
import { readFile } from 'node:fs/promises';

// A promise is a placeholder for a future value with three states:
//   pending → fulfilled (value)  or  rejected (reason)
const pkgPromise = readFile('./package.json', 'utf8');

pkgPromise
  .then((raw) => JSON.parse(raw))
  .then((pkg) => console.log('name:', pkg.name))
  .catch((error) => console.error('failed:', error.message))
  .finally(() => console.log('done either way'));
```

The same nesting problem, solved:

```js
// File: promises-flat.mjs
import { readFile } from 'node:fs/promises';

// ✅ Flat, linear, one error handler for the whole chain.
async function loadConfigThenData() {
  const pkgRaw = await readFile('./package.json', 'utf8');
  const pkg = JSON.parse(pkgRaw);                       // throw → caught by the caller's try/catch
  const dataRaw = await readFile('./package.json', 'utf8');
  const extraRaw = await readFile('./package.json', 'utf8');

  return { name: pkg.name, sizes: [dataRaw.length, extraRaw.length] };
}

try {
  console.log('result:', await loadConfigThenData());
} catch (error) {
  console.error('failed:', error.message);
}
```

**`async`/`await` is not a different mechanism** — it is syntax over the same promises, with the
error handling moved into `try`/`catch` and the sequencing expressed as normal statements. Promises
and `await` are covered in full in [13 — Promises](13-promises.md).

---

## 4. Sequential vs parallel: the decision that dominates performance

```js
// File: sequential-vs-parallel.mjs
import { setTimeout as sleep } from 'node:timers/promises';
import { performance } from 'node:perf_hooks';

const fetchResource = async (name, ms = 100) => {
  await sleep(ms);                    // pretend this is a database/HTTP call
  return { name, ms };
};

async function sequential() {
  const start = performance.now();
  const results = [];
  results.push(await fetchResource('users'));
  results.push(await fetchResource('orders'));
  results.push(await fetchResource('products'));
  return { results, elapsed: performance.now() - start };
}

async function parallel() {
  const start = performance.now();
  const results = await Promise.all([
    fetchResource('users'),
    fetchResource('orders'),
    fetchResource('products'),
  ]);
  return { results, elapsed: performance.now() - start };
}

const seq = await sequential();
const par = await parallel();

console.log(`sequential: ${seq.elapsed.toFixed(0)}ms  (100 + 100 + 100)`);
console.log(`parallel  : ${par.elapsed.toFixed(0)}ms  (max of the three)`);
```

```text
sequential: 305ms  (100 + 100 + 100)
parallel  : 102ms  (max of the three)
```

### When each is correct

| Use sequential (`for...of` + `await`) when | Use parallel (`Promise.all`) when |
| --- | --- |
| Each step needs the previous result | The operations are independent |
| Order matters for side effects | Order of *initiation* does not matter to the outcome |
| You must respect a rate limit | You have capacity for the concurrency |
| Partial failure must stop everything | You want all results (or all settled outcomes) |
| Memory/connection limits demand it | The inputs are known up front |

### The version that scales: bounded concurrency

`Promise.all` with 10,000 inputs fires 10,000 simultaneous operations — which overwhelms databases
(often 100-connection pools), APIs (rate limits → 429s) and file descriptors (EMFILE). The
production pattern is a **worker pool with a fixed width**:

```js
// File: bounded-concurrency.mjs
import { setTimeout as sleep } from 'node:timers/promises';
import { performance } from 'node:perf_hooks';

/**
 * Run `worker` over `items` with at most `concurrency` operations in flight.
 * Results keep the input order. One failure does not cancel the others
 * (use Promise.all internally if you want fail-fast semantics instead).
 */
async function mapWithConcurrency(items, worker, { concurrency = 5 } = {}) {
  const results = new Array(items.length);
  let nextIndex = 0;
  let firstError = null;

  async function runWorker() {
    while (nextIndex < items.length) {
      const index = nextIndex;
      nextIndex += 1;
      try {
        results[index] = await worker(items[index], index);
      } catch (error) {
        firstError ??= error;
        results[index] = { error: error.message };
      }
    }
  }

  const workers = Array.from(
    { length: Math.min(concurrency, items.length) },
    () => runWorker()
  );

  await Promise.all(workers);

  if (firstError) {
    // Optional: surface failures without losing the successful results.
    console.warn(`completed with errors (${firstError.message})`);
  }
  return results;
}

// Demo: 20 tasks, each taking 50ms, with a pool of 4.
const items = Array.from({ length: 20 }, (_, i) => ({ id: i + 1 }));

const start = performance.now();
const results = await mapWithConcurrency(
  items,
  async (item) => {
    await sleep(50);
    return { ...item, processed: true };
  },
  { concurrency: 4 }
);
const elapsed = performance.now() - start;

console.log('processed:', results.length, 'items');
console.log(`elapsed  : ${elapsed.toFixed(0)}ms`);
console.log(`serial would be ~${items.length * 50}ms, unbounded ~50ms, pool of 4 ~${Math.ceil(items.length / 4) * 50}ms`);
```

```text
processed: 20 items
elapsed  : 252ms
serial would be ~1000ms, unbounded ~50ms, pool of 4 ~250ms
```

That is the trade-off in one line: **a pool of N is roughly N× faster than serial and roughly
`items/N` slower than unlimited — while never overwhelming the thing you are calling.**

For large pipelines, `p-limit`, `p-map` or `fastq` do this for you (and handle a lot of edge cases).
Knowing how to write it, though, is what lets you reason about which one you need.

---

## 5. Combining and racing promises

```js
// File: combining-promises.mjs
import { setTimeout as sleep } from 'node:timers/promises';

const ok = (value, ms = 20) => sleep(ms).then(() => value);
const fail = (message, ms = 20) => sleep(ms).then(() => {
  throw new Error(message);
});

// Promise.all — all must succeed, or the whole thing rejects with the FIRST error.
try {
  const all = await Promise.all([ok('users'), ok('orders'), fail('products are down')]);
  console.log('all:', all);
} catch (error) {
  console.log('all rejected with:', error.message);      // products are down
}

// Promise.allSettled — never rejects; you inspect each outcome. Best default for
// "gather from several sources and report on each".
const settled = await Promise.allSettled([ok('users'), fail('orders down'), ok('products')]);
for (const outcome of settled) {
  if (outcome.status === 'fulfilled') console.log('  ✓', outcome.value);
  else console.log('  ✗', outcome.reason.message);
}

// Promise.race — the first SETTLED promise wins (fulfil or reject).
const winner = await Promise.race([ok('fast', 10), ok('slow', 200)]);
console.log('race winner:', winner);

// Promise.any — the first FULFILMENT wins; rejects only if ALL fail (AggregateError).
try {
  const first = await Promise.any([fail('broken A', 5), ok('working B', 30)]);
  console.log('any winner:', first);
} catch (error) {
  console.log('aggregate:', error.name, error.errors.map((e) => e.message));
}

// A practical use of race: a timeout wrapper.
function withTimeout(promise, ms, label = 'operation') {
  let timer;
  const timeout = new Promise((resolve, reject) => {
    timer = setTimeout(() => {
      reject(Object.assign(new Error(`${label} timed out after ${ms}ms`), { code: 'ETIMEDOUT' }));
    }, ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

try {
  await withTimeout(sleep(200).then(() => 'never seen'), 50, 'slow query');
} catch (error) {
  console.log('timeout:', error.code, '-', error.message);
}

// Node 18+ has this built in — prefer it in real code:
try {
  await sleep(200, undefined, { signal: AbortSignal.timeout(30) });
} catch (error) {
  console.log('AbortSignal.timeout:', error.name);      // TimeoutError
}
```

| Combinator | Resolves when | Rejects when | Use for |
| --- | --- | --- | --- |
| `Promise.all` | All fulfil | Any rejects (immediately) | Required data from several sources |
| `Promise.allSettled` | All settle | Never | Optional enrichment, bulk jobs, partial failures |
| `Promise.race` | First settles (either way) | First rejects | Timeouts, "whichever responds first" |
| `Promise.any` | First fulfils | All reject (`AggregateError`) | Redundant sources, fallback providers |

> **`Promise.all` and connection pools:** firing 500 queries at once against a pool of 10 does not
> give you 500× throughput. The 490 waiting requests queue in the pool (good — that is backpressure)
> but they also hold memory, and the first-query latency of a burst can trip timeouts. Bound your
> concurrency to something near the pool size.

---

## 6. Cancellation with `AbortController`

Async operations should be cancellable — for timeouts, for client disconnects, and to stop work
whose result nobody wants any more.

```js
// File: cancellation.mjs
import { setTimeout as sleep } from 'node:timers/promises';

// 1. Cancelling built-in operations: fetch, timers, streams all accept a signal.
const controller = new AbortController();

const work = (async () => {
  try {
    await sleep(1000, undefined, { signal: controller.signal });
    return 'finished (should not happen)';
  } catch (error) {
    return `cancelled: ${error.name}`;
  }
})();

setTimeout(() => controller.abort(), 50);
console.log(await work);          // cancelled: AbortError

// 2. Making YOUR OWN function cancellable — the correct pattern.
async function queryDatabase(sql, { signal } = {}) {
  // Fail immediately if the signal is already aborted.
  signal?.throwIfAborted();

  // Hook up cleanup that runs if the caller aborts.
  const onAbort = () => {
    // In a real driver: driverConnection.cancel(), cursor.close(), socket.destroy()
  };
  signal?.addEventListener('abort', onAbort, { once: true });

  try {
    await sleep(200);                      // pretend this is the query
    signal?.throwIfAborted();              // check again after the work
    return [`row for ${sql}`];
  } finally {
    signal?.removeEventListener('abort', onAbort);   // ALWAYS clean up the listener
  }
}

// Normal use
console.log(await queryDatabase('SELECT 1'));

// Timed use
try {
  await queryDatabase('SELECT pg_sleep(10)', { signal: AbortSignal.timeout(50) });
} catch (error) {
  console.log('query aborted:', error.name);         // TimeoutError
}

// 3. The real-world case: a client disconnects, so stop the expensive work.
import { createServer } from 'node:http';

const server = createServer(async (req, res) => {
  const abortController = new AbortController();

  // `req` emits 'close' when the client goes away (including aborted requests).
  req.on('close', () => {
    if (!res.writableEnded) {
      console.log('client disconnected — cancelling the query');
      abortController.abort();
    }
  });

  try {
    const rows = await queryDatabase('SELECT expensive_report', { signal: abortController.signal });
    if (!res.headersSent) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
    }
    res.end(JSON.stringify({ rows }));
  } catch (error) {
    if (error.name === 'AbortError' || error.name === 'TimeoutError') {
      // The client is gone; there is nothing to send.
      return res.destroy();
    }
    throw error;
  }
});

server.listen(0, '127.0.0.1', async () => {
  const { port } = server.address();
  console.log(`\ndemo server on http://127.0.0.1:${port}/report`);

  // A client that disconnects early:
  const clientController = new AbortController();
  fetch(`http://127.0.0.1:${port}/report`, { signal: clientController.signal })
    .then((response) => response.json())
    .catch(() => {});                     // expected: we abort it below
  setTimeout(() => clientController.abort(), 30);

  await sleep(300);
  server.close();
});
```

**Why cancellation is not optional in production:** without it, a client that closes a tab still
occupies a database connection and CPU until your query finishes. Multiply by a retry loop or a
slow report and you have an outage caused by users leaving.

---

## 7. Common async mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| `forEach` with an async callback | Work never awaited; function returns early | `for...of` + `await`, or `Promise.all(items.map(...))` |
| Missing `await` | Silent "undefined", unhandled rejections, races | Await it, or `void` it *deliberately* with a comment |
| `await` inside a loop over independent items | Slower than necessary | `Promise.all` with bounded concurrency |
| No `try/catch` around `await` | Unhandled rejection / 500s | Wrap, or forward to the error middleware |
| Mixing callbacks and promises | Double-calling callbacks, hard-to-follow flow | `util.promisify` / `fs/promises` |
| Swallowing errors with `.catch(() => {})` | Silent failures in production | Log with context; rethrow unexpected errors |
| Creating promises for value-less work | `await` on a non-promise | Just call the function |
| Relying on timing (`setTimeout(fn, 0)` to "wait") | Race conditions under load | Await the actual event/promise |
| Unbounded `Promise.all` over a large array | Pool exhaustion, 429s, EMFILE | Bounded concurrency |
| Forgetting to clean up listeners in cancellable code | Memory leak, MaxListeners warning | Remove in `finally` |

### The async/await traps in one snippet

```js
// File: async-traps.mjs
import { setTimeout as sleep } from 'node:timers/promises';

const ids = [1, 2, 3];

// ❌ 1. forEach + async: nothing is awaited, errors vanish.
async function badForEach() {
  ids.forEach(async (id) => {
    await sleep(10);
    if (id === 2) throw new Error('nobody sees this error');
  });
  return 'returned immediately';
}
console.log(await badForEach());          // returned immediately

// ✅ 2. Correct: await the group.
async function goodParallel() {
  await Promise.all(
    ids.map(async (id) => {
      await sleep(10);
      return id;
    })
  );
  return 'all done';
}
console.log(await goodParallel());        // all done

// ❌ 3. Missing await in a try/catch: the catch never fires.
async function badCatch() {
  try {
    sleep(10).then(() => {
      throw new Error('escapes the try/catch');
    });
    return 'not caught here';
  } catch (error) {
    return `caught: ${error.message}`;
  }
}
console.log(await badCatch());            // not caught here

// ✅ 4. With await, the catch works as expected.
async function goodCatch() {
  try {
    await sleep(10).then(() => {
      throw new Error('caught properly');
    });
    return 'unreachable';
  } catch (error) {
    return `caught: ${error.message}`;
  }
}
console.log(await goodCatch());           // caught: caught properly

// ⚠️ 5. Sequential awaits over independent work: measurable waste.
import { performance } from 'node:perf_hooks';
const slow = () => sleep(50);

let start = performance.now();
for (const id of [1, 2, 3]) await slow();
console.log(`sequential loop  : ${(performance.now() - start).toFixed(0)}ms`);

start = performance.now();
await Promise.all([1, 2, 3].map(() => slow()));
console.log(`parallel map     : ${(performance.now() - start).toFixed(0)}ms`);
```

---

## Exercise 12.1 — Convert callback code to async/await

Convert this helper to promises *without* changing its behaviour, and fix the error handling.

```js
// File: callbacks-to-promises-before.js
import { readFile } from 'node:fs';
import { createHash } from 'node:crypto';

export function fileChecksum(filePath, callback) {
  readFile(filePath, (error, data) => {
    if (error) return callback(error);
    const hash = createHash('sha256').update(data).digest('hex');
    return callback(null, hash);
  });
}
```

<details>
<summary>Solution</summary>

```js
// File: callbacks-to-promises-after.mjs
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

/**
 * Compute the SHA-256 checksum of a file.
 *
 * Behaviour is identical to the callback version, but errors propagate
 * through the promise instead of a callback argument.
 */
export async function fileChecksum(filePath) {
  const data = await readFile(filePath);              // Buffer, no encoding needed
  return createHash('sha256').update(data).digest('hex');
}

// Optional: a streaming version for large files — constant memory.
import { createReadStream } from 'node:fs';

export function fileChecksumStreaming(filePath) {
  return new Promise((resolve, reject) => {
    const hash = createHash('sha256');
    createReadStream(filePath)
      .on('error', reject)
      .on('data', (chunk) => hash.update(chunk))
      .on('end', () => resolve(hash.digest('hex')));
  });
}

// ---------------------------------------------------------------------------
// Usage, demonstrating the improvement in error handling
// ---------------------------------------------------------------------------
try {
  const checksum = await fileChecksum('./package.json');
  console.log('checksum:', checksum.slice(0, 16), '…');

  // Errors now surface in one place, with a stack trace, instead of at every level.
  await fileChecksum('./missing-file.json');
} catch (error) {
  console.log('caught in one place:', error.code, '-', error.message);
}

const [a, b] = await Promise.all([
  fileChecksum('./package.json'),
  fileChecksumStreaming('./package.json'),
]);
console.log('both approaches agree:', a === b);
```

**What improved, and why it is not merely cosmetic**

| Before (callbacks) | After (async/await) |
| --- | --- |
| `callback(error)` at every level | A single `try/catch` at the call site |
| Return value awkward (`return callback(...)`) | Ordinary `return` |
| Callers must remember the callback contract | The promise contract is enforced by the language |
| Hard to compose (combining two? nesting) | Compose freely with `Promise.all`/`allSettled` |
| Errors were data, not exceptions | Errors are exceptions: they propagate, carry stacks, and cannot be forgotten as easily |

**Also note what did *not* change:** the function is still asynchronous; there is still one file read;
the encoding/`Buffer` handling is identical. `async/await` changes how you *express* asynchrony, not
what the runtime does. Internally, the `await` still yields to the event loop exactly as the callback
did — that is the subject of [14 — The Event Loop](14-event-loop.md).

</details>

## Exercise 12.2 — Diagnose the production incident

Your API has these symptoms: p99 latency spikes to 8 seconds every few minutes, all endpoints are
affected simultaneously (even `/health`), CPU is at 100% on one core, and memory is stable. The logs
show requests completing normally, just slowly. What is your diagnosis, and what would you look for
in the code?

<details>
<summary>Solution</summary>

**Diagnosis: the event loop is being blocked.** The evidence line up exactly with that cause:

| Symptom | Why it points to event-loop blocking |
| --- | --- |
| **All** endpoints affected at once, including `/health` | There is one thread; a blocking operation stops everything |
| CPU at 100% on **one** core | Synchronous CPU work on the main thread |
| Memory stable | It is not a leak or a queue of unprocessed data |
| Periodic spikes ("every few minutes") | Something scheduled, or a request pattern that triggers it |
| Requests still complete (slowly) | Not a crash — the loop is starved, not dead |

**What to search the code for, in order of likelihood:**

1. **Synchronous `fs` calls in request paths:** `readFileSync`, `readdirSync`, `statSync`,
   `existsSync`. Especially in middleware (they run on *every* request) and in config reloads.
2. **CPU-heavy work in a handler:** image resizing, PDF generation, XML/CSV parsing, report
   aggregation, `crypto.pbkdf2Sync` / `bcrypt.hashSync` (password hashing done synchronously is a
   classic incident), `zlib.gzipSync`.
3. **Big `JSON.parse` / `JSON.stringify`**: parsing a 50 MB payload blocks for hundreds of
   milliseconds; stringifying a huge response does too.
4. **Unbounded loops or `while` conditions** over large in-memory arrays, and `Array.prototype.sort`
   with an expensive comparator on huge collections.
5. **Regex catastrophic backtracking** on user input (e.g. a "validated" email regex applied to a
   crafted string). This looks exactly like an infinite loop and is a real DoS vector.
6. **Synchronous third-party libraries**: validate that the SDK you call does not do sync I/O.
7. **A periodic task on a timer** (cache refresh, metrics flush, report generation) that runs
   synchronously — consistent with "every few minutes".

**How to confirm it (measure, do not guess):**

```js
// File: loop-lag-monitor.mjs — run this in production; it is cheap and decisive.
import { monitorEventLoopDelay } from 'node:perf_hooks';

const histogram = monitorEventLoopDelay({ resolution: 10 });
histogram.enable();

setInterval(() => {
  const p99Ms = histogram.percentile(99) / 1e6;
  const maxMs = histogram.max / 1e6;

  if (p99Ms > 100) {
    console.warn(
      JSON.stringify({
        level: 'warn',
        message: 'event loop lag detected',
        p99Ms: Number(p99Ms.toFixed(1)),
        maxMs: Number(maxMs.toFixed(1)),
      })
    );
  }
  histogram.reset();
}, 5_000).unref();
```

```bash
# Profile to find the culprit function:
node --cpu-prof --cpu-prof-dir=./profiles src/server.js
# then open the .cpuprofile in Chrome DevTools → Performance → Load profile
# look for a wide, tall stack: that is your blocking function.
```

**The fixes, in order of preference:**

| Fix | When it applies |
| --- | --- |
| **Make it async** (`fs.readFileSync` → `fs.promises.readFile`) | Most cases — it is a one-line change |
| **Cache it** (read the config once, not per request) | Data that rarely changes |
| **Move it off the request path** | Reports, thumbnails, exports: enqueue a job, respond `202`, notify later |
| **Move it to a worker/child process** | Genuinely CPU-bound: `worker_threads` pool, or a separate service |
| **Stream it** | Large JSON payloads, large files |
| **Bound it** (row limits, payload limits, timeouts) | Any user-controlled amount of work |
| **Fix the regex** (or use a linear-time matcher) | Regex backtracking |
| **Use the async variant of the CPU-bound API** (`scrypt` async, not `scryptSync`) | Password hashing |

**The interview-quality summary:** "Because Node runs your JavaScript on a single thread, any
synchronous CPU work or blocking I/O delays every other concurrent request, including health checks.
I would confirm it with event-loop-lag metrics and a CPU profile, then locate the synchronous call —
usually `*Sync` file APIs, an in-process CPU task like image or password processing, or a huge
JSON/parsing operation — and either make it asynchronous, cache it, bound it, or move it to a queue
or worker thread depending on whether it is I/O or CPU."

</details>

---

## What's next

You have used promises; now let's understand them properly — the states, the guarantees, the
microtask queue that `await` uses, and the patterns (`Promise.allSettled`, `finally`, rejection
handling) that keep async code correct at scale.

→ [13 — Promises, async and await](13-promises.md)
