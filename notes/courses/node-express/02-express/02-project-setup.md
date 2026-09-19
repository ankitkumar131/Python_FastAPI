# 02 — Project Setup

> **Where this fits:** Chapter 01 gave you a working Express app in one file. Real projects do not stay
> in one file. This chapter sets up the structure, scripts, environment handling and tooling that the
> remaining 19 chapters build on — and explains *why* each choice exists.

---

## 1. Why setup deserves a chapter

A "setup" chapter is where most tutorials say *"run `npm init -y`"* and move on. Then, 200 lines later,
the tutorial's `app.js` is untestable, the port is hard-coded, the environment variables are read in
nine places, and errors are indistinguishable because everything is `res.status(500)`.

Every one of those problems is a *structural* decision, and structural decisions are cheap at the start
and expensive later:

| Decision | Made at the start | Made later |
| --- | --- | --- |
| Folder layers | Free | A refactor of every file |
| `app.js` / `server.js` split | 5 minutes | Test failures you cannot diagnose |
| One validated config module | 20 minutes | Grepping `process.env` across 40 files |
| Scripts (`dev`, `start`, `test`) | 2 minutes | Deploy scripts that do not match local behaviour |
| Node version pinned | 1 minute | "Works on my machine" |

So this chapter is genuinely part of the framework material, not throat-clearing.

---

## 2. Prerequisites and versions

```bash
node --version     # v22.x or newer (v24 LTS recommended)
npm --version      # v10 or newer
```

| Tool | Version used in these notes | Notes |
| --- | --- | --- |
| Node.js | 22 LTS minimum, 24 LTS recommended | Required for `require(esm)`, `node --env-file-if-exists`, and stable `node:test` |
| Express | **5.2.x** | `latest` on npm since March 2025; async errors handled automatically |
| npm | 10+ | Ships with Node 22 |

Pin the version the moment two people work on the project:

```bash
# .nvmrc — read by nvm/fnm/Volta
22
```

```json
// package.json (excerpt)
{
  "engines": {
    "node": ">=22.0.0",
    "npm": ">=10.0.0"
  }
}
```

> **Why `engines` matters:** npm warns by default, and with `engine-strict=true` in `.npmrc` it
> *fails*. That single line turns "it crashed on the deploy box" into "install refused, with the reason".

---

## 3. Creating the project

```bash
mkdir express-api && cd express-api
npm init -y

# ESM everywhere — no mixed module systems.
npm pkg set type=module
npm pkg set private=true
npm pkg set engines.node=">=22.0.0"

# Ports and behaviour come from the environment, never from the code.
npm pkg set scripts.start="node src/server.js"
npm pkg set scripts.dev="node --watch --env-file-if-exists=.env src/server.js"
npm pkg set scripts.test="node --test tests/"
```

### `package.json` anatomy

```json
{
  "name": "express-api",
  "version": "0.1.0",
  "private": true,
  "description": "Notes API — Express 5 reference implementation",
  "type": "module",
  "engines": { "node": ">=22.0.0" },
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js",
    "dev": "node --watch --env-file-if-exists=.env src/server.js",
    "test": "node --test tests/",
    "test:watch": "node --test --watch tests/",
    "lint": "eslint .",
    "format": "prettier --write .",
    "check": "npm run lint && npm test"
  }
}
```

| Field | Why it is there |
| --- | --- |
| `"type": "module"` | All `.js` files are ESM. No `require`, no `__dirname` (use `import.meta.dirname`) |
| `"private": true` | Guards against accidental `npm publish` — an API is not a library |
| `"engines"` | Documents and enforces the supported Node version |
| `"main"` | Points at the entry file; only meaningful for consumers, but keeps tooling honest |
| `"scripts"` | The project's *verbs*: anyone can run `npm start` without reading your README |

> **Version pinning philosophy (from [01-nodejs/05-npm.md](../01-nodejs/05-npm.md)):** use ranges in
> `package.json` (`^5.2.1`) and let `package-lock.json` pin exact versions. Commit the lockfile —
> always, for applications.

### Runtime vs development dependencies

```bash
# Runtime: needed to serve requests in production
npm install express helmet cors pino pino-http zod

# Development: needed only on your machine and in CI
npm install --save-dev eslint @eslint/js prettier supertest
```

