# 08 — Events and EventEmitter

> **Where this fits:** Node calls itself "event-driven". This chapter explains what that actually means in code: the `EventEmitter` class, how listeners work, and why you care. Every server, socket, stream and database connection you use is an EventEmitter underneath — and `EventEmitter` is the foundation of the observer pattern you will use for your own modules.

***

## 1. What is an event?

An **event** is "something happened". A **listener** is a function that runs when it does.

```
Something happens                    Your code reacts
─────────────────                    ────────────────
a request arrives          →         route handler runs
data arrives on a socket   →         'data' listener appends to a buffer
a file finishes reading    →         callback runs
a timer fires              →         callback runs
an error occurs            →         'error' listener handles it (or the process crashes)
a user signs up            →         'user:registered' listener sends a welcome email
```

Instead of writing a loop that constantly asks "has anything happened yet?" (**polling**), you register functions and Node calls them (**inversion of control**). That is the essence of the event-driven model, and it is why Node uses almost no CPU while waiting for thousands of idle connections.

***

## 2. `EventEmitter` — the base class

`node:events` exports `EventEmitter`. You create an emitter with `.on()`, fire with `.emit()`.

```js
// File: first-emitter.mjs
import { EventEmitter } from 'node:events';

const emitter = new EventEmitter();

// Register a listener (also called a handler or subscriber).
emitter.on('order:created', (order) => {
  console.log(`[email] sending confirmation for order ${order.id}`);
});

// Multiple listeners for the same event — all of them run, in registration order.
emitter.on('order:created', (order) => {
  console.log(`[analytics] order ${order.id} worth ${order.total} recorded`);
});

// Emit: "this happened" — synchronously calls every listener in order.
emitter.emit('order:created', { id: 'o_1042', total: 4999 });

console.log('emit() returned — all listeners have already run');
```

```
[email] sending confirmation for order o_1042
[analytics] order o_1042 worth 4999 recorded
emit() returned — all listeners have already run
```

The last line is important: **`emit` is synchronous.** Listeners run before `emit` returns. In practice you rarely rely on that, but it explains ordering bugs and why a slow listener delays everything after it.

### The API

```js
// File: emitter-api.mjs
import { EventEmitter } from 'node:events';

const emitter = new EventEmitter();

const onMessage = (msg) => console.log('A received:', msg);
const onceOnly = (msg) => console.log('B (once) received:', msg);

emitter.on('message', onMessage);        // runs every time
emitter.once('message', onceOnly);       // runs at most once
emitter.prependListener('message', (m) => console.log('C (prepended) first:', m));

emitter.emit('message', 'first');
emitter.emit('message', 'second');

// Removing listeners
emitter.off('message', onMessage);        // alias: removeListener
console.log('listener count:', emitter.listenerCount('message'));

// Introspection
console.log('event names:', emitter.eventNames());
console.log('max listeners:', emitter.getMaxListeners());

// Removing everything (careful — this also removes listeners you did not add)
emitter.removeAllListeners('message');
```

```
C (prepended) first: first
A received: first
B (once) received: first
C (prepended) first: second
A received: second
listener count: 2
```

### Full API reference

| Method                                              | Purpose                                                              |
| --------------------------------------------------- | -------------------------------------------------------------------- |
| `on(name, fn)`                                      | Add a listener (fires every time)                                    |
| `once(name, fn)`                                    | Add a listener that removes itself after the first call              |
| `prependListener(name, fn)` / `prependOnceListener` | Add to the front of the queue                                        |
| `off(name, fn)` / `removeListener`                  | Remove a specific listener (must be the **same function reference**) |
| `removeAllListeners([name])`                        | Remove all listeners for an event, or all events                     |
| `emit(name, ...args)`                               | Invoke every listener for `name`, passing the args                   |
| `listenerCount(name)`                               | How many listeners are registered                                    |
| `listeners(name)` / `rawListeners(name)`            | Get the listener functions                                           |
| `eventNames()`                                      | Array of event names that have listeners                             |
| `setMaxListeners(n)` / `getMaxListeners()`          | Control the leak warning threshold                                   |
| `addAbortListener(signal, fn)`                      | Node 20+: listener that auto-removes when an `AbortSignal` aborts    |

***

## 3. The `'error'` event — special and dangerous

`'error'` is the one event name with built-in behaviour:

> **If you `emit('error')` and no `'error'` listener is registered, Node throws the error.**

