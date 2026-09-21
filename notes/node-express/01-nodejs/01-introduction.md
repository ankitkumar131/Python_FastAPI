# 01 — Introduction to Node.js

> **Where this fits:** You understand HTTP and how a request travels. Now you meet the runtime that will sit at the other end of it. This chapter answers "what _is_ Node.js, really?" — because almost every beginner misconception about backends (blocking, event loops, "is it a framework?", "is it a language?") comes from skipping this question.

***

## 1. What is Node.js?

> **Node.js is a runtime environment that lets you run JavaScript outside a web browser, on a server, using an event-driven, non-blocking I/O model.**

Three parts deserve unpacking:

| Word                               | Meaning                                                                                                                            |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Runtime environment**            | A program that provides the machinery to execute your code: a JS engine, memory management, and APIs for files, network, processes |
| **Outside a browser**              | No `document`, no `window`, no DOM — but files, sockets, and OS processes instead                                                  |
| **Event-driven, non-blocking I/O** | Instead of waiting for a slow operation to finish, Node registers a callback and continues doing other work                        |

### The one-sentence definition to use in an interview

> "Node.js is a JavaScript runtime built on Chrome's V8 engine that uses a single-threaded event loop and a libuv thread pool to perform non-blocking I/O, which makes it a great fit for I/O-heavy workloads like APIs and real-time applications."

Note what is _not_ in that sentence: "server", "framework", "language". Node is not any of those.

***

## 2. Runtime vs language vs framework (the #1 beginner confusion)

```
┌──────────────────────────────────────────────────────────┐
│ LANGUAGE       JavaScript (ECMAScript)                   │
│                syntax + semantics: let, functions, async │
└──────────────────────────────────────────────────────────┘
        │ written in
        ▼
┌──────────────────────────────────────────────────────────┐
│ ENGINE         V8  (or SpiderMonkey, JavaScriptCore)     │
│                compiles JS → machine code, runs it,      │
│                manages memory (garbage collection)       │
└──────────────────────────────────────────────────────────┘
        │ embedded in, plus extra APIs
        ▼
┌──────────────────────────────────────────────────────────┐
│ RUNTIME        Node.js  (vs Deno, Bun, a browser)        │
│                file system, network, processes, timers,  │
│                event loop, worker threads, npm modules   │
└──────────────────────────────────────────────────────────┘
        │ you add a library on top of
        ▼
┌──────────────────────────────────────────────────────────┐
│ FRAMEWORK      Express.js (or Fastify, NestJS, Koa)      │
│                routing, middleware, req/res sugar        │
└──────────────────────────────────────────────────────────┘
```

So: **JavaScript is the language. V8 is the engine. Node.js is the runtime. Express is the framework.** Learning Express is much easier once this stack is clear, because you then know which layer to blame and where each feature comes from.

***

## 3. Why was Node.js created?

In 2009, most web servers handled each connection with a thread (or a process). With 10,000 concurrent connections, you needed 10,000 threads — each with its own stack (\~1 MB+), plus context switching. It worked, but it was expensive, and for I/O-bound traffic it wasted most of that memory. Worse, a thread sitting idle waiting for a database reply is doing nothing useful.

Ryan Dahl's insight: **most server work is waiting, not computing.** A typical API request spends microseconds on CPU and milliseconds (or seconds) waiting on a database, a disk, or another service. If you could avoid dedicating resources to the _waiting_, one process could serve a huge number of connections.

His design: take an engine that already existed and was fast (V8), add an **event-driven I/O library** (libuv), and expose a **single-threaded, callback-based** programming model. The result was Node.js, and it made "JavaScript on the server" viable.

There was a second reason: the same language on the client and the server. One language, one mental model, shared validation logic, JSON everywhere. That turned out to be a huge practical advantage for teams.

***

## 4. Node.js architecture

