# 04 — Modules: CommonJS and ES Modules

> **Where this fits:** Every real backend is split across dozens of files. This chapter
> explains the two module systems Node supports — CommonJS (`require`) and ES Modules
> (`import`) — how to choose, how they interact, and why "Cannot find module" and "Cannot use
> import statement outside a module" happen. You cannot read a modern codebase without this.

---

## 1. What is a module, and why do we need them?

A **module** is a file that keeps its contents private by default and explicitly exposes a
public interface.

Problems they solve:

| Problem | Without modules | With modules |
| --- | --- | --- |
| Name collisions | Every `const user` fights for one global namespace | Each file has its own scope |
| Accidental global leakage | A typo creates a global | Impossible — file scope is closed |
| Reusability | Copy-paste | `import` a file |
| Testability | Cannot isolate a function | Import one function and test it |
| Dependency clarity | "Where does this come from?" | The imports list the dependencies |

Node has supported **CommonJS** since 2009 and **ES Modules** (the official ECMAScript
standard, same syntax as browsers) since v12, stable since v14. Both work today; the
ecosystem is migrating to ESM, and new projects should generally use ESM.

---

## 2. CommonJS (the original, still everywhere)

```js
// File: math.cjs
// Everything in a file is private unless exported.
const INTERNAL_FACTOR = 2;

function add(a, b) {
  return a + b;
}

function multiply(a, b) {
  return a * b * INTERNAL_FACTOR;
}

// module.exports is a plain object: whatever you attach is public.
module.exports = { add, multiply };
// INTERNAL_FACTOR is NOT exported — it is inaccessible from outside.
```

```js
// File: use-math.cjs
const { add, multiply } = require('./math.cjs');   // relative path, extension optional in CJS
const math = require('./math.cjs');                 // or take the whole object

console.log(add(2, 3));            // 5
console.log(math.multiply(2, 3));  // 12  (2 * 3 * INTERNAL_FACTOR)

// Built-in modules
const fs = require('node:fs');
const path = require('node:path');

// Third-party packages from node_modules — no ./ prefix
const express = require('express');
```

### The four ways to export (and their subtle differences)

```js
// File: exports-patterns.cjs

// 1. Attach to exports — equivalently module.exports
exports.add = (a, b) => a + b;

// 2. Replace module.exports entirely (returns an object)
module.exports = {
  subtract: (a, b) => a - b,
  PI: 3.14159,
};

// 3. Export a single function (the "default export" of CJS)
module.exports = function greet(name) {
  return `Hello, ${name}`;
};
```

> **The classic `exports` trap:**
>
> ```js
> // ❌ This does NOT work — it rebinds the local `exports` variable, not module.exports
> exports = { add: (a, b) => a + b };
> // The importer gets `{}`.
>
> // ✅ These both work:
> exports.add = (a, b) => a + b;      // mutation → visible
> module.exports = { add: (a, b) => a + b };  // reassignment of the real export object
> ```
>
> `exports` is just a variable initialised to the same object as `module.exports`. Reassigning
> the *variable* breaks the link. The robust habit: **always use `module.exports = …`**.

### `require()` semantics you must know

```js
// File: require-semantics.cjs
const path = require('node:path');

// 1. SYNCHRONOUS: require blocks until the module is loaded and executed.
//    That is why imports are top-level statements in CommonJS.

// 2. CACHED: the module body runs ONCE per resolved filename. Every subsequent
//    require returns the SAME object (a shared singleton).
const a = require('./math.cjs');
const b = require('./math.cjs');
console.log(a === b);                       // true — same object

// 3. Resolution order for a bare specifier like `require('express')`:
//    ./node_modules/express/package.json → "main" or "exports" field
//    1. core modules (fs, path, http) unless prefixed with node:
//    2. ./node_modules/express
//    3. ../node_modules/express
//    4. … up to the filesystem root
//    5. then throw MODULE_NOT_FOUND
console.log(require.resolve('./math.cjs')); // absolute path to the resolved file

// 4. CACHE-BUSTING (rare, e.g. for config files in a long-running process)
delete require.cache[require.resolve('./math.cjs')];
const fresh = require('./math.cjs');
console.log(fresh === a);                   // false — a brand-new module instance
```

---

## 3. ES Modules (the modern standard)

ESM is the same syntax browsers use. In Node it requires either a `.mjs` extension or
`"type": "module"` in `package.json`.

