# 17 — Debugging and Tooling

> **Where this fits:** Writing code is half the job; finding out why it misbehaves is the other half. This chapter is the practical toolkit: the inspector, breakpoints, structured logging, diagnostics reports, CPU and heap profiling, and a systematic approach to debugging that works when you have no idea what is wrong.

***

## 1. The debugging mindset: bisect, do not guess

Most debugging time is wasted on guessing. The professional approach is a loop:

```
1. Reproduce        — get a reliable, minimal failing case
2. Observe         — what exactly happens? (exact error, exact input, exact timing)
3. Hypothesise     — what single change would explain this?
4. Test            — prove or disprove it (add a log, write a test, bisect)
5. Fix             — the smallest change that addresses the cause, not the symptom
6. Verify          — the failing case passes AND nothing else broke
7. Prevent         — a test, a validation rule, or a guard so it cannot recur
```

Two habits make this fast:

* **Bisect the input space.** Halve the failing data set. Comment out half the code. Disable half the middleware. `git bisect` does exactly this over commits.
* **Change one thing at a time.** Two simultaneous changes tell you nothing when the result flips.

And the most valuable question, asked _before_ you touch the debugger: **"What have I assumed that might not be true?"** The bug almost always lives in that assumption.

***

## 2. `console.log`-driven debugging, done properly

`console.log` is legitimate and often the fastest tool. Used badly it produces noise; used well it answers a specific question.

```js
// File: log-debugging.mjs
// ❌ Nearly useless: no labels, no ordering, no context.
function badTotal(items) {
  let total = 0;
  for (const item of items) {
    console.log(item);
    total += item.price * item.quantity;
  }
  console.log(total);
  return total;
}

// ✅ Useful: labelled, shows the decision path, and prints exactly what you need to compare.
function goodTotal(items) {
  let total = 0;
  for (const [index, item] of items.entries()) {
    const lineTotal = item.price * item.quantity;
    console.log(
      `[goodTotal] item ${index}: price=${item.price} qty=${item.quantity} lineTotal=${lineTotal} running=${total + lineTotal}`
    );
    total += lineTotal;
  }
  console.log(`[goodTotal] final total=${total} from ${items.length} items`);
  return total;
}

const items = [
  { sku: 'A', price: 19.99, quantity: 2 },
  { sku: 'B', price: 5.5, quantity: 3 },
];

badTotal(items);
console.log('---');
goodTotal(items);
```

### `console` methods that replace "add a log and then remove it"

```js
// File: console-tools.mjs
const order = { id: 'o_1', customer: { id: 'c_9', name: 'Priya' }, items: [{ sku: 'A', qty: 2 }] };

// Full-depth object printing (default depth is 2 — nested data shows as [Object])
console.log(order);
console.dir(order, { depth: null, colors: true });

// Tables: compare many objects at a glance
console.table([
  { route: '/users', status: 200, ms: 12 },
  { route: '/orders', status: 500, ms: 340 },
  { route: '/health', status: 200, ms: 1 },
]);

// Timings
console.time('serialise');
JSON.stringify(Array.from({ length: 10_000 }, (_, i) => ({ i })));
console.timeEnd('serialise');

// Counting occurrences
for (let i = 0; i < 3; i += 1) console.count('iteration');

// Assertions — prints only when false
console.assert(order.items.length === 2, 'expected 2 items', { actual: order.items.length });

// A stack trace at the current point (find who called this)
function traceMe() {
  console.trace('who called traceMe?');
}
traceMe();

// Grouping related output
console.group('request');
console.log('method: GET');
console.log('path: /users');
console.groupEnd();
```

### When `console.log` is not enough

| Situation                                                | Tool                                                     |
| -------------------------------------------------------- | -------------------------------------------------------- |
| You need to inspect live variables and step through code | **`--inspect` + Chrome DevTools** (§3)                   |
| The bug is timing/concurrency-related                    | Structured logs with timestamps and request ids          |
| Latency, not correctness                                 | `--cpu-prof` or `performance.now()` instrumentation (§5) |
| Memory growth                                            | Heap snapshots, `--heap-prof` (§6)                       |
| It only happens in production                            | Start with the diagnostics report (§4)                   |