| Package | Layer | What it gives you | Chapter |
| --- | --- | --- | --- |
| `express` | runtime | Routing + middleware pipeline | 01–21 |
| `helmet` | runtime | Security-related HTTP headers | 18 |
| `cors` | runtime | Cross-Origin Resource Sharing headers | 16 |
| `pino`, `pino-http` | runtime | Fast structured JSON logging | 20 |
| `zod` | runtime | Schema validation | 12 |
| `supertest` | dev | HTTP assertions for tests | 19 |
| `eslint`, `prettier` | dev | Linting and formatting | this chapter |

**Deliberately absent:** `body-parser` (built into Express as `express.json()`), `dotenv` (Node reads
`.env` files natively), `nodemon` (`node --watch` is built in), `morgan` (pino-http is structured).
Every dependency you do not add is one you never have to audit, upgrade or debug.

```json
// package.json (dependencies section, after install)
{
  "dependencies": {
    "cors": "^2.8.5",
    "express": "^5.2.1",
    "helmet": "^8.1.0",
    "pino": "^10.0.0",
    "pino-http": "^11.0.0",
    "zod": "^4.1.11"
  },
  "devDependencies": {
    "@eslint/js": "^9.30.0",
    "eslint": "^9.30.0",
    "prettier": "^3.6.0",
    "supertest": "^7.1.0"
  }
}
```

---

## 4. The folder structure

```text
express-api/
├── .env                       ← real values, gitignored
├── .env.example               ← documented keys, committed
├── .gitignore
├── .nvmrc
├── eslint.config.js
├── package.json
├── package-lock.json          ← committed
├── README.md
├── src/
│   ├── server.js              ← process entry: listen, signals, process-level guards
│   ├── app.js                 ← builds the Express app (no listen) → testable
│   ├── config/
│   │   └── env.js             ← the ONLY module that reads process.env
│   ├── routes/
│   │   ├── index.js           ← mounts every resource router under /api/v1
│   │   ├── noteRoutes.js
│   │   └── userRoutes.js
│   ├── controllers/
│   │   ├── noteController.js  ← HTTP in, HTTP out: read req, call service, send res
│   │   └── userController.js
│   ├── services/
│   │   ├── noteService.js     ← business rules; no req, no res
│   │   └── userService.js
│   ├── repositories/
│   │   ├── noteRepository.js  ← persistence; no business rules
│   │   └── userRepository.js
│   ├── models/
│   │   └── noteModel.js       ← data shape + invariants (Mongoose schemas live here later)
│   ├── middleware/
│   │   ├── requestId.js
│   │   ├── requestLogger.js
│   │   ├── authenticate.js
│   │   ├── notFound.js
│   │   └── errorHandler.js
│   ├── validators/
│   │   └── noteSchemas.js     ← Zod schemas per request shape
│   ├── utils/
│   │   ├── AppError.js        ← error classes + HTTP mapping
│   │   └── asyncHandler.js    ← only needed if you wrap async handlers (see ch. 08)
│   └── database/
│       └── connect.js         ← connection lifecycle (Mongo/Postgres/MySQL)
└── tests/
    ├── health.test.js
    └── notes.test.js
```

### The dependency rule

```text
        ┌──────────────────────────────────────────────┐
route ──▶ controller ──▶ service ──▶ repository ──▶ database
 (URL)      (HTTP)       (rules)     (queries)        (driver)
                                            ▲
                    models / validators ────┘  (data shape, shared)
```

**Arrows point one way only.** A repository must never import a service; a service must never import
`express`. Why this rule is worth enforcing:

| Violation | What breaks |
| --- | --- |
| Service imports `req`/`res` | You cannot reuse the logic from a cron job, a CLI or a queue worker — and you cannot unit test it without fake HTTP objects |
| Repository contains business rules | Rules spread across every query; a rule change means touching ten files |
| Controller talks to the database | Tests need a real database; there is nowhere to put a rule that both endpoints share |
| Config imported everywhere | You cannot tell which settings the app actually uses — or test with different ones |

`req` and `res` exist **only** in `routes/`, `controllers/` and `middleware/`. That single sentence
keeps a codebase testable.

### Layer responsibilities in one table

