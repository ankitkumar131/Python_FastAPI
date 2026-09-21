# 06 — The fs Module

> **Where this fits:** The `fs` (file system) module is how Node reads and writes files: configuration, logs, uploads, CSV/JSON imports and exports, generated reports. It is also where you learn the difference between blocking and non-blocking I/O in the most concrete way possible — which is why it comes before streams, HTTP and the event loop.

***

## 1. What is `fs`, and why does it exist?

JavaScript in a browser cannot touch the file system (by design — a web page must not read your documents). A server obviously must. So Node provides **`node:fs`**: a binding to the operating system's file APIs.

```js
// File: first-fs.mjs
import fs from 'node:fs';

// Synchronous: blocks the thread until the read finishes.
const packageJson = JSON.parse(fs.readFileSync('./package.json', 'utf8'));
console.log('name:', packageJson.name);

// Asynchronous, callback style (the original Node API)
fs.readFile('./package.json', 'utf8', (error, data) => {
  if (error) {
    console.error('read failed:', error.message);
    return;
  }
  console.log('name (callback):', JSON.parse(data).name);
});
```

That example shows the three API styles you must be able to recognise — and they exist because of history:

| Style       | Introduced    | Shape                                              | Use it?                                 |
| ----------- | ------------- | -------------------------------------------------- | --------------------------------------- |
| Synchronous | The beginning | `fs.readFileSync(path, 'utf8')` → returns the data | Only at startup or in scripts           |
| Callback    | The beginning | `fs.readFile(path, 'utf8', (err, data) => …)`      | Rarely — legacy code and streaming APIs |
| **Promise** | Node 10+      | `await fsPromises.readFile(path, 'utf8')`          | ✅ **Yes — the default choice**          |

```js
// File: promise-style.mjs
import { readFile, writeFile, mkdir } from 'node:fs/promises';

try {
  const data = await readFile('./package.json', 'utf8');
  console.log('name:', JSON.parse(data).name);
} catch (error) {
  console.error('read failed:', error.code, error.message);
}
```

`node:fs/promises` exports the same functions with promises instead of callbacks — designed for `async`/`await`.

***

## 2. The synchrony decision (the important part)

> **Internally:** `readFileSync` asks the OS for the file and does not return until the bytes are in memory. During that time, the event loop cannot run a single callback — no other request is served, no timer fires. `readFile` (the promise/callback version) hands the job to libuv's thread pool (4 threads by default) and returns immediately; when the data is ready, the callback is queued on the event loop.

```
readFileSync:   [====wait for disk====][run rest of my code]  ← everything else in the app waits
                (event loop blocked)

readFile:       [submit to thread pool] → [handle other requests] → callback fires later
                (event loop free)
```

**The rule:** `*Sync` methods are acceptable in a CLI or during application startup (where nothing else exists to block). They are **not** acceptable inside a request handler. One `readFileSync` of a slow file can stall every concurrent user of your API.

```js
// ❌ In a route handler — blocks the whole server for the duration of the read.
app.get('/report', (req, res) => {
  const html = fs.readFileSync('./templates/report.html', 'utf8');
  res.type('html').send(html);
});

// ✅ Non-blocking.
app.get('/report', async (req, res) => {
  const html = await readFile('./templates/report.html', 'utf8');
  res.type('html').send(html);
});
```

(For a _static file_ you would use `res.sendFile()`, which streams — see streams below.)

***

## 3. Reading files

### Small files: read the whole thing

```js
// File: read-all.mjs
import { readFile } from 'node:fs/promises';

// 1. As text
const text = await readFile('./notes.txt', 'utf8');
console.log('chars:', text.length);

// 2. As a Buffer (no encoding argument) — raw bytes
const bytes = await readFile('./logo.png');
console.log('bytes:', bytes.length, 'isBuffer:', Buffer.isBuffer(bytes));

// 3. JSON — the pattern you will write constantly
async function readJson(filePath) {
  const raw = await readFile(filePath, 'utf8');
  return JSON.parse(raw);
}

const config = await readJson('./package.json');
console.log('version:', config.version);
```

> **Always pass `'utf8'` when reading text.** Without it you get a `Buffer`, and `buffer.toString()` in every operation. Passing the encoding is both shorter and clearer about intent.

### Large files: never read the whole thing into memory

