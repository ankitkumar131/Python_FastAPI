# 07 — The path Module

> **Where this fits:** Every `ENOENT`, every "it worked on my machine", and every path-traversal vulnerability traces back to path handling. `node:path` is small — a dozen functions — and one of the highest-value modules to know precisely. Read this before you write any code that touches the file system.

***

## 1. Why paths need a dedicated module

Three reasons, each capable of breaking your app:

1. **Separators differ.** POSIX (Linux/macOS) uses `/`; Windows uses `\` (and accepts `/`). Concatenating with `'/'` is subtly wrong on Windows; the OS will often cope, but the strings you log, compare and store are inconsistent.
2. **Resolution is contextual.** `./uploads/x.png` means nothing until you know the _base directory_. Different bases ⇒ different files ⇒ "works locally, fails in production".
3. **Traversal is a security hole.** `../../../../etc/passwd` in a filename is the classic directory-traversal attack. `path` gives you the tools to detect and prevent it.

```js
// File: separators.mjs
import path from 'node:path';

console.log('sep      :', path.sep);          // '/' on Linux/macOS, '\\' on Windows
console.log('delimiter:', path.delimiter);    // ':' on POSIX, ';' on Windows (for PATH lists)

// Manual concatenation — fragile.
const naive = 'uploads' + '/' + 'avatars' + '/' + 'user.png';
console.log('naive    :', naive);             // uploads/avatars/user.png  (wrong style on Windows)

// Correct on every platform.
const correct = path.join('uploads', 'avatars', 'user.png');
console.log('join     :', correct);
```

Note that `path` is also available as `path.posix` and `path.win32` — fixed-version helpers, handy when you must handle Windows paths on Linux (e.g. parsing a user-supplied path from a Windows client) or write tests that must pass everywhere.

***

## 2. The functions you will actually use

```js
// File: path-basics.mjs
import path from 'node:path';

const filePath = '/srv/app/uploads/avatars/user-42.png';

// 1. Join: build a path from segments. Handles separators and does NOT resolve absolutes.
console.log(path.join('/srv/app', 'uploads', 'avatars'));       // /srv/app/uploads/avatars
console.log(path.join('config', '..', 'config', 'app.json'));   // config/app.json (normalised)

// 2. Resolve: build an ABSOLUTE path, using the rightmost absolute segment (or cwd).
console.log(path.resolve('uploads', 'user.png'));
// /current/working/directory/uploads/user.png    ← depends on cwd. Use with care!

console.log(path.resolve('/srv/app', 'uploads'));  // /srv/app/uploads

// 3. Basename / dirname / extname: the path parts
console.log(path.basename(filePath));       // user-42.png
console.log(path.basename(filePath, '.png')); // user-42   (strip an extension)
console.log(path.dirname(filePath));        // /srv/app/uploads/avatars
console.log(path.extname(filePath));        // .png

// 4. Parse: everything at once
console.log(path.parse(filePath));
// { root: '/', dir: '/srv/app/uploads/avatars', base: 'user-42.png',
//   ext: '.png', name: 'user-42' }

// 5. Format: build a path from parts
console.log(path.format({ dir: '/srv/app', name: 'report', ext: '.json' }));
// /srv/app/report.json

// 6. Normalise: collapse . and .. and duplicate separators
console.log(path.normalize('/srv//app/./uploads/../uploads/x.png'));
// /srv/app/uploads/x.png

// 7. Absolute check
console.log(path.isAbsolute('/srv/app'));   // true
console.log(path.isAbsolute('srv/app'));    // false
console.log(path.isAbsolute('C:\\app'));    // true on win32, false on posix

// 8. Relative: the inverse of resolve — how do I get from A to B?
console.log(path.relative('/srv/app', '/srv/app/uploads/user.png')); // uploads/user.png
console.log(path.relative('/srv/app/api', '/srv/app/uploads'));      // ../uploads

// 9. toNamespacedPath: Windows-only helper for long/UNC paths (rarely needed manually)
console.log(path.toNamespacedPath('/srv/app') === '/srv/app');       // true on POSIX
```

### `join` vs `resolve` — the distinction that matters

```js
// File: join-vs-resolve.mjs
import path from 'node:path';

// join: concatenate and normalise. The result may be relative.
console.log(path.join('a', 'b'));                 // a/b