| Layer | Knows about | Must not know about | Typical line length |
| --- | --- | --- | --- |
| `routes/` | URLs, HTTP verbs, which middleware | Business rules, databases | 5–20 |
| `controllers/` | `req`, `res`, status codes | Databases, raw SQL, Mongo queries | 10–30 |
| `services/` | Rules, repository interfaces, errors | HTTP status codes, `req`, `res` | 20–80 |
| `repositories/` | The database driver, queries | HTTP, request-scoped data | 20–80 |
| `models/` | Data shape, invariants | Anything about transport | 10–60 |
| `middleware/` | Cross-cutting concerns | Business rules | 5–40 |
| `validators/` | Request shapes | Persistence | 10–60 |
| `utils/` | Nothing app-specific | Everything app-specific | — |
| `config/` | `process.env` | Everything else | 20–60 |

---

## 5. The `app.js` / `server.js` split

This is the single most important structural decision in a Node API, and it exists to make the app
testable.

```js
// File: src/app.js
import express from 'express';
import { createNoteRepository } from './repositories/noteRepository.js';
import { createNoteService } from './services/noteService.js';
import { createNoteController } from './controllers/noteController.js';
import { createNoteRouter } from './routes/noteRoutes.js';
import { requestId } from './middleware/requestId.js';
import { createRequestLogger } from './middleware/requestLogger.js';
import { notFound } from './middleware/notFound.js';
import { createErrorHandler } from './middleware/errorHandler.js';
import { env } from './config/env.js';

/**
 * Build the Express application. No listen(), no process signals, no I/O at import time.
 * Tests call this with a test config; server.js calls it with the real one.
 */
export function createApp({ config = env, logger } = {}) {
  const app = express();

  // --- global configuration ---------------------------------------------------
  app.disable('x-powered-by');
  app.set('trust proxy', config.trustProxy ?? false);
  app.set('json spaces', config.isProduction ? 0 : 2);   // pretty JSON in development only

  // --- cross-cutting middleware (order matters — see ch. 07) -------------------
  app.use(requestId);
  app.use(express.json({ limit: config.bodyLimit }));
  if (logger) app.use(createRequestLogger({ logger }));

  // --- routes -----------------------------------------------------------------
  const repository = createNoteRepository({ config, logger });
  const service = createNoteService({ repository, logger });
  const controller = createNoteController({ service });

  app.get('/health', (req, res) => {
    res.json({ status: 'ok', uptimeSeconds: Number(process.uptime().toFixed(1)) });
  });

  app.use('/api/v1/notes', createNoteRouter({ controller }));

  // --- terminal middleware (always last, in this order) ------------------------
  app.use(notFound);
  app.use(createErrorHandler({ config, logger }));

  return app;
}
```

```js
// File: src/server.js
import { createApp } from './app.js';
import { env } from './config/env.js';
import { logger } from './utils/logger.js';

const app = createApp({ config: env, logger });

const server = app.listen(env.port, env.host, () => {
  logger.info('server started', {
    url: `http://${env.host}:${env.port}`,
    env: env.nodeEnv,
    node: process.version,
    pid: process.pid,
  });
});

// Fail fast on EADDRINUSE instead of hanging silently.
server.on('error', (error) => {
  logger.error('failed to start server', { code: error.code, message: error.message });
  process.exit(1);
});

// --- graceful shutdown --------------------------------------------------------
let shuttingDown = false;