```
┌───────────────────────────────────────────────────────────────────┐
│ YOUR JAVASCRIPT CODE                                              │
│   app.get('/users', async (req, res) => { … })                    │
└───────────────────────────────┬───────────────────────────────────┘
                                │ executed by
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ V8 ENGINE                                                         │
│   • parses JS                                                     │
│   • JIT-compiles hot functions to machine code                    │
│   • executes on the MAIN THREAD                                   │
│   • manages the heap + garbage collector                          │
│   (V8 knows nothing about files or sockets!)                      │
└───────────────────────────────┬───────────────────────────────────┘
                                │ embedded in
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ NODE.JS BINDINGS  (C++ layer)                                     │
│   the bridge that lets JavaScript call into native code           │
└───────────────────────────────┬───────────────────────────────────┘
                                │ implemented by
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ LIBUV  (the asynchronous I/O library, written in C)               │
│   • the EVENT LOOP  (the orchestrator)                            │
│   • a THREAD POOL   (4 threads by default) for blocking work:     │
│       fs, dns.lookup, crypto, zlib                                │
│   • OS async facilities: epoll (Linux), kqueue (macOS),           │
│       IOCP (Windows) — used for sockets, which need no thread     │
│   • timers, child processes, signals, worker-thread plumbing      │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ OPERATING SYSTEM                                                  │
│   files, sockets, threads, CPU, memory                            │
└───────────────────────────────────────────────────────────────────┘
```

The description of that flow, from the notes' outline, is:

```
JavaScript
     ↓
V8 Engine
     ↓
Node.js Runtime
     ↓
Event Loop
     ↓
Operating System
```

### What each component actually does

| Component          | Responsibility                                 | What it does _not_ do                         |
| ------------------ | ---------------------------------------------- | --------------------------------------------- |
| **Your code**      | Business logic                                 | Nothing automatic — you must not block        |
| **V8**             | Execute JS fast; manage memory                 | No I/O, no timers, no `require`, no `process` |
| **Bindings (C++)** | Translate JS calls into native calls           | No policy                                     |
| **libuv**          | Event loop, thread pool, OS event notification | Does not understand JavaScript                |
| **OS**             | Real reads/writes, timers, scheduling          | —                                             |

A useful mental model: **V8 runs your code on one thread; libuv does the waiting elsewhere and tells V8 when there is a result.**

### The two kinds of asynchronous work in Node

This distinction explains most "why is my API slow?" questions:

```
A. NETWORK I/O  (sockets: HTTP, TCP, databases, DNS via getaddrinfo)
   Handled by epoll/kqueue/IOCP — the OS tells libuv when data is ready.
   NO thread is consumed while waiting. Scales to tens of thousands of sockets.

B. FILE / CPU-ISH WORK  (fs, dns.lookup, crypto.pbkdf2, zlib, bcrypt)
   Not exposed consistently asynchronously by all OSes, so libuv uses a
   THREAD POOL of 4 threads by default (UV_THREADPOOL_SIZE).
   If 5 fs operations are in flight, the 5th waits for a free thread!
```

That last point is a real production issue: password hashing with `bcrypt` uses the thread pool, so an authentication spike can starve file reads. We cover the fixes in [18 — Node.js Project](18-nodejs-project.md) and 04-authentication/02-password-hashing.md _(not available in this published source revision)_.

### Single-threaded — with important caveats

"Node.js is single-threaded" is a useful simplification with three exceptions:

1. **The libuv thread pool** (4 threads by default) for fs/dns/crypto/zlib.
2. **`worker_threads`** — real parallelism for CPU-bound work, in-process.
3. **`child_process` / `cluster`** — separate processes (this is how you use all CPU cores in production).

So the accurate statement is: **your JavaScript runs on a single thread per process; the runtime uses other threads and processes for specific jobs.**

### Why this architecture is fast for APIs

```
Traditional thread-per-connection server, 10,000 idle-but-open connections:
   10,000 threads × ~1 MB stack  ≈ 10 GB of memory, plus scheduler overhead

Node.js, 10,000 idle-but-open connections:
   ONE event loop thread + 10,000 small socket objects  ≈ tens of MB
```

Memory per connection drops by orders of magnitude. That is the entire reason Node became the default for API gateways, chat servers, and streaming services.

And the flip side, which you must internalise:

```
IF YOU BLOCK THE EVENT LOOP, EVERY CONNECTION WAITS.
One synchronous 3-second computation = the whole server is frozen for 3 seconds.
```

***

## 5. Node.js vs browser JavaScript

Both run the same language, from the same specification, but the _environments_ differ:

|                 | Browser                        | Node.js                                  |
| --------------- | ------------------------------ | ---------------------------------------- |
| Global object   | `window` (or `self`)           | `globalThis`                             |
| DOM             | ✅ `document`, elements, events | ❌ none                                   |
| `localStorage`  | ✅                              | ❌                                        |
| File system     | ❌ (except sandboxed APIs)      | ✅ `node:fs`                              |
| Network server  | ❌ cannot listen                | ✅ `node:http`, `node:net`                |
| Process control | ❌                              | ✅ `process`, `node:child_process`        |
| Module system   | ESM (`import`) only            | ESM **and** CommonJS (`require`)         |
| `process.env`   | ❌                              | ✅ environment variables                  |
| Entry point     | `index.html` + `<script>`      | `node server.js`                         |
| Lifecycle       | Page lives until closed        | Process runs until it exits or is killed |
| Security model  | Hostile code, sandboxed        | Trusted code, full machine access        |
| `fetch`         | ✅ always                       | ✅ since Node 18 (global)                 |
| Timers          | `setTimeout` etc.              | Same API, same semantics                 |
| Console         | `console.log`                  | Same, writes to stdout                   |

Practical consequences:

* A tutorial that uses `document` cannot be copy-pasted into Node.
* Code that "works in Node" may use APIs the browser lacks (`fs`), so you cannot always move backend code to the frontend.
* `process.env`, `fs`, and `path` are always available in Node and never in a browser, which is why libraries use `typeof window === 'undefined'` to detect the environment.

***

## 6. What Node.js is good at, and what it is not

### Excellent fit

| Use case                                              | Why                                                        |
| ----------------------------------------------------- | ---------------------------------------------------------- |
| REST/JSON APIs                                        | I/O-bound: mostly waiting on databases                     |
| Real-time apps (chat, collaboration, live dashboards) | WebSockets are cheap; thousands of concurrent connections  |
| API gateways / BFF (backend-for-frontend)             | Proxying and aggregating calls is all I/O                  |
| Streaming                                             | Native stream support; backpressure built in               |
| Serverless functions                                  | Fast cold starts, small memory footprint                   |
| CLIs and build tools                                  | Node ships with npm, and the tooling ecosystem is JS-first |
| Microservices with light CPU work                     | High concurrency per unit of memory                        |

### Poor fit (or needs care)

| Use case                                                       | Why                       | Alternative/mitigation                                        |
| -------------------------------------------------------------- | ------------------------- | ------------------------------------------------------------- |
| Heavy CPU computation (video encoding, ML, big data crunching) | Blocks the event loop     | `worker_threads`, a native addon, or another language/service |
| Long-running synchronous work (image resizing in-process)      | Same                      | Offload to a queue + worker                                   |
| Tasks needing true parallelism by default                      | One JS thread per process | `cluster`, `worker_threads`, containers                       |
| Systems programming / tight memory control                     | GC, dynamic types         | Go, Rust, C++                                                 |
| Very high-throughput numeric computing                         | JS numbers are doubles    | Rust/C++ service behind an API                                |

The honest framing for an interview: _"Node is optimised for I/O concurrency, not CPU throughput. It is the wrong tool for a CPU-bound service and the right tool for an API."_

***

## 7. Installing Node.js

### Recommended: a version manager

Install **nvm** (macOS/Linux) or **fnm** / **nvm-windows** so you can switch versions per project:

```bash
# macOS / Linux
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
# restart the shell, then:
nvm install --lts
nvm use --lts
```

```bash
# Windows PowerShell
winget install CoreyButler.NVMforWindows
nvm install lts
nvm use lts
```

### Verify

```bash
node --version      # e.g. v24.10.0
npm --version       # e.g. 11.6.0
which node          # /Users/you/.nvm/versions/node/v24.10.0/bin/node
```

### Which version should you use?

The version landscape as of September 2026:

| Line     | Status                       | Use it for                                             |
| -------- | ---------------------------- | ------------------------------------------------------ |
| **24.x** | **Active LTS** (recommended) | Production and learning — this is what these notes use |
| 22.x     | Maintenance LTS              | Existing projects that need a slower upgrade           |
| 26.x     | Current                      | Trying new features, not yet LTS                       |
| ≤ 20     | End of life                  | Nothing. Upgrade.                                      |

Rules of thumb:

* **Use the Active LTS in production.** Odd-numbered releases (21, 23, 25) were never LTS and should not be deployed.
* **Pin the version per project** in `.nvmrc` and `package.json` `engines` so every teammate and CI job uses the same one.
* **Upgrade once a year**, deliberately, with your test suite as the safety net.

```bash
# .nvmrc
24
```

```json
// package.json (fragment)
{
  "engines": { "node": ">=22.0.0" }
}
```

> **Change coming:** from Node.js 27, the project moves to **one major release per year** (April), and **every** release becomes LTS (October). The odd/even distinction disappears. The practical advice — "use LTS for production" — stays correct.