That turns a misconfigured listener into a process crash. It is deliberate: an unhandled error must never be swallowed silently.

```js
// File: error-event.mjs
import { EventEmitter } from 'node:events';

const emitter = new EventEmitter();

// ❌ Without an error listener, this throws:
try {
  emitter.emit('error', new Error('no listener attached'));
} catch (error) {
  console.log('caught from emit:', error.message);
}

// ✅ With a listener, the error is delivered to it and emit() returns normally.
emitter.on('error', (error) => {
  console.error('[error listener]', error.message);
});

emitter.emit('error', new Error('handled cleanly'));
console.log('still running');
```

```
caught from emit: no listener attached
[error listener] handled cleanly
still running
```

Every object you create that extends `EventEmitter` should document its error events, and every consumer should attach an `'error'` listener. A forgotten `'error'` listener on a database connection or an HTTP request is one of the most common causes of crashes in Node services.

### `captureRejections` — async listeners that throw

By default, if an `async` listener rejects, you get an unhandled rejection. `captureRejections` converts that into an `'error'` event:

```js
// File: capture-rejections.mjs
import { EventEmitter, captureRejections } from 'node:events';

const emitter = new EventEmitter({ captureRejections: true });

emitter.on('message', async () => {
  throw new Error('async listener failed');
});

emitter.on('error', (error) => {
  console.log('[error event]', error.message);  // async listener failed
});

emitter.emit('message', 'hello');

// The decorator form for classes:
class Service extends EventEmitter {
  constructor() {
    super({ captureRejections: true });
  }
}
console.log(typeof captureRejections); // 'symbol' — used internally by the class decorator
```

### `events.once()` and `events.on()` — promises from events

Two utilities turn events into promises, which makes them composable with `async`/`await`:

```js
// File: events-promises.mjs
import { EventEmitter, once, on } from 'node:events';

const emitter = new EventEmitter();

// once(): resolves with the next emission's arguments, REJECTS on 'error'.
setTimeout(() => emitter.emit('ready', { port: 3000 }), 50);
const [payload] = await once(emitter, 'ready');
console.log('ready with port:', payload.port);

// Useful pattern: wait for a server to start listening.
import { createServer } from 'node:http';
const server = createServer();
server.listen(0, '127.0.0.1');
await once(server, 'listening');
console.log('server bound to port', server.address().port);
server.close();

// on(): an async iterator over every emission — the cleanest way to consume a stream of events.
const emitter2 = new EventEmitter();
let received = 0;
setTimeout(() => {
  emitter2.emit('tick', 1);
  emitter2.emit('tick', 2);
  emitter2.emit('tick', 3);
  emitter2.emit('stop');
}, 10);

for await (const [value] of on(emitter2, 'tick')) {
  received += 1;
  console.log('tick', value);
  if (received === 3) break;   // iterators must be broken out of, or they wait forever
}
```

***

## 4. Memory leaks: the MaxListeners warning

```
MaxListenersExceededWarning: Possible EventEmitter memory leak detected.
11 message listeners added to [EventEmitter]. MaxListeners is 10.
Use emitter.setMaxListeners() to increase limit
```

This warning is one of Node's most valuable diagnostics. It usually means one of:

1. **You add a listener inside a function that runs repeatedly** (a request handler, a loop) without removing it. Each call adds one more, and old ones are never garbage-collected because the emitter still references them.
2. **You created a new emitter per operation and never released it** — often a connection or client created per request instead of once.
3. **A legitimate fan-out** (a "bus" with 50 subscribers) — in which case raise the limit deliberately _and document why_.

```js
// File: leak-demo.mjs
import { EventEmitter } from 'node:events';

const bus = new EventEmitter();

// ❌ Classic leak: a new listener per simulated request, never removed.
function handleRequestBad(id) {
  bus.on('config:reloaded', () => console.log(`request ${id} reacting to reload`));
}

for (let i = 0; i < 12; i += 1) handleRequestBad(i);
// → MaxListenersExceededWarning after the 11th
console.log('bad listener count:', bus.listenerCount('config:reloaded'));

// ✅ Fix 1: remove the listener when the work is done.
const bus2 = new EventEmitter();
function handleRequestGood(id) {
  const react = () => console.log(`request ${id} reacting to reload`);
  bus2.once('config:reloaded', react);      // auto-removes after firing
  // …and if the request can finish first, remove it explicitly:
  // bus2.off('config:reloaded', react);
}
for (let i = 0; i < 12; i += 1) handleRequestGood(i);
console.log('good listener count:', bus2.listenerCount('config:reloaded')); // 12 (but transient)

// ✅ Fix 2: attach ONE listener for the process, not one per request/connection.
bus2.setMaxListeners(100);                   // deliberate, documented
console.log('max listeners raised to:', bus2.getMaxListeners());
```

