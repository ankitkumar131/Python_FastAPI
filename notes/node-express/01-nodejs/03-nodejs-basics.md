# 03 — Node.js Basics

> **Where this fits:** You understand the architecture and the language. This chapter covers the _environment_ your code runs inside: how `node file.js` actually executes, the globals Node gives you that browsers do not, the `process` object, timers, and how a program starts and stops. Everything here appears in every backend file you will ever write.

***

## 1. How a Node program runs

```bash
node server.js
```

What happens, step by step:

```
1. The `node` executable starts.
2. It creates a V8 isolate (a fresh JS heap) and a libuv event loop for this process.
3. It reads and parses server.js.
4. It executes the file top-to-bottom, SYNCHRONOUSLY, on the main thread.
5. Your file finishes — but the process does NOT exit if the event loop still has work:
      • a listening server socket
      • pending timers
      • pending I/O
      • open handles
6. The event loop keeps running: callbacks fire as timers expire and I/O completes.
7. The process exits when the event loop has nothing left to do (or when you call
   process.exit(), or when a signal/fatal error kills it).
```

Two beginner-surprising consequences:

* **`node server.js` does not "return".** It stays alive. To stop it, press Ctrl+C (which sends `SIGINT`).
* **A script that only registers a listener exits immediately** if nothing keeps the loop alive — that is why `server.listen()` matters.

```js
// File: keeps-alive.js
console.log('A');

// A pending timer keeps the process alive for ~1 second.
setTimeout(() => {
  console.log('C — timer fired, and now the event loop is empty');
}, 1000);

console.log('B');
```

```
A
B
C — timer fired, and now the event loop is empty
```

The process does not exit after printing `B` because the timer is outstanding work.

```js
// File: exits-immediately.js
console.log('This script exits right after this line.');
// Nothing registered anything with the event loop → the process ends.
```

> **Internally:** Node keeps a count of "active handles" (sockets, timers, file watchers) and "active requests". When both counts reach zero, `uv_run` returns and the process exits with code 0. That is the whole definition of "the program is finished".

***

## 2. Globals

Node exposes these globally — no import needed.

| Global                                                        | What it is                               | Browser equivalent                       |
| ------------------------------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| `globalThis`                                                  | The global object itself                 | `window` / `self`                        |
| `process`                                                     | Info and control for the current process | ❌ none                                   |
| `console`                                                     | stdout/stderr logging                    | ✅ (devtools console)                     |
| `Buffer`                                                      | Raw binary data                          | ❌ (ArrayBuffer/TypedArray exist)         |
| `setTimeout` / `setInterval` / `setImmediate`                 | Timers                                   | ⚠️ timers exist, `setImmediate` does not |
| `queueMicrotask`                                              | Schedule a microtask                     | ✅                                        |
| `URL`, `URLSearchParams`                                      | Parse/build URLs                         | ✅                                        |
| `TextEncoder`, `TextDecoder`                                  | string ↔ bytes                           | ✅                                        |
| `fetch`, `Headers`, `Request`, `Response`, `FormData`, `Blob` | Web platform APIs                        | ✅                                        |
| `AbortController`, `AbortSignal`                              | Cancel async work                        | ✅                                        |
| `structuredClone`                                             | Deep copy                                | ✅                                        |
| `crypto`                                                      | Web Crypto (also `node:crypto` for more) | ✅ partially                              |
| `performance`                                                 | High-resolution timing                   | ✅                                        |
| `navigator`                                                   | Minimal (`navigator.userAgent`)          | Full DOM navigator                       |

**Not present in Node:** `window`, `document`, `localStorage`, `alert`, `XMLHttpRequest`, `Element`, DOM events.

```js
// File: globals.js
console.log('globalThis === global:', globalThis === global); // true (Node's legacy alias)
console.log('typeof window:', typeof window);                 // 'undefined'
console.log('typeof document:', typeof document);             // 'undefined'
console.log('Node has fetch:', typeof fetch);                 // 'function'
console.log('Node has structuredClone:', typeof structuredClone); // 'function'
```

