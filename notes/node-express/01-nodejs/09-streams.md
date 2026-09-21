# 09 — Streams

> **Where this fits:** Streams are how Node moves data that is too big for memory, and they are everywhere: HTTP request/response bodies, file I/O, gzip, database cursors, S3 uploads, `child_process` pipes. This chapter explains what a stream is, the four kinds, backpressure (the concept that separates beginners from professionals), and the pipelines you will write in real services.

***

## 1. Why streams exist

Suppose a user uploads a 4 GB video, and you need to store it.

```js
// ❌ Without streams: the whole file is loaded into memory, then written.
import express from 'express';
import { writeFile } from 'node:fs/promises';

const app = express();
app.use(express.raw({ limit: '10gb' }));

app.post('/upload', async (req, res) => {
  await writeFile('./uploads/video.mp4', req.body);   // req.body is 4 GB in RAM
  res.json({ ok: true });
});
```

Problems: 4 GB of RAM (probably a crash), no response until the entire upload completes, twice the memory used during the write, and every concurrent upload multiplies the problem.

```js
// ✅ With streams: chunks flow through in constant memory.
import express from 'express';
import { createWriteStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';

const app = express();

app.post('/upload', async (req, res) => {
  const destination = createWriteStream('./uploads/video.mp4');
  await pipeline(req, destination);     // memory usage stays in the tens of KB
  res.status(201).json({ ok: true });
});
```

**A stream is an abstraction for data that arrives over time, in pieces (chunks), instead of all at once.** It decouples _how fast data is produced_ from _how fast it is consumed_ — which is the whole trick.

### What streams give you

| Benefit                       | Explanation                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------------- |
| **Constant memory**           | You process chunk-by-chunk; a 100 GB file needs kilobytes of buffer                 |
| **Time to first byte**        | You can respond/act before the whole payload arrives                                |
| **Backpressure**              | A slow consumer automatically slows the producer instead of buffering without limit |
| **Composability**             | `source.pipe(transform).pipe(destination)` — Unix pipes in JavaScript               |
| **Composability with the OS** | Streams map to real sockets and file descriptors                                    |

***

## 2. The four kinds of stream

```
Readable    ── produces data you consume      (fs.createReadStream, req, process.stdin)
Writable    ── consumes data you write        (fs.createWriteStream, res, process.stdout)
Duplex      ── both, independently            (net.Socket, a TCP connection)
Transform   ── duplex where output is derived from input (zlib.createGzip, crypto cipher)
```

Think of a transform as a function with a stream interface: bytes in, different bytes out.

```
Readable ──▶ Transform ──▶ Transform ──▶ Writable
 file          gzip         encrypt        network
```

***

## 3. Readable streams

### Two modes: flowing and paused

A readable stream starts **paused**. It switches to **flowing** when you attach a `'data'` listener or call `.resume()`.

```js
// File: readable-flowing.mjs
import { Readable } from 'node:stream';

// A readable stream from an array of chunks — the easiest way to experiment.
const readable = Readable.from(['Hello ', 'from ', 'a ', 'stream\n']);

// Flowing mode: 'data' fires as chunks arrive.
readable.on('data', (chunk) => {
  process.stdout.write(`[chunk] ${chunk}`);
});

readable.on('end', () => console.log('[end] no more data'));

readable.on('close', () => console.log('[close] stream released its resources'));
```

```
[chunk] Hello [chunk] from [chunk] a [chunk] stream
[end] no more data
[close] stream released its resources
```

### Paused mode: `read()` and async iteration

```js
// File: readable-iterator.mjs
import { Readable } from 'node:stream';

// Async iteration is the modern, loop-friendly API — and it handles backpressure properly
// because each iteration waits for the previous chunk to be processed.
const chunks = ['alpha ', 'beta ', 'gamma '];
const readable = Readable.from(chunks);

let total = 0;

for await (const chunk of readable) {
  total += chunk.length;
  // Processing is naturally paced: the stream will not push the next chunk
  // until this iteration completes.
  await new Promise((resolve) => setTimeout(resolve, 5));
  console.log('processed:', chunk.toString().trim());
}

console.log('total bytes:', total);
```