```js
// File: math.mjs

// Named exports — as many as you like, and they can be added/removed freely.
export const PI = 3.14159;

export function add(a, b) {
  return a + b;
}

export function multiply(a, b) {
  return a * b;
}

// Private: not exported, not reachable from outside.
const INTERNAL_FACTOR = 2;
export const internalMultiply = (a, b) => a * b * INTERNAL_FACTOR;

// Default export — exactly one per module, imported without braces.
export default function greet(name) {
  return `Hello, ${name}`;
}
```

```js
// File: use-math.mjs

// Named imports, in any order you like
import { add, PI } from './math.mjs';

// Default import — the local name is your choice
import greet from './math.mjs';

// Both together
import greet2, { multiply, internalMultiply } from './math.mjs';

// Rename to avoid collisions
import { add as sum } from './math.mjs';

// Import everything into a namespace object
import * as math from './math.mjs';

// Side-effect-only import (runs the module, imports nothing) — used for polyfills/registers
import './setup-globals.mjs';

console.log(add(2, 3), sum(3, 4), PI);              // 5 7 3.14159
console.log(greet('Ankit'), greet2('Priya'));       // Hello, Ankit Hello, Priya
console.log(multiply(2, 3), internalMultiply(2, 3)); // 6 12
console.log(math.PI, typeof math.default);          // 3.14159 function
```

### ESM rules that differ from CommonJS

| Rule | Consequence |
| --- | --- |
| **Imports are hoisted** | All `import` statements are evaluated before the module body runs, regardless of where they appear |
| **Static, not dynamic** | The specifier must be a string literal — you cannot `import(someVariable)` |
| **`.js` extension is required in relative imports** | `import './utils'` fails; `import './utils.js'` works |
| **Bindings are live** | If the exporting module changes an exported `let`, importers see the new value |
| **`exports` is read-only** | You cannot assign to an imported binding |
| **Modules are strict by default** | No sloppy-mode behaviours (`this` at top level is `undefined`) |
| **Top-level `await`** | Allowed in ESM — very useful for initialising connections |
| **`__dirname`/`__filename`/`require` do not exist** | Use `import.meta.dirname`, `import.meta.url`, `createRequire` |

```js
// File: live-bindings.mjs
// counter.mjs
//   export let count = 0;
//   export function increment() { count += 1; }
//
// main.mjs
//   import { count, increment } from './counter.mjs';
//   console.log(count);  // 0
//   increment();
//   console.log(count);  // 1  ← live binding, NOT a copy (CommonJS would still print 0)
```

```js
// File: top-level-await.mjs
// Top-level await: the module does not finish loading until this resolves.
// Excellent for "make sure the DB is reachable before the app starts".
const config = { ok: true };

async function loadConfig() {
  return config;
}

const loaded = await loadConfig();
console.log('config loaded before any import that depends on this module:', loaded.ok);

export { loaded };
```

---

## 4. Choosing between them

### The decision table

| | CommonJS | ES Modules |
| --- | --- | --- |
| Syntax | `require` / `module.exports` | `import` / `export` |
| Loading | Synchronous, runtime | Asynchronous, parsed statically (can be pre-loaded) |
| Tree-shaking (dropping unused code) | ❌ Hard | ✅ Static shape enables it |
| Top-level `await` | ❌ | ✅ |
| Works in browsers | ❌ | ✅ (same syntax) |
| `__dirname`, `__filename` | ✅ built in | ✅ via `import.meta` |
| `require()` inside `if`/functions | ✅ | ❌ (use `await import()`) |
| JSON import | ✅ `require('./x.json')` | ⚠️ needs `with { type: 'json' }` (Node 22+), or `readFile` + `JSON.parse` |
| `__filename`-style debugging | Simple | Simple |
| Ecosystem status | Mature, legacy | The direction everything is moving |
| Recommended for | Maintaining existing code | **New projects** |

**Recommendation for these notes and for new work: ES Modules.** The syntax is the language
standard, it matches the frontend, it supports top-level `await`, and it lets tooling
analyse your code.

### How Node decides which system a file uses

```text
1. Extension wins:
     .mjs  → ES module, always
     .cjs  → CommonJS, always

2. Otherwise, look for the nearest package.json:
     "type": "module"  → .js files are ESM
     "type": "commonjs" or absent → .js files are CommonJS

3. No package.json found → .js is CommonJS
```

```json
// package.json (fragment)
{
  "name": "my-api",
  "type": "module",
  "main": "src/server.js"
}
```