Notice `typeof window` returns `'undefined'` rather than throwing — that is exactly how libraries detect their environment:

```js
const isBrowser = typeof window !== 'undefined' && typeof window.document !== 'undefined'; // snippet: partial
```

***

## 3. The `process` object

`process` is the control panel for the running program. The parts you will use daily:

### `process.argv` — command-line arguments

```js
// File: args.js
// Run: node args.js add 3 5 --verbose
console.log(process.argv);
// [ '/path/to/node', '/path/to/args.js', 'add', '3', '5', '--verbose' ]

const [, , command, ...rest] = process.argv;
const numbers = rest.filter((a) => !a.startsWith('--')).map(Number);
const verbose = rest.includes('--verbose');

console.log({ command, numbers, verbose });
// { command: 'add', numbers: [ 3, 5 ], verbose: true }
```

`argv[0]` is the Node executable and `argv[1]` is your script — real arguments start at index 2. This is how every CLI works (and why `npm run` passes extra args after `--`).

### `process.env` — environment variables

```js
// File: env.js
// Run: NODE_ENV=production PORT=4000 node env.js
console.log('NODE_ENV:', process.env.NODE_ENV);   // production
console.log('PORT:', process.env.PORT);           // 4000

// Every value is a STRING (or undefined if unset).
const port = Number(process.env.PORT ?? 3000);
console.log('port + 1 =', port + 1);              // 4001

// Never hardcode secrets — read them from the environment.
const dbUrl = process.env.DATABASE_URL;
if (!dbUrl) {
  console.error('DATABASE_URL is not set. Refusing to start.');
  process.exit(1);                                // fail fast at startup
}
console.log('database configured:', dbUrl.replace(/:\/\/.*@/, '://***@')); // never log credentials
```

Detailed coverage: [15 — Environment Variables](15-environment-variables.md).

### `process.exit()` and exit codes

```js
// File: exit-codes.js
const mode = process.argv[2];

if (mode === 'ok') {
  console.log('Everything is fine');
  process.exit(0);          // 0 = success (the default on normal completion)
}

if (mode === 'bad') {
  console.error('Something went wrong');
  process.exit(1);          // non-zero = failure; CI, Docker and supervisors read this
}

console.log('No explicit exit — Node exits with 0 when the event loop drains');
```

Exit code conventions: `0` success, `1` general failure, `2` misuse of shell built-ins, `126` not executable, `127` command not found, `130` terminated by Ctrl+C (128 + signal 2). Your scripts should return non-zero on failure so CI and orchestrators notice.

**Use `process.exit()` sparingly.** It terminates immediately, so buffered stdout writes can be truncated and cleanup does not run. Prefer setting `process.exitCode = 1` and letting the process end naturally:

```js
// File: exit-code-safe.js
process.exitCode = 1;                  // the process will exit 1 when it finishes
console.log('This line is guaranteed to be flushed');
```

### Signals — graceful shutdown

```js
// File: signals.js
console.log('Running. Press Ctrl+C.');

// SIGINT = Ctrl+C, SIGTERM = "please stop" (sent by Docker/Kubernetes/systemd)
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    console.log(`\nReceived ${signal}. Cleaning up…`);
    // In a real app: stop accepting connections (server.close()), finish in-flight
    // requests, close the DB pool, then exit.
    process.exit(0);
  });
}

// Keep the process alive so there is something to interrupt.
setInterval(() => {}, 1000);
```

Graceful shutdown is covered properly in 07-deployment/03-deployment.md _(not available in this published source revision)_.

### Other useful members

```js
// File: process-info.js
console.log('pid:', process.pid);
console.log('version:', process.version);
console.log('cwd:', process.cwd());
console.log('platform:', process.platform);
console.log('uptime (s):', process.uptime().toFixed(2));
console.log('heap used (MB):', (process.memoryUsage().heapUsed / 1024 / 1024).toFixed(1));
console.log('rss (MB):', (process.memoryUsage().rss / 1024 / 1024).toFixed(1));
console.log('execPath:', process.execPath);

// process.nextTick schedules a callback BEFORE timers and I/O in the current phase.
process.nextTick(() => console.log('nextTick runs first'));
console.log('sync code runs before that');
```