***

## 3. The debugger: `--inspect` and breakpoints

The Node inspector is a full debugging experience: pause, inspect, step, evaluate.

```bash
# Start with the inspector listening (default port 9229)
node --inspect src/server.js

# Pause before the first line — essential for debugging startup code
node --inspect-brk src/server.js

# Already running process: send it SIGUSR1
kill -USR1 <pid>
```

```
Debugger listening on ws://127.0.0.1:9229/8f3c1d2a-…
For help, see: https://nodejs.org/en/docs/inspector
```

Open `chrome://inspect` in Chrome → **Open dedicated DevTools for Node** → the Sources panel.

### What you can do that `console.log` cannot

| Capability                                   | Why it matters                                                                      |
| -------------------------------------------- | ----------------------------------------------------------------------------------- |
| **Breakpoints** (including conditional ones) | Stop exactly when `index === 42`                                                    |
| **Step over / into / out**                   | Follow the actual control flow, not what you assume it is                           |
| **Inspect live scope**                       | See every variable, closure and `this` value                                        |
| **Evaluate in the console**                  | Test a fix hypothesis without editing code: `users.filter(u => u.role === 'admin')` |
| **Call stack + async stack traces**          | See the chain through promises — invaluable for async bugs                          |
| **Watch expressions**                        | Pin a value and watch it change as you step                                         |
| **Blackboxing**                              | Skip `node_modules` while stepping                                                  |
| **Pause on exceptions**                      | Stop at the throw site, not the catch site                                          |

### Method 1: `debugger` statements (fastest for a quick session)

```js
// File: debug-statement.mjs
function calculateDiscount(user, subtotalCents) {
  let discountRate = 0;

  if (user.tier === 'gold') discountRate = 0.15;
  else if (user.tier === 'silver') discountRate = 0.08;

  debugger;   // ← with --inspect, execution pauses here and DevTools opens

  const discount = Math.round(subtotalCents * discountRate);
  return { discount, total: subtotalCents - discount };
}

const result = calculateDiscount({ tier: 'gold' }, 10_000);
console.log(result);
```

```bash
node --inspect-brk debug-statement.mjs
# In DevTools: Sources → press Resume (F8) → execution stops at `debugger`
# Inspect discountRate, step over the next lines, evaluate expressions in the Console.
```

**Important:** remove `debugger` statements before committing. A linter rule (`no-debugger`) will catch them.

### Method 2: `--inspect` with an editor (VS Code / WebStorm)

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug API",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/src/server.js",
      "envFile": "${workspaceFolder}/.env",
      "skipFiles": ["<node_internals>/**", "**/node_modules/**"],
      "console": "integratedTerminal"
    },
    {
      "name": "Debug current test file",
      "type": "node",
      "request": "launch",
      "program": "${file}",
      "skipFiles": ["<node_internals>/**"]
    },
    {
      "name": "Attach to running process",
      "type": "node",
      "request": "attach",
      "port": 9229,
      "restart": true
    }
  ]
}
```

Press F5, set breakpoints by clicking the gutter, and debug with the same experience as the browser. This is the setup professional Node developers use daily — worth ten minutes to configure once.

***

## 4. When it only breaks in production: the diagnostics report

```bash
# Generate a report about the process — safe to run on a live server.
kill -USR2 <pid>            # the report appears in the working directory (or /tmp)
```

```
Writing Node.js report to file: report.20260918.101530.41283.0.001.json
```

The JSON report contains exactly what you need in an incident:

* **JavaScript and native stack traces** of every thread (often shows _where_ it is stuck)
* **Environment**: Node version, OS, CPU, memory limits, container hints
* **Heap statistics** and memory usage
* **Active handles and requests** — a leaking socket or timer shows up here
* **libuv handle details** and **resource usage**

```bash
# Read the interesting parts without loading the whole file
node -e "
const report = require('./report.20260918.101530.41283.0.001.json');
console.log('node:', report.header.nodejsVersion);
console.log('memory (MB):', Math.round(report.header.processMemory.heapUsed / 1048576));
console.log('libuv handles:', report.libuv.length);
console.log('active js handles:', report.javascriptHeap.totalHeapSize / 1048576, 'MB heap');
console.log('platform:', report.header.platform, report.header.arch);
"
```

### Inspecting handles at runtime (a private API, but invaluable)

```js
// File: handles.mjs
// "What is keeping my process alive?" — the answer to a hanging process.
const handles = process._getActiveHandles?.() ?? [];
const requests = process._getActiveRequests?.() ?? [];