function shutdown(reason) {
  if (shuttingDown) return;
  shuttingDown = true;
  logger.info('shutdown initiated', { reason });

  server.close((error) => {
    if (error) {
      logger.error('error during shutdown', { message: error.message });
      process.exit(1);
    }
    logger.info('server closed cleanly');
    process.exit(0);
  });

  // Stop accepting new connections and idle keep-alive sockets immediately.
  server.closeIdleConnections?.();

  setTimeout(() => {
    logger.error('forced exit after 10s — open connections were killed');
    process.exit(1);
  }, 10_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('uncaughtException', (error) => {
  logger.error('uncaughtException', { message: error.message, stack: error.stack });
  shutdown('uncaughtException');
});
process.on('unhandledRejection', (reason) => {
  logger.error('unhandledRejection', {
    message: reason instanceof Error ? reason.message : String(reason),
  });
  shutdown('unhandledRejection');
});
```

### Why the split matters (concretely)

```js
// File: tests/health.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';

let server;
let baseUrl;

before(() => {
  const app = createApp({ config: { isProduction: false, bodyLimit: '100kb', trustProxy: false } });
  server = app.listen(0, '127.0.0.1');                 // port 0 = any free port
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

test('GET /health returns ok', async () => {
  const response = await fetch(`${baseUrl}/health`);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).status, 'ok');
});
```

| Without the split | With the split |
| --- | --- |
| Importing `app.js` starts a server on port 3000 | Importing `app.js` does nothing |
| Tests collide on the port and hang | Each test gets port `0` — the OS picks a free one |
| You cannot test two configurations at once | `createApp({ config })` — different config per test |

Compare the equivalent in the raw-`http` project from [01-nodejs/18-nodejs-project.md](../01-nodejs/18-nodejs-project.md)
— same idea, same benefit.

---

## 6. Environment configuration

```bash
# .env.example — COMMITTED. Documents every key, contains no secrets.
NODE_ENV=development
PORT=3000
HOST=0.0.0.0
LOG_LEVEL=debug
BODY_LIMIT=100kb
TRUST_PROXY=false
# DATABASE_URL=postgres://user:password@localhost:5432/app
# JWT_SECRET=replace-me-with-32-plus-random-bytes
```

```bash
# .env — GITIGNORED. Real local values.
NODE_ENV=development
PORT=3000
LOG_LEVEL=debug
```

```bash
# .gitignore
node_modules/
.env
.env.*
!.env.example
*.log
coverage/
dist/
.DS_Store
```

```js
// File: src/config/env.js
/**
 * The ONLY module that reads process.env.
 * Throws at import time if the configuration is invalid — so the process dies
 * before it can serve a request with a missing secret.
 */
const problems = [];

function required(name) {
  const value = process.env[name];
  if (value === undefined || value.trim() === '') {
    problems.push(`${name} is required`);
    return undefined;
  }
  return value;
}

function optional(name, fallback) {
  const value = process.env[name];
  return value === undefined || value.trim() === '' ? fallback : value;
}

function optionalInt(name, fallback, { min, max } = {}) {
  const raw = process.env[name];
  if (raw === undefined || raw.trim() === '') return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value)) {
    problems.push(`${name} must be an integer, received "${raw}"`);
    return fallback;
  }
  if (min !== undefined && value < min) problems.push(`${name} must be >= ${min}`);
  if (max !== undefined && value > max) problems.push(`${name} must be <= ${max}`);
  return value;
}

function optionalBool(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw.trim() === '') return fallback;
  if (['true', '1', 'yes'].includes(raw.toLowerCase())) return true;
  if (['false', '0', 'no'].includes(raw.toLowerCase())) return false;
  problems.push(`${name} must be a boolean, received "${raw}"`);
  return fallback;
}

export const env = Object.freeze({
  nodeEnv: optional('NODE_ENV', 'development'),
  host: optional('HOST', '0.0.0.0'),
  port: optionalInt('PORT', 3000, { min: 0, max: 65535 }),
  logLevel: optional('LOG_LEVEL', 'info'),
  bodyLimit: optional('BODY_LIMIT', '100kb'),
  trustProxy: optionalBool('TRUST_PROXY', false),
  serviceName: optional('SERVICE_NAME', 'express-api'),
});

if (problems.length > 0) {
  // console.error, not the logger: the logger needs config, which is what just failed.
  console.error('Invalid configuration:');
  for (const problem of problems) console.error(`  - ${problem}`);
  process.exit(1);
}
```

> **Do not use `dotenv` in new projects.** Node 20.6+ reads `.env` files natively:
> `node --env-file=.env src/server.js`. Use `--env-file-if-exists=.env` in `npm run dev` so a missing
> file is not an error, and rely on real environment variables in production (Docker, systemd, your
> platform). Full reasoning in [01-nodejs/15-environment-variables.md](../01-nodejs/15-environment-variables.md).

### `NODE_ENV` — the only three values

| Value | Meaning | Behaviour that may change |
| --- | --- | --- |
| `development` | Your machine; `npm run dev` | Pretty JSON, verbose logs, stack traces in error responses |
| `test` | Automated tests | In-memory or throwaway database, logging silenced |
| `production` | Real users | No stack traces in responses, JSON logs, `secure` cookies, no pretty printing |

Anything else (`staging`, `qa`) is *your* convention and Express does not know about it — check for it
explicitly if it behaves differently.

---

## 7. Editor and code-quality tooling

```js
// File: eslint.config.js — ESLint 9 flat config (the current format)
import js from '@eslint/js';

