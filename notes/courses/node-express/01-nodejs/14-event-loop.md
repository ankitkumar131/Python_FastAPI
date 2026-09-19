# 14 — The Event Loop

> **Where this fits:** This is the chapter that explains Node's performance characteristics — and
> every "why is my API slow?" question you will ever debug. It covers the phases of the loop, the two
> microtask queues, the libuv thread pool, event-loop starvation, and the four ways to use all your
> CPU cores. Everything you learned about callbacks, promises and streams comes together here.

---

## 1. The model

Node runs your JavaScript on a **single thread**. Everything asynchronous is orchestrated by a loop
that repeatedly asks the operating system "is anything ready?" and then runs the corresponding
callbacks.

```text
┌──────────────────────────────────────────────────────────────┐
│                      MAIN THREAD (one)                        │
│                                                              │
│   ┌────────────────────────────────────────────────────┐     │
│   │  CALL STACK   ← your JavaScript runs here          │     │
│   └────────────────────────────────────────────────────┘     │
│                          ▲                                   │
│                          │ callbacks are invoked here         │
│   ┌──────────────────────┴─────────────────────────────┐     │
│   │  EVENT LOOP (libuv)                                │     │
│   │   timers → pending → idle/prepare → poll → check    │     │
│   │   → close callbacks → (microtasks between phases)   │     │
│   └──────────────────────┬─────────────────────────────┘     │
└──────────────────────────┼───────────────────────────────────┘
                           │
        ┌──────────────────┴───────────────────┐
        ▼                                      ▼
┌────────────────────────┐        ┌─────────────────────────────┐
│ OS ASYNC FACILITIES    │        │ LIBUV THREAD POOL (4)       │
│ epoll / kqueue / IOCP  │        │ fs, dns.lookup, crypto,     │
│ → sockets, pipes       │        │ zlib — blocking OS APIs     │
└────────────────────────┘        └─────────────────────────────┘
```

The crucial insight: **the loop itself is not a thread doing work.** It is a scheduler. The waiting
happens in the OS kernel (for sockets) or in libuv's thread pool (for APIs the kernel cannot do
asynchronously). Your JavaScript — the callbacks — is what runs on the single main thread.

---

## 2. The phases of the event loop

Each iteration ("tick") of the loop goes through these phases in order:

```text
   ┌───────────────────────────────────────────────────────────────┐
   │ 1. TIMERS                                                     │
   │    run callbacks whose setTimeout/setInterval time has elapsed │
   ├───────────────────────────────────────────────────────────────┤
   │ 2. PENDING CALLBACKS                                          │
   │    deferred system callbacks (e.g. TCP errors from the last   │
   │    iteration)                                                 │
   ├───────────────────────────────────────────────────────────────┤
   │ 3. IDLE / PREPARE   (internal use)                            │
   ├───────────────────────────────────────────────────────────────┤
   │ 4. POLL                                                       │
   │    retrieve new I/O events; run I/O callbacks (fs, network)    │
   │    BLOCKS here if there is nothing else to do (waiting for    │
   │    incoming connections/data)                                 │
   ├───────────────────────────────────────────────────────────────┤
   │ 5. CHECK                                                      │
   │    run setImmediate() callbacks                               │
   ├───────────────────────────────────────────────────────────────┤
   │ 6. CLOSE CALLBACKS                                            │
   │    e.g. socket.on('close')                                    │
   └───────────────────────────────────────────────────────────────┘
              │
              └──▶ back to 1 (or exit if nothing is left)

   MICROTASKS run between EVERY phase and after EVERY callback:
      process.nextTick queue  (highest priority)
      promise microtask queue (then/catch/finally/await continuations)
```

### Phase-by-phase, with what actually schedules work into each

| Phase | What runs | Scheduled by | Notes |
| --- | --- | --- | --- |
| **Timers** | Timers whose time has elapsed | `setTimeout`, `setInterval` | Delays are minimums, not guarantees |
| **Pending callbacks** | Deferred system callbacks | TCP errors, some `fs` completion | Rarely relevant in application code |
| **Idle/prepare** | libuv internals | — | Not user-visible |
| **Poll** | I/O callbacks; blocks waiting for events when the queue is empty | sockets, files, DNS results | Where the process idles |
| **Check** | `setImmediate` callbacks | `setImmediate` | Always after the poll phase |
| **Close** | `close` event handlers | `socket.destroy()`, stream cleanup | Cleanup logic |
| *(between phases)* | Microtasks | `Promise.then`, `await`, `queueMicrotask`, `process.nextTick` | Drained completely before continuing |