| Event / method                        | Meaning                                                           |
| ------------------------------------- | ----------------------------------------------------------------- |
| `'data'`                              | A chunk is available (switches the stream to flowing)             |
| `'end'`                               | No more data will be read (only emitted for reading, not writing) |
| `'close'`                             | The stream and its resources are released                         |
| `'error'`                             | Something failed                                                  |
| `'readable'`                          | Data is available to be pulled with `read()`                      |
| `readable.read()`                     | Pull chunks manually (paused mode)                                |
| `readable.pause()` / `.resume()`      | Stop/start flowing                                                |
| `readable.pipe(dest)`                 | Connect to a writable                                             |
| `for await (const chunk of readable)` | Async iteration                                                   |
| `readable.setEncoding('utf8')`        | Receive strings instead of Buffers                                |

### The `highWaterMark` — how much the stream buffers

```js
// File: high-water-mark.mjs
import { createReadStream } from 'node:fs';

// highWaterMark is the internal buffer size in BYTES.
// Defaults: 64 KiB for files, 16 KiB for most other streams, 16 KiB for sockets.
const stream = createReadStream('./package.json', { highWaterMark: 16 * 1024 });
console.log('file stream highWaterMark:', stream.readableHighWaterMark); // 16384

let chunks = 0;
for await (const chunk of stream) {
  chunks += 1;
  console.log(`chunk ${chunks}: ${chunk.length} bytes`);
}
```

It is a _threshold_, not a limit — a stream may deliver bigger chunks. Its role: it is the amount of buffering the stream is willing to do before it signals "slow down" to its source (backpressure).

***

## 4. Writable streams and backpressure — the crucial concept

```js
// File: write-backpressure.mjs
import { createWriteStream } from 'node:fs';
import { once } from 'node:events';

const writable = createWriteStream('./big.txt');

console.log('writable highWaterMark:', writable.writableHighWaterMark);

// write() returns false when the internal buffer is FULL — the signal to stop producing.
let produced = 0;
let canContinue = true;

while (canContinue && produced < 50_000) {
  const line = `line ${produced} — ${'x'.repeat(50)}\n`;
  produced += 1;
  canContinue = writable.write(line);

  if (!canContinue) {
    // Wait for the buffer to drain before writing more.
    await once(writable, 'drain');
    canContinue = true;
  }
}

writable.end();                       // no more writes; flushes and closes
await once(writable, 'finish');

console.log(`wrote ${produced} lines`);
```

### Why backpressure matters (the professional part)

Without backpressure, a fast producer feeds a slow consumer, and the data piles up in memory until the process dies:

```
Fast source (disk read at 2 GB/s)
        │
        ▼
   [ unbounded buffer ]  ← memory grows without limit
        │
        ▼
Slow destination (network at 10 MB/s)
```

With backpressure:

```
Fast source
        │  write() returns false
        ▼
   [ bounded buffer: highWaterMark ]
        │  'drain' event when it empties
        ▼
Slow destination ──▶ producer waits, memory stays flat
```

Concretely, that is why:

* A file upload endpoint that streams does not care whether the client is on fibre or 2G.
* A proxy (`nginx`, a Node reverse proxy) does not need gigabytes of RAM per connection.
* `pipeline()` can copy a 50 GB file on a 256 MB container.

**The rule: never write to a stream in a loop without checking the return value of `write()` and waiting for `'drain'` — or, better, let `pipeline()` do it for you.**

***

## 5. `pipe()` vs `pipeline()` — use `pipeline()`

```js
// File: pipe-vs-pipeline.mjs
import { createReadStream, createWriteStream } from 'node:fs';
import { createGzip } from 'node:zlib';
import { pipeline } from 'node:stream/promises';

// ⚠️ pipe() does NOT propagate errors and does NOT clean up.
//    If the read fails, the write stream stays open and the process may hang.
createReadStream('./package.json')
  .pipe(createGzip())
  .pipe(createWriteStream('./package.json.gz'));

// ✅ pipeline() propagates errors, destroys every stream on failure, and can be awaited.
try {
  await pipeline(
    createReadStream('./package.json'),
    createGzip(),
    createWriteStream('./package.json.gz')
  );
  console.log('compressed successfully');
} catch (error) {
  console.error('pipeline failed:', error.message);
  process.exitCode = 1;
}
```

|                    | `pipe()`                                   | `pipeline()`                       |
| ------------------ | ------------------------------------------ | ---------------------------------- |
| Error propagation  | ❌ Only to the first stream; others leak    | ✅ To the returned promise/callback |
| Cleanup on failure | ❌ Streams may stay open, file handles leak | ✅ All streams destroyed            |
| Awaitable          | ❌                                          | ✅ (`node:stream/promises`)         |
| Backpressure       | ✅                                          | ✅                                  |
| Recommendation     | Legacy code only                           | **Always**                         |