export default [
  js.configs.recommended,
  {
    files: ['**/*.js'],
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: 'module',                 // ESM: `import`/`export`, not `require`
      globals: {
        process: 'readonly',
        console: 'readonly',
        Buffer: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        fetch: 'readonly',
        URL: 'readonly',
      },
    },
    rules: {
      'no-unused-vars': ['error', { argsIgnorePattern: '^_|next$' }],  // `next` is required by Express
      'no-console': ['warn', { allow: ['warn', 'error'] }],            // structure your logs
      'prefer-const': 'error',
      'no-var': 'error',
      eqeqeq: ['error', 'always'],
      'no-return-await': 'error',
      'require-atomic-updates': 'warn',
    },
  },
  {
    ignores: ['node_modules/**', 'coverage/**', 'dist/**'],
  },
];
```

```json
// File: .prettierrc.json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "arrowParens": "always"
}
```

```bash
# .editorconfig — consistency regardless of editor
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false
```

```bash
npm run lint      # find problems
npm run format    # fix formatting
npm run check     # lint + test — the command CI runs
```

---

## 8. Optional: TypeScript

You do **not** need TypeScript to follow these notes. But a real API benefits enormously from types at
the boundary (request bodies, environment, service signatures). Adding it to this structure is small:

```bash
npm install --save-dev typescript tsx @types/node @types/express
npx tsc --init
```

```json
// File: tsconfig.json (the parts that matter)
{
  "compilerOptions": {
    "target": "ES2023",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2023"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "verbatimModuleSyntax": true,
    "outDir": "dist",
    "rootDir": "src",
    "sourceMap": true,
    "declaration": false,
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts"]
}
```

```json
// package.json (scripts)
{
  "scripts": {
    "dev": "tsx watch --env-file-if-exists=.env src/server.ts",
    "build": "tsc",
    "start": "node --env-file-if-exists=.env dist/server.js",
    "typecheck": "tsc --noEmit"
  }
}
```

| Setting | Why |
| --- | --- |
| `module`/`moduleResolution: NodeNext` | The correct ESM resolution for Node 22+ — matches runtime behaviour |
| `strict: true` | The whole point; without it TypeScript is documentation, not a check |
| `noUncheckedIndexedAccess` | `array[0]` becomes `T \| undefined` — catches a whole class of runtime bugs |
| `verbatimModuleSyntax` | Forces `import type` where needed, so emitted JS matches what Node expects |
| `tsx` for development | Runs `.ts` directly with no build step; use `tsc` for the production build |

Every example in these notes is plain JavaScript so the framework behaviour is never hidden behind
type machinery — but the structure, layering and error contract translate 1:1.

---

## 9. Verify the setup end to end

```bash
npm run dev
```

```text
{"level":"info","message":"server started","url":"http://0.0.0.0:3000","env":"development","node":"v22.22.3","pid":55123}
```

```bash
curl -s localhost:3000/health
# {"status":"ok","uptimeSeconds":0.4}

curl -s -i localhost:3000/does-not-exist | head -3
# HTTP/1.1 404 Not Found
# Content-Type: application/json; charset=utf-8
# {"error":{"code":"ROUTE_NOT_FOUND","message":"GET /does-not-exist not found"}}

# Confirm the version disclosure is gone:
curl -s -I localhost:3000/health | grep -i x-powered-by || echo "x-powered-by disabled ✅"

# Confirm graceful shutdown:
# press Ctrl+C and watch the log
# {"level":"info","message":"shutdown initiated","reason":"SIGINT"}
# {"level":"info","message":"server closed cleanly"}
```

```bash
node --env-file=.env -e "console.log(process.env.PORT)"   # 3000 — proves .env is being read
node -e "process.exit(process.env.NOPE ? 1 : 0)"; echo "exit=$?"   # exit=0
```

---

## 10. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| `app.listen()` inside `app.js` | Tests hang or collide on a port | Split: `createApp()` in `app.js`, `listen` in `server.js` |
| `process.env` read all over the codebase | Config errors surface deep inside requests | One validated `config/env.js`, fail fast |
| `.env` committed | Secrets in git history forever | `.env.example` committed, `.env*` ignored |
| No `"type": "module"` yet ESM syntax | `SyntaxError: Cannot use import statement outside a module` | Set it, or use `.mjs` |
| `nodemon` + `dotenv` by reflex | Two dependencies doing what Node does | `node --watch`, `--env-file` |
| Dependencies in `devDependencies` | Works locally, crashes in production (`Cannot find module 'express'`) | Anything imported by `src/` is a runtime dependency |
| `package-lock.json` ignored | Non-reproducible installs | Commit it for applications |
| Port hard-coded | Deployment platform cannot inject `PORT` | Read from config |
| Business logic in route handlers | Impossible to unit test or reuse | Controller → service → repository |
| No `notFound`/error middleware | HTML error pages from a JSON API | Register both, last, in that order |
| `next` unused and removed by the linter | Middleware is not recognised as an error handler | Keep the 4th parameter (the ESLint rule above allows it) |
| `import.meta.dirname` on Node < 20.11 | `undefined` | Upgrade Node, or use `fileURLToPath(new URL('.', import.meta.url))` |

---

## Exercise 2.1 — Build the skeleton

Create the project from scratch with no copy-pasting from this chapter, such that:

1. `npm start` serves `GET /health` returning `{ status: 'ok', uptimeSeconds: <number> }`.
2. `GET /api/v1/notes` returns `{ data: [], meta: { total: 0 } }` (empty for now).
3. Any unknown route returns the JSON error contract `{ error: { code, message } }` with status 404.
4. A route that throws returns `500` with code `INTERNAL_ERROR`, and a route that throws an error with
   `statusCode = 422` returns `422` with that code.
5. `PORT`, `HOST` and `LOG_LEVEL` come from the environment, validated centrally.
6. `src/app.js` exports a factory that does not listen; `src/server.js` starts it.
7. `node --test tests/` passes a test that imports the factory and hits `/health` on port `0`.

<details>
<summary>Solution</summary>

```json
// File: package.json
{
  "name": "express-api-exercise",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "engines": { "node": ">=22.0.0" },
  "scripts": {
    "start": "node src/server.js",
    "dev": "node --watch --env-file-if-exists=.env src/server.js",
    "test": "node --test tests/"
  },
  "dependencies": {
    "express": "^5.2.1"
  }
}
```

```js
// File: src/config/env.js
const problems = [];

function read(name, fallback) {
  const raw = process.env[name];
  return raw === undefined || raw.trim() === '' ? fallback : raw;
}

function readInt(name, fallback, { min = -Infinity, max = Infinity } = {}) {
  const raw = process.env[name];
  if (raw === undefined || raw.trim() === '') return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < min || value > max) {
    problems.push(`${name} must be an integer between ${min} and ${max}, received "${raw}"`);
    return fallback;
  }
  return value;
}