### nvm cheat sheet

```bash
nvm ls                 # installed versions
nvm ls-remote --lts    # available LTS versions
nvm install 24         # install latest 24.x
nvm use 24             # switch for this shell
nvm alias default 24   # make it the default
nvm current            # what am I on?
```

***

## 8. Your first Node.js program

You do not need a browser, an HTML file, or a build step. One file is enough.

```js
// File: hello.js
// In Node, `console.log` writes to stdout — the terminal — not to a browser console.
console.log('Hello from Node.js!');
console.log('Node version:', process.version);
console.log('Platform:', process.platform);
console.log('Current directory:', process.cwd());
console.log('Process id:', process.pid);
```

Run it:

```bash
node hello.js
```

Expected output (values will differ on your machine):

```
Hello from Node.js!
Node version: v24.10.0
Platform: darwin
Current directory: /Users/you/projects/hello
Process id: 41283
```

Line by line:

| Line                                 | What happens                                                                                                                                                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `console.log('Hello from Node.js!')` | Writes the string plus a newline to stdout. In Node this is a stream write — for high-throughput logging, `console.log` can be slow, which is why production apps use a logger                               |
| `process.version`                    | The running Node version, from the built-in `process` global. There is no `process` in browsers                                                                                                              |
| `process.platform`                   | `'darwin'`, `'linux'`, `'win32'` — used for platform-specific code                                                                                                                                           |
| `process.cwd()`                      | Current working directory. **Important:** this is where you _ran_ the command, not where the file lives. Relative paths in `fs` calls resolve against it — a common source of "file not found" in production |
| `process.pid`                        | The OS process id — useful for logs and for sending signals                                                                                                                                                  |

`process` is a **global** object in Node: no `require`, no import.

### The REPL

Run `node` with no arguments for a Read-Eval-Print-Loop — an interactive sandbox:

```bash
$ node
Welcome to Node.js v24.10.0.
Type ".help" for more information.
> 2 + 3
5
> const greet = (name) => `Hi ${name}`;
undefined
> greet('Ankit')
'Hi Ankit'
> process.version
'v24.10.0'
> .exit
```

`undefined` after a declaration is normal — a declaration produces no value. Use `.exit` or Ctrl+D to leave.

Other handy invocations:

```bash
node -e "console.log(process.arch)"   # evaluate an expression
node --watch server.js                # restart automatically when files change (Node 18.11+)
node --env-file=.env server.js        # load env vars without dotenv (Node 20.6+)
node --inspect server.js              # start the debugger
node --test                           # run the built-in test runner (Node 18+)
```

`--watch` and `--env-file` mean you can build a modern dev setup with **zero** dev dependencies — a fact many tutorials predate.

***

## 9. Your first server (30 seconds of wonder)

One of the best things about Node: a working HTTP server in nine lines, no framework.

```js
// File: server.js
import { createServer } from 'node:http';

const server = createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify({ ok: true, message: 'Hello from Node!' }));
});

server.listen(3000, '0.0.0.0', () => {
  console.log('Server listening on http://localhost:3000');
});
```

```bash
node server.js
# in another terminal:
curl http://localhost:3000/anything
```

```
{"ok":true,"message":"Hello from Node!"}
```

That is a real HTTP server handling real requests. You will build a much better one in [11 — The http Module](11-http-module.md), and then rebuild it in Express — at which point every line Express saves you will be obvious rather than magic.

Note `'0.0.0.0'`: binding to all interfaces. Bind to `127.0.0.1` and the server is only reachable from that machine (which breaks containers, VMs and preview environments).

***

## 10. Common mistakes

| Mistake                                                    | Why it happens                   | Fix                                                       |
| ---------------------------------------------------------- | -------------------------------- | --------------------------------------------------------- |
| Thinking Node is a framework/language                      | Tutorials say "Node vs Django"   | Language = JS, runtime = Node, framework = Express        |
| Using `window`/`document` in Node                          | Browser habits                   | There is no DOM; use `node:fs`, `node:http`, etc.         |
| Blocking the event loop with sync code                     | Convenience of `fs.readFileSync` | Use async APIs in request paths                           |
| Believing "single-threaded" means "only one thread exists" | Oversimplification               | Thread pool + workers exist; _your JS_ is single-threaded |
| Expecting Node to use all CPU cores automatically          | It does not                      | `cluster`, `PM2`, containers per core                     |
| Using an odd-numbered Node in production                   | Not LTS                          | Use Active LTS (24.x today)                               |
| Assuming `process.cwd()` is the script's folder            | Relative paths surprise          | Use `import.meta.dirname` / `__dirname`                   |
| `require` in an ESM project                                | Mixed module systems             | See [04 — Modules](04-modules.md)                         |
| Writing huge CPU-bound loops in a handler                  | Not obvious until load           | Offload to workers/queues                                 |
| Not pinning the Node version                               | "Works on my machine"            | `.nvmrc` + `engines`                                      |