### `process.exitCode` vs `process.exit()` vs throwing

| Situation                               | Do this                                                                     |
| --------------------------------------- | --------------------------------------------------------------------------- |
| Script has a validation failure         | `console.error(...); process.exitCode = 1;`                                 |
| Fatal startup error, nothing else to do | `process.exit(1)` is acceptable                                             |
| Unexpected bug in a request handler     | Throw/`next(error)` — let the framework respond                             |
| **Uncaught exception in an API**        | Log it, then decide: crash (recommended) or recover, depending on the error |

> **Production note:** an uncaught exception leaves the process in an undefined state. The correct behaviour for a _web server_ is to log, stop accepting new requests, finish in-flight work, and exit so the supervisor restarts a clean process. "Catch everything and keep going" hides corruption. We implement this in [02-express/20-production-architecture.md](../02-express/20-production-architecture.md).

```js
// File: unhandled.js
process.on('uncaughtException', (error) => {
  console.error('UNCAUGHT EXCEPTION — exiting:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  console.error('UNHANDLED REJECTION — exiting:', reason);
  process.exit(1);
});

// Note: in modern Node (15+), an unhandled rejection crashes the process by default.
// Registering this handler changes that — only do so if you really intend to.
```

***

## 4. `console` beyond `log`

```js
// File: console-methods.js
console.log('plain');                         // stdout
console.info('informational');                // stdout
console.warn('careful');                      // stderr
console.error('something failed');            // stderr

const user = { id: 1, name: 'Ankit', roles: ['admin'], nested: { deep: { value: 42 } } };
console.log(user);                            // util.inspect formatting, nested, colorised
console.dir(user, { depth: null });           // force full depth
console.table([
  { id: 1, name: 'Ankit', role: 'admin' },
  { id: 2, name: 'Priya', role: 'user' },
]);                                           // a real ASCII table — great for reports

console.time('db');
// …some operation…
console.timeEnd('db');                        // db: 12.348ms

console.group('request');
console.log('GET /users');
console.groupEnd();

console.count('hits');                       // hits: 1
console.count('hits');                       // hits: 2

console.assert(1 === 2, 'this message appears because the assertion is false');
console.trace('where am I?');                 // prints a stack trace
```

### Why `console.log` is not production logging

| Problem                   | Consequence                                      |
| ------------------------- | ------------------------------------------------ |
| Always stdout, no levels  | You cannot filter errors from noise              |
| No structure              | Cannot query "all 500s for user 42"              |
| No timestamps by default  | Cannot correlate with other services             |
| Synchronous-ish, per call | High-throughput logging measurably slows the app |
| No redaction              | Passwords and tokens end up in log files         |

For real services, use a structured logger (`pino` is the standard for Node) and log JSON:

```js
// File: logger-preview.js
// A minimal structured logger to show the idea — pino does this properly and fast.
const logger = {
  write(level, message, context = {}) {
    process.stdout.write(
      `${JSON.stringify({ level, time: new Date().toISOString(), message, ...context })}\n`
    );
  },
  info(message, context) {
    this.write('info', message, context);
  },
  error(message, context) {
    this.write('error', message, context);
  },
};

logger.info('server started', { port: 3000, env: process.env.NODE_ENV ?? 'development' });
logger.error('payment failed', { orderId: 'o_9', provider: 'stripe', code: 'card_declined' });
```

```
{"level":"info","time":"2026-09-18T10:15:30.001Z","message":"server started","port":3000,"env":"development"}
{"level":"error","time":"2026-09-18T10:15:30.002Z","message":"payment failed","orderId":"o_9","provider":"stripe","code":"card_declined"}
```

That shape is what log aggregation (Datadog, Grafana Loki, CloudWatch) can actually search.