> **Internally:** if the poll queue is empty and there are no timers or immediates pending, libuv
> blocks in `epoll_wait`/`kevent`/`GetQueuedCompletionStatus` — this is the "idle" state, and it
> consumes no CPU. That is why a Node server with 10,000 open connections shows ~0% CPU until a
> request arrives. When a socket becomes readable, the kernel wakes the loop and the callback runs.

---

## 3. Microtasks: `nextTick` and promises

Two queues that run outside the phase structure, in this priority order:

```text
1. process.nextTick queue          ← highest priority
2. Promise microtask queue         ← then/catch/finally, await continuations, queueMicrotask
```

Both are **drained completely** before the loop proceeds to the next phase. And callbacks added
while draining are also processed — which is the mechanism behind starvation (§5).

```js
// File: microtask-order.mjs
import { setTimeout as sleep } from 'node:timers/promises';

console.log('1: sync');

process.nextTick(() => console.log('2: nextTick'));
Promise.resolve().then(() => console.log('3: promise'));
queueMicrotask(() => console.log('4: queueMicrotask'));
setTimeout(() => console.log('5: setTimeout 0'), 0);
setImmediate(() => console.log('6: setImmediate'));

await sleep(10);
console.log('7: end');
```

```text
1: sync
2: nextTick
3: promise
4: queueMicrotask
5: setTimeout 0
6: setImmediate
7: end
```

(Caveat: `5` and `6` can swap at the top level of the main module — see §4. Everything before them is
deterministic.)

### Where `nextTick` fits in real code

`process.nextTick` exists to let an API call its callback *after* the current operation completes but
*before* I/O — historically the tool for making APIs consistently asynchronous.

```js
// File: nexttick-use.mjs
// The classic correct use: guarantee the callback is asynchronous,
// even when the result is available immediately (avoids releasing Zalgo).
function safeLookup(cache, key, callback) {
  if (Object.hasOwn(cache, key)) {
    // Without nextTick, the callback would run synchronously here — and code that
    // works when the value is cached would break when it is not.
    process.nextTick(callback, null, cache[key]);
    return;
  }
  setTimeout(() => callback(null, 'loaded from disk'), 10);
}

const cache = { a: 1 };

console.log('before');
safeLookup(cache, 'a', (error, value) => console.log('callback (cached):', value));
console.log('after');

setTimeout(() => {
  console.log('before (uncached)');
  safeLookup(cache, 'b', (error, value) => console.log('callback (uncached):', value));
  console.log('after (uncached)');
}, 30).unref();

await new Promise((resolve) => setTimeout(resolve, 60));
```

```text
before
after
callback (cached): 1
before (uncached)
after (uncached)
callback (uncached): loaded from disk
```

**Modern guidance:** prefer `queueMicrotask` for "run this after the current operation" in new code;
`nextTick` remains common in libraries and is subtly faster. Both starve the loop if abused.

---

## 4. `setTimeout(…, 0)` vs `setImmediate()` vs `setTimeout(…, 1)`

```js
// File: timer-vs-immediate.mjs
import { readFile } from 'node:fs/promises';

// ---- Case 1: top level (NON-DETERMINISTIC ORDER) ----
setTimeout(() => console.log('A: setTimeout 0'), 0);
setImmediate(() => console.log('B: setImmediate'));
console.log('C: sync');

// ---- Case 2: inside an I/O callback (DETERMINISTIC) ----
await readFile('./package.json', 'utf8');
console.log('D: inside the I/O continuation');

setTimeout(() => console.log('E: setTimeout 0 (inside I/O)'), 0);
setImmediate(() => console.log('F: setImmediate (inside I/O)'));
```

```text
C: sync
A: setTimeout 0      ← order of A and B varies between runs at the top level
B: setImmediate
D: inside the I/O continuation
F: setImmediate (inside I/O)     ← ALWAYS before E
E: setTimeout 0 (inside I/O)
```

**Why case 1 is non-deterministic:** at startup, the process has to reach the timers phase within 1ms
for the 0ms timer to fire on the first pass. Sometimes it does, sometimes it does not, depending on
machine speed. Never rely on it.