console.log('active handles:', handles.length);
for (const handle of handles) {
  console.log('  -', handle.constructor?.name ?? typeof handle);
}

console.log('active requests:', requests.length);
for (const request of requests) {
  console.log('  -', request.constructor?.name ?? typeof request);
}

// Typical findings:
//   Socket / Server  → a server or client connection still open
//   Timeout          → a timer you forgot to clear
//   FSReqCallback    → a file operation still pending
```

Use this in a `beforeExit` handler to find what prevents a graceful exit:

```js
// File: why-not-exiting.mjs
process.on('beforeExit', (code) => {
  // Fires only when the event loop is about to drain — so this tells you the loop IS empty.
  console.log(`about to exit with code ${code}`);
});

setInterval(() => {}, 1000);   // ← keeps the process alive forever

setTimeout(() => {
  console.log('If you see this but never the beforeExit line, a handle is holding the loop open.');
  const handles = process._getActiveHandles?.() ?? [];
  console.log('active handle types:', handles.map((h) => h.constructor?.name));
  process.exit(0);
}, 200);
```

***

## 5. Profiling: finding _where_ the time goes

Debugging is not only for crashes. "Why is this endpoint slow?" is a debugging question.

### Quick and precise: `performance.now()` instrumentation

```js
// File: timing.mjs
import { performance } from 'node:perf_hooks';

async function timed(label, fn) {
  const start = performance.now();
  const result = await fn();
  const elapsed = performance.now() - start;
  console.log(`${label.padEnd(28)} ${elapsed.toFixed(2)}ms`);
  return result;
}

// Simulate the stages of a request.
const findUser = () => new Promise((resolve) => setTimeout(() => resolve({ id: 1 }), 12));
const findOrders = () => new Promise((resolve) => setTimeout(() => resolve([]), 45));
const serialise = (data) => JSON.stringify(data);

await timed('1. findUser', findUser);
await timed('2. findOrders', findOrders);
await timed('3. serialise', () => serialise({ ok: true }));

// The lesson: instrument the STAGES, and you immediately see where the time is.
// `findOrders` at 45ms is the bottleneck; there is no need to guess.
```

### The built-in CPU profiler (the real tool)

```bash
# Record a CPU profile for the whole process
node --cpu-prof --cpu-prof-dir=./profiles src/server.js

# Record with a name and interval (1000µs = 1ms sampling, the default)
node --cpu-prof --cpu-prof-name=api.cpuprofile src/server.js
```

Then open the `.cpuprofile` in Chrome DevTools → **Performance** → **Load profile**:

```
┌─────────────────────────────────────────────────────────────┐
│ The flame chart's WIDTH is time. Find the widest bars.      │
│                                                             │
│ ██████████████████ buildReport()          ← 62% of the time │
│   ███████████ queryAllRows()                                │
│   ██████ formatCurrency()   ← called 40,000 times!          │
│ ██ parseRequest()                                           │
└─────────────────────────────────────────────────────────────┘
```

| Symptom in the profile                   | Usually means                                            |
| ---------------------------------------- | -------------------------------------------------------- |
| One wide bar in your code                | A slow algorithm or a loop over too much data            |
| A function called a huge number of times | N+1 pattern, or a helper called inside a loop            |
| Wide bars in `node:internal` / `node:fs` | Synchronous I/O                                          |
| Wide `JSON.parse`/`stringify`            | Payloads too large; paginate or stream                   |
| Wide garbage-collection bars             | Allocation churn (creating objects/strings in hot loops) |

```bash
# Quick and dirty: is the CPU in my code or in native/GC?
node --prof src/server.js
node --prof-process isolate-*.log | head -40
```

### Measuring async operations: `perf_hooks`

```js
// File: async-timing.mjs
import { performance, PerformanceObserver } from 'node:perf_hooks';
import { setTimeout as sleep } from 'node:timers/promises';