| Symptom                               | Usual cause                               | Fix                                   |
| ------------------------------------- | ----------------------------------------- | ------------------------------------- |
| Warning grows over time, memory grows | Listener added per request/iteration      | `once`, `off`, or one shared listener |
| Warning appears at startup            | Many independent subscribers legitimately | `setMaxListeners(n)` with a comment   |
| Warning plus `EMFILE`                 | Sockets/clients created per request       | Reuse a single client/pool            |

***

## 5. Extending `EventEmitter` — your own event-driven classes

```js
// File: job-queue.mjs
import { EventEmitter } from 'node:events';

/**
 * A tiny in-memory job queue that announces what it is doing.
 *
 * Events:
 *   'job:queued'    (job)            — a job was added
 *   'job:started'   (job)            — processing began
 *   'job:completed' (job, result)    — finished successfully
 *   'job:failed'    (job, error)     — threw
 *   'drained'       ()               — queue is empty and idle
 *   'error'         (error)          — emitter-level failure (never emitted silently)
 */
export class JobQueue extends EventEmitter {
  #queue = [];
  #running = 0;
  #concurrency;

  constructor({ concurrency = 2 } = {}) {
    super();
    this.#concurrency = concurrency;
  }

  get size() {
    return this.#queue.length;
  }

  get running() {
    return this.#running;
  }

  add(job) {
    if (!job || typeof job.run !== 'function') {
      // Programmer error: throw synchronously rather than emitting 'error',
      // because it is not an operational failure.
      throw new TypeError('job must be an object with a run() function');
    }
    this.#queue.push(job);
    this.emit('job:queued', job);
    this.#process();
    return this;
  }

  async #process() {
    while (this.#running < this.#concurrency && this.#queue.length > 0) {
      const job = this.#queue.shift();
      this.#running += 1;
      this.emit('job:started', job);

      // Run each job in its own async context so one failure cannot stop the queue.
      this.#runOne(job).finally(() => {
        this.#running -= 1;
        if (this.#queue.length === 0 && this.#running === 0) this.emit('drained');
        else this.#process();
      });
    }
  }

  async #runOne(job) {
    try {
      const result = await job.run();
      this.emit('job:completed', job, result);
    } catch (error) {
      // Operational failure: emit 'error' ONLY if someone is listening.
      // Otherwise emit a specific event the caller can subscribe to.
      if (this.listenerCount('error') > 0) this.emit('error', error, job);
      this.emit('job:failed', job, error);
    }
  }
}
```

```js
// File: queue-demo.mjs
import { JobQueue } from './job-queue.mjs';
import { once } from 'node:events';

const queue = new JobQueue({ concurrency: 2 });

queue.on('job:queued', (job) => console.log(`queued    ${job.id}`));
queue.on('job:started', (job) => console.log(`started   ${job.id}`));
queue.on('job:completed', (job, result) => console.log(`completed ${job.id} → ${result}`));
queue.on('job:failed', (job, error) => console.log(`failed    ${job.id} → ${error.message}`));

const work = (id, ms, shouldFail = false) =>
  new Promise((resolve, reject) =>
    setTimeout(() => (shouldFail ? reject(new Error('simulated failure')) : resolve(`${ms}ms`)), ms)
  );

queue.add({ id: 'j1', run: () => work('j1', 60) });
queue.add({ id: 'j2', run: () => work('j2', 40) });
queue.add({ id: 'j3', run: () => work('j3', 30, true) });
queue.add({ id: 'j4', run: () => work('j4', 20) });

await once(queue, 'drained');
console.log(`drained: ${queue.size} queued, ${queue.running} running`);
```

```
queued    j1
queued    j2
queued    j3
queued    j4
started   j1
started   j2
failed    j3
completed j2 → 40ms
completed j1 → 60ms
completed j4 → 20ms
drained: 0 queued, 0 running
```

Notice the design points that apply to every emitter you write:

| Decision                                                             | Why                                                         |
| -------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Events are past-tense nouns** (`job:completed`, not `completeJob`) | Events describe what happened; commands describe what to do |
| **Namespaced names** (`job:`, `user:`)                               | Prevents collisions in a shared emitter                     |
| **Errors are events, and documented**                                | Consumers know what to subscribe to                         |
| **Programmer errors throw synchronously**                            | A bad argument is a bug in the caller, not a runtime event  |
| **`error` only emitted when listened to**                            | Prevents an unhandled `'error'` from crashing the process   |
| **Results and errors passed as arguments**                           | No class-level mutable state needed                         |

***

## 6. Events vs callbacks vs promises

Three mechanisms for "tell me when it's done", and the right one depends on how many times it happens:

| Mechanism                 | Fires                    | Best for                                                          | Example                         |
| ------------------------- | ------------------------ | ----------------------------------------------------------------- | ------------------------------- |
| **Callback**              | Once                     | Simple, single-outcome operations                                 | `fs.readFile(path, cb)`         |
| **Promise / async-await** | Once                     | Sequential async logic, error propagation with `try/catch`        | `await readFile(path)`          |
| **EventEmitter**          | Zero, one, or many times | Things that happen repeatedly, or that several parties care about | `server.on('request')`, sockets |
| **Async iterator**        | Many times, sequentially | Processing a stream of events with backpressure and `for await`   | `readline` over a stream        |

A useful mental rule: **if it happens once, use a promise. If it happens many times, use events.** `events.once()` exists precisely to convert the second case into the first when you only need one.

***

## 7. Common mistakes

| Mistake                                                               | Consequence                                                | Fix                                                        |
| --------------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- |
| No `'error'` listener on an emitter that can fail                     | Emitting `'error'` throws and crashes the process          | Always attach, or only emit when listened to               |
| Adding a listener inside a hot path                                   | MaxListeners warning, memory leak                          | `once`, `off` in cleanup, or one shared listener           |
| Removing a listener with a different function reference               | No effect, silent leak                                     | Keep the reference: `const fn = …; on(fn); off(fn)`        |
| Assuming `emit` is async                                              | Ordering bugs, timing assumptions                          | It is synchronous; listeners run before `emit` returns     |
| Long-running work inside a listener                                   | Blocks the emitter (and, at the top level, the event loop) | Keep listeners tiny; defer heavy work                      |
| Swallowing errors in a listener                                       | Silent failures                                            | Log and re-emit, or let `captureRejections` handle it      |
| Using an emitter as a global message bus without namespacing          | Event-name collisions, spooky action                       | Namespace names and prefer per-domain emitters             |
| Forgetting that `once` still counts toward MaxListeners before firing | Warnings under load                                        | Understand the semantics; raise deliberately if legitimate |
| Emitting in a loop for 1 million items                                | CPU spent in listener bookkeeping                          | Batch, or use a stream                                     |

***

## Exercise 8.1 — Build a payment event system

Create a `PaymentService` that extends `EventEmitter` and exposes `pay({ orderId, amountCents, currency })`. It should:

* Validate input and throw a `TypeError` for programmer errors.
* Reject payments over a configurable limit with an `'payment:declined'` event and a resolved `{ status: 'declined' }` result (a declined payment is not a crash).
* Emit `'payment:succeeded'` with a transaction id on success.
* Emit `'payment:failed'` when the (simulated) provider throws, and rethrow nothing.
* Support an `'error'` listener for unexpected internal failures.
* Return a result object in all cases so it can be awaited.

Then write a demo that wires up logging, an email "sender" and an analytics "tracker", and process several payments.

<details>

<summary>Solution</summary>