**Why case 2 is deterministic:** we are inside the poll phase (the I/O callback). The next phase is
**check**, which runs `setImmediate` — the timer has to wait until the loop comes back around to the
timers phase.

| Mechanism | Runs in | Ordering guarantee |
| --- | --- | --- |
| `process.nextTick` | Before anything else | First |
| Promise continuations | Microtasks | After nextTick, before timers |
| `setTimeout(fn, 0)` | Timers phase | Not before the next timers phase; ≥1ms effectively |
| `setImmediate(fn)` | Check phase | After the current poll phase |
| `setTimeout(fn, 1)` | Timers phase | Same bucket as 0 in practice |

**Practical rule:** use `setImmediate` when you want "after the current I/O work, before timers" — for
example yielding to let a response flush before doing more CPU work.

---

## 5. Starvation: how to freeze your server

Because microtask queues are drained completely, an unbounded chain of microtasks prevents the loop
from ever reaching timers or I/O.

```js
// File: starvation.mjs
// ⚠️ This intentionally demonstrates a bug. It will make the timer fire very late.
const start = process.hrtime.bigint();
let iterations = 0;

setTimeout(() => {
  const elapsedMs = Number(process.hrtime.bigint() - start) / 1e6;
  console.log(`timer scheduled for 0ms fired after ${elapsedMs.toFixed(0)}ms`);
  console.log(`nextTick callbacks executed first: ${iterations}`);
}, 0);

function recursiveNextTick() {
  iterations += 1;
  if (iterations < 1_000_000) {
    process.nextTick(recursiveNextTick);     // always adds to the front of the same queue
  }
}

recursiveNextTick();
```

```text
timer scheduled for 0ms fired after 412ms
nextTick callbacks executed first: 1000000
```

The timer was ready ~1ms after scheduling, but the loop never reached the timers phase. **A recursive
`nextTick` (or a promise chain that always creates another microtask) is an infinite loop that does
not look like one.**

The same class of bug, in realistic code:

```js
// File: starve-realistic.mjs
import { setTimeout as sleep } from 'node:timers/promises';

// ❌ Re-processing inside a microtask keeps the loop busy indefinitely.
async function processQueueBad(items) {
  if (items.length === 0) return;
  const [first, ...rest] = items;
  // …process first…
  return processQueueBad(rest);        // recursion through async = chained microtasks
}

// ✅ Yield to the event loop between batches so timers and I/O can run.
async function processQueueGood(items, { batchSize = 100 } = {}) {
  for (let index = 0; index < items.length; index += batchSize) {
    const batch = items.slice(index, index + batchSize);
    for (const item of batch) {
      // …process item…
      void item;
    }
    // setImmediate yields to the loop (macrotask), unlike a microtask.
    await new Promise((resolve) => setImmediate(resolve));
  }
}

const items = Array.from({ length: 1000 }, (_, i) => i);
const timerFired = {};
setTimeout(() => {
  timerFired.ok = true;
}, 5);

await processQueueGood(items);
await sleep(20);
console.log('timer fired while processing:', Boolean(timerFired.ok));
console.log('bad version items:', (await processQueueBad([])) === undefined ? 'done' : 'done');
```

### The four things that block the loop

| Blocker | Example | Fix |
| --- | --- | --- |
| **Synchronous I/O** | `readFileSync`, `execSync` | Async equivalents |
| **CPU-bound JavaScript** | big `JSON.parse`, image processing, crypto loops, catastrophic regex | Worker thread, child process, or a queue |
| **Unbounded microtask chains** | recursive `nextTick`, chained promises in a tight loop | Yield with `setImmediate` between batches |
| **Blocking third-party code** | a library that does the above internally | Audit it, or move it off the request path |

---

## 6. Measuring it: event-loop lag

You cannot fix what you do not measure. Event-loop lag is the single most useful health metric for a
Node service.