With `"type": "module"`, every `.js` in the project is ESM. To keep one CommonJS file in an
ESM project, name it `.cjs`.

### Migrating a CommonJS file to ESM (mechanical, but mind these)

```js
// BEFORE (CommonJS)
const fs = require('node:fs');
const path = require('node:path');
const express = require('express');
const { router } = require('./routes/users.js');

const PORT = process.env.PORT || 3000;

function createApp() {
  const app = express();
  app.use('/users', router);
  return app;
}

module.exports = { createApp, PORT, fs, path };
```

```js
// AFTER (ESM)
import fs from 'node:fs';
import path from 'node:path';
import express from 'express';
import { router } from './routes/users.js';   // ← extension is REQUIRED now

const PORT = process.env.PORT ?? 3000;

function createApp() {
  const app = express();
  app.use('/users', router);
  return app;
}

export { createApp, PORT, fs, path };
```

Migration checklist:

1. `require` → `import` (extension added to relative paths).
2. `module.exports = x` → `export default x` or `export { … }`.
3. `exports.a = x` → `export const a = …` or `export { x as a }`.
4. `__dirname` → `import.meta.dirname`.
5. `require('node:fs')` in ESM → `import fs from 'node:fs'` (or `import { readFile } from 'node:fs/promises'`).
6. Add `"type": "module"` and rename any straggler to `.cjs`.
7. JSON files: `import data from './x.json' with { type: 'json' }` (or read + parse).

---

## 5. Interoperability: mixing the two systems

This is where people get stuck, so here are the exact rules.

### Importing CommonJS from ESM — works, with one gotcha

```js
// File: esm-imports-cjs.mjs
// ./legacy.cjs does: module.exports = { add, multiply }
import legacy from './legacy.cjs';              // ✅ default import = module.exports
import { add } from './legacy.cjs';             // ⚠️ works ONLY via named-export detection

console.log(legacy.add(1, 2));                  // 3
console.log(add(1, 2));                         // 3
```

Node's ESM loader statically analyses CommonJS modules and exposes their properties as named
exports using `cjs-module-lexer`. It works for the common patterns
(`module.exports = { a, b }`, `exports.a = …`) and **fails for computed/dynamic ones**:

```js
// File: legacy-dynamic.cjs
const name = 'add';
module.exports[name] = (a, b) => a + b;   // ❌ not statically detectable
```

```js
// This will throw: "The requested module './legacy-dynamic.cjs' does not provide an export named 'add'"
// import { add } from './legacy-dynamic.cjs';

// ✅ The reliable fallback for any CommonJS module:
import legacy from './legacy-dynamic.cjs';
console.log(legacy.add(1, 2));             // 3
```

**Rule: when importing CommonJS from ESM, use the default import and access properties off it
if named imports fail.**

### Importing ESM from CommonJS

Historically impossible (`require` of an ES module threw `ERR_REQUIRE_ESM`). Modern Node
(22.12+ / 23+) supports `require(esm)` **as long as the ESM module has no top-level `await`**:

```js
// File: cjs-requires-esm.cjs
const esmModule = require('./math.mjs');   // ✅ works when there is no top-level await
console.log(esmModule.add(2, 3));          // 5
// console.log(esmModule.default('Ankit')); // the default export lives on `.default`
```

If the ESM module *does* use top-level `await`, `require` throws `ERR_REQUIRE_ASYNC_MODULE` —
the fallback there is dynamic `import()`:

```js
// File: cjs-dynamic-import.cjs
async function load() {
  const mod = await import('./top-level-await.mjs');   // dynamic import works everywhere
  return mod.loaded;
}

load().then((config) => console.log('loaded:', config.ok));
```

### Dynamic `import()` — the universal escape hatch

`import()` works in **both** module systems, is asynchronous, and can take a computed
specifier:

```js
// File: dynamic-import.mjs
const pluginName = process.env.PLUGIN ?? 'math';

// Load a module at runtime, based on configuration.
const module = await import(`./${pluginName}.mjs`);
console.log('add:', module.add(1, 2));

// Common uses:
//  - lazy-loading route handlers or heavy dependencies
//  - loading an optional dependency that may not be installed
//  - loading a different provider based on NODE_ENV (e.g. a fake mailer in tests)
try {
  const optional = await import('some-optional-package');
  console.log('optional package available:', typeof optional.default);
} catch (error) {
  console.log('optional package not installed:', error.code); // ERR_MODULE_NOT_FOUND
}
```