The classic symptom of `pipe()`-based code: **the process hangs after an error**, because a read stream errored but the write stream still holds the event loop open.

***

## 6. Transform streams — processing data as it flows

```js
// File: transforms.mjs
import { Transform, pipeline } from 'node:stream';
import { promisify } from 'node:util';

// A custom transform: uppercase text and count lines.
// NOTE: a real transform must respect chunk boundaries — a chunk is NOT a line.
class UppercaseLines extends Transform {
  #remainder = '';
  #lineCount = 0;

  _transform(chunk, encoding, callback) {
    const text = this.#remainder + chunk.toString('utf8');
    const lines = text.split('\n');
    this.#remainder = lines.pop() ?? '';         // keep the incomplete tail
    this.#lineCount += lines.length;

    const output = lines.map((line) => line.toUpperCase()).join('\n');
    callback(null, output.length > 0 ? `${output}\n` : '');
  }

  _flush(callback) {
    // Called once at the end: flush any buffered tail.
    if (this.#remainder) {
      this.#lineCount += 1;
      this.push(`${this.#remainder.toUpperCase()}\n`);
    }
    console.log(`[transform] processed ${this.#lineCount} lines`);
    callback();
  }
}

// Demonstrate with a source of text.
import { Readable } from 'node:stream';
import { once } from 'node:events';
import { Writable } from 'node:stream';

const collected = [];
const collector = new Writable({
  write(chunk, encoding, callback) {
    collected.push(chunk.toString('utf8'));
    callback();
  },
});

await pipeline(
  Readable.from(['first line\nsecond ', 'line\nthird li', 'ne\npartial']),
  new UppercaseLines(),
  collector
);

console.log(collected.join(''));
console.log('---');
console.log('line count check passed:', collected.join('').includes('THIRD LINE'));
```

**Why the `_flush` and `#remainder` handling matter:** stream chunks are arbitrary byte ranges, not lines. `"third li" | "ne\n"` splits a line across two chunks. Code that naively does `chunk.toString().split('\n')` per chunk produces corrupted output on real data — a bug that only appears with large files, never in your unit test with one small input. This is the single most common stream bug.

### Built-in transforms you will use

```js
// File: builtin-transforms.mjs
import { createReadStream, createWriteStream } from 'node:fs';
import { createGzip, createGunzip } from 'node:zlib';
import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto';
import { pipeline } from 'node:stream/promises';

// 1. Compress
await pipeline(
  createReadStream('./package.json'),
  createGzip(),
  createWriteStream('./archive/package.json.gz')
);

// 2. Decompress
await pipeline(
  createReadStream('./archive/package.json.gz'),
  createGunzip(),
  createWriteStream('./archive/restored.json')
);

// 3. Encrypt (AES-256-GCM: authenticated encryption)
const key = randomBytes(32);
const iv = randomBytes(12);
await pipeline(
  createReadStream('./package.json'),
  createCipheriv('aes-256-gcm', key, iv),
  createWriteStream('./archive/package.json.enc')
);
console.log('wrote compressed and encrypted copies');

// 4. Decrypt — note: GCM requires the auth tag, which must be stored with the ciphertext.
//    Shown here only to demonstrate the transform shape.
void createDecipheriv;
```

***

## 7. Object-mode streams

Streams are not limited to bytes. With `objectMode: true`, each "chunk" is any JavaScript value:

```js
// File: object-mode.mjs
import { Readable, Transform, Writable } from 'node:stream';
import { pipeline } from 'node:stream/promises';

const source = Readable.from(
  [
    { id: 1, amount: 2500 },
    { id: 2, amount: 0 },
    { id: 3, amount: 19900 },
    { id: 4, amount: -50 },
  ],
  { objectMode: true }
);

// Transform: keep only valid rows and normalise them.
const validate = new Transform({
  objectMode: true,
  transform(row, encoding, callback) {
    if (!Number.isInteger(row.amount) || row.amount <= 0) {
      return callback(null, null);         // drop invalid row (callback with no value)
    }
    return callback(null, { id: row.id, amountInRupees: row.amount / 100 });
  },
});

// Writable: batch into a database insert every N rows.
class BatchWriter extends Writable {
  #buffer = [];
  #batchSize;
  #batches = 0;

  constructor({ batchSize = 2, ...options } = {}) {
    super({ objectMode: true, ...options });
    this.#batchSize = batchSize;
  }

  async _write(row, encoding, callback) {
    this.#buffer.push(row);
    if (this.#buffer.length >= this.#batchSize) {
      await this.#flushBatch();
    }
    callback();
  }

  async _final(callback) {
    await this.#flushBatch();
    callback();
  }

  async #flushBatch() {
    if (this.#buffer.length === 0) return;
    this.#batches += 1;
    // A real implementation inserts here: await db.collection.insertMany(this.#buffer)
    console.log(`[batch ${this.#batches}] inserting`, this.#buffer);
    this.#buffer = [];
  }
}