```js
// File: event-loop-monitor.mjs
import { monitorEventLoopDelay, performance } from 'node:perf_hooks';
import { setTimeout as sleep } from 'node:timers/promises';

const histogram = monitorEventLoopDelay({ resolution: 20 });
histogram.enable();

/** Report lag and alert when the loop is struggling. */
function reportLag(label) {
  const p50 = histogram.percentile(50) / 1e6;
  const p99 = histogram.percentile(99) / 1e6;
  const max = histogram.max / 1e6;
  console.log(
    `${label.padEnd(28)} p50=${p50.toFixed(1)}ms p99=${p99.toFixed(1)}ms max=${max.toFixed(1)}ms`
  );
  histogram.reset();
}

await sleep(200);
reportLag('idle');

// A blocking operation: 300ms of synchronous CPU work.
const start = performance.now();
while (performance.now() - start < 300) {
  /* busy-wait, exactly like a synchronous JSON.parse of a large payload */
}

await sleep(200);
reportLag('after 300ms of blocking work');

histogram.disable();
```

```text
idle                         p50=20.2ms p99=20.4ms max=21.0ms
after 300ms of blocking work p50=20.3ms p99=120.2ms max=321.7ms
```

In production you export these numbers to your metrics system and alert on p99 lag (a useful
threshold is 100ms — beyond that, users are noticing). This is also the metric that distinguishes "the
database is slow" (lag stays low; your request waits on I/O) from "my code is blocking" (lag spikes).

---

## 7. The libuv thread pool: the trap nobody teaches

Sockets are handled by the OS asynchronously — **no thread is consumed while waiting**. But some
operations cannot be done that way portably, so libuv uses a **thread pool of 4 threads by default**
for:

- `fs` operations (all of them: read, write, stat, …)
- `dns.lookup` (the system resolver, unlike `dns.resolve*` which uses the network)
- `crypto.pbkdf2`, `crypto.scrypt`, `crypto.randomBytes` (asynchronously)
- `zlib` compression/decompression

**The pool is a shared, limited resource. Four is small.**

```js
// File: threadpool.mjs
import { pbkdf2 } from 'node:crypto';
import { promisify } from 'node:util';
import { performance } from 'node:perf_hooks';

const pbkdf2Async = promisify(pbkdf2);

/** Simulate one password hash — real bcrypt/argon2 work runs in this same pool. */
const hashPassword = (id) =>
  pbkdf2Async(`password-${id}`, 'salt-value', 300_000, 64, 'sha512').then(
    (derived) => derived.length
  );

async function measureParallel(count) {
  const start = performance.now();
  const results = await Promise.all(Array.from({ length: count }, (_, i) => hashPassword(i)));
  const elapsed = performance.now() - start;
  console.log(
    `${count} hashes in parallel: ${elapsed.toFixed(0)}ms  (${results.length} completed)`
  );
  return elapsed;
}

console.log('UV_THREADPOOL_SIZE =', process.env.UV_THREADPOOL_SIZE ?? '4 (default)');
const four = await measureParallel(4);      // fits the pool: run truly in parallel
const eight = await measureParallel(8);     // two waves: the second 4 wait

console.log(`\n8 hashes took ${(eight / four).toFixed(2)}× as long as 4 hashes`);
console.log('with infinite threads it would be ~1.0×; with 4 threads it is ~2.0×');
```

```text
UV_THREADPOOL_SIZE = 4 (default)
4 hashes in parallel: 214ms
8 hashes in parallel: 428ms

8 hashes took 2.00× as long as 4 hashes
with infinite threads it would be ~1.0×; with 4 threads it is ~2.0×
```

### Why this matters in production

Realistic consequences of a 4-thread pool under load:

| Workload | Effect |
| --- | --- |
| 100 concurrent password resets (bcrypt in the pool) | The 5th onwards queue behind the first four; p99 latency explodes |
| Password hashing + file uploads to disk | They compete for the same 4 threads |
| `zlib` compressing JSON responses | Compression now delays unrelated file reads |

```bash
# Raise the pool — and understand what you are trading:
UV_THREADPOOL_SIZE=16 node src/server.js
```

Things to know about raising it:

- It helps I/O-ish work (file reads, hashing) up to the point where the CPU is saturated.
- The pool threads are **not** for your JavaScript. They do not make your code faster; they make more
  concurrent *blocking-native* operations possible.
- bcrypt/argon2 (native modules) often maintain their own thread usage — check the library.
- More threads means more context switching and memory; measure rather than guessing.
- `dns.lookup` using the pool is why, under heavy load, DNS resolution can queue behind file reads.
  `dns.resolve4()` (which performs real DNS queries over the network) bypasses the pool.