export const env = Object.freeze({
  nodeEnv: read('NODE_ENV', 'development'),
  host: read('HOST', '0.0.0.0'),
  port: readInt('PORT', 3000, { min: 0, max: 65535 }),
  logLevel: read('LOG_LEVEL', 'info'),
  bodyLimit: read('BODY_LIMIT', '100kb'),
});

if (problems.length > 0) {
  console.error('Invalid configuration:');
  for (const problem of problems) console.error(`  - ${problem}`);
  process.exit(1);
}
```

```js
// File: src/utils/AppError.js
/** Errors the API deliberately sends to clients carry an HTTP status. */
export class AppError extends Error {
  constructor(message, { statusCode = 500, code = 'INTERNAL_ERROR', details } = {}) {
    super(message);
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.expected = statusCode < 500;
    Error.captureStackTrace?.(this, new.target);
  }
}

export class ValidationError extends AppError {
  constructor(details, message = 'Request validation failed') {
    super(message, { statusCode: 422, code: 'VALIDATION_ERROR', details });
  }
}

export class NotFoundError extends AppError {
  constructor(message = 'Resource not found') {
    super(message, { statusCode: 404, code: 'NOT_FOUND' });
  }
}
```

```js
// File: src/middleware/notFound.js
export function notFound(req, res) {
  res.status(404).json({
    error: { code: 'ROUTE_NOT_FOUND', message: `${req.method} ${req.originalUrl} not found` },
  });
}
```

```js
// File: src/middleware/errorHandler.js
import { AppError } from '../utils/AppError.js';