await pipeline(source, validate, new BatchWriter({ batchSize: 2 }));
```

```
[batch 1] inserting [ { id: 1, amountInRupees: 25 }, { id: 3, amountInRupees: 199 } ]
```

This is exactly the shape of a **bulk import** (CSV → validate → batch insert), and of the `pipeline()` loops you will build in the projects section. Object mode is what makes streams useful for data engineering, not just for bytes.

***

## 8. Real-world patterns

### Pattern 1: streaming a file download

```js
// File: download.example.js
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { pipeline } from 'node:stream/promises';

export async function sendFile(res, filePath, { contentType = 'application/octet-stream' } = {}) {
  try {
    const info = await stat(filePath);                 // fails with ENOENT if missing
    if (!info.isFile()) return res.status(404).json({ error: { code: 'NOT_FOUND' } });

    res.status(200);
    res.setHeader('Content-Type', contentType);
    res.setHeader('Content-Length', info.size);        // lets the client show a progress bar
    res.setHeader('Last-Modified', info.mtime.toUTCString());
    res.setHeader('Content-Disposition', `attachment; filename="${encodeURIComponent(filePath.split('/').pop())}"`);

    await pipeline(createReadStream(filePath), res);   // streams the file to the socket
  } catch (error) {
    if (error.code === 'ENOENT') {
      return res.status(404).json({ error: { code: 'NOT_FOUND' } });
    }
    // If the client aborted, we get ERR_STREAM_PREMATURE_CLOSE — not a server error.
    if (error.code === 'ERR_STREAM_PREMATURE_CLOSE') return undefined;
    throw error;
  }
}
```

### Pattern 2: CSV export of a large table, streamed

```js
// File: csv-export.example.js
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { Readable } from 'node:stream';

// Escape a CSV field: wrap in quotes and double any internal quotes.
const csvField = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`;

function toCsvRow(row, columns) {
  return `${columns.map((column) => csvField(row[column])).join(',')}\n`;
}

/**
 * Streams rows (from a DB cursor, a file, anything iterable) as CSV.
 * Memory stays bounded regardless of table size — the difference between
 * "exports 2 million rows" and "the container gets OOM-killed".
 */
export async function streamCsv(res, rowSource, columns) {
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="export.csv"');

  const header = `${columns.map(csvField).join(',')}\n`;

  const rowTransform = new Transform({
    objectMode: true,
    transform(row, encoding, callback) {
      callback(null, toCsvRow(row, columns));
    },
  });

  res.write(header);
  await pipeline(Readable.from(rowSource, { objectMode: true }), rowTransform, res);
}
```

```js
// Usage sketch inside a controller (the database part arrives in the MySQL chapter):
// const cursor = db.collection('employees').find({}).stream();   // MongoDB
// await streamCsv(res, cursor, ['id', 'name', 'department', 'createdAt']);
```

### Pattern 3: proxying/aggregating upstream responses

```js
// File: proxy.example.js
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';

export async function proxyJson(req, res, upstreamUrl) {
  const upstream = await fetch(upstreamUrl, {
    method: req.method,
    headers: { accept: 'application/json' },
    signal: AbortSignal.timeout(5_000),          // never hang forever
  });

  res.status(upstream.status);
  res.setHeader('Content-Type', upstream.headers.get('content-type') ?? 'application/json');

  // Stream the upstream body straight through instead of buffering it.
  if (!upstream.body) return res.end();
  await pipeline(Readable.fromWeb(upstream.body), res);
}
```

`Readable.fromWeb()` converts a web `ReadableStream` (from `fetch`) into a Node stream — the bridge between the two worlds, and something you will need constantly.

***

## 9. Common mistakes