---

## 8. Using all your CPU cores: four options

Node uses one core per process. To use more:

| Approach | Isolation | Memory | Best for |
| --- | --- | --- | --- |
| **`cluster` module** | Separate processes, shared port | Highest (full V8 per process) | Scaling a web server across cores |
| **Process manager (PM2, systemd, Docker replicas)** | Separate processes | High | Production deployments — clearer and more observable than `cluster` |
| **`worker_threads`** | Threads in one process, separate V8 isolates | Lower | CPU-bound work inside an app (image resize, parsing, crypto) |
| **A separate service / queue** | Full separation | Independent | Heavy or bursty work (video encoding, report generation) |

### `cluster` — one port, many processes

```js
// File: cluster-example.mjs
import cluster from 'node:cluster';
import { availableParallelism } from 'node:os';
import { createServer } from 'node:http';

const WORKERS = Number(process.env.WEB_CONCURRENCY ?? availableParallelism());

if (cluster.isPrimary) {
  console.log(`primary ${process.pid} forking ${WORKERS} workers`);

  for (let i = 0; i < WORKERS; i += 1) cluster.fork();

  // Restart a worker that dies — this is the supervision value of cluster.
  cluster.on('exit', (worker, code, signal) => {
    console.warn(`worker ${worker.process.pid} died (${signal ?? code}); forking a replacement`);
    cluster.fork();
  });
} else {
  // Each worker listens on the SAME port; the primary distributes connections.
  createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ pid: process.pid, url: req.url }));
  }).listen(3000, '0.0.0.0', () => {
    console.log(`worker ${process.pid} listening on 3000`);
  });
}
```

```bash
for i in $(seq 1 6); do curl -s localhost:3000/ ; echo; done
# {"pid":41201,"url":"/"}   ← different pids: the load is spread across processes
# {"pid":41202,"url":"/"}
# …
```

Each worker is a full Node process: separate memory, separate event loop, no shared state. **That is
the point and the problem** — in-memory caches, sessions and rate-limit counters are no longer
shared, which is why Redis exists in the stack
(03-databases/05-redis/01-redis-basics.md *(not available in this published source revision)*).

> **In production today**, most teams let the platform do this: Kubernetes replicas, `docker compose
> --scale`, ECS tasks, or PM2's cluster mode. It is the same idea with better tooling around
> restarts, logs and rolling deploys.

### `worker_threads` — CPU work without blocking

```js
// File: worker-example.mjs
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';

if (isMainThread) {
  /**
   * A CPU-bound task: counting primes below `limit`.
   * Running this on the main thread blocks the event loop; in a worker it does not.
   */
  const countPrimesBelow = (limit) => {
    let count = 0;
    for (let candidate = 2; candidate < limit; candidate += 1) {
      let isPrime = true;
      for (let divisor = 2; divisor * divisor <= candidate; divisor += 1) {
        if (candidate % divisor === 0) {
          isPrime = false;
          break;
        }
      }
      if (isPrime) count += 1;
    }
    return count;
  };

  // Keep a heartbeat running to prove whether the loop is responsive.
  let heartbeats = 0;
  const heartbeat = setInterval(() => {
    heartbeats += 1;
  }, 20);

  // 1. On the main thread: the loop is frozen for the duration.
  let start = performance.now();
  const syncCount = countPrimesBelow(300_000);
  console.log(`main thread : ${(performance.now() - start).toFixed(0)}ms, ${heartbeats} heartbeats`);

  // 2. In a worker: the loop keeps running.
  heartbeats = 0;
  start = performance.now();
  const workerCount = await new Promise((resolve, reject) => {
    const worker = new Worker(fileURLToPath(import.meta.url), {
      workerData: { limit: 300_000 },
    });
    worker.on('message', resolve);
    worker.on('error', reject);
  });
  console.log(`worker      : ${(performance.now() - start).toFixed(0)}ms, ${heartbeats} heartbeats`);
  console.log('results agree:', syncCount === workerCount, `(${workerCount} primes)`);

  clearInterval(heartbeat);
} else {
  // Worker side: this runs on its own thread with its own V8 isolate.
  const { limit } = workerData;

  let count = 0;
  for (let candidate = 2; candidate < limit; candidate += 1) {
    let isPrime = true;
    for (let divisor = 2; divisor * divisor <= candidate; divisor += 1) {
      if (candidate % divisor === 0) {
        isPrime = false;
        break;
      }
    }
    if (isPrime) count += 1;
  }

  parentPort.postMessage(count);
}
```