```js
// File: read-large.mjs
import { createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';

// Process a 2 GB log file line by line with constant memory usage (~a few KB).
const stream = createReadStream('./huge.log', { encoding: 'utf8' });
const lines = createInterface({ input: stream, crlfDelay: Infinity });

let errorCount = 0;
let lineCount = 0;

for await (const line of lines) {
  lineCount += 1;
  if (line.includes(' ERROR ')) errorCount += 1;
}

console.log(`scanned ${lineCount} lines, found ${errorCount} errors`);
```

A 2 GB file read with `readFile` needs 2 GB (plus the string copy) — and in a 512 MB container, that is a crash. Streaming is covered in depth in [09 — Streams](09-streams.md); this is the practical rule: **if the size is not bounded and small, stream it.**

***

## 4. Writing files

```js
// File: write-files.mjs
import { writeFile, appendFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

// 1. Write (creates the file, or TRUNCATES it if it exists — data loss if you are wrong)
await writeFile('./output.txt', 'Hello, file system!\n', 'utf8');

// 2. Append (safe for logs)
await appendFile('./output.txt', 'A second line\n', 'utf8');

// 3. Write JSON, human-readable
await writeFile('./config-backup.json', JSON.stringify({ port: 3000 }, null, 2));

// 4. Write to a nested path — the directory must exist first
const nestedDir = path.join(import.meta.dirname, 'data', '2026', '09');
await mkdir(nestedDir, { recursive: true });     // recursive: true is essential
await writeFile(path.join(nestedDir, 'summary.json'), JSON.stringify({ ok: true }));

console.log('done');
```

### Atomic writes: the pattern that prevents corrupted files

If the process is killed _during_ `writeFile`, you are left with a half-written file. For config, state, or anything another process reads, write to a temporary file and rename it. A rename within the same file system is atomic — readers see either the old file or the new one, never a mixture:

```js
// File: atomic-write.mjs
import { writeFile, rename, rm } from 'node:fs/promises';
import path from 'node:path';

async function writeFileAtomic(filePath, contents) {
  const tempPath = `${filePath}.${process.pid}.tmp`;
  try {
    await writeFile(tempPath, contents, 'utf8');
    await rename(tempPath, filePath);   // atomic on POSIX when on the same filesystem
  } catch (error) {
    await rm(tempPath, { force: true }); // clean up the temp file on failure
    throw error;
  }
}

await writeFileAtomic('./atomic.txt', 'This will never be seen half-written.\n');
console.log('written atomically');
```

This is exactly how databases and editors avoid corrupting your data — and the technique the `write-file-atomic` package and most lockfile writers use.

***

## 5. Directories, metadata and existence

```js
// File: fs-metadata.mjs
import { stat, lstat, access, readdir, mkdir, rm, cp } from 'node:fs/promises';
import { constants } from 'node:fs';

// Metadata about a file or directory
const info = await stat('./package.json');
console.log({
  isFile: info.isFile(),
  isDirectory: info.isDirectory(),
  sizeBytes: info.size,
  modified: info.mtime.toISOString(),
  created: info.birthtime.toISOString(),
});

// stat() follows symlinks; lstat() does not (it reports the link itself)
const linkInfo = await lstat('./some-symlink').catch(() => null);
console.log('is symlink:', linkInfo?.isSymbolicLink());

// Does it exist? — the modern way: try to access it
async function exists(filePath) {
  try {
    await access(filePath, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

console.log('package.json exists:', await exists('./package.json'));
console.log('nope.txt exists:', await exists('./nope.txt'));

// List a directory
const entries = await readdir(import.meta.dirname, { withFileTypes: true });
for (const entry of entries.slice(0, 5)) {
  console.log(entry.isDirectory() ? 'DIR ' : 'FILE', entry.name);
}

// Remove / copy
await mkdir('./scratch', { recursive: true });
await cp('./package.json', './scratch/copy.json');
await rm('./scratch', { recursive: true, force: true });

console.log('cleanup complete');
```

> **A note on `fs.existsSync`:** it exists and it is convenient, but it is a race condition by design — the file can be deleted between the check and your next operation. Prefer "attempt the operation and handle `ENOENT`" (try/catch) over check-then-act.

***

## 6. Error codes you will actually see