/** Four parameters — this arity is what marks it as an error handler. */
export function createErrorHandler({ config, logger = console } = {}) {
  return function errorHandler(error, req, res, next) {
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    const code = error instanceof AppError ? error.code : 'INTERNAL_ERROR';

    logger.error(
      JSON.stringify({
        level: 'error',
        message: error.message,
        path: req.originalUrl,
        statusCode,
        stack: statusCode >= 500 ? error.stack : undefined,
      })
    );

    if (res.headersSent) return next(error);      // delegate to Express's default handler

    const isProduction = config?.nodeEnv === 'production' || config?.isProduction === true;
    return res.status(statusCode).json({
      error: {
        code,
        message: statusCode >= 500 && isProduction ? 'Something went wrong' : error.message,
        details: error instanceof AppError ? error.details : undefined,
      },
    });
  };
}
```

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';

export function createNoteRouter() {
  const router = Router();

  router.get('/', (req, res) => {
    res.json({ data: [], meta: { total: 0 } });
  });

  return router;
}
```

```js
// File: src/app.js
import express from 'express';
import { createNoteRouter } from './routes/noteRoutes.js';
import { notFound } from './middleware/notFound.js';
import { createErrorHandler } from './middleware/errorHandler.js';
import { env as defaultEnv } from './config/env.js';
import { AppError, NotFoundError } from './utils/AppError.js';

export function createApp({ config = defaultEnv, logger = console } = {}) {
  const app = express();

  app.disable('x-powered-by');
  app.use(express.json({ limit: config.bodyLimit }));

  app.get('/health', (req, res) => {
    res.json({ status: 'ok', uptimeSeconds: Number(process.uptime().toFixed(1)) });
  });

  app.use('/api/v1/notes', createNoteRouter());

  // Deliberate failure routes, to prove the error contract works.
  app.get('/debug/boom', () => {
    throw new Error('deliberate programmer error');
  });
  app.get('/debug/business', () => {
    throw new AppError('Business rule violated', { statusCode: 422, code: 'BUSINESS_RULE' });
  });
  app.get('/debug/missing', () => {
    throw new NotFoundError('Nothing here');
  });

  app.use(notFound);
  app.use(createErrorHandler({ config, logger }));

  return app;
}
```

```js
// File: src/server.js
import { createApp } from './app.js';
import { env } from './config/env.js';

const app = createApp({ config: env });
const server = app.listen(env.port, env.host, () => {
  console.log(`listening on http://${env.host}:${env.port} (${env.nodeEnv}, log level ${env.logLevel})`);
});

server.on('error', (error) => {
  console.error(`failed to start: ${error.code} — ${error.message}`);
  process.exit(1);
});