### The `createRequire` bridge

Sometimes a CommonJS-only package must be used from ESM (or you need `require.resolve`):

```js
// File: create-require.mjs
import { createRequire } from 'node:module';
import path from 'node:path';

const require = createRequire(import.meta.url);

const pkg = require('./package.json');            // JSON works again
console.log('project name:', pkg.name);

const resolved = require.resolve('./math.cjs');   // absolute path resolution
console.log('resolved path:', resolved);
console.log('dirname:', path.dirname(resolved));
```

---

## 6. Built-in, custom and third-party modules

Node's modules come in three flavours, and the import syntax makes the difference visible:

```js
// File: three-kinds.mjs
// 1. BUILT-IN (core) modules — prefer the `node:` prefix: it is unambiguous and can never
//    be shadowed by an npm package with the same name.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { EventEmitter } from 'node:events';
import { randomUUID } from 'node:crypto';
import { readFile } from 'node:fs/promises';   // promise-based variant
import * as os from 'node:os';

// 2. CUSTOM modules — always a relative or absolute path
import { createApp } from './app.js';
import { logger } from '../lib/logger.js';

// 3. THIRD-PARTY modules — a bare specifier, resolved from node_modules
import express from 'express';
import { z } from 'zod';
```

### The built-in modules you will meet in this section

| Module | Purpose | Chapter |
| --- | --- | --- |
| `node:fs`, `node:fs/promises` | Files and directories | [06](06-filesystem.md) |
| `node:path` | Path manipulation | [07](07-path.md) |
| `node:events` | Event emitters | [08](08-events.md) |
| `node:stream` | Streaming data, backpressure | [09](09-streams.md) |
| `node:buffer` | Raw binary data | [10](10-buffers.md) |
| `node:http` / `node:https` | HTTP servers and clients | [11](11-http-module.md) |
| `node:os` | System info | [03](03-nodejs-basics.md) |
| `node:url` | URL parsing | [00-web-fundamentals/04](../00-web-fundamentals/04-urls-endpoints-and-routing.md) |
| `node:crypto` | Hashing, UUIDs, random bytes, encryption | 04-authentication/02 *(not available in this published source revision)* |
| `node:process` | The process (also a global) | [03](03-nodejs-basics.md) |
| `node:util` | Helpers: `parseArgs`, `promisify`, `inspect` | [03](03-nodejs-basics.md) |
| `node:test`, `node:assert` | Built-in test runner | 05-testing/01 *(not available in this published source revision)* |
| `node:child_process` | Spawn processes | 07-deployment/01 *(not available in this published source revision)* |
| `node:worker_threads` | True parallelism | [14](14-event-loop.md) |

```bash
# List every built-in module
node -e "console.log(require('node:module').builtinModules.join('\n'))"
```

---

## 7. Circular dependencies (and why you should avoid them)

```js
// File: a.mjs
import { b } from './b.mjs';
export const a = 'A';
console.log('in a.mjs, b =', b);
```

```js
// File: b.mjs
import { a } from './a.mjs';
export const b = 'B';
console.log('in b.mjs, a =', a);
```

```bash
node a.mjs
```

```text
in b.mjs, a = undefined     ← a is not initialised yet!
in a.mjs, b = B
```

**Why:** ESM resolves the whole graph first, then evaluates in dependency order. When `b.mjs`
is evaluated, `a.mjs` has started but has not reached the line that assigns `a` yet, so the
live binding is still in its "temporal dead zone" and reads as `undefined`.

CommonJS behaves differently (and worse — you get a partial object rather than an error),
which is why people say "circular imports are a footgun in both systems, just differently".

**How to fix circular dependencies:**

1. **Restructure.** If `userService` needs `orderService` and vice versa, extract the shared
   piece into a third module both import.
2. **Depend on interfaces, not implementations.** Put types/constants in a separate file.
3. **Inject at call time** rather than at import time:

```js
// File: service-with-injection.mjs
// Instead of importing the dependency at the top, accept it as a parameter.
export function createOrderService({ userService }) {
  return {
    async createOrder(userId, items) {
      const user = await userService.findById(userId);
      return { userId, items, user };
    },
  };
}
```

4. **Use dynamic `import()`** inside the function that needs it (a real fix, but a last
   resort — it hides the coupling rather than removing it).

You will meet this for real in the Express section, where `routes → controllers → services →
repositories` must flow in **one direction only**. A cycle there is a design smell.