Node file errors are `Error` objects with a `code` property. Handling by code (not by message text) is what makes code robust across platforms and Node versions:

```js
// File: fs-errors.mjs
import { readFile } from 'node:fs/promises';

async function safeRead(filePath, fallback = null) {
  try {
    return await readFile(filePath, 'utf8');
  } catch (error) {
    switch (error.code) {
      case 'ENOENT':
        console.warn(`${filePath} does not exist — using fallback`);
        return fallback;
      case 'EACCES':
        console.error(`${filePath} is not readable — check permissions`);
        throw error;
      case 'EISDIR':
        console.error(`${filePath} is a directory, not a file`);
        throw error;
      default:
        throw error; // unknown: let it bubble up
    }
  }
}

console.log(await safeRead('./does-not-exist.txt', 'default value'));
```

| Code              | Meaning                                         | Usual cause                                                   |
| ----------------- | ----------------------------------------------- | ------------------------------------------------------------- |
| `ENOENT`          | No such file or directory                       | Wrong path, file not created, typo, wrong `cwd`               |
| `EACCES`          | Permission denied                               | Wrong file mode, running as the wrong user (common in Docker) |
| `EEXIST`          | File already exists                             | `mkdir` without `recursive`, `copyFile` with `COPYFILE_EXCL`  |
| `EISDIR`          | Is a directory                                  | Trying to read a directory as a file                          |
| `ENOTDIR`         | Not a directory                                 | A path component is a file                                    |
| `ENOSPC`          | No space left on device                         | Full disk — a real production incident                        |
| `EMFILE`          | Too many open files                             | File descriptor leak: opening files without closing them      |
| `EPERM` / `EROFS` | Operation not permitted / read-only file system | Immutable container filesystem, mounted volume                |

`ENOENT` on a path that "definitely exists" is almost always a **`process.cwd()` problem** (see [03 §6](03-nodejs-basics.md)).

***

## 7. Watching files (dev tooling)

```js
// File: watch-demo.mjs
import { watch } from 'node:fs';

// Recursive watching (recursive: true works on macOS and Windows; on Linux it works
// in recent Node versions too, but verify for your platform/version).
const watcher = watch('./src', { recursive: true }, (eventType, filename) => {
  console.log(`[${new Date().toISOString()}] ${eventType}: ${filename}`);
});

console.log('Watching ./src — press Ctrl+C to stop');

process.on('SIGINT', () => {
  watcher.close();
  process.exit(0);
});
```

Facts about `fs.watch`:

* It is **platform-dependent** (inotify, FSEvents, ReadDirectoryChangesW) and can emit duplicate or coalesced events.
* It does not tell you _what_ changed — only that something did.
* For a development reloader, `node --watch` (built in) or `chokidar` (battle-tested, cross-platform, handles editor write patterns) are better choices.

***

## 8. A complete, realistic example: a JSON-file data store

This is the classic "no database yet" exercise, done properly: atomic writes, concurrent-safe, with the same interface a database layer would expose. You will extend this in [18 — Node.js Project](18-nodejs-project.md).

```js
// File: src/lib/jsonStore.mjs
import { readFile, writeFile, rename, mkdir } from 'node:fs/promises';
import path from 'node:path';

/**
 * A tiny persistent store backed by a single JSON file.
 *
 * - Loads the file once into memory (fine for small datasets).
 * - Writes atomically (temp file + rename) so a crash cannot corrupt the file.
 * - Serialises writes and coalesces bursts, so concurrent requests cannot
 *   interleave and lose data.
 */
export function createJsonStore({ filePath, defaultData = [] }) {
  let cache = null;
  let writePromise = Promise.resolve();
  let dirty = false;

  async function load() {
    if (cache !== null) return cache;
    try {
      const raw = await readFile(filePath, 'utf8');
      cache = JSON.parse(raw);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
      cache = structuredClone(defaultData);
      await mkdir(path.dirname(filePath), { recursive: true });
      await persist();
    }
    return cache;
  }

  async function persist() {
    dirty = true;
    // Chain writes: each waits for the previous one, and bursts collapse into one write.
    writePromise = writePromise.then(async () => {
      if (!dirty) return;
      dirty = false;
      const tempPath = `${filePath}.${process.pid}.tmp`;
      await writeFile(tempPath, JSON.stringify(cache, null, 2), 'utf8');
      await rename(tempPath, filePath);
    });
    return writePromise;
  }

  return {
    async all() {
      return structuredClone(await load());
    },
    async findById(id) {
      const items = await load();
      return items.find((item) => String(item.id) === String(id)) ?? null;
    },
    async insert(item) {
      const items = await load();
      items.push(item);
      await persist();
      return structuredClone(item);
    },
    async update(id, patch) {
      const items = await load();
      const index = items.findIndex((item) => String(item.id) === String(id));
      if (index === -1) return null;
      items[index] = { ...items[index], ...patch };
      await persist();
      return structuredClone(items[index]);
    },
    async remove(id) {
      const items = await load();
      const index = items.findIndex((item) => String(item.id) === String(id));
      if (index === -1) return false;
      items.splice(index, 1);
      await persist();
      return true;
    },
  };
}
```