Expected shape of the output:

```text
main thread : 190ms, 0 heartbeats      ← the event loop was frozen the whole time
worker      : 205ms, 9 heartbeats      ← same work, loop still alive
results agree: true (25997 primes)
```

That is the trade-off in one output: the worker is slightly *slower* for this single task (thread
startup + message passing), but the server stays responsive. **Workers buy responsiveness, not raw
speed** — they are for keeping the loop free, not for making a computation faster.

For real workloads, use a **worker pool** rather than creating a worker per request:
`piscina` is the standard library for this.

---

## 9. A complete mental model, in interview-ready form

> "Node.js runs JavaScript on a single thread. Asynchronous operations are delegated to the operating
> system (for sockets, via epoll/kqueue/IOCP) or to libuv's thread pool (4 threads by default, for
> filesystem, DNS lookup, crypto and zlib). The event loop iterates through phases — timers, pending
> callbacks, poll (where I/O callbacks run and where the loop blocks when idle), check
> (setImmediate), close callbacks — running microtasks (process.nextTick first, then promise
> callbacks) between phases and after each callback. Because there is one thread, any synchronous
> CPU work or blocking I/O delays every other request, so CPU-bound work is moved to worker threads,
> child processes, or a queue, and horizontal scaling uses multiple processes via cluster or the
> deployment platform."

If you can say that, plus explain why `setImmediate` beats `setTimeout(…, 0)` inside an I/O callback,
and why 5 concurrent bcrypt hashes are slower than 4, you can answer essentially every event-loop
interview question.

---

## 10. Common mistakes

| Mistake | Consequence | Fix |
| --- | --- | --- |
| Blocking I/O in a handler (`readFileSync`, `execSync`) | Every concurrent request stalls | Async APIs |
| CPU-heavy work in the request path | Freezes the loop; all endpoints slow | Worker thread / queue |
| Assuming `setTimeout(fn, 0)` runs immediately | Ordering bugs; races | Use `setImmediate` or explicit promise sequencing |
| Relying on timer ordering at the top level | Non-deterministic tests | Assert on outcomes, not relative timer order |
| Unbounded microtask recursion | Starvation; timers never fire | Yield with `setImmediate`/`setTimeout` between batches |
| Assuming the thread pool is infinite | Unexplained latency under auth load | Raise `UV_THREADPOOL_SIZE`; measure; consider a queue |
| Expecting `cluster` workers to share state | Sessions/caches silently diverge | Externalise state to Redis |
| Creating a worker per request | Thread-creation overhead dominates | Worker pool (`piscina`) |
| Using `process.nextTick` for "later" | Higher priority than intended → starvation | `setImmediate` for "later", `queueMicrotask` for "after this" |
| No event-loop-lag metric | You find out from users | `monitorEventLoopDelay` → metrics + alerts |
| Blocking in a health check | The orchestrator sees timeouts and kills the pod | Keep health checks trivial |

---

## Exercise 14.1 — Explain the difference

For each pair, state the ordering guarantee (deterministic or not) and why:

1. `setTimeout(fn, 0)` vs `setImmediate(fn)` — at the top level of `index.js`.
2. The same two — inside a `fs.readFile` callback.
3. `Promise.resolve().then(fn)` vs `process.nextTick(fn)`.
4. `await somePromise` vs `somePromise.then(fn)`.

<details>
<summary>Solution</summary>

**1. Top level: non-deterministic.**
The main module is executed, then the loop enters the timers phase. Whether the 0ms timer is "due"
by the time the loop gets there depends on how long process startup and module evaluation took. If it
is due, the timer runs first; otherwise the loop proceeds to poll and then check, and `setImmediate`
runs first. On a fast machine you will see both orders across runs.

**2. Inside an I/O callback: deterministic — `setImmediate` first.**
The I/O callback runs during the **poll** phase. The next phase is **check**, which drains
`setImmediate` callbacks. The timer must wait until the loop wraps around to the **timers** phase. So
`setImmediate` always wins here.