// Track named measurements automatically — useful for instrumenting a whole app.
const observer = new PerformanceObserver((items) => {
  for (const entry of items.getEntries()) {
    console.log(`[perf] ${entry.name}: ${entry.duration.toFixed(2)}ms`);
  }
});
observer.observe({ entryTypes: ['measure'] });

performance.mark('query:start');
await sleep(37);
performance.mark('query:end');
performance.measure('database query', 'query:start', 'query:end');

performance.mark('render:start');
await sleep(5);
performance.mark('render:end');
performance.measure('response render', 'render:start', 'render:end');

observer.disconnect();
```

***

## 6. Memory: leaks and heap inspection

```js
// File: memory-watch.mjs
import { setTimeout as sleep } from 'node:timers/promises';

function report(label) {
  const { heapUsed, heapTotal, rss, external } = process.memoryUsage();
  const mb = (bytes) => (bytes / 1024 / 1024).toFixed(1).padStart(6);
  console.log(`${label.padEnd(22)} heapUsed=${mb(heapUsed)}MB heapTotal=${mb(heapTotal)}MB rss=${mb(rss)}MB external=${mb(external)}MB`);
}

report('start');

const leaked = [];                              // ← deliberately retained

for (let round = 1; round <= 4; round += 1) {
  // Allocate 10 MB of data...
  for (let i = 0; i < 10; i += 1) {
    leaked.push(Buffer.alloc(1024 * 1024));     // ← and retain it: a leak
  }
  await sleep(50);
  report(`after round ${round}`);
}

console.log('\nTip: run with --expose-gc and call global.gc() to see what is truly retained:');
if (typeof global.gc === 'function') global.gc();
report('after forced gc');
```

```
start                  heapUsed=   4.1MB heapTotal=   5.2MB rss=  42.0MB external=  1.2MB
after round 1          heapUsed=  14.3MB heapTotal=  18.0MB rss=  52.4MB external= 11.2MB
after round 2          heapUsed=  24.4MB heapTotal=  28.0MB rss=  62.8MB external= 21.2MB
after round 3          heapUsed=  34.6MB heapTotal=  40.0MB rss=  73.2MB external= 31.2MB
after round 4          heapUsed=  44.7MB heapTotal=  52.0MB rss=  83.6MB external= 41.2MB
```

**Steadily rising `rss` with stable load = a leak.** Common causes in Node services:

| Cause                                                              | Fix                                                    |
| ------------------------------------------------------------------ | ------------------------------------------------------ |
| Listeners added per request (`emitter.on` in a handler)            | Add once, or `off` on cleanup                          |
| In-memory caches with no eviction                                  | LRU with a max size and TTL (or Redis)                 |
| Unbounded arrays/maps accumulating requests, ids, or logs          | Bound the structure                                    |
| Closures capturing large objects (a socket, a request, a response) | Release the reference; do not store in long-lived maps |
| Growing `Metrics`/histogram arrays                                 | Cap the number of buckets/samples                      |
| Global mutable state holding request data                          | Move to per-request scope                              |
| Very large payloads kept for caching                               | Cache selectively; stream                              |

```bash
# Heap snapshot for DevTools analysis:
node --heapsnapshot-signal=SIGUSR2 src/server.js
kill -USR2 <pid>          # writes a .heapsnapshot file