| Mistake                                                 | Symptom                                 | Fix                                                     |
| ------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------- |
| Assuming a chunk is a line / a whole message            | Corrupted output on large inputs        | Buffer the remainder (`_transform` + `_flush`)          |
| Using `pipe()` instead of `pipeline()`                  | Hangs after errors, leaked file handles | `pipeline()` from `node:stream/promises`                |
| Ignoring `write()`'s return value                       | Unbounded memory growth                 | Check it and wait for `'drain'`, or use `pipeline()`    |
| Buffering a stream into memory (`await streamToBuffer`) | OOM on large files                      | Stream it end to end                                    |
| Not handling `'error'` on every stream                  | Process crash, hanging requests         | `pipeline()` or explicit error listeners                |
| Reading `req.body` for a file upload                    | Whole file in RAM                       | Stream `req` to disk/object storage                     |
| Forgetting to destroy streams on client abort           | Leaks sockets and file handles          | `pipeline` handles it; check `req.aborted`/`res.closed` |
| Using `JSON.parse` on a stream directly                 | Crash on partial data                   | Collect until complete, or use a streaming JSON parser  |
| `highWaterMark` set huge "for speed"                    | Memory blowups under concurrency        | Keep it modest; measure                                 |
| Mixing `'data'` listeners and `for await`               | Data loss (the two modes conflict)      | Pick one consumption style                              |

***

## Exercise 9.1 — A log analyser

Build a program that streams a large log file (you can generate one first) and produces a summary without ever loading the whole file into memory: total lines, count per level (`INFO`/`WARN`/`ERROR`), and the five slowest requests (from lines containing `took=<n>ms`).

<details>

<summary>Solution</summary>

```js
// File: generate-log.mjs — creates a 200k-line sample log
import { createWriteStream } from 'node:fs';
import { once } from 'node:events';

const LEVELS = ['INFO', 'INFO', 'INFO', 'WARN', 'ERROR'];   // weighted
const PATHS = ['/api/v1/users', '/api/v1/orders', '/api/v1/health', '/api/v1/products'];

const stream = createWriteStream('./logs/app.log');
const startTime = Date.now();

for (let i = 0; i < 200_000; i += 1) {
  const level = LEVELS[Math.floor(Math.random() * LEVELS.length)];
  const path = PATHS[Math.floor(Math.random() * PATHS.length)];
  const ms = Math.floor(Math.random() * 900) + 20;
  const time = new Date(startTime + i).toISOString();
  // Respect backpressure even in a generator script.
  if (!stream.write(`${time} ${level} ${path} status=200 took=${ms}ms\n`)) {
    await once(stream, 'drain');
  }
}

stream.end();
await once(stream, 'finish');
console.log('generated logs/app.log with 200000 lines');
```

```js
// File: analyse-log.mjs
import { createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';

export async function analyseLog(filePath) {
  const summary = { totalLines: 0, byLevel: { INFO: 0, WARN: 0, ERROR: 0 }, slowest: [] };
  const SLOWEST_KEPT = 5;

  const fileStream = createReadStream(filePath, { encoding: 'utf8' });
  // crlfDelay: handles Windows line endings correctly.
  const lines = createInterface({ input: fileStream, crlfDelay: Infinity });

  for await (const line of lines) {
    summary.totalLines += 1;

    // Cheap checks first; parse only what is needed.
    if (line.includes(' INFO ')) summary.byLevel.INFO += 1;
    else if (line.includes(' WARN ')) summary.byLevel.WARN += 1;
    else if (line.includes(' ERROR ')) summary.byLevel.ERROR += 1;

    const tookMatch = line.match(/took=(\d+)ms/);
    if (tookMatch) {
      const ms = Number(tookMatch[1]);
      // Keep a bounded top-K list instead of storing every line: memory stays O(K).
      if (
        summary.slowest.length < SLOWEST_KEPT ||
        ms > summary.slowest[summary.slowest.length - 1].ms
      ) {
        summary.slowest.push({ ms, line: line.trim() });
        summary.slowest.sort((a, b) => b.ms - a.ms);
        summary.slowest.length = Math.min(summary.slowest.length, SLOWEST_KEPT);
      }
    }
  }

  return summary;
}

const before = process.memoryUsage().heapUsed;
const summary = await analyseLog('./logs/app.log');
const after = process.memoryUsage().heapUsed;

console.log('total lines :', summary.totalLines);
console.log('by level    :', summary.byLevel);
console.log('\nslowest 5:');
for (const { ms, line } of summary.slowest) {
  console.log(`  ${String(ms).padStart(4)}ms  ${line}`);
}
console.log(`\nheap delta  : ${((after - before) / 1024 / 1024).toFixed(2)} MB (should be a few MB, not 30+)`);
```