**3. `process.nextTick` first — always.**
The `nextTick` queue is processed before the promise microtask queue. Node drains `nextTick` entirely,
then promises, then continues. (This is why libraries use `nextTick` to be "as soon as possible"
and why abusing it starves everything else.)

**4. They are equivalent in ordering — both schedule a microtask.**
`await p` is (conceptually) `p.then(continuation)`, and the continuation runs as a microtask when `p`
settles. Differences are ergonomic, not semantic: `await` suspends the current function and integrates
with `try/catch`, whereas `.then` returns a new promise. One practical difference: `await` on a
non-promise value still yields for one microtask tick (`await null`), and an *already resolved*
promise's `.then` also runs as a microtask — both asynchronous, never synchronous.

</details>

## Exercise 14.2 — Diagnose and fix

A user reports: "The file-upload endpoint works fine, but whenever someone uploads a 50 MB CSV, the
entire API becomes unresponsive for about 4 seconds, including the health check." CPU is saturated on
one core during the freeze.

Identify the three most likely causes in the code and give a fix for each, with the trade-offs.

<details>
<summary>Solution</summary>

**Likely causes, in order of probability**

1. **The body is buffered into memory and parsed synchronously.**
   `express.raw({ type: 'text/csv', limit: '100mb' })` or `express.text()` collects the whole 50 MB
   into a Buffer, then code does `req.body.toString().split('\n')` — creating a 50 MB string and an
   array of hundreds of thousands of strings, **on the main thread**, blocking everything.
2. **Synchronous CSV parsing or validation loop.**
   Even if reading is streamed, `csv-parse`'s sync mode, `for` loops over 500k rows, `JSON.parse` per
   row, or an expensive per-row regex will block. Catastrophic regex backtracking would look the same
   and is a DoS vector.
3. **Synchronous file writes or a synchronous database driver.**
   `writeFileSync` per row, `appendFileSync` in a loop, or a sync SQLite/OR driver. Each call blocks
   while the kernel works.
4. *(bonus)* **Unbounded insert loop with `Promise.all` over 500k rows** — this does not block the
   loop, but it will exhaust the connection pool and memory, producing a different but equally
   severe incident.

**Fixes and trade-offs**

| Fix | How | Trade-off |
| --- | --- | --- |
| **Stream the upload to disk** | `pipeline(req, createWriteStream(tmpPath))` — never hold it in memory | You need a temp-file lifecycle (cleanup on failure, disk space limits) |
| **Stream-parse the CSV** | `csv-parse` with `for await (const row of parser)`, batching inserts (e.g. 1,000 rows) | More code; you must handle partially-imported files and malformed rows |
| **Do the work asynchronously** | Respond `202 Accepted` with a job id; a worker process does the import; the client polls or receives a webhook | Requires a queue (Redis/BullMQ) and a status endpoint — real architectural work |
| **Bound the work** | Cap the row count and file size; reject with `413`/`422` beyond it | Users must split large files |
| **Increase the thread pool** | `UV_THREADPOOL_SIZE=16` for the fs/crypto parts | Only helps native/blocking work; CPU-bound JS is unaffected |
| **Move CPU work to a worker thread** | `worker_threads` for parsing/validation | Complexity; message-passing overhead; needs a pool (`piscina`) |

**The recommended answer (what a senior engineer would do):**

1. **Immediately:** stream the upload to a temp file and stream-parse it with batched inserts, so memory
   stays bounded and the loop is never blocked. This alone fixes the reported symptom for reasonable
   files.
2. **For large or bursty imports:** make the endpoint asynchronous — accept the upload, enqueue a job,
   return `202` with a status URL. The HTTP request becomes short and predictable regardless of file
   size; the worker can be scaled independently and retried safely.
3. **Always:** bound the input (max size and rows), set timeouts, and add an event-loop-lag metric so
   this class of incident is detected before users report it.

**Why the health check is the tell:** a health check does essentially no work. If it is slow, the
delay is not in the request's own logic — the process is blocked. That single observation is what
should send you looking for synchronous, main-thread work rather than at the database.

</details>

---

## What's next

Now you know how Node runs. Next: how to configure a Node application for different environments —
`process.env`, `.env` files, defaults, validation and secrets, which is the difference between code
that only runs on your laptop and code that deploys.

→ [15 — Environment Variables](15-environment-variables.md)