***

## 5. Timers

```js
// File: timers.js
// setTimeout: run once after at least N milliseconds
const timeoutId = setTimeout(() => console.log('after 100ms'), 100);

// clearTimeout: cancel it
clearTimeout(timeoutId);

// setInterval: run repeatedly (note: first run is after the delay, not immediately)
let ticks = 0;
const intervalId = setInterval(() => {
  ticks += 1;
  console.log('tick', ticks);
  if (ticks === 3) clearInterval(intervalId);   // ALWAYS clear intervals
}, 50);

// setImmediate: run in the "check" phase of the current loop iteration, after I/O callbacks
setImmediate(() => console.log('immediate'));

// Promises/timers in a friendly wrapper — with cancellation
const delay = (ms, { signal } = {}) =>
  new Promise((resolve, reject) => {
    const id = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => {
      clearTimeout(id);
      reject(new Error('Aborted'));
    });
  });

const controller = new AbortController();
delay(500, { signal: controller.signal })
  .then(() => console.log('500ms elapsed'))
  .catch((error) => console.log('cancelled:', error.message));

controller.abort();                            // cancels the timer immediately
```

### Timer facts that matter in production

| Fact                                               | Why it matters                                                                             |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| The delay is a **minimum**, not a guarantee        | A busy event loop delays timers; never use them for precise scheduling                     |
| An uncleared `setInterval` keeps the process alive | Use `interval.unref()` or always clear                                                     |
| `setTimeout(fn, 0)` is not "immediately"           | It is "next timer phase"; `process.nextTick` and microtasks come first                     |
| `setInterval` drifts                               | For clocks/cron prefer a scheduler or recompute the next delay                             |
| Long timers cap out                                | A delay > 2^31-1 ms overflows and fires immediately — a classic bug with "30-day" timeouts |

```js
// File: unref.js
// `unref()` tells Node: "this handle should not keep the process alive by itself."
const heartbeat = setInterval(() => console.log('heartbeat'), 1000);
heartbeat.unref();
// The process can now exit even though the interval is pending.
```

***

## 6. `__dirname` and `__filename` in modern Node

In CommonJS, `__dirname` and `__filename` exist. In ES modules they do not — you use `import.meta`:

```js
// File: paths.mjs  (ESM)
import path from 'node:path';
import { fileURLToPath } from 'node:url';

console.log('import.meta.url      :', import.meta.url);          // file:///…/paths.mjs
console.log('import.meta.dirname  :', import.meta.dirname);      // /…           (Node 20.11+)
console.log('import.meta.filename :', import.meta.filename);     // /…/paths.mjs (Node 20.11+)

// Portable fallbacks for older Node versions:
const __filenameCompat = fileURLToPath(import.meta.url);
const __dirnameCompat = path.dirname(__filenameCompat);
console.log('compat dirname       :', __dirnameCompat);
```

```js
// File: paths.cjs  (CommonJS)
const path = require('node:path');

console.log('__filename:', __filename);   // /…/paths.cjs
console.log('__dirname :', __dirname);    // /…
console.log('resolved  :', path.join(__dirname, 'data', 'file.json'));
```

### Why this matters more than it looks

```js
// ❌ Depends on WHERE YOU RAN THE COMMAND, not where the file is.
const configPath = './config/app.json';
```

```js
// ✅ Always correct, regardless of the working directory.
const configPath = path.join(import.meta.dirname, '../config/app.json');
```

In development you run `node src/server.js` from the project root, so `./config/app.json` resolves correctly. In production a supervisor may run it from `/`, and the same code cannot find the file. **Always resolve paths relative to the module, not the process.**

***

## 7. Standard input, output and pipes

```js
// File: echo-cat.js
// Read all of stdin and echo it back — the "cat" program in 8 lines.
process.stdin.setEncoding('utf8');

let input = '';
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  process.stdout.write(input.split('').reverse().join(''));
});
```

```bash
echo "hello node" | node echo-cat.js
# edon olleh
```