```js
// File: try-store.mjs
import path from 'node:path';
import { createJsonStore } from './src/lib/jsonStore.mjs';
import { randomUUID } from 'node:crypto';

const store = createJsonStore({
  filePath: path.join(import.meta.dirname, 'data', 'notes.json'),
});

const created = await store.insert({ id: randomUUID(), title: 'Learn fs', done: false });
console.log('created:', created.title);

// Twenty concurrent inserts: without the write queue, this is where data gets lost.
await Promise.all(
  Array.from({ length: 20 }, (_, i) =>
    store.insert({ id: randomUUID(), title: `Note ${i + 1}`, done: i % 2 === 0 })
  )
);

console.log('total after concurrent inserts:', (await store.all()).length); // 21
console.log('first:', (await store.findById(created.id)).title);
```

**Why the details matter:**

| Detail                             | Reason                                                                        |
| ---------------------------------- | ----------------------------------------------------------------------------- |
| Temp file + `rename`               | A crash mid-write leaves the old file intact instead of a truncated JSON file |
| `mkdir(..., { recursive: true })`  | The `data/` directory may not exist on a fresh checkout                       |
| Write queue (`writePromise` chain) | Concurrent writes would otherwise interleave and lose updates                 |
| `dirty` flag                       | Collapses a burst of 20 writes into far fewer disk writes                     |
| `structuredClone` on read          | Callers cannot mutate the cache accidentally — a real bug class               |
| `ENOENT` handled explicitly        | First run must create the file, not crash                                     |

This is also a preview of something important: **this is what a repository layer looks like.** When you swap it for MongoDB in 03-databases/02-mongodb/10 _(not available in this published source revision)_, the controllers will not change, because they never knew it was a file.

***

## 9. Common mistakes

| Mistake                                          | Consequence                                                | Fix                                                                  |
| ------------------------------------------------ | ---------------------------------------------------------- | -------------------------------------------------------------------- |
| `readFileSync` in a request handler              | Blocks the event loop for every user                       | `await readFile(...)`                                                |
| No encoding argument                             | You get a `Buffer`, then `[object Object]`-style confusion | Pass `'utf8'`                                                        |
| Relative paths                                   | Breaks when `cwd` changes                                  | `path.join(import.meta.dirname, …)`                                  |
| Assuming the directory exists                    | `ENOENT` on first run                                      | `mkdir(dir, { recursive: true })`                                    |
| `JSON.parse` unguarded on a file                 | `SyntaxError` kills the process                            | try/catch → clear error, or validate                                 |
| Reading a huge file with `readFile`              | Out-of-memory crash                                        | Stream it                                                            |
| Non-atomic writes of important files             | Truncated/corrupt file after a crash                       | Temp file + rename                                                   |
| Ignoring the error argument                      | Silent failures                                            | Always handle or `throw`                                             |
| `watch` without closing                          | Handle leak, process never exits                           | Keep the watcher and `.close()` on shutdown                          |
| Opening many files without limits                | `EMFILE`                                                   | Streams close themselves; use `graceful-fs` or a queue for bulk work |
| Writing to `node_modules` or app code at runtime | Read-only in production                                    | Write to a volume/`/tmp`/object storage                              |

***

## Exercise 6.1 — Log rotation

Write `appendLog(filePath, message)` that appends an ISO-timestamped line, and a companion `rotateIfTooBig(filePath, maxBytes)` that renames the file to `.1` (keeping one previous generation) when it exceeds the limit. Then demonstrate both with a script.