# In DevTools → Memory → Load → take two snapshots at different times →
# choose "Comparison": look for the object types that grew.
```

```
Comparison view, sorted by "Delta":
  +48,120   EventListener
  +12,004   IncomingMessage      ← requests being retained!
   +9,112   Socket
```

`IncomingMessage` and `Socket` growing over time means something holds a reference to each request — almost always a listener registered on a long-lived emitter inside a request handler (exactly the leak from [08 §4](08-events.md)).

### `--expose-gc` and reading memory honestly

```bash
node --expose-gc -e "
  const before = process.memoryUsage().heapUsed;
  const junk = Array.from({ length: 1000 }, () => ({ payload: 'x'.repeat(1000) }));
  const after = process.memoryUsage().heapUsed;
  global.gc();                                  // force a collection
  const afterGc = process.memoryUsage().heapUsed;
  console.log('allocated (MB):', ((after - before) / 1048576).toFixed(2));
  console.log('still held (MB):', ((afterGc - before) / 1048576).toFixed(2));
  console.log('junk still in scope:', junk.length > 0);
"
```

Heap usage that drops after `gc()` was garbage — not a leak. Heap usage that stays is retention. Only the second is a problem, which is why measuring right after a forced GC is the honest measurement.

***

## 7. Logging as debugging infrastructure

Debug logs you can turn on without redeploying are worth more than a debugger you cannot attach to production.

```js
// File: mini-logger.mjs
const LEVELS = { error: 50, warn: 40, info: 30, debug: 20, trace: 10 };

function createLogger({ level = 'info', base = {} } = {}) {
  const threshold = LEVELS[level] ?? LEVELS.info;

  const emit = (name, message, context = {}) => {
    if (LEVELS[name] < threshold) return;
    const line = JSON.stringify({
      level: name,
      time: new Date().toISOString(),
      message,
      ...base,
      ...context,
    });
    (name === 'error' || name === 'warn' ? process.stderr : process.stdout).write(`${line}\n`);
  };

  return {
    error: (message, context) => emit('error', message, context),
    warn: (message, context) => emit('warn', message, context),
    info: (message, context) => emit('info', message, context),
    debug: (message, context) => emit('debug', message, context),
    trace: (message, context) => emit('trace', message, context),
    /** Attach fields to every subsequent log line (request id, user id). */
    child: (childBase) =>
      createLogger({ level, base: { ...base, ...childBase } }),
  };
}

const logger = createLogger({ level: process.env.LOG_LEVEL ?? 'debug', base: { service: 'api' } });

logger.info('server started', { port: 3000 });
logger.debug('cache miss', { key: 'user:42', ttl: 60 });