let shuttingDown = false;
function shutdown(reason) {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(`shutting down (${reason})`);
  server.close(() => process.exit(0));
  server.closeIdleConnections?.();
  setTimeout(() => process.exit(1), 10_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
```

```js
// File: tests/app.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';

const testConfig = { nodeEnv: 'test', bodyLimit: '100kb', host: '127.0.0.1', port: 0 };

let server;
let baseUrl;

before(async () => {
  const app = createApp({ config: testConfig, logger: { error: () => {} } });
  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

test('GET /health', async () => {
  const response = await fetch(`${baseUrl}/health`);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.status, 'ok');
  assert.equal(typeof body.uptimeSeconds, 'number');
});

test('GET /api/v1/notes starts empty', async () => {
  const response = await fetch(`${baseUrl}/api/v1/notes`);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { data: [], meta: { total: 0 } });
});

test('unknown route → 404 with the error contract', async () => {
  const response = await fetch(`${baseUrl}/nope`);
  assert.equal(response.status, 404);
  const body = await response.json();
  assert.equal(body.error.code, 'ROUTE_NOT_FOUND');
  assert.match(body.error.message, /GET \/nope/);
});

test('a thrown programmer error → 500 INTERNAL_ERROR', async () => {
  const response = await fetch(`${baseUrl}/debug/boom`);
  assert.equal(response.status, 500);
  assert.equal((await response.json()).error.code, 'INTERNAL_ERROR');
});

test('an AppError keeps its status and code', async () => {
  const response = await fetch(`${baseUrl}/debug/business`);
  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.code, 'BUSINESS_RULE');
});

test('a thrown NotFoundError → 404 NOT_FOUND', async () => {
  const response = await fetch(`${baseUrl}/debug/missing`);
  assert.equal(response.status, 404);
  assert.equal((await response.json()).error.code, 'NOT_FOUND');
});
```

```bash
npm test
curl -s localhost:3000/health
curl -s -i localhost:3000/nope | head -5
PORT=not-a-number npm start; echo "exit=$?"     # validation refuses to start: exit=1
```

**Why this is the correct solution:** the app factory takes its configuration as a parameter (so tests
never touch `process.env`), the error contract is identical for every failure path, and the only place
that knows about `process.env` is `src/config/env.js`.

</details>

---

## Exercise 2.2 — Audit someone else's setup

A colleague's repository contains:

```text
api/
├── index.js                 ← app.listen(3000) at line 4, routes below it
├── routes.js                ← imports db from './db.js'
├── db.js                    ← const url = process.env.DATABASE_URL || 'mongodb://localhost/x'
├── .env                     ← committed, contains a real password
├── package.json             ← no "type", no engines, express in devDependencies
└── (no tests)
```

List every problem, the failure it causes in production, and the minimum fix.

<details>
<summary>Solution</summary>

| # | Problem | Failure it causes | Minimum fix |
| --- | --- | --- | --- |
| 1 | `app.listen` in the same file as the routes | Nothing can import the app; no tests possible | Split `app.js` (factory) and `server.js` (listen) |
| 2 | Committed `.env` with a real password | The secret is in git history and must be rotated | Remove from the repo, add to `.gitignore`, commit `.env.example`, **rotate the credential** |
| 3 | No `"type": "module"` | `import` fails, or you are stuck in CommonJS | Add `"type": "module"` and convert, or use `.mjs` |
| 4 | No `engines` | A newer Node on the deploy box behaves differently | Add `"engines": { "node": ">=22" }` + `.nvmrc` |
| 5 | `express` in `devDependencies` | Production install (`npm ci --omit=dev`) has no Express → `Cannot find module 'express'` | Move to `dependencies` |
| 6 | Hard-coded port 3000 | Heroku/Render/Fly inject `$PORT`; the app listens on the wrong port and the health check fails | `const port = Number(process.env.PORT ?? 3000)` via config |
| 7 | `process.env` read where it is used, with a fallback | In production, a missing variable silently uses a local default — you connect to the wrong database | Validate all config at startup; no fallbacks for secrets in production |
| 8 | Connection URL created at import time with a default | A typo becomes a runtime failure on the first request, not a startup failure | Validate `DATABASE_URL` as required; fail fast |
| 9 | No tests | Every refactor is a gamble | `node --test` with `createApp({ config })` |
| 10 | No `notFound`/error middleware | HTML error pages; stack traces leaked in production | Add both, in that order |
| 11 | No graceful shutdown | In-flight requests are cut off on every deploy | `SIGTERM` handler with `server.close()` |
| 12 | Routes import the database directly | No place for shared rules; untestable without a real DB | Introduce service/repository layers |

**Minimum viable structure after the fixes:**

```text
api/
├── .env.example
├── .gitignore
├── .nvmrc
├── package.json          (type: module, engines, express in dependencies)
├── src/
│   ├── app.js            (createApp — no listen)
│   ├── server.js         (listen + signals)
│   ├── config/env.js     (validated; DATABASE_URL required)
│   └── routes/index.js
└── tests/app.test.js
```

```bash
# Rotate the leaked credential first — git history keeps it forever.
# Then, in the repository root:
git rm --cached .env
printf 'node_modules/\n.env\n.env.*\n!.env.example\n' >> .gitignore
npm pkg set type=module
npm pkg set engines.node=">=22.0.0"
npm install express                # moves it to dependencies
git add -A && git commit -m "fix: harden project setup (config, secrets, layering)"
```

**The lesson:** none of these problems are about Express. Every one is a *structure* decision — which
is exactly why this chapter exists before routing and middleware.

</details>

---

## What's next

Now that the skeleton exists and config is centralised, we can talk about the framework's core job:
turning URLs into handler functions.

→ [03 — Routing](03-routing.md)