// resolve: produce an ABSOLUTE path. Left-to-right; an absolute segment RESETS the result.
console.log(path.resolve('a', 'b'));              // /cwd/a/b
console.log(path.resolve('a', '/b'));             // /b          ← the absolute segment wins
console.log(path.resolve('a', '/b', 'c'));        // /b/c

// The practical rule:
//  - join()  for combining segments you control
//  - resolve() when you deliberately want to anchor to the current directory
//  - path.join(__dirname/import.meta.dirname, …) is almost always what you actually want
```

`resolve`'s dependence on `process.cwd()` is a footgun: it means the same code resolves to different files depending on where it was started. Prefer `import.meta.dirname` as the base.

***

## 3. `__dirname`, `import.meta.dirname`, and a helper

```js
// File: esm-paths.mjs
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// ESM (Node 20.11+): built in and simple.
console.log('import.meta.dirname :', import.meta.dirname);
console.log('import.meta.filename:', import.meta.filename);

// Portable fallback for older Node versions.
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
console.log('fallback dirname    :', __dirname);

// The helper you will write once and reuse in every project.
export function resolveFromHere(...segments) {
  return path.join(import.meta.dirname, ...segments);
}

console.log('resolved            :', resolveFromHere('..', 'package.json'));
```

```js
// File: cjs-paths.cjs
const path = require('node:path');
const fs = require('node:fs');

// CommonJS provides these directly.
console.log('__dirname :', __dirname);
console.log('__filename:', __filename);

const configPath = path.join(__dirname, '..', 'config', 'app.json');
console.log('config    :', configPath);
console.log('exists    :', fs.existsSync(configPath));
```

### The project layout convention that keeps paths sane

```
project/
├── src/
│   ├── lib/
│   │   └── paths.js        ← ONE module that computes every important path
│   ├── routes/
│   └── server.js
├── data/                   ← writable (gitignored, or a mounted volume)
├── public/                 ← static files served to clients
├── config/
└── package.json
```

```js
// File: src/lib/paths.js
import path from 'node:path';

// Project root = two levels up from src/lib
export const ROOT_DIR = path.resolve(import.meta.dirname, '..', '..');