// Per-request child logger — the pattern that makes production debugging possible.
const requestLogger = logger.child({ requestId: 'req_a1b2c3', userId: 'u_17' });
requestLogger.debug('fetching orders', { page: 1, limit: 20 });
requestLogger.error('database timeout', { query: 'SELECT …', durationMs: 3001 });
```

```
{"level":"info","time":"2026-09-18T10:15:30.001Z","message":"server started","service":"api","port":3000}
{"level":"debug","time":"2026-09-18T10:15:30.002Z","message":"cache miss","service":"api","key":"user:42","ttl":60}
{"level":"debug","time":"2026-09-18T10:15:30.003Z","message":"fetching orders","service":"api","requestId":"req_a1b2c3","userId":"u_17","page":1,"limit":20}
{"level":"error","time":"2026-09-18T10:15:30.004Z","message":"database timeout","service":"api","requestId":"req_a1b2c3","userId":"u_17","query":"SELECT …","durationMs":3001}
```

**Why child loggers matter:** every line from a request carries the same `requestId`. Given a user's report, you filter by that id and see the entire story of that request, including lines from libraries you did not write.

In a real service, use **`pino`** (fast, JSON-native, redaction built in) rather than hand-rolling:

```js
// File: pino-preview.mjs
// import pino from 'pino';
//
// const logger = pino({
//   level: process.env.LOG_LEVEL ?? 'info',
//   redact: {
//     paths: ['req.headers.authorization', 'req.headers.cookie', '*.password', '*.token'],
//     censor: '[REDACTED]',
//   },
//   base: { service: 'api', env: process.env.NODE_ENV },
// });
//
// logger.info({ requestId, userId }, 'request completed');
console.log('See the Express and deployment chapters for the full pino + pino-http setup.');
```

***

## 8. Debugging tools cheat sheet

| Task                              | Command / tool                                                |
| --------------------------------- | ------------------------------------------------------------- |
| Attach a debugger                 | `node --inspect app.js`, then `chrome://inspect`              |
| Pause at startup                  | `node --inspect-brk app.js`                                   |
| Attach to a running process       | `kill -USR1 <pid>`                                            |
| Restart on file change            | `node --watch app.js`                                         |
| Diagnostics report                | `kill -USR2 <pid>`                                            |
| CPU profile                       | `node --cpu-prof app.js`                                      |
| Heap snapshot                     | `node --heapsnapshot-signal=SIGUSR2 app.js` then `kill -USR2` |
| Force GC (for measurements)       | `node --expose-gc`, then `global.gc()`                        |
| Built-in test runner              | `node --test`                                                 |
| Type checking JS                  | `npx tsc --checkJs --noEmit` with `// @ts-check`              |
| Lint                              | `npx eslint .`                                                |
| Syntax check a file               | `node --check file.js`                                        |
| Unhandled rejection trace         | `node --trace-uncaught app.js`                                |
| Deprecation warnings with a stack | `node --trace-deprecation app.js`                             |
| Warnings with traces              | `node --trace-warnings app.js`                                |
| See what blocks the loop          | `node --trace-sync-io app.js`                                 |
| Show where a warning came from    | `node --pending-deprecation app.js`                           |

```bash
# --trace-sync-io is underused: it warns whenever synchronous I/O happens.
node --trace-sync-io src/server.js
# (node:41283) WARNING: Detected use of sync API
#     at Object.readFileSync (node:fs:…)
#     at loadConfig (file:///…/src/config.js:12:20)
```

That one flag finds the exact cause of "the endpoint is slow" incidents in seconds.

***

## 9. Common mistakes

| Mistake                                                 | Consequence                                        | Fix                                                                |
| ------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------ |
| Guessing instead of measuring                           | Hours lost on the wrong hypothesis                 | Profile or instrument first                                        |
| `console.log` everywhere, never removed                 | Noisy, slow, may leak secrets                      | Structured logger with levels; `no-console` lint rule in libraries |
| Committing `debugger` statements                        | Pauses in production if inspectors are enabled     | Lint rule                                                          |
| Debugging in production with `--inspect` bound publicly | Remote code execution risk                         | Bind to localhost, or tunnel over SSH                              |
| Assuming the error message is the cause                 | Fixes symptoms                                     | Find the stack, the `cause`, and the actual failing input          |
| Only testing the happy path                             | Bugs found by users                                | Reproduce the failure in a test, then fix it                       |
| Not reproducing first                                   | "Fixed" things that were never broken              | Write a failing test, then fix it                                  |
| Ignoring warnings                                       | Deprecations become breakage in the next major     | Treat warnings as work to schedule                                 |
| Logging objects with circular references                | `TypeError: Converting circular structure to JSON` | Log ids and selected fields, not whole entities                    |
| Leaving `--watch` in production                         | Restarts on file changes, double processes         | Use a process manager                                              |
| Reading memory before a GC                              | False "leak" reports                               | Compare with `--expose-gc` + `global.gc()`                         |

***

## Exercise 17.1 — Debug a real bug

This endpoint returns `total: 0` for an order that clearly has items, but only _sometimes_ — it works in your test suite and fails in the browser.