```bash
# Piping processes together — the Unix idea that Node fits into perfectly
node generate-report.js | head -20
node app.js > out.log 2> err.log        # separate stdout and stderr
node app.js &                          # run in the background
```

Three streams are always available: `process.stdin` (0), `process.stdout` (1), `process.stderr` (2). Writing errors to **stderr** is not cosmetic — it is how log collectors and CI separate failures from normal output.

***

## 8. The shape of a Node application

By the end of this section you will build this, but here is the skeleton so the pieces have a home:

```
my-api/
├── src/
│   ├── server.js          ← entry point: starts the HTTP server, handles shutdown
│   ├── app.js             ← builds and configures the app (no listening) — testable
│   ├── config/
│   │   └── env.js         ← reads and validates process.env ONCE, at startup
│   ├── routes/
│   ├── controllers/
│   ├── services/
│   └── lib/               ← pure helpers, testable without a server
├── scripts/               ← one-off operational scripts
├── tests/
├── package.json
├── .env                   ← NEVER commit (gitignored)
├── .env.example           ← committed, documents required variables
└── .nvmrc
```

The `server.js` / `app.js` split is not decoration: it lets tests import `app.js` and fire requests at it **without opening a port**, which is exactly what Supertest does in 05-testing/03-supertest.md _(not available in this published source revision)_.

```js
// File: src/server.js  (the pattern, previewed)
import { createApp } from './app.js';
import { env } from './config/env.js';

const app = createApp();
const server = app.listen(env.PORT, '0.0.0.0', () => {
  console.log(`API listening on http://0.0.0.0:${env.PORT} (${env.NODE_ENV})`);
});

// Graceful shutdown: stop accepting, finish in-flight, then exit.
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    console.log(`${signal} received, shutting down…`);
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(1), 10_000).unref(); // force-exit safety net
  });
}
```

***

## 9. Common mistakes

| Mistake                                   | Symptom                                 | Fix                                                 |
| ----------------------------------------- | --------------------------------------- | --------------------------------------------------- |
| Relative paths from `process.cwd()`       | "Works locally, file not found in prod" | `import.meta.dirname` / `__dirname`                 |
| Forgetting `process.env.X` is a string    | `"3000" + 1 === "30001"`                | `Number(...)` and validate                          |
| Not failing fast on missing config        | Crashes later, confusingly              | Validate env at startup and `exit(1)`               |
| `process.exit()` inside a request handler | Truncated responses, unfinished writes  | Throw / `next(error)`                               |
| No `unhandledRejection` policy            | Silent lost work                        | Decide and document; log and exit                   |
| `setInterval` never cleared               | Memory leak, process never exits        | `clearInterval` or `.unref()`                       |
| Logging with `console.log` in production  | Unsearchable, slow, leaks secrets       | Structured logger with redaction                    |
| `console.log(process.env)`                | Dumps every secret you own              | Log specific values, redacted                       |
| Using `setTimeout` for precise timing     | Drift, ordering surprises               | Measure with `performance.now()`, schedule properly |
| Ignoring the exit code in scripts         | CI passes while the job failed          | `process.exitCode = 1`                              |

***

## Exercise 3.1 — A useful CLI

Write `greet.js` that:

1. Reads a `--name` flag (default `"World"`).
2. Reads an optional `--shout` flag.
3. Prints `Hello, <name>!` (uppercased with `--shout`).
4. Exits with code `1` and prints a usage message to **stderr** if an unknown flag is passed.
5. Prints a summary to stderr when `--verbose` is passed.

<details>

<summary>Solution</summary>

```js
// File: greet.js
// Usage: node greet.js --name Ankit --shout --verbose

function parseArgs(argv) {
  const flags = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) return { error: `Unexpected argument: ${token}` };

    const [rawKey, inlineValue] = token.slice(2).split('=');
    // Support both --name=Ankit and --name Ankit
    const next = argv[i + 1];
    const takesValue = inlineValue === undefined && next !== undefined && !next.startsWith('--');

    if (takesValue) i += 1;
    flags[rawKey] = takesValue ? next : (inlineValue ?? true);
  }
  return { flags };
}