```js
// File: payment-service.mjs
import { EventEmitter } from 'node:events';
import { randomUUID } from 'node:crypto';

export class PaymentService extends EventEmitter {
  #limitCents;
  #failureRate;

  constructor({ limitCents = 500_000, failureRate = 0 } = {}) {
    super({ captureRejections: true });
    this.#limitCents = limitCents;
    this.#failureRate = failureRate;
  }

  /** Simulated provider call. In a real service this would be an HTTP request with a timeout. */
  async #charge({ amountCents, currency }) {
    await new Promise((resolve) => setTimeout(resolve, 20));
    if (Math.random() < this.#failureRate) {
      throw new Error('provider timeout');
    }
    return { transactionId: `txn_${randomUUID().slice(0, 8)}`, amountCents, currency };
  }

  async pay({ orderId, amountCents, currency = 'INR' }) {
    // 1. Programmer errors: throw. These are bugs, not events.
    if (typeof orderId !== 'string' || orderId.length === 0) {
      throw new TypeError('pay() requires a non-empty orderId string');
    }
    if (!Number.isInteger(amountCents) || amountCents <= 0) {
      throw new TypeError('pay() requires amountCents to be a positive integer');
    }
    if (!/^[A-Z]{3}$/.test(currency)) {
      throw new TypeError('pay() requires a 3-letter uppercase currency code');
    }

    // 2. Business rule: declined, but not an error.
    if (amountCents > this.#limitCents) {
      const decline = { status: 'declined', orderId, reason: 'amount_exceeds_limit' };
      this.emit('payment:declined', decline);
      return decline;
    }

    // 3. Attempt the charge.
    try {
      const result = await this.#charge({ amountCents, currency });
      const success = { status: 'succeeded', orderId, ...result };
      this.emit('payment:succeeded', success);
      return success;
    } catch (error) {
      // 4. Operational failure: emit, and return a result rather than throwing —
      //    the caller asked "what happened?" and a failed payment is a valid answer.
      const failure = { status: 'failed', orderId, reason: error.message };
      this.emit('payment:failed', failure, error);
      return failure;
    }
  }
}
```

```js
// File: payments-demo.mjs
import { PaymentService } from './payment-service.mjs';

const payments = new PaymentService({ limitCents: 100_000, failureRate: 0.2 });

// --- listeners: each one does exactly one small job -------------------------------
payments.on('payment:succeeded', (p) => {
  console.log(`[ledger]   ✓ recorded txn ${p.transactionId} for order ${p.orderId}`);
});

payments.on('payment:succeeded', (p) => {
  console.log(`[email]    ✉ confirmation queued for ${p.orderId}`);
});

payments.on('payment:succeeded', (p) => {
  console.log(`[metrics]  +1 success, amount=${p.amountCents}${p.currency === 'INR' ? ' ₹' : ''}`);
});

payments.on('payment:declined', (p) => {
  console.log(`[ledger]   ✗ declined ${p.orderId} (${p.reason})`);
});

payments.on('payment:failed', (p, error) => {
  console.log(`[alert]    ⚠ ${p.orderId} failed: ${p.reason}`);
  console.log(`[alert]    ↳ underlying error name: ${error.name}`);
});

payments.on('error', (error) => {
  console.error('[fatal]    unexpected internal failure:', error);
});

// --- exercise it -----------------------------------------------------------------
const attempts = [
  { orderId: 'o_1', amountCents: 49_900 },
  { orderId: 'o_2', amountCents: 250_000 },            // declined: over the limit
  { orderId: 'o_3', amountCents: 9_900, currency: 'USD' },
  { orderId: 'o_4', amountCents: 12_000 },
  { orderId: 'o_5', amountCents: 300 },
];

const results = await Promise.all(attempts.map((a) => payments.pay(a)));

console.log('\n--- summary ---');
const byStatus = results.reduce((acc, r) => {
  acc[r.status] = (acc[r.status] ?? 0) + 1;
  return acc;
}, {});
console.log(byStatus);

// Programmer errors still throw, as they should:
try {
  await payments.pay({ orderId: 'o_6', amountCents: -5 });
} catch (error) {
  console.log(`\nTypeError for bad input: ${error.message}`);
}
```

Expected output (order varies because the provider calls run concurrently):

```
[ledger]   ✗ declined o_2 (amount_exceeds_limit)
[ledger]   ✓ recorded txn txna1b2c3d4 for order o_1
[email]    ✉ confirmation queued for o_1
[metrics]  +1 success, amount=49900 ₹
[alert]    ⚠ o_4 failed: provider timeout
[alert]    ↳ underlying error name: Error
…

--- summary ---
{ declined: 1, succeeded: 3, failed: 1 }

TypeError for bad input: pay() requires amountCents to be a positive integer
```

**Design discussion — the parts that matter in a real review**