```js
// File: buggy.mjs
import { createServer } from 'node:http';

const orders = new Map();
let nextId = 1;

const readJson = (req) =>
  new Promise((resolve) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk;
    });
    req.on('end', () => {
      try {
        resolve(JSON.parse(body));
      } catch {
        resolve({});          // ← suspicious
      }
    });
  });

createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/orders') {
    const payload = await readJson(req);
    const order = {
      id: `o_${nextId++}`,
      items: payload.items ?? [],
      total: (payload.items ?? []).reduce((sum, item) => sum + item.price * item.qty, 0),
    };
    orders.set(order.id, order);
    res.writeHead(201, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(order));
    return;
  }
  res.writeHead(404).end();
}).listen(3000);
```

Investigate with the tools from this chapter and find the bug(s).

<details>

<summary>Solution</summary>

**How to investigate, using the chapter's tools:**

1. **Reproduce it.** The clue "works in tests, fails from the browser" is about _the client_. Tests probably send `Content-Type: application/json` and body `{"items":[...], "qty": 2}`. A frontend might send `quantity` instead of `qty` — or, more likely, a form-encoded body.
2.  **Log the raw input** (not the parsed object):

    ```js
    req.on('data', (chunk) => {
      console.log('[debug] raw chunk:', JSON.stringify(chunk.toString()));
      body += chunk;
    });
    ```
3. **Check the client's request in DevTools → Network → Payload.** This is the decisive step: it shows exactly what the browser sent, headers included.

**The bugs, once you look:**

1. **Swallowed JSON parse error.** The `catch { resolve({}) }` turns a malformed or differently-encoded body into an empty object. Then `payload.items ?? []` yields `[]`, and `total` is `0` — with a `201 Created`. The failure is silent. This is why the bug is intermittent: it only happens when the body does not parse (for example, a URL-encoded form body like `items%5B0%5D%5Bprice%5D=10`).
2. **`JSON.parse` on a form-encoded body throws** — the server never checks `Content-Type`, so it accepts bodies it cannot understand.
3. **`body += chunk` on a Buffer** relies on implicit `toString('utf8')`. For multi-byte characters split across chunk boundaries this can corrupt the payload — a real bug with non-ASCII data.
4. **No size limit** — a large body can exhaust memory.
5. **No validation of `items`** — `item.price` or `item.qty` missing → `NaN` → `total: NaN` in JSON, which becomes `null` client-side. Another silent failure path.
6. **No content-type check, no `415`, no `400`** — all malformed input becomes a "successful" creation of an empty order.

**The fix**