<details>

<summary>Solution</summary>

```js
// File: logger-lite.mjs
import { appendFile, stat, rename, mkdir } from 'node:fs/promises';
import path from 'node:path';

export async function appendLog(filePath, message) {
  await mkdir(path.dirname(filePath), { recursive: true });
  const line = `${new Date().toISOString()} ${message}\n`;
  // appendFile opens with the 'a' flag: the OS guarantees the write goes to the end,
  // so concurrent appends do not overwrite each other.
  await appendFile(filePath, line, 'utf8');
}

export async function rotateIfTooBig(filePath, maxBytes = 1024) {
  try {
    const { size } = await stat(filePath);
    if (size < maxBytes) return false;

    // Keep exactly one previous generation: app.log → app.log.1 (overwriting any old .1).
    await rename(filePath, `${filePath}.1`);
    return true;
  } catch (error) {
    if (error.code === 'ENOENT') return false; // nothing to rotate
    throw error;
  }
}
```

```js
// File: rotate-demo.mjs
import path from 'node:path';
import { appendLog, rotateIfTooBig } from './logger-lite.mjs';
import { readFile, rm } from 'node:fs/promises';

const logPath = path.join(import.meta.dirname, 'logs', 'app.log');
await rm(path.dirname(logPath), { recursive: true, force: true }); // clean slate for the demo

for (let i = 1; i <= 40; i += 1) {
  await appendLog(logPath, `request ${i} completed in ${i * 3}ms`);
  const rotated = await rotateIfTooBig(logPath, 1024);
  if (rotated) console.log(`rotated after request ${i}`);
}

const current = await readFile(logPath, 'utf8');
const previous = await readFile(`${logPath}.1`, 'utf8');

console.log('current lines :', current.trim().split('\n').length);
console.log('previous lines:', previous.trim().split('\n').length);
console.log('current first :', current.split('\n')[0]);
```

Expected output:

```
rotated after request 12
rotated after request 24
rotated after request 36
current lines : 4
previous lines: 12
current first : 2026-09-18T10:15:30.123Z request 37 completed in 111ms
```

**Notes on the design**

* **Append (`'a'`) is atomic for small writes** on POSIX systems, which is why appending is safe for logs while rewriting a whole file is not.
* **Rotation is not atomic** in this simplified version: there is a window where `app.log` does not exist (between `rename` and the next `appendLog`). In production you would use a dedicated logger — `pino` with `pino-roll`, or logrotate at the OS level — or write to stdout and let the platform handle rotation (the preferred approach in containers).
* **Rotation depends on being called before the file grows unbounded.** A real implementation also rotates on size _at write time_, or on a schedule.
* **Logs must never contain secrets.** Notice that the message is caller-controlled — the discipline of not logging tokens/passwords belongs to the caller (and better, to a logger with redaction rules).

</details>

## Exercise 6.2 — Find the bug

```js
import fs from 'node:fs';

export function getConfig() {
  const raw = fs.readFileSync('./config/app.json');
  return JSON.parse(raw);
}

export function saveUser(user) {
  const users = JSON.parse(fs.readFileSync('./data/users.json', 'utf8'));
  users.push(user);
  fs.writeFileSync('./data/users.json', JSON.stringify(users));
}
```

List every problem, in order of severity, and rewrite both functions.

<details>

<summary>Solution</summary>

**Problems, worst first:**

1. **Synchronous I/O in exported functions** — these will be called from request handlers, so every concurrent request blocks on disk. This is the most serious issue.
2. **`getConfig` reads without an encoding** — `raw` is a `Buffer`. `JSON.parse(buffer)` happens to work because the Buffer is coerced to a string, but it is accidental, slower, and will break for encodings other than UTF-8. Pass `'utf8'`.
3. **Relative paths tied to `process.cwd()`** — running from a different directory throws `ENOENT`, and in production the working directory is often `/`.
4. **Read-modify-write race** — two concurrent `saveUser` calls both read the same array; the second write silently discards the first user. This is the classic lost-update bug.
5. **No error handling** — a missing file, malformed JSON or permission error becomes an unhandled exception (very likely a 500 with a stack trace).
6. **No directory creation** — a fresh deployment has no `data/` directory, so the first save fails with `ENOENT`.
7. **Non-deterministic output** — `JSON.stringify` without indentation is fine, but without a trailing newline and pretty printing the file becomes unreadable and produces noisy diffs.
8. **No validation of `user`** — whatever the caller passes is persisted, including `passwordHash` if the caller is careless.
9. **The whole file is rewritten on every save** — acceptable for small data, catastrophic for large data; the pattern does not scale past a few MB.