export const PATHS = {
  root: ROOT_DIR,
  src: path.join(ROOT_DIR, 'src'),
  public: path.join(ROOT_DIR, 'public'),
  data: path.join(ROOT_DIR, 'data'),
  uploads: path.join(ROOT_DIR, 'data', 'uploads'),
  logs: path.join(ROOT_DIR, 'data', 'logs'),
  config: path.join(ROOT_DIR, 'config'),
};
```

```js
// File: use-paths.js
import { writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { PATHS } from './src/lib/paths.js';

await mkdir(PATHS.uploads, { recursive: true });
const target = path.join(PATHS.uploads, 'example.txt');
await writeFile(target, 'paths are resolved once, in one place\n', 'utf8');

console.log('wrote:', target);
console.log('is absolute:', path.isAbsolute(target));
```

**Why centralise?** Because a path computed in five places will be wrong in at least one of them, and the wrong one is always the one that runs in production. One module, one source of truth, one place to test.

***

## 4. Working with extensions and filenames safely

```js
// File: filenames.mjs
import path from 'node:path';

// Changing an extension
const image = '/uploads/photo.jpeg';
console.log(path.format({ ...path.parse(image), base: undefined, ext: '.webp' }));
// /uploads/photo.webp

// Adding a suffix before the extension (common for thumbnails)
const thumb = `${path.parse(image).name}-thumb${path.extname(image)}`;
console.log(path.join(path.dirname(image), thumb));   // /uploads/photo-thumb.jpeg

// Detecting file type from the extension (never trust it for security — sniff the bytes too)
const ALLOWED_IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif']);
function isAllowedImage(filePath) {
  return ALLOWED_IMAGE_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

console.log(isAllowedImage('a.PNG'), isAllowedImage('b.svg')); // true false
```

**Never build an upload filename from user input.** The safe pattern (`crypto.randomUUID()` for the name, extension from an allowlist) is in [02-express/17-file-upload.md](../02-express/17-file-upload.md).

***

## 5. Path traversal: the security lesson of this chapter

The dangerous pattern:

```js
// ❌ VULNERABLE — a "download a file by name" endpoint
app.get('/files/:name', (req, res) => {
  const filePath = path.join('./uploads', req.params.name);
  res.sendFile(filePath);
});
```

An attacker requests:

```bash
curl "http://localhost:3000/files/..%2F..%2Fetc%2Fpasswd"
# decoded → ../..//etc/passwd → served! Your server's files are now public.
```

`path.join` normalises the `..`, which does **not** protect you — it _completes_ the escape.

### The correct defence: resolve, then verify containment

```js
// File: safe-file-path.mjs
import path from 'node:path';

const UPLOADS_DIR = path.resolve(import.meta.dirname, 'uploads');

/**
 * Turn a user-supplied relative name into an absolute path that is guaranteed
 * to live inside UPLOADS_DIR. Returns null when the name tries to escape.
 */
export function safeResolveUpload(name) {
  // 1. Reject obvious garbage early.
  if (typeof name !== 'string' || name.length === 0 || name.length > 255) return null;
  if (name.includes('\0')) return null;                 // null bytes truncate C strings

  // 2. Resolve to an absolute path.
  const candidate = path.resolve(UPLOADS_DIR, name);

  // 3. Containment check: the resolved path must be UPLOADS_DIR itself
  //    or start with UPLOADS_DIR + separator.
  const relative = path.relative(UPLOADS_DIR, candidate);
  const escapes = relative.startsWith('..') || path.isAbsolute(relative);
  if (escapes) return null;

  return candidate;
}

const cases = [
  'report.pdf',                     // ✅ legit
  'avatars/user-1.png',             // ✅ nested, still inside
  '../secrets.env',                 // ❌ escape
  '../../etc/passwd',               // ❌ escape
  '/etc/passwd',                    // ❌ absolute path overrides the base
  'a/../../b.txt',                  // ❌ normalises outside
];

for (const name of cases) {
  const resolved = safeResolveUpload(name);
  console.log(name.padEnd(22), resolved ? `OK  ${resolved}` : 'BLOCKED');
}
```

```
report.pdf             OK  /…/uploads/report.pdf
avatars/user-1.png     OK  /…/uploads/avatars/user-1.png
../secrets.env         BLOCKED
../../etc/passwd       BLOCKED
/etc/passwd            BLOCKED
a/../../b.txt          BLOCKED
```

**Why `path.relative` is the right check:** comparing with `startsWith(UPLOADS_DIR)` is not enough — `/srv/uploads-evil/x` also starts with `/srv/uploads`. `path.relative` yields `../uploads-evil/x`, which starts with `..`, so it is correctly rejected.

Additional hardening for file-serving endpoints:

| Measure                                    | Reason                                                 |
| ------------------------------------------ | ------------------------------------------------------ |
| Serve by **id**, not by filename           | The client never controls any part of the path         |
| Store files outside the app directory      | `..` escapes only reach non-sensitive data             |
| Check the extension against an allowlist   | Blocks `index.html`-style active content               |
| `res.sendFile(absPath)` with `root` option | Express refuses paths that escape `root`               |
| Never serve dotfiles                       | `.env`, `.git`, `.ssh` are exactly what attacks target |
| Run the app as a non-root user             | Limits the blast radius                                |

***

## 6. Windows, POSIX and normalisation

```js
// File: cross-platform.mjs
import path from 'node:path';

// A Windows path on POSIX Node is just a string — it is NOT a directory separator here.
const winPath = 'C:\\Users\\ankit\\project\\server.js';
console.log('posix basename  :', path.basename(winPath));      // the whole string on Linux!
console.log('win32 basename  :', path.win32.basename(winPath)); // server.js
console.log('win32 dirname   :', path.win32.dirname(winPath));  // C:\Users\ankit\project

// And the reverse: use path.posix when you deliberately want POSIX semantics on Windows
// (for example, when generating URLs or git paths that must always use "/").
const urlPath = path.posix.join('api', 'v1', 'users');
console.log('always forward slashes:', urlPath);               // api/v1/users

// Case sensitivity differs: Linux is case-sensitive, macOS is not (by default), Windows is not.
// Never rely on case to distinguish two files.
console.log(path.resolve('/srv/app') === path.resolve('/SRV/APP')); // true on Windows/macOS, false on Linux
```

Practical guidance:

| Situation                                        | Do this                                                                                             |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| Building paths in app code                       | `path.join(...)`                                                                                    |
| Storing paths in a database                      | **Store POSIX-style with `/`** and convert on the way out — mixing separators makes data unportable |
| Building URLs                                    | `path.posix.join` or the `URL` class, never `path.join`                                             |
| Comparing paths                                  | Normalise first: `path.normalize(a) === path.normalize(b)` (and consider case)                      |
| Long/UNC Windows paths                           | `path.toNamespacedPath`                                                                             |
| Handling a user-supplied path from an unknown OS | Parse with `path.win32`/`path.posix` explicitly according to the client's OS                        |

***

## 7. Common mistakes

| Mistake                                    | Symptom                                 | Fix                                        |
| ------------------------------------------ | --------------------------------------- | ------------------------------------------ |
| `path.join('./uploads', userInput)`        | Directory traversal                     | Resolve + containment check (§5)           |
| Using `path.resolve` to build app paths    | Depends on `process.cwd()`              | `path.join(import.meta.dirname, …)`        |
| Hardcoding `'/'`                           | Inconsistent paths on Windows           | `path.join` / `path.posix` deliberately    |
| Comparing paths as raw strings             | Fails on different separators/case      | Normalise (and `resolve`) both sides first |
| `path.basename` on a Windows path in Linux | Returns the whole string                | Use `path.win32.basename`                  |
| Building a URL with `path.join`            | Backslashes on Windows                  | `URL` + `path.posix.join`                  |
| Using `extname` as a security check        | `.php.jpg`, extension spoofing          | Allowlist + validation + content sniffing  |
| Extracting an extension with `split('.')`  | Breaks on `archive.tar.gz` and dotfiles | `path.extname`                             |
| Assuming case-insensitive paths            | Fails in Linux containers               | Match exactly; test in Docker              |
| Forgetting to normalise before storing     | Duplicate rows for the same file        | `path.normalize` before persisting         |

***

## Exercise 7.1 — A safe, portable static-file resolver

Write `resolvePublicFile(urlPath)` that maps a URL path (e.g. `/css/site.css`) to an absolute path inside `public/`, rejecting traversal attempts, query strings, null bytes and dotfiles. Then test it against a list of hostile inputs.

<details>

<summary>Solution</summary>

```js
// File: public-resolver.mjs
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const PUBLIC_DIR = path.resolve(import.meta.dirname, 'public');

/**
 * Map a URL path to a safe absolute file path inside PUBLIC_DIR.
 * Returns null when the request must be rejected.
 */
export function resolvePublicFile(urlPath) {
  if (typeof urlPath !== 'string') return null;

  // 1. Strip the query string and fragment (a URL path may contain them).
  const withoutQuery = urlPath.split('?')[0].split('#')[0];

  // 2. Percent-decode FIRST — otherwise %2e%2e%2f survives the checks below.
  let decoded;
  try {
    decoded = decodeURIComponent(withoutQuery);
  } catch {
    return null; // malformed percent-encoding
  }

  // 3. Reject control characters and null bytes.
  if (/[\0-\x1f\x7f]/.test(decoded)) return null;

  // 4. Normalise separators: browsers always send "/", but be defensive.
  const normalised = decoded.replaceAll('\\', '/');

  // 5. Reject dotfiles and any explicit traversal segment.
  const segments = normalised.split('/').filter(Boolean);
  if (segments.some((s) => s.startsWith('.'))) return null;

  // 6. Resolve and verify containment — the authoritative check.
  const candidate = path.resolve(PUBLIC_DIR, normalised.replace(/^\/+/, ''));
  const relative = path.relative(PUBLIC_DIR, candidate);
  if (relative.startsWith('..') || path.isAbsolute(relative)) return null;

  return candidate;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
const cases = [
  ['/css/site.css', true],
  ['/index.html', true],
  ['/img/logo.svg?v=2', true],
  ['/../../etc/passwd', false],
  ['/..%2f..%2fetc%2fpasswd', false],
  ['/%2e%2e/%2e%2e/etc/passwd', false],
  ['/./.env', false],
  ['/.git/config', false],
  ['/', true],                       // resolves to the directory itself; the caller returns 404
  ['/css\\..\\..\\secret', false],
  ['/file\0.txt', false],
];

let failures = 0;

for (const [input, shouldSucceed] of cases) {
  const result = resolvePublicFile(input);
  const ok = (result !== null) === shouldSucceed;
  if (!ok) failures += 1;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${input.padEnd(28)} → ${result ?? 'REJECTED'}`);
}

console.log(`\n${failures === 0 ? 'All cases passed' : `${failures} case(s) failed`}`);
process.exitCode = failures === 0 ? 0 : 1;
```

Expected output:

```
PASS  /css/site.css                 → /…/public/css/site.css
PASS  /index.html                   → /…/public/index.html
PASS  /img/logo.svg?v=2             → /…/public/img/logo.svg
PASS  /../../etc/passwd             → REJECTED
PASS  /..%2f..%2fetc%2fpasswd       → REJECTED
PASS  /%2e%2e/%2e%2e/etc/passwd     → REJECTED
PASS  /./.env                       → REJECTED
PASS  /.git/config                  → REJECTED
PASS  /                             → /…/public
PASS  /css\..\..\secret             → REJECTED
PASS  /file\0.txt                   → REJECTED

All cases passed
```

**Why each step exists**

| Step                            | Attack it stops                                                        |
| ------------------------------- | ---------------------------------------------------------------------- |
| Strip query/fragment            | `/file.png?x=/etc/passwd` confusion, cache-key tricks                  |
| **Decode before checking**      | `%2e%2e%2f` bypasses a naive `..` check — the classic mistake          |
| Control-character rejection     | Null-byte truncation in downstream C libraries                         |
| Backslash normalisation         | Windows-style traversal arriving at a Linux server                     |
| Dotfile rejection               | `.env`, `.git/config`, `.htaccess`, `.ssh`                             |
| Containment via `path.relative` | All remaining escapes, including absolute paths that override the base |

**Note the honest limitation:** this function returns the _path_; the route must still refuse directories, set correct `Content-Type`s, avoid serving active content from user uploads, and handle `ENOENT`. Security is a chain — this is one link.

</details>

## Exercise 7.2 — Predict the output

```js
import path from 'node:path';

console.log(path.join('/a', '/b', 'c'));
console.log(path.resolve('/a', '/b', 'c'));
console.log(path.normalize('/a/b/../c/./d//'));
console.log(path.basename('/x/y/z.tar.gz'));
console.log(path.extname('/x/y/z.tar.gz'));
console.log(path.dirname('/x/y/z.tar.gz'));
console.log(path.relative('/a/b/c', '/a/d'));
console.log(path.isAbsolute('../x'));
console.log(path.join('a', '..', '..', 'b'));
console.log(path.resolve('a', '..', 'b'));
```

<details>

<summary>Solution</summary>

```
/a/b/c            join: the second absolute segment is treated as a plain piece
/a/b/c            resolve: the second absolute segment RESETS the result to /b, then + c
/a/c/d            normalize: b/.. cancels, . drops, duplicate separator collapses
z.tar.gz          basename: everything after the last separator
.gz               extname: only the LAST extension (this is why .tar.gz handling needs care)
/x/y              dirname
../d              relative: how to get from /a/b/c to /a/d
false             isAbsolute: relative path
../b              join normalises: a/.. cancels, then .. goes up → ../b
/current/dir/b    resolve: anchored to cwd, 'a' then '..' cancel → cwd/b
```

Two takeaways worth remembering:

1. **`join` vs `resolve` with an absolute segment.** `path.join('/a', '/b', 'c')` gives `/a/b/c`, but `path.resolve('/a', '/b', 'c')` gives `/b/c`. If you are mixing a user-supplied absolute path into `resolve`, the user can override your base directory directly — which is exactly why §5's containment check is mandatory.
2.  **`extname('z.tar.gz')` is `.gz`.** For compound extensions, check for the double extension explicitly:

    ```js
    const lower = filePath.toLowerCase();
    const isGzipTarball = lower.endsWith('.tar.gz');
    console.log(isGzipTarball);
    ```

</details>

***

## What's next

Paths handled. Next: Node's event system — the mechanism behind servers, streams, sockets and almost every core module, and the reason the word "event-driven" appears in every Node description.

→ [08 — Events](08-events.md)