1. **Declined ≠ failed.** A declined payment is a legitimate business outcome (the caller may want to ask for another card). A failed charge is an infrastructure problem (retry, alert). Modelling them as separate events with separate statuses means the caller can respond differently. This distinction — _business outcome vs error_ — is one of the most valuable habits in backend code.
2. **Results, not exceptions, for expected outcomes.** `pay()` always resolves with a status, so callers cannot forget to `try/catch`. Genuine bugs (bad arguments) still throw.
3. **One listener = one job.** Email, ledger and metrics are independent. If the email listener throws, the ledger has already run — this is loose coupling in action (and a reason to keep listeners tiny, since `emit` is synchronous and a throwing listener would break the chain).
4. **`captureRejections: true`** means an `async` listener that throws becomes an `'error'` event instead of an unhandled rejection.
5. **The `'error'` listener is attached**, so the emitter can never crash the process from this path.

**Follow-up challenges**

* Add a `'refunded'` event and a `refund(transactionId)` method with a rule that a refund must not exceed the original amount.
* Add an idempotency check: the same `orderId` paid twice should return the first result with `{ status: 'succeeded', duplicate: true }`.
* Replace the in-memory listener set with a persistent "outbox" so events survive a crash — that is how production systems make event-driven flows reliable.

</details>

## Exercise 8.2 — Find the leak

```js
// File: leaky-server.mjs
import { createServer } from 'node:http';

const metrics = { requestCount: 0 };

const server = createServer((req, res) => {
  metrics.requestCount += 1;

  // Record the duration of every response…
  res.on('finish', () => {
    console.log(`done ${req.url}`);
  });

  res.on('close', () => {
    console.log(`closed ${req.url}`);
  });

  res.end('ok');
});

server.listen(3000, '0.0.0.0', () => console.log('listening'));
```

Would this leak? Run it under load and reason about what `res` is and when it is collected.

<details>

<summary>Solution</summary>

**This particular snippet does not leak**, and understanding why is the point.

Each incoming request creates a **new `res` object**. The listeners are attached to _that_ object, and when the response finishes, nothing references `res` any more, so it and its listeners are garbage-collected together. There is no accumulation.

```
res#1 → listeners → finished → res#1 unreferenced → GC
res#2 → listeners → finished → res#2 unreferenced → GC
```

A leak would appear if the listener were attached to a **long-lived** object instead:

```js
// File: actually-leaky.mjs
import { createServer } from 'node:http';
import { EventEmitter } from 'node:events';

const appEvents = new EventEmitter();      // lives for the whole process
const server = createServer((req, res) => {
  // ❌ Attaching to a process-lifetime emitter, once per request, forever.
  appEvents.on('metrics:flush', () => {
    console.log(`${req.url} observed a flush`);
  });
  res.end('ok');
});

server.listen(3000, '0.0.0.0');
```

Every request adds a listener to `appEvents` that is **never removed**, and each closure keeps `req` (and therefore the whole request/socket graph) alive. After 11 requests you get `MaxListenersExceededWarning`, and memory grows without bound.

```js
// ✅ Fixes, in order of preference:
// 1. Attach once, at startup, not per request.
appEvents.on('metrics:flush', () => console.log('flush observed'));

// 2. If per-request work is genuinely needed, remove it when the request ends.
server.on('request', (req, res) => {
  const onFlush = () => console.log(`${req.url} observed a flush`);
  appEvents.on('metrics:flush', onFlush);
  res.on('close', () => appEvents.off('metrics:flush', onFlush));   // guaranteed cleanup
});

// 3. Or use once(), when a single observation is all you need.
```

**How to diagnose this class of bug in a real service**

```bash
node --inspect leaky-server.mjs      # then: Chrome DevTools → Memory → Heap snapshots
# take a snapshot, send 1,000 requests, take another, compare "Objects allocated between snapshots"
# look for growing counts of: EventEmitter listeners, IncomingMessage, Socket, closures over req
```

| Signal                                                           | Meaning                                           |
| ---------------------------------------------------------------- | ------------------------------------------------- |
| `MaxListenersExceededWarning`                                    | A long-lived emitter is accumulating listeners    |
| Memory grows with request count, not payload size                | Retention, not usage                              |
| `process.memoryUsage().heapUsed` climbs and never drops after GC | Something holds references                        |
| Heap snapshot diff shows growing `IncomingMessage`/`Socket`      | The request graph is being retained by a listener |

**The transferable rule:** _listeners attached to objects that die with the request are safe; listeners attached to objects that live for the process must be added once, or removed explicitly._ `res.on('close', …)` is the standard safety net for per-request cleanup.

</details>

***

## What's next

Events are how things are announced. Next: how _data_ flows — streams, the feature that makes Node capable of handling files and payloads larger than memory, with backpressure built in.

→ [09 — Streams](09-streams.md)