```js
// File: fixed.mjs
import { createServer } from 'node:http';

const MAX_BODY_BYTES = 100_000;

/** Read the body as a Buffer, with a limit, and reject a premature client disconnect. */
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;

    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        const error = Object.assign(new Error('Payload too large'), { statusCode: 413 });
        req.destroy(error);
        return;
      }
      chunks.push(chunk);
    });

    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
    req.on('aborted', () => reject(Object.assign(new Error('Client aborted'), { statusCode: 400 })));
  });
}

const sendJson = (res, status, payload) => {
  const body = JSON.stringify(payload);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': Buffer.byteLength(body) });
  res.end(body);
};

const orders = new Map();
let nextId = 1;

const server = createServer(async (req, res) => {
  try {
    if (req.method !== 'POST' || req.url !== '/orders') {
      return sendJson(res, 404, { error: { code: 'NOT_FOUND' } });
    }

    // 1. Reject content types we cannot parse, with the correct status.
    const contentType = (req.headers['content-type'] ?? '').split(';')[0].trim().toLowerCase();
    if (contentType !== 'application/json') {
      return sendJson(res, 415, {
        error: { code: 'UNSUPPORTED_MEDIA_TYPE', message: `Expected application/json, received "${contentType || 'none'}"` },
      });
    }

    const raw = await readBody(req);

    // 2. A parse failure is a client error, not an empty object.
    let payload;
    try {
      payload = JSON.parse(raw.toString('utf8'));
    } catch (error) {
      return sendJson(res, 400, {
        error: { code: 'INVALID_JSON', message: `Request body is not valid JSON: ${error.message}` },
      });
    }

    // 3. Validate the shape and every numeric field.
    const issues = [];
    if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
      issues.push({ field: 'body', message: 'must be a JSON object' });
    }
    const items = Array.isArray(payload?.items) ? payload.items : null;
    if (items === null) {
      issues.push({ field: 'items', message: 'must be an array' });
    } else {
      items.forEach((item, index) => {
        if (!Number.isFinite(item?.price) || item.price < 0) {
          issues.push({ field: `items[${index}].price`, message: 'must be a non-negative number' });
        }
        if (!Number.isInteger(item?.quantity) || item.quantity < 1) {
          // Accept both spellings ONLY if you document it — here we require `quantity`.
          issues.push({ field: `items[${index}].quantity`, message: 'must be an integer >= 1' });
        }
      });
    }

    if (issues.length > 0) {
      return sendJson(res, 422, { error: { code: 'VALIDATION_ERROR', message: 'Invalid order', details: issues } });
    }

    const totalCents = items.reduce((sum, item) => sum + Math.round(item.price * 100) * item.quantity, 0);

    const order = {
      id: `o_${nextId++}`,
      items: items.map((item) => ({ sku: item.sku, price: item.price, quantity: item.quantity })),
      total: totalCents / 100,          // returning major units; document which you use!
      totalCents,
    };

    orders.set(order.id, order);
    res.setHeader('Location', `/orders/${order.id}`);
    return sendJson(res, 201, { data: order });
  } catch (error) {
    const status = error.statusCode ?? 500;
    // 4. Log the real problem; return a safe message.
    console.error(JSON.stringify({ level: 'error', message: error.message, status }));
    return sendJson(res, status, {
      error: { code: status === 500 ? 'INTERNAL_ERROR' : 'REQUEST_ERROR', message: status === 500 ? 'Something went wrong' : error.message },
    });
  }
});

server.listen(3000, '0.0.0.0', async () => {
  console.log('listening on 3000');

  // Self-test: the good case, the buggy case, and the invalid case.
  const post = (body, headers) =>
    fetch('http://127.0.0.1:3000/orders', { method: 'POST', headers, body }).then(async (r) => ({
      status: r.status,
      body: await r.json(),
    }));

  console.log('\n1. valid JSON with quantity:');
  console.log(await post(JSON.stringify({ items: [{ sku: 'A', price: 19.99, quantity: 2 }] }), { 'Content-Type': 'application/json' }));

  console.log('\n2. the old broken shape (qty instead of quantity):');
  console.log(await post(JSON.stringify({ items: [{ sku: 'A', price: 19.99, qty: 2 }] }), { 'Content-Type': 'application/json' }));

  console.log('\n3. a form-encoded body (the likely browser bug):');
  console.log(await post('items[0][price]=19.99', { 'Content-Type': 'application/x-www-form-urlencoded' }));

  console.log('\n4. malformed JSON:');
  console.log(await post('{"items": [', { 'Content-Type': 'application/json' }));

  server.close();
});
```

**The debugging lessons this exercise encodes**

| Lesson                                                                        | Evidence                                            |
| ----------------------------------------------------------------------------- | --------------------------------------------------- |
| "Works in tests, fails in the browser" points at the _request_, not the logic | DevTools → Network → Payload                        |
| Swallowing an error turns a clear failure into a wrong answer                 | `resolve({})` produced `201` with `total: 0`        |
| Validate at the boundary and reject with the right status                     | `415`, `400`, `422`                                 |
| Log the raw input during investigation                                        | `JSON.stringify(chunk.toString())`                  |
| Intermittent bugs are usually input-dependent                                 | Different content types and field names             |
| A "success" response can still be a bug                                       | The original code returned `201` for an empty order |

</details>

***

## What's next

You have the whole toolbox for writing and debugging Node code. Time to build a complete project with it: a CRUD API backed by a JSON file store — routing by hand, validation, error handling, tests and all — which is the rehearsal for the Express version in the next section.

→ [18 — Project: JSON File CRUD API](18-nodejs-project.md)