---

## 8. `package.json` fields that control module behaviour

```json
// package.json (fragment, with annotations)
{
  "name": "my-api",
  "version": "1.0.0",
  "type": "module",            // ".js" files in this package are ES modules
  "main": "./src/index.js",    // legacy entry point used by require()
  "exports": {                 // the modern, explicit entry point map
    ".": {
      "import": "./src/index.js",
      "require": "./src/index.cjs"
    },
    "./utils": "./src/utils.js"   // a named subpath: import 'my-api/utils'
  },
  "engines": { "node": ">=22.0.0" }
}
```

| Field | Meaning |
| --- | --- |
| `main` | Entry point for `require` in older resolvers |
| `module` | A bundler-only hint for ESM entry (not used by Node) |
| `exports` | The authoritative map: it **restricts** what outsiders may import. Once present, deep imports like `my-api/src/internal.js` are blocked |
| `type` | `"module"` or `"commonjs"` — decides `.js` semantics |
| `imports` | Private subpath map, e.g. `"#db": "./src/db.js"` for internal aliasing |

> **Important:** adding `exports` is a breaking change for anyone deep-importing your package.
> That is intentional — it lets you refactor internals — but it must be a conscious decision.

---

## 9. Common mistakes

| Error message | Cause | Fix |
| --- | --- | --- |
| `Cannot find module './utils'` | ESM requires the extension | `import './utils.js'` |
| `Cannot find module 'node-fs'` | Wrong built-in name | `node:fs`, not `node-fs` |
| `Cannot use import statement outside a module` | ESM syntax in a `.js` file, but no `"type": "module"` | Add it, or use `.mjs` |
| `require is not defined in ES module scope` | `require` in ESM | `import`, or `createRequire(import.meta.url)` |
| `__dirname is not defined` | `__dirname` in ESM | `import.meta.dirname` |
| `ERR_REQUIRE_ESM` / `ERR_REQUIRE_ASYNC_MODULE` | `require()` of an ESM with top-level await | `await import()` instead |
| `The requested module does not provide an export named 'x'` | Importing a named export from CommonJS that the lexer cannot see | Import the default and access `.x` |
| `ERR_MODULE_NOT_FOUND` for an installed package | It is in `devDependencies` and you deployed with `--omit=dev`, or not installed | `npm install`, or move it to `dependencies` |
| `SyntaxError: Cannot use import statement` in a `.ts` file | TypeScript not compiled | Use `tsx`/`ts-node`, or compile first |
| Importing `./math` in CJS but `./math.mjs` on disk | Extension mismatch | Match the real filename, or omit consistently |
| Circular import gives `undefined` | Evaluation order | Restructure (see §7) |
| `exports = {...}` in CommonJS | Rebinding the local variable | `module.exports = {...}` |

---

## Exercise 4.1 — Convert to ESM

Convert this CommonJS module and its consumer to ES Modules, preserving behaviour.

```js
// File: database.cjs
const mongoose = require('mongoose');
const path = require('node:path');
const fs = require('node:fs');

const CONFIG_PATH = path.join(__dirname, '..', 'config', 'database.json');
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));

let connection = null;

async function connect() {
  if (connection) return connection;
  connection = await mongoose.connect(process.env.DATABASE_URL || config.url);
  return connection;
}

function isConnected() {
  return connection !== null;
}

module.exports = { connect, isConnected };
```

<details>
<summary>Solution</summary>

```js
// File: database.js  (ESM — requires "type": "module" in package.json)
import mongoose from 'mongoose';
import path from 'node:path';
import { readFile } from 'node:fs/promises';

// __dirname does not exist in ESM → import.meta.dirname (Node 20.11+)
const CONFIG_PATH = path.join(import.meta.dirname, '..', 'config', 'database.json');

// Top-level await: the config is guaranteed to be loaded before this module is done,
// which removes the need for a lazy getter and makes the failure a startup failure.
const config = JSON.parse(await readFile(CONFIG_PATH, 'utf8'));

let connection = null;

export async function connect() {
  if (connection) return connection;
  connection = await mongoose.connect(process.env.DATABASE_URL ?? config.url);
  return connection;
}

export function isConnected() {
  return connection !== null;
}

// Optional: keep a default export so consumers can also do `import db from './database.js'`
export default { connect, isConnected };
```

```js
// File: server.js (the consumer)
import { connect, isConnected } from './database.js';

await connect();
console.log('connected:', isConnected());
```