**Rewritten:**

```js
// File: config-store.mjs
import { readFile } from 'node:fs/promises';
import path from 'node:path';

let cachedConfig = null;

export async function getConfig() {
  if (cachedConfig) return cachedConfig;               // read once per process
  const filePath = path.join(import.meta.dirname, '..', 'config', 'app.json');
  try {
    const raw = await readFile(filePath, 'utf8');       // async + explicit encoding
    cachedConfig = JSON.parse(raw);
    return cachedConfig;
  } catch (error) {
    if (error.code === 'ENOENT') {
      throw new Error(`Config file not found at ${filePath}`, { cause: error });
    }
    if (error instanceof SyntaxError) {
      throw new Error(`Config file ${filePath} is not valid JSON: ${error.message}`, { cause: error });
    }
    throw error;
  }
}
```

```js
// File: user-store.mjs (uses the atomic + serialised pattern from §8)
import { readFile, writeFile, rename, mkdir } from 'node:fs/promises';
import path from 'node:path';

const DATA_DIR = path.join(import.meta.dirname, '..', 'data');
const USERS_FILE = path.join(DATA_DIR, 'users.json');

let queue = Promise.resolve();

/**
 * Serialise all read-modify-write cycles through a promise chain.
 * This is the minimum required to stop concurrent saves losing data.
 */
function withLock(task) {
  const result = queue.then(task, task);   // continue even if the previous task failed
  queue = result.then(
    () => undefined,
    () => undefined
  );
  return result;
}

async function readUsers() {
  try {
    return JSON.parse(await readFile(USERS_FILE, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return [];                     // first run
    if (error instanceof SyntaxError) {
      throw new Error(`${USERS_FILE} is corrupted: ${error.message}`, { cause: error });
    }
    throw error;
  }
}

async function writeUsers(users) {
  await mkdir(DATA_DIR, { recursive: true });
  const tempPath = `${USERS_FILE}.${process.pid}.tmp`;
  await writeFile(tempPath, `${JSON.stringify(users, null, 2)}\n`, 'utf8');
  await rename(tempPath, USERS_FILE);
}

export function saveUser(user) {
  // Validate at the boundary — never persist arbitrary caller input.
  if (!user || typeof user.id !== 'string' || typeof user.email !== 'string') {
    throw new TypeError('saveUser requires { id: string, email: string }');
  }
  const { passwordHash, ...safeUser } = user;   // never persist a credential to a log-like file

  return withLock(async () => {
    const users = await readUsers();
    if (users.some((existing) => existing.id === safeUser.id)) {
      throw new Error(`User ${safeUser.id} already exists`);
    }
    users.push(safeUser);
    await writeUsers(users);
    return safeUser;
  });
}

export const listUsers = () => withLock(readUsers);
```

```js
// File: demo.mjs
import { randomUUID } from 'node:crypto';
import { saveUser, listUsers } from './user-store.mjs';

// 10 concurrent saves — with the original code, several would vanish.
await Promise.all(
  Array.from({ length: 10 }, (_, i) =>
    saveUser({ id: randomUUID(), email: `user${i + 1}@example.com`, passwordHash: 'should-not-be-stored' })
  )
);

const users = await listUsers();
console.log('users persisted:', users.length);                          // 10
console.log('any passwordHash stored?', users.some((u) => 'passwordHash' in u)); // false
```

**What the rewrite demonstrates:** async I/O, module-relative paths, explicit error handling and re-throwing with `cause`, a serialised write queue, atomic writes, validation at the boundary, and never persisting credentials. Those six habits are what "production-ready file handling" means.

**The honest conclusion:** once all of that is in place, you have hand-written a worse version of a database. That is exactly the lesson — and precisely why 03-databases _(not available in this published source revision)_ exists.

</details>

***

## What's next

Paths are the source of half the bugs in the previous section. Next: `node:path` — building, resolving and reasoning about paths correctly on every platform.

→ [07 — The path Module](07-path.md)