const [, , ...argv] = process.argv;
const { flags, error } = parseArgs(argv);

if (error) {
  process.stderr.write(`Error: ${error}\n`);
  process.stderr.write('Usage: node greet.js [--name <name>] [--shout] [--verbose]\n');
  process.exit(1);
}

const allowed = new Set(['name', 'shout', 'verbose']);
const unknown = Object.keys(flags).filter((key) => !allowed.has(key));

if (unknown.length > 0) {
  process.stderr.write(`Error: unknown flag(s): ${unknown.map((k) => `--${k}`).join(', ')}\n`);
  process.stderr.write('Usage: node greet.js [--name <name>] [--shout] [--verbose]\n');
  process.exit(1);
}

const name = typeof flags.name === 'string' ? flags.name : 'World';
const message = `Hello, ${name}!`;
const output = flags.shout ? message.toUpperCase() : message;

process.stdout.write(`${output}\n`);

if (flags.verbose) {
  process.stderr.write(
    `[verbose] parsed=${JSON.stringify(flags)} node=${process.version} pid=${process.pid}\n`
  );
}
```

```bash
$ node greet.js
Hello, World!

$ node greet.js --name Ankit --shout
HELLO, ANKIT!

$ node greet.js --name "Priya Sharma"
Hello, Priya Sharma!

$ node greet.js --oops ; echo "exit code: $?"
Error: unknown flag(s): --oops
Usage: node greet.js [--name <name>] [--shout] [--verbose]
exit code: 1

$ node greet.js --name Ankit --verbose > /dev/null
[verbose] parsed={"name":"Ankit","verbose":true} node=v24.10.0 pid=9123
```

**Design notes**

* Errors go to **stderr** and the exit code is **non-zero** — that is what makes a CLI scriptable. A script that prints an error to stdout and exits `0` is unusable in CI.
* `--name=Ankit` and `--name Ankit` are both supported, because users expect both.
* Unknown flags fail loudly. Silently ignoring typos like `--nam Ankit` is how people lose an hour.
* `--verbose` output goes to stderr so it never pollutes piped stdout.

_(In a real project you would use `node:util`'s `parseArgs`, which is built in and handles all this — try rewriting it with `parseArgs` as a follow-up exercise.)_

</details>

## Exercise 3.2 — Predict the output

Without running it, write down the exact output order of `node order.js`:

```js
console.log('1 sync');

setTimeout(() => console.log('2 timeout'), 0);

Promise.resolve().then(() => console.log('3 promise'));

process.nextTick(() => console.log('4 nextTick'));

setImmediate(() => console.log('5 immediate'));

console.log('6 sync');
```

<details>

<summary>Solution</summary>

```
1 sync
6 sync
4 nextTick
3 promise
2 timeout        (order of 2 and 5 can swap; see below)
5 immediate
```

**Why:**

1. Synchronous code runs first, in order: `1 sync`, `6 sync`.
2. Then **`process.nextTick` callbacks**, which run before anything else and before promises.
3. Then the **microtask queue** (promises): `3 promise`.
4. Then the **timers phase** of the event loop: `setTimeout(…, 0)` → `2 timeout`.
5. Then the **check phase**: `setImmediate` → `5 immediate`.

**The caveat about 2 vs 5:** at the top level of the main module, which of `setTimeout(…, 0)` and `setImmediate` runs first is **non-deterministic** — it depends on how long the process took to reach the timers phase. Inside an I/O callback, `setImmediate` always runs first because the check phase follows the poll phase.

This exercise is a preview; the full model (phases, microtasks, starvation) is in [14 — The Event Loop](14-event-loop.md).

</details>

***

## What's next

A Node application is never one file. Next: how Node splits code across files — `require`, `import`, the two module systems, and the rules that make "Cannot find module" either obvious or maddening.

→ [04 — Modules: CommonJS and ESM](04-modules.md)