**Expected output**

```
total lines : 200000
by level    : { INFO: 120022, WARN: 39914, ERROR: 40064 }

slowest 5:
   919ms  2026-09-18T10:20:11.402Z INFO /api/v1/orders status=200 took=919ms
   919ms  2026-09-18T10:19:44.118Z ERROR /api/v1/users status=200 took=919ms
   918ms  …
   918ms  …

heap delta  : 2.14 MB (should be a few MB, not 30+)
```

**Why this is the right shape**

| Decision                        | Reason                                                           |
| ------------------------------- | ---------------------------------------------------------------- |
| `createReadStream` + `readline` | Constant memory; the file never fully materialises               |
| `for await`                     | Backpressure is handled for you — no `'data'`/`'drain'` juggling |
| Bounded top-K list              | Storing every candidate would grow with the file                 |
| Substring checks before regex   | Cheaper per line; matters at millions of lines                   |
| `crlfDelay: Infinity`           | Correctly handles `\r\n` files, e.g. logs copied from Windows    |

**Compare with the naive version** — `const text = await readFile(path, 'utf8'); text.split('\n')` — which needs \~3× the file size in memory (buffer + string + array of strings) and dies on a 5 GB log. The streaming version analyses any size in a few MB.

**Follow-up challenges**

* Add per-endpoint p95 latency (keep a bounded histogram rather than all values).
* Handle malformed lines without crashing, and report `unparsedLines`.
* Write the summary out as JSON **via a stream** so it works even for huge outputs.
* Run the analyser against a `gzip`ed log: insert `createGunzip()` into the pipeline and notice that nothing else in your code has to change.

</details>

## Exercise 9.2 — Debug the hanging process

```js
// File: hang.mjs
import { createReadStream, createWriteStream } from 'node:fs';

createReadStream('./does-not-exist.txt')
  .pipe(createWriteStream('./out.txt'));

console.log('done');
```

It prints `done`, then hangs instead of exiting — or crashes with an unhandled error. Explain both behaviours and fix it.

<details>

<summary>Solution</summary>

**What happens:** `createReadStream` emits `'error'` (ENOENT) asynchronously, _after_ the synchronous part of the script has finished. With `pipe()`:

* There is **no `'error'` listener**, so the error is emitted on the read stream. For streams (unlike a bare `EventEmitter`), an unhandled `'error'` throws — in newer Node this crashes the process with an unhandled error; in some arrangements the error is simply not connected to the destination.
* Meanwhile the **write stream was already created and opened**, so it holds an open file descriptor. That open handle keeps the event loop alive. Since nothing closes or destroys it, the process never exits, and you see the "prints done, then hangs" behaviour.

`pipe()` forwards data and end-of-stream, but **not errors** to the next stream — that is the documented behaviour, and it is exactly why `pipeline()` exists.

**Fixed version:**

```js
// File: no-hang.mjs
import { createReadStream, createWriteStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';

try {
  await pipeline(createReadStream('./does-not-exist.txt'), createWriteStream('./out.txt'));
  console.log('copied successfully');
} catch (error) {
  console.error('copy failed:', error.code, error.message);   // ENOENT … no such file or directory
  process.exitCode = 1;
}
console.log('process will now exit cleanly');
```

`pipeline()` destroys **every** stream in the chain when any of them fails: the write stream is closed, the file descriptor is released, and the event loop drains so the process exits.

**The generalisable rules**

1. Every stream needs an error path. `pipeline()` is the shortest path to having one.
2. A hanging Node process after "success" output almost always means **an open handle**: an unclosed stream, an unclosed server, an interval, or a socket.
3.  To diagnose which handle is keeping the process alive:

    ```js
    process.on('beforeExit', () => {
      // This runs only when the event loop is empty — so it never fires when something leaks.
      console.log('event loop drained');
    });
    ```

    or inspect with:

    ```bash
    node --inspect hang.mjs
    # DevTools → Memory → "Detached elements"/heap snapshot, or use:
    node -e "process._getActiveHandles().forEach(h => console.log(h.constructor.name))"
    ```

    (The last one is a private API — handy for debugging, not for production code.)

</details>

***

## What's next

Streams move bytes; now let's look at what those bytes actually are in Node — `Buffer`, the type that represents raw binary data, and the encoding rules that explain most "why is my file corrupted?" bugs.

→ [10 — Buffers](10-buffers.md)