***

## Exercise 1.1 — Inspect the runtime

Write a script `inspect-runtime.js` that prints: Node version, V8 version, platform, CPU architecture, the number of CPUs, free memory in MB, uptime in seconds, and the absolute path of the running script. Then answer: which of these are available in a browser?

<details>

<summary>Solution</summary>

```js
// File: inspect-runtime.js
import os from 'node:os';
import path from 'node:path';

const cpu = os.cpus()[0];

console.log('Node version      :', process.version);
console.log('V8 version        :', process.versions.v8);
console.log('Platform          :', process.platform);
console.log('CPU architecture  :', process.arch);
console.log('CPU model         :', cpu?.model);
console.log('CPU cores         :', os.cpus().length);
console.log('Free memory (MB)  :', Math.round(os.freemem() / 1024 / 1024));
console.log('Total memory (MB) :', Math.round(os.totalmem() / 1024 / 1024));
console.log('Uptime (s)        :', process.uptime().toFixed(1));
console.log('Script filename   :', process.argv[1]);
console.log('Absolute path     :', path.resolve(process.argv[1]));
console.log('Directory         :', import.meta.dirname);
```

Run:

```bash
node inspect-runtime.js
```

**Which of these exist in a browser?**

| Value             | Browser?      | Why                                                                                                |
| ----------------- | ------------- | -------------------------------------------------------------------------------------------------- |
| Node version      | ❌             | There is no Node                                                                                   |
| V8 version        | ⚠️ indirectly | Engines do not expose it to page JS                                                                |
| Platform / arch   | ⚠️ partially  | Inferable via `navigator.userAgent`/`navigator.platform`, which is unreliable and being deprecated |
| CPU cores         | ✅             | `navigator.hardwareConcurrency` (approximate)                                                      |
| Free/total memory | ⚠️ limited    | `navigator.deviceMemory` (coarse, privacy-rounded)                                                 |
| Uptime            | ❌             | No process in a page                                                                               |
| Script path       | ❌             | A page cannot read its own filesystem path                                                         |

**The lesson:** Node exposes the _machine_; the browser exposes the _page_. Design your code around that boundary — and when you write code that must run in both (a shared validation module), never touch `process`, `fs`, or `os` in it.

</details>

## Exercise 1.2 — Explain the architecture

Your colleague says: "Node.js is fast because it's multi-threaded." Correct them, and explain precisely what _is_ multi-threaded and why the architecture is fast anyway.

<details>

<summary>Solution</summary>

**Correction:** Your JavaScript runs on **one thread** per process. There is no thread per request. What exists in addition:

1. **libuv's thread pool** — 4 threads by default (`UV_THREADPOOL_SIZE`), used for operations the OS does not expose asynchronously in a portable way: `fs`, `dns.lookup`, `crypto.pbkdf2`/`scrypt`, `zlib`.
2. **`worker_threads`** — opt-in, in-process parallelism for CPU-bound work.
3. **`cluster` / `child_process`** — separate _processes_, which is how production setups use all cores.

**Why it is fast anyway:** because most API work is _waiting_, not computing. When your handler awaits a database query, no thread is blocked — the socket is registered with `epoll`/`kqueue`/`IOCP`, the event loop goes off and serves other requests, and a callback runs when the data arrives. A thread-per-connection server would have a whole thread parked on that same wait. So Node trades _thread-count concurrency_ for _event-loop concurrency_, using far less memory per idle connection.

**The trade-off you must state in the same breath:** because there is one JS thread, a synchronous CPU-bound operation (a big loop, `JSON.parse` of 50 MB, a synchronous `bcrypt.hashSync`) blocks _every_ request for its whole duration. That is the cost of the design, and the reason "don't block the event loop" is rule #1 in Node.

</details>

***

## What's next

Node runs JavaScript — but not exactly the JavaScript you learned from a 2015 tutorial. Next: the language features that modern backend code depends on every single day.

→ [02 — JavaScript Prerequisites](02-javascript-prerequisites.md)