**What changed and why**

| Change | Reason |
| --- | --- |
| `require` → `import` | ESM syntax |
| `__dirname` → `import.meta.dirname` | Not defined in ESM |
| `require('node:fs').readFileSync` → `await readFile` from `node:fs/promises` | Top-level await is available, so there is no reason to block the event loop at startup |
| `module.exports = {…}` → `export function …` | Named exports; the importer gets the same API |
| `process.env.DATABASE_URL \|\| config.url` → `??` | A defined-but-empty env var is a misconfiguration, not a fallback trigger; `??` is the more honest operator here |

**One warning about the top-level `await`:** it makes this module asynchronous, which means
`require('database.js')` from CommonJS will now throw `ERR_REQUIRE_ASYNC_MODULE`. That is
usually fine (and desirable: the connection is guaranteed before anything else runs), but it
must be a deliberate choice if you still have CommonJS consumers.

</details>

## Exercise 4.2 — Diagnose the import errors

For each situation, say what is wrong and how to fix it.

1. `package.json` has `"type": "module"`. A file `src/utils/logger.js` is imported as
   `import { logger } from './utils/logger'` from `src/app.js` → `ERR_MODULE_NOT_FOUND`.
2. `app.js` (CommonJS, `.js`, no `"type"`) starts with `import express from 'express';` →
   `SyntaxError: Cannot use import statement outside a module`.
3. `import pkg from './package.json'` → `ERR_IMPORT_ATTRIBUTE_MISSING`.
4. In an ESM file: `const p = __dirname;` → `ReferenceError: __dirname is not defined`.
5. `import { add } from 'lodash-es'` inside a `.cjs` file → `SyntaxError: Cannot use import statement outside a module`.
6. `import { v4 } from 'uuid'` fails with `The requested module does not provide an export named 'v4'`.

<details>
<summary>Solution</summary>

1. **Missing extension.** ESM does not do extension-less resolution. Fix:
   `from './utils/logger.js'`.

2. **The project is CommonJS, but the file uses ESM syntax.** Fix: either add
   `"type": "module"` to `package.json` (and rename any file that must stay CommonJS to
   `.cjs`), or use `const express = require('express')`.

3. **JSON imports in ESM need an import attribute** (Node 22+):
   ```js
   import pkg from './package.json' with { type: 'json' };
   ```
   Or, if you would rather not depend on that syntax, read and parse it explicitly:
   ```js
   import { readFile } from 'node:fs/promises';
   const pkg = JSON.parse(await readFile(new URL('./package.json', import.meta.url), 'utf8'));
   ```
   (Note: the `assert { type: 'json' }` syntax you may see in older tutorials is deprecated in
   favour of `with`.)

4. **`__dirname` is CommonJS-only.** Fix: `import.meta.dirname` (Node 20.11+). For older
   versions:
   ```js
   import path from 'node:path';
   import { fileURLToPath } from 'node:url';
   const __dirname = path.dirname(fileURLToPath(import.meta.url));
   ```

5. **`import` is not valid in a `.cjs` file, ever.** `.cjs` is always CommonJS. Fix: use
   `require` (if the package is CJS-compatible), or convert the file to ESM, or use dynamic
   import from an async function:
   ```js
   async function load() {
     const { default: lodash } = await import('lodash-es');
     return lodash;
   }
   ```

6. **`uuid` v9+ is ESM-first and has no `v4` named export reachable this way** (or you are
   importing the CommonJS build, which exposes a default). Fixes, in order of preference:
   ```js
   // Current versions of `uuid` export v4 as a named export:
   import { v4 as uuidv4 } from 'uuid';
   const requestId = uuidv4();

   // Or via the default export (works with the CommonJS build too):
   import uuid from 'uuid';
   const traceId = uuid.v4();
   ```

   Simplest of all, since Node has this built in — **no dependency needed**:

   ```js
   import { randomUUID } from 'node:crypto';
   const sessionId = randomUUID();
   console.log(sessionId); // a v4-style UUID, cryptographically random
   ```
   That last option is worth remembering: **`node:crypto.randomUUID()` removes the `uuid`
   dependency from most projects entirely.**

</details>

---

## What's next

Your code is now organised into modules. Next: the tool that installs the modules everyone
else wrote — npm, `package.json`, semver, and the commands you will type a hundred times a
week.

→ [05 — npm and package.json](05-npm.md)
