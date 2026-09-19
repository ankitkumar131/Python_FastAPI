# 20 — Production Architecture

> **Where this fits:** The previous nineteen chapters built features. This one organises them into a
> codebase that a team can grow, debug at 2 a.m., and deploy without fear — the layout, the request flow
> through every layer, and the runtime concerns (configuration, logging, health checks, graceful shutdown,
> scaling) that separate "works on my laptop" from "runs in production".

---

## 1. Why structure is a survival tool

A small Express app can live in one file. The same app after a year has 60 routes, 12 tables, three
integrators and four people committing to it. Without structure:

| Symptom | Root cause | Consequence |
| --- | --- | --- |
| "Where does this validation live?" | No agreed home for each kind of code | Duplication, drift, bugs in one path only |
| A test needs a server and a database | Business logic entangled with HTTP and drivers | Slow suites, fear of refactoring |
| Changing the ORM takes a month | Queries spread through controllers and routes | A rewrite instead of an adapter swap |
| One query from the request handler | No boundary between layers | N+1 queries, untestable code, leaks |
| "Who calls this?" is unanswerable | Circular imports between modules | Fragile startup, confusion |

**The layout is not decoration. Each folder exists to answer a question** — "where do I put this?" and
"where do I look for it?".

```text
src/
├── config/          What differs per environment        → env validation, constants, feature flags
├── routes/          The URL surface                     → paths, methods, which middleware runs
├── controllers/     HTTP in, HTTP out                   → status codes, headers, DTOs
├── services/        The business rules                  → decisions that need data
├── repositories/    Data access                         → queries, transactions, mapping
├── models/          Data shape (when using an ODM/ORM)  → Mongoose schemas / Sequelize models
├── middleware/      Cross-cutting request concerns      → auth, validation, logging, errors, limits
├── validators/      Input contracts                     → Zod/Joi schemas per resource
├── utils/           Small shared tools                  → AppError, logger, pagination, clock, ids
├── database/        Connection lifecycle                → pool/client, health check, migrations
├── app.js           Builds the Express app (no listen)  → testable, environment-agnostic
└── server.js        Owns the process                    → listen, signals, shutdown, timeouts
```

Two invariants keep the layout honest:

1. **Dependencies point one way**: `routes → controllers → services → repositories → database`. Nothing
   points back. A repository never imports a controller; a service never sees `req`.
2. **Only `server.js` listens, and only `config/` reads `process.env`.**

---

## 2. The complete tree, with every file explained

```text
notes-api/
├── .env.example                     # the configuration contract (no secrets)
├── .gitignore                       # .env*, node_modules, coverage, var/
├── .nvmrc                           # 24
├── package.json                     # scripts, engines, no secrets
├── package-lock.json                # committed
├── eslint.config.js
├── Dockerfile
├── compose.yaml
├── README.md
├── src/
│   ├── app.js                       # express app: middleware + routers, no listen
│   ├── server.js                    # createServer(app), listen, signals, timeouts
│   ├── container.js                 # composition root: builds services/controllers once
│   ├── config/
│   │   ├── env.js                   # validates process.env, exports a frozen config object
│   │   └── constants.js             # limits, defaults, enums (no environment logic)
│   ├── database/
│   │   ├── client.js                # pool + withTransaction + healthCheck
│   │   ├── withTransaction.js       # BEGIN / COMMIT / ROLLBACK / release
│   │   └── migrate.js               # forward-only migrations runner
│   ├── routes/
│   │   ├── index.js                 # /api/v1 tree
│   │   ├── noteRoutes.js
│   │   ├── authRoutes.js
│   │   └── adminRoutes.js
│   ├── controllers/
│   │   ├── noteController.js
│   │   ├── authController.js
│   │   └── adminController.js
│   ├── services/
│   │   ├── noteService.js
│   │   ├── authService.js
│   │   └── tokenService.js
│   ├── repositories/
│   │   ├── noteRepository.js
│   │   └── userRepository.js
│   ├── models/                      # empty for SQL; Mongoose schemas live here
│   │   └── noteModel.js
│   ├── middleware/
│   │   ├── requestId.js
│   │   ├── httpLogger.js
│   │   ├── auth.js                  # authenticate + requireAuth + requireRole
│   │   ├── cors.js                  # the origin allowlist (narrow, explicit)
│   │   ├── loadNote.js              # loads :id resources once, for the whole chain
│   │   ├── validate.js              # Zod → req.validated
│   │   ├── csrf.js
│   │   ├── rateLimit.js
│   │   ├── notFound.js
│   │   ├── methodNotAllowed.js
│   │   └── errorHandler.js
│   ├── validators/
│   │   ├── noteSchemas.js
│   │   └── authSchemas.js
│   ├── dtos/
│   │   ├── noteDto.js               # the wire contract, explicit
│   │   └── userDto.js
│   ├── utils/
│   │   ├── AppError.js
│   │   ├── logger.js
│   │   ├── pagination.js
│   │   ├── metrics.js               # prom-client registry + RED middleware
│   │   ├── clock.js                 # injectable time
│   │   └── ids.js                   # injectable id generation
│   └── errors/                      # domain error classes
│       ├── AppError.js              # AppError + Validation/NotFound/Conflict/…
│       └── normalizeError.js        # anything → { statusCode, code, details }
├── tests/
│   ├── support/
│   │   ├── harness.js
│   │   └── inMemoryNoteRepository.js
│   ├── unit/
│   │   └── noteService.test.js
│   ├── integration/
│   │   ├── notes.routes.test.js
│   │   └── architecture.test.js     # asserts the dependency rules
│   └── e2e/
│       └── notes.e2e.test.js        # real database, real HTTP
├── scripts/
│   ├── migrate.mjs
│   └── seed.mjs
└── var/                             # runtime data (gitignored): uploads, logs, reports
```

### `config/` — the only place that reads the environment

```js
// File: src/config/env.js
import { z } from 'zod';

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(0).max(65_535).default(3000),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),

  DATABASE_URL: z.url(),
  REDIS_URL: z.url().optional(),

  JWT_SECRET: z.string().min(32),
  JWT_REFRESH_SECRET: z.string().min(32),
  COOKIE_SECRET: z.string().min(32),
  SESSION_SECRET: z.string().min(32),

  ALLOWED_ORIGINS: z.string().default('http://localhost:5173')
    .transform((value) => value.split(',').map((item) => item.trim()).filter(Boolean)),

  SHUTDOWN_TIMEOUT_MS: z.coerce.number().int().min(1_000).max(120_000).default(15_000),
  RATE_LIMIT_ENABLED: z.enum(['true', 'false']).default('true').transform((value) => value === 'true'),
});
// Note: no .strict() — process.env contains PATH, HOME and dozens of other keys, so a strict
// object schema would reject every real process. Unknown keys are ignored, as they should be.

const parsed = schema.safeParse(process.env);

if (!parsed.success) {
  // Fail fast, name the variables, never print values.
  console.error('Invalid environment configuration:');
  for (const issue of parsed.error.issues) console.error(`  ${issue.path.join('.')}: ${issue.message}`);
  process.exit(1);
}

export const env = Object.freeze({
  ...parsed.data,
  isProduction: parsed.data.NODE_ENV === 'production',
  isTest: parsed.data.NODE_ENV === 'test',
});
```

| Rule | Why |
| --- | --- |
| Validate once, at startup | A typo becomes a clear error, not a 2 a.m. mystery |
| Export a frozen object | Nothing mutates configuration at runtime |
| Never print values, only names | A failed validation must not dump secrets into logs |
| Defaults only for safe things | A missing `DATABASE_URL` must crash, not silently point at localhost |

### `database/` — connection lifecycle and transactions

```js
// File: src/database/client.js
import { Pool } from 'pg';
import { withTransaction } from './withTransaction.js';

export function createDatabase({ connectionString, logger, max = 10 }) {
  const pool = new Pool({
    connectionString,
    max,                                    // more connections ≠ more throughput; they queue at the DB
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 5_000,
    application_name: 'notes-api',
  });

  pool.on('error', (error) => logger.error({ err: error }, 'idle client error'));

  return {
    query: (text, params) => pool.query(text, params),
    withTransaction: (fn) => withTransaction({ pool, logger, fn }),
    async healthCheck() {
      const started = performance.now();
      await pool.query('SELECT 1');
      return { ok: true, latencyMs: Math.round(performance.now() - started) };
    },
    async close() {
      await pool.end();
    },
  };
}
```

```js
// File: src/database/withTransaction.js
export async function withTransaction({ pool, logger, fn, isolation }) {
  const client = await pool.connect();
  try {
    await client.query(isolation ? `BEGIN ISOLATION LEVEL ${isolation}` : 'BEGIN');
    const result = await fn(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    await client.query('ROLLBACK');
    logger.warn({ err: error }, 'transaction rolled back');
    throw error;
  } finally {
    client.release();                      // ALWAYS: a leaked client shrinks the pool
  }
}
```

| Concern | Where it belongs | Why |
| --- | --- | --- |
| Pool creation | `database/client.js`, called from `server.js` | One pool per process |
| Transactions | `withTransaction`, used by repositories | The mechanics of `BEGIN`/`COMMIT` are infrastructure |
| Migration runner | `database/migrate.js` + `scripts/migrate.mjs` | Schema changes are a deploy step, not a request-time action |
| Health check | `database/client.js` | Readiness must not run a business query |

### `repositories/` — the only place that speaks the database

```js
// File: src/repositories/noteRepository.js
export function createNoteRepository({ db }) {
  return {
    async list({ authorId, offset, limit, sort, tags, q }) {
      // Identifiers come from an allowlist (see 02-express/18-security.md), values from parameters.
      const SORTS = { createdAt: 'created_at', updatedAt: 'updated_at', title: 'title' };
      const [field, direction] = sort.startsWith('-') ? [sort.slice(1), 'DESC'] : [sort, 'ASC'];
      const orderBy = SORTS[field] ?? 'created_at';

      const conditions = ['author_id = $1'];
      const values = [authorId];

      if (tags?.length) {
        values.push(tags);
        conditions.push(`tags && $${values.length}`);
      }
      if (q) {
        values.push(`%${q}%`);
        conditions.push(`title ILIKE $${values.length}`);
      }

      values.push(limit, offset);

      const { rows } = await db.query(
        `SELECT id, title, content, tags, pinned, author_id, created_at, updated_at
           FROM notes
          WHERE ${conditions.join(' AND ')}
          ORDER BY ${orderBy} ${direction}
          LIMIT $${values.length - 1} OFFSET $${values.length}`,
        values,
      );

      const { rows: [{ count }] } = await db.query(
        `SELECT count(*)::int AS count FROM notes WHERE ${conditions.join(' AND ')}`,
        values.slice(0, -2),
      );

      return { items: rows.map(toDomain), total: count };
    },
    /* findById, create, update, remove, countByNote … */
  };
}

/** Rows are snake_case; the domain is camelCase. Convert at the boundary, once. */
function toDomain(row) {
  return {
    id: row.id,
    title: row.title,
    content: row.content,
    tags: row.tags ?? [],
    pinned: row.pinned,
    authorId: row.author_id,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}
```

| Rule | Why |
| --- | --- |
| Repositories return domain objects, not driver rows | The rest of the app never knows the column names |
| No business rules here | "May this user edit it?" needs policy; repositories only answer questions |
| Every query parameterised | The last line of defence against injection |
| Pagination and sorting inside the repository | The SQL dialect is the repository's problem |

### `utils/` — the small shared tools

```js
// File: src/utils/clock.js — injectable time
export function createClock({ now = () => new Date() } = {}) {
  return { now, isoNow: () => now().toISOString() };
}

export const systemClock = createClock();
```

```js
// File: src/utils/pagination.js
export function buildPaginationMeta({ page, limit, total }) {
  return {
    page,
    limit,
    total,
    pages: limit > 0 ? Math.ceil(total / limit) : 0,
    hasNext: page * limit < total,
    hasPrevious: page > 1,
  };
}
```

```js
// File: src/utils/ids.js — injectable identity generation
import { randomUUID } from 'node:crypto';

export function createIdGenerator({ uuid = randomUUID } = {}) {
  return { next: () => uuid() };
}
```

> **Why inject time and ids?** Tests become deterministic (chapter 19), and a future change (Snowflake ids,
> a different clock source) touches one file instead of everywhere.

---

## 3. The request flow, end to end

The instruction's flow diagram, annotated with what each step owns and what can go wrong:

```text
Client
  │
  ▼
1. Reverse proxy / load balancer     TLS, HTTP→HTTPS, compression, timeouts, IP forwarding
  │
  ▼
2. Node HTTP server (server.js)      requestTimeout, headersTimeout, keepAliveTimeout
  │
  ▼
3. Global middleware (app.js)        requestId → logging → helmet → cors → json (limit) → cookie → session
  │
  ▼
4. Router (routes/)                  which method + path → which middleware + controller
  │
  ▼
5. Route middleware                  authenticate → requireAuth → rateLimit → validate(schema) → loadResource
  │
  ▼
6. Controller                        read req.validated / req.user → call the service → map to HTTP
  │
  ▼
7. Service                           business rules, orchestration, transactions, domain events
  │
  ▼
8. Repository                        queries, parameter binding, row → domain mapping
  │
  ▼
9. Database                          constraints, indexes, transactions — the final guarantee
  │
  ▼ (and back up the same path, with DTOs replacing domain objects on the way out)
10. Controller                       status code, Location, headers, { data, meta }
  │
  ▼
11. Response middleware              logging (status, duration), request id header
  │
  ▼
Client
```

A concrete trace of `PATCH /api/v1/notes/6b1f…` with `Authorization: Bearer …`:

| Step | File | What happens | Failure mode |
| --- | --- | --- | --- |
| 1 | proxy | TLS terminated, `X-Forwarded-For` set | Missing `trust proxy` → wrong `req.ip` |
| 2 | `server.js` | Socket accepted, timeouts applied | Slowloris without timeouts |
| 3 | `middleware/httpLogger.js` | `req.id` generated, log line started | Logging the `authorization` header |
| 3 | `middleware/rateLimit.js` | Counter incremented for this key | Memory store per instance |
| 4 | `routes/noteRoutes.js` | `PATCH /:id` matched | Route order shadows another route |
| 5 | `middleware/auth.js` | Token verified, user loaded | 401 with the wrong error code |
| 5 | `middleware/validate.js` | Body parsed by the Zod schema | Raw body used instead of `req.validated` |
| 5 | `middleware/loadNote.js` | Note loaded into `res.locals` | 404 vs 403 leaking existence |
| 6 | `controllers/noteController.js` | Calls `noteService.update(id, input, { actor })` | Business logic creeping in |
| 7 | `services/noteService.js` | Ownership rule; DTO-ready result | Rule bypassed by another entry point |
| 8 | `repositories/noteRepository.js` | `UPDATE … WHERE id = $1 AND author_id = $2 RETURNING *` | N+1 or missing `WHERE` |
| 9 | PostgreSQL | Row updated, constraint enforced | Unique violation surfaces as a 500 without mapping |
| 10 | `controllers/noteController.js` | `res.json({ data: toNoteDto(note) })` | Leaking internal columns |
| 11 | `middleware/httpLogger.js` | `res.on('finish')` logs status + duration | No duration metric → no latency visibility |

```js
// File: src/app.js — the complete production app builder
import express from 'express';
import helmet from 'helmet';
import cookieParser from 'cookie-parser';
import { createRequestId } from './middleware/requestId.js';
import { createHttpLogger } from './middleware/httpLogger.js';
import { createCorsMiddleware, createCorsOptions } from './middleware/cors.js';
import { createCsrfProtection } from './middleware/csrf.js';
import { createLimiters } from './middleware/rateLimit.js';
import { notFound } from './middleware/notFound.js';
import { methodNotAllowed } from './middleware/methodNotAllowed.js';
import { createErrorHandler } from './middleware/errorHandler.js';

export function createApp({ config, container }) {
  const app = express();
  const { logger, database, redis, apiRouter, metrics, allowedMethods } = container;

  // ── Identity of the process ────────────────────────────────────────────────
  app.disable('x-powered-by');
  if (config.isProduction) app.set('trust proxy', 1);
  app.set('etag', 'strong');
  app.set('json escape', true);              // escapes <, >, & in JSON output (XSS belt-and-braces)

  // ── Security and cross-cutting concerns ────────────────────────────────────
  app.use(helmet({ /* … see 02-express/18-security.md … */ }));
  app.use(createCorsMiddleware(createCorsOptions({ allowedOrigins: config.allowedOrigins, isProduction: config.isProduction })));
  app.use(createRequestId);
  app.use(createHttpLogger({ logger }));

  // ── Body and cookies ───────────────────────────────────────────────────────
  app.use(express.json({ limit: '100kb', strict: true }));
  app.use(express.urlencoded({ extended: false, limit: '100kb' }));
  app.use(cookieParser(config.cookieSecret));

  // ── Limits ─────────────────────────────────────────────────────────────────
  const limiters = createLimiters({ redis, isProduction: config.isProduction });
  if (config.rateLimitEnabled) {
    app.use('/api/v1/auth/login', limiters.auth);
    app.use('/api/v1/auth/register', limiters.register);
    app.use('/api/v1', limiters.global);
  }

  // ── CSRF for cookie-authenticated mutations ────────────────────────────────
  app.use(createCsrfProtection({ isProduction: config.isProduction }));

  // ── Observability endpoints (before auth, minimal output) ──────────────────
  app.get('/health/live', (req, res) => res.json({ status: 'ok' }));           // is the process alive?
  app.get('/health/ready', async (req, res) => {                               // can it serve traffic?
    try {
      const [db, cache] = await Promise.all([
        database ? database.healthCheck() : { ok: true },
        redis ? redis.ping().then(() => ({ ok: true })) : { ok: true },
      ]);
      if (!db.ok || !cache.ok) throw new Error('dependency unhealthy');
      return res.json({ status: 'ok', checks: { database: db, redis: cache } });
    } catch (error) {
      return res.status(503).json({ status: 'unavailable', error: error.message });
    }
  });
  app.get('/metrics', metrics.handler);

  // ── Application routes ─────────────────────────────────────────────────────
  app.use('/api/v1', apiRouter);

  // ── Terminators: order matters ─────────────────────────────────────────────
  app.use(methodNotAllowed({ allowedMethods }));         // 405 before 404, or it never runs
  app.use(notFound);
  app.use(createErrorHandler({ logger, isProduction: config.isProduction }));

  return app;
}
```

```js
// File: src/server.js — the only file that owns the process
import { createServer } from 'node:http';
import { createApp } from './app.js';
import { env } from './config/env.js';
import { createContainer } from './container.js';

const container = createContainer({ config: env });
const app = createApp({ config: env, container });
const server = createServer(app);

// ── Timeouts: the cheapest DoS protection you will ever add ─────────────────
server.requestTimeout = 30_000;       // whole request must arrive within 30 s
server.headersTimeout = 10_000;       // headers within 10 s (must be < requestTimeout)
server.keepAliveTimeout = 5_000;      // slightly higher than the proxy's keep-alive
server.maxHeadersCount = 100;

server.listen(env.PORT, '0.0.0.0', () => {
  container.logger.info({ port: env.PORT, env: env.NODE_ENV, pid: process.pid }, 'server listening');
});

// ── Graceful shutdown ───────────────────────────────────────────────────────
let shuttingDown = false;

async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;

  container.logger.info({ signal }, 'shutdown started');
  const forceExit = setTimeout(() => {
    container.logger.error('shutdown timed out — forcing exit');
    process.exit(1);
  }, env.SHUTDOWN_TIMEOUT_MS);

  forceExit.unref();

  server.close(async (error) => {                 // stop accepting NEW connections
    if (error) {
      container.logger.error({ err: error }, 'error while closing the server');
      clearTimeout(forceExit);
      process.exit(1);
    }

    await container.close();                      // close pools, queues, redis
    clearTimeout(forceExit);
    container.logger.info('shutdown complete');
    process.exit(0);
  });

  // Stop keep-alive sockets from holding the process open.
  server.closeIdleConnections?.();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));   // containers, systemd, orchestration
process.on('SIGINT', () => shutdown('SIGINT'));     // Ctrl+C in development
process.on('uncaughtException', (error) => {
  container.logger.fatal({ err: error }, 'uncaughtException');
  shutdown('uncaughtException');                    // exit non-zero via the timeout path
});
process.on('unhandledRejection', (reason) => {
  container.logger.fatal({ err: reason }, 'unhandledRejection');
  shutdown('unhandledRejection');
});
```

```js
// File: src/container.js — the composition root
import { createDatabase } from './database/client.js';
import { createLogger } from './utils/logger.js';
import { createClock } from './utils/clock.js';
import { createIdGenerator } from './utils/ids.js';
import { createPasswordHasher } from './security/passwordHasher.js';
import { createTokenService } from './services/tokenService.js';
import { createNoteRepository } from './repositories/noteRepository.js';
import { createUserRepository } from './repositories/userRepository.js';
import { createNoteService } from './services/noteService.js';
import { createAuthService } from './services/authService.js';
import { createNoteController } from './controllers/noteController.js';
import { createAuthController } from './controllers/authController.js';
import { createApiRouter } from './routes/index.js';
import { createAuthenticate, requireAuth, requireRole } from './middleware/auth.js';
import { createLoadNote } from './middleware/loadNote.js';
import { createMetrics } from './utils/metrics.js';

export function createContainer({ config }) {
  // ── Infrastructure ──────────────────────────────────────────────────────────
  const logger = createLogger({ level: config.LOG_LEVEL, isProduction: config.isProduction });
  const database = createDatabase({ connectionString: config.DATABASE_URL, logger });
  const clock = createClock();
  const ids = createIdGenerator();
  const passwordHasher = createPasswordHasher();
  const metrics = createMetrics();

  // What the app is allowed to answer with; the 405 middleware reads this map.
  const allowedMethods = {
    '/api/v1/notes': ['GET', 'POST'],
    '/api/v1/notes/:id': ['GET', 'PATCH', 'DELETE'],
    '/api/v1/auth/login': ['POST'],
    '/api/v1/auth/logout': ['POST'],
  };

  // ── Data access ─────────────────────────────────────────────────────────────
  const noteRepository = createNoteRepository({ db: database });
  const userRepository = createUserRepository({ db: database });

  // ── Domain ──────────────────────────────────────────────────────────────────
  const tokenService = createTokenService({ config, clock });
  const noteService = createNoteService({ noteRepository, logger, clock, ids });
  const authService = createAuthService({ userRepository, passwordHasher, tokenService, logger, clock });

  // ── HTTP adapters ───────────────────────────────────────────────────────────
  const noteController = createNoteController({ noteService, logger });
  const authController = createAuthController({ authService });

  // ── Middleware that needs dependencies ──────────────────────────────────────
  const middleware = {
    authenticate: createAuthenticate({ tokenService, userRepository, logger }),
    requireAuth,
    requireRole,
    loadNote: createLoadNote({ noteService }),
  };

  // ── The router tree ─────────────────────────────────────────────────────────
  const apiRouter = createApiRouter({
    controllers: { note: noteController, auth: authController },
    middleware,
  });

  return {
    logger,
    database,
    apiRouter,
    metrics,
    allowedMethods,
    async close() {
      // Close in reverse dependency order; every open resource must be released here,
      // or the graceful shutdown in server.js will hang until the force-exit timer fires.
      await database.close();
    },
  };
}
```

> **The container is the only place that knows how everything connects.** Tests build the same objects
> with fakes; `server.js` builds them with real infrastructure. Nothing else imports a repository directly.

---

## 4. Why each folder exists — the one-line answers

| Folder | Exists because… | If it did not exist |
| --- | --- | --- |
| `config/` | Environments differ; bad configuration must fail fast | `process.env` reads scattered everywhere, no validation |
| `routes/` | URLs are a public contract that must be reviewed at a glance | Paths hidden inside controllers; no overview of the API surface |
| `controllers/` | HTTP mapping (status, headers, DTOs) is a distinct concern | Status codes decided inside business logic; untestable without HTTP |
| `services/` | Rules need a home that is framework- and storage-agnostic | Rules duplicated per endpoint; jobs and CLIs cannot reuse them |
| `repositories/` | SQL belongs in one layer | Queries in controllers; an ORM change is a rewrite |
| `models/` | With an ODM/ORM the schema *is* code (validation, hooks, indexes) | Schemas defined ad hoc; inconsistent field rules |
| `middleware/` | Cross-cutting concerns must be composable and ordered | Auth/logging pasted into every handler |
| `validators/` | Input contracts must be reusable and auditable | Ad-hoc `if (!req.body.x)` checks with inconsistent errors |
| `dtos/` | The wire shape is a deliberate decision | Internal fields leak; every schema change breaks clients |
| `utils/` | Small shared tools with no domain meaning | Copy-paste of `AppError`, loggers, pagination math |
| `database/` | Connections, transactions and migrations have a lifecycle | Pools created per request; migrations run by hand |
| `app.js` | The app must be testable without a port | Tests open sockets; CORS-order bugs slip through |
| `server.js` | The process needs to start, report readiness and stop cleanly | Deploys drop in-flight requests |

---

## 5. Environment differences: dev, test, production

| Concern | Development | Test | Production |
| --- | --- | --- | --- |
| `NODE_ENV` | `development` | `test` | `production` |
| Process manager | `node --watch src/server.js` | `node --test` | systemd / Docker / k8s; one process per core |
| Config source | `.env` (gitignored) | fixtures/CI env | Secret manager + platform env |
| Logging | `pino-pretty`, `debug` level | Silent or `error` | JSON to stdout, `info`, redacted |
| Error bodies | Full message + stack in `details` | Full | Generic 5xx; details in logs by request id |
| Database | Local container | Container or in-memory fake | Managed instance, connection pooling, backups |
| HTTPS | plain HTTP (or `mkcert`) | n/a | TLS at the proxy; HSTS on |
| Cookies | `secure: false`, `SameSite: Lax` | same | `secure: true`, `SameSite=Strict` for refresh |
| Rate limits | effectively off | off or tiny limits | enabled, Redis-backed |
| CORS | permissive localhost | n/a | explicit allowlist |
| Caching | off | off | Redis + `Cache-Control` for GETs |
| Deploys | every save (`--watch`) | every commit | blue/green or rolling, migrations first |
| Backups | none | none | automated, restored in a drill |

```bash
# Development
node --watch --env-file=.env src/server.js

# Test
NODE_ENV=test node --test --test-concurrency=4

# Production (systemd or a container)
NODE_ENV=production node src/server.js
```

---

## 6. Process management and zero-downtime deploys

```ini
# File: deploy/notes-api.service — systemd, the plainest production setup
[Unit]
Description=Notes API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=notes
WorkingDirectory=/srv/notes-api
EnvironmentFile=/etc/notes-api/env
ExecStart=/usr/bin/node src/server.js
Restart=always
RestartSec=2

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/srv/notes-api/var
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

```yaml
# File: compose.yaml (production-shaped, abbreviated — full treatment in 06-docker/)
services:
  api:
    build: .
    environment:
      NODE_ENV: production
      PORT: '3000'
    env_file: [.env]
    ports: ['3000:3000']
    depends_on:
      db: { condition: service_healthy }
      cache: { condition: service_healthy }
    restart: unless-stopped
    stop_grace_period: 20s           # must exceed SHUTDOWN_TIMEOUT_MS
    healthcheck:
      test: ['CMD', 'node', '-e', "fetch('http://127.0.0.1:3000/health/live').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
      interval: 15s
      timeout: 3s
      retries: 3
      start_period: 20s
    deploy:
      replicas: 2
    logging:
      driver: json-file             # or your platform's log collector
      options: { max-size: '10m', max-file: '3' }

  db:
    image: postgres:18
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U $${POSTGRES_USER}']
      interval: 10s
      retries: 5

  cache:
    image: redis:8-alpine
    command: ['redis-server', '--save', '60', '1', '--appendonly', 'yes']
    volumes: [redisdata:/data]
    healthcheck:
      test: ['CMD', 'redis-cli', 'ping']
      interval: 10s

volumes:
  pgdata:
  redisdata:
```

| Component | Choice | Notes |
| --- | --- | --- |
| Process manager | systemd (VM), the orchestrator (containers), PM2 (single-server Node) | Prefer the platform's supervisor; PM2 only when you manage the box yourself |
| Clustering | Kubernetes replicas / Docker `--scale` / `cluster.fork()` | `cluster` is only justified on a single box with many cores |
| Zero-downtime | Rolling or blue/green + a readiness probe | Requires graceful shutdown, which requires `SIGTERM` handling |
| Migrations | Run as a job before the new version starts | Never auto-migrate on boot with multiple replicas |
| Secrets | Platform secret store, mounted as env | Never in the image or the repo |
| Config | Env vars + `env.js` validation | A bad deploy fails immediately at startup |

```text
Deploy sequence (rolling)
1. Build the new image / artefact
2. Run migrations (backwards-compatible: add columns, never drop in the same deploy)
3. Start new instances; they answer /health/live but fail /health/ready until dependencies are reachable
4. Load balancer shifts traffic once /health/ready is 200
5. SIGTERM the old instances; in-flight requests finish (≤ SHUTDOWN_TIMEOUT_MS)
6. Old instances exit; remove them

This is why readiness ≠ liveness, and why the process must handle SIGTERM.
```

---

## 7. Observability: logs, metrics, traces

```js
// File: src/middleware/httpLogger.js
import { pinoHttp } from 'pino-http';

export function createHttpLogger({ logger }) {
  return pinoHttp({
    logger,
    genReqId: (req, res) => {
      const existing = req.get('x-request-id');
      const id = existing && existing.length <= 100 ? existing : crypto.randomUUID();
      res.setHeader('X-Request-Id', id);
      return id;
    },
    // Never log credentials; redaction is configured on the logger itself.
    redact: ['req.headers.authorization', 'req.headers.cookie', 'res.headers["set-cookie"]'],
    customLogLevel: (req, res, error) => {
      if (error || res.statusCode >= 500) return 'error';
      if (res.statusCode >= 400) return 'warn';
      return 'info';
    },
    customSuccessMessage: (req, res) => `${req.method} ${req.url} → ${res.statusCode}`,
    customProps: (req) => ({ requestId: req.id, userId: req.user?.id ?? null }),
    autoLogging: { ignore: (req) => req.url === '/health/live' },
  });
}
```

```js
// File: src/utils/metrics.js — the RED method, without a dependency
import { Counter, Histogram, Registry, collectDefaultMetrics } from 'prom-client';

export function createMetrics() {
  const registry = new Registry();
  registry.setDefaultLabels({ service: 'notes-api' });
  collectDefaultMetrics({ register: registry });        // CPU, memory, event-loop lag, GC

  const requests = new Counter({
    name: 'http_requests_total',
    help: 'Total HTTP requests',
    labelNames: ['method', 'route', 'status'],
    registers: [registry],
  });

  const duration = new Histogram({
    name: 'http_request_duration_seconds',
    help: 'Request duration in seconds',
    labelNames: ['method', 'route', 'status'],
    buckets: [0.01, 0.05, 0.1, 0.3, 0.5, 1, 2, 5],
    registers: [registry],
  });

  return {
    middleware: (req, res, next) => {
      const start = process.hrtime.bigint();
      res.on('finish', () => {
        const route = req.route?.path ?? req.baseUrl ?? 'unmatched';   // label by ROUTE, not raw URL
        const labels = { method: req.method, route, status: String(res.statusCode) };
        requests.inc(labels);
        duration.observe(labels, Number(process.hrtime.bigint() - start) / 1e9);
      });
      next();
    },
    handler: async (req, res) => {
      res.set('Content-Type', registry.contentType);
      res.end(await registry.metrics());
    },
  };
}
```

| Pillar | Question it answers | Tool | Watch out for |
| --- | --- | --- | --- |
| **Logs** | What happened in this one request? | pino → stdout → collector | Never log secrets; always include `requestId`, `userId`, `route`, `status`, `durationMs` |
| **Metrics** | How is the system behaving overall? | Prometheus/OpenTelemetry | Never label by raw URL or user id (cardinality explodes); label by route pattern |
| **Traces** | Where did this request spend its time across services? | OpenTelemetry → Jaeger/Tempo | Sample in production; propagate the trace id like a request id |
| **Alerts** | Wake someone up | Error rate, p95 latency, saturation, queue depth | Alert on symptoms (users affected), not on causes (CPU) |

```text
Log line you want at 2 a.m.
{"level":30,"time":1789713664000,"requestId":"0f2c…","userId":"u1","method":"PATCH",
 "url":"/api/v1/notes/6b1f…","status":200,"durationMs":23,"msg":"PATCH /api/v1/notes/6b1f… → 200"}

Log line you never want
{"level":30,"req":{"headers":{"authorization":"Bearer eyJhbGciOiJIUzI1NiIs…"}}}
```

---

## 8. Background work, caching and scale

| Concern | Naive approach | Production approach | Where it lives |
| --- | --- | --- | --- |
| Sending email | `await mailer.send()` inside the request | Enqueue a job; a worker sends it | `services/` + a queue (BullMQ on Redis) |
| Image processing | Resize during upload | Upload → queue → worker → update the row | same |
| Reports | Generate on demand | Precompute on a schedule; serve the artefact | `scripts/` + a scheduler |
| Cache | None | Redis + `Cache-Control` for GETs | `services/` wraps the repository |
| Rate limits | In-memory counters | Redis-backed store | `middleware/rateLimit.js` |
| Sessions | MemoryStore | Redis store | `config/session.js` |
| Idempotency | None | An `Idempotency-Key` table/Redis entry | `middleware/idempotency.js` |
| Read scale | One database | Read replicas for reporting queries | `database/` — a separate pool |
| Write scale | Every write synchronous | Queue + outbox pattern for multi-system writes | `services/` |

```js
// File: src/queue/emailQueue.js — enqueue in the request, process in a worker
import { Queue, Worker } from 'bullmq';

export function createEmailQueue({ redis, logger, mailer }) {
  const queue = new Queue('email', { connection: redis.connection });

  const worker = new Worker(
    'email',
    async (job) => {
      switch (job.name) {
        case 'welcome': return mailer.sendWelcome(job.data.userId);
        case 'order-confirmation': return mailer.sendOrderConfirmation(job.data.orderId);
        default: throw new Error(`Unknown job: ${job.name}`);
      }
    },
    { connection: redis.connection, concurrency: 5, limiter: { max: 50, duration: 1_000 } },
  );

  worker.on('failed', (job, error) => logger.error({ err: error, jobId: job?.id }, 'job failed'));

  return {
    async enqueueWelcome(userId) {
      // jobId makes the enqueue idempotent: the same id is never processed twice.
      await queue.add('welcome', { userId }, { jobId: `welcome:${userId}`, attempts: 5, backoff: { type: 'exponential', delay: 1_000 } });
    },
    async close() { await worker.close(); await queue.close(); },
  };
}
```

```js
// File: src/services/noteService.js (excerpt) — the cache-aside pattern
export function createCachedNoteService({ noteRepository, cache }) {
  return {
    async listForUser({ actor, page, limit }) {
      const key = `notes:list:${actor.id}:${page}:${limit}`;

      const cached = await cache.get(key);
      if (cached) return { ...cached, cached: true };

      const { items, total } = await noteRepository.list({ authorId: actor.id, offset: (page - 1) * limit, limit });
      const result = { items, total, page, limit };

      await cache.set(key, result, { ttlSeconds: 30 });    // short TTL: correctness over cleverness
      return result;
    },

    // Invalidation is explicit and boring: every write deletes the affected keys.
    async update(id, patch, { actor }) {
      const note = await noteRepository.updateOwned(id, patch, { authorId: actor.id });
      if (!note) throw new Error('not found');            // mapped to 404 by the error handler

      await cache.deleteByPrefix(`notes:list:${actor.id}:`);
      return note;
    },
  };
}
```

| Pattern | Use when | Cost |
| --- | --- | --- |
| Cache-aside with a short TTL | Reads dominate; slight staleness is acceptable | Invalidation bugs if TTLs are long |
| Write-through | The cache must always be current | More write latency; still needs invalidation for workers |
| Queue for side effects | The response must not depend on a third party | Eventual consistency; needs monitoring |
| Outbox pattern | A database write and a message must both happen | Extra table + a relay process |
| Read replicas | Reporting/analytics load | Replication lag: reads may be stale |
| Horizontal scaling | More traffic than one process can serve | Requires stateless processes: sessions/cache in Redis, uploads in object storage |

---

## 9. Tests that protect the architecture

Structure rots silently. Two cheap tests keep it in place.

```js
// File: tests/integration/architecture.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

const SRC = path.resolve(import.meta.dirname, '../../src');

async function listSourceFiles(directory = SRC) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await listSourceFiles(full)));
    else if (entry.name.endsWith('.js')) files.push(full);
  }

  return files;
}

const importers = async (dir) => {
  const files = (await listSourceFiles()).filter((file) => file.includes(`/src/${dir}/`));
  return Promise.all(files.map(async (file) => ({ file, source: await readFile(file, 'utf8') })));
};

test('controllers never import a database driver or a repository', async () => {
  for (const { file, source } of await importers('controllers')) {
    assert.doesNotMatch(source, /from '\.\.\/repositories\//, `${file} imports a repository`);
    assert.doesNotMatch(source, /from 'pg'|from 'mongodb'|from 'mongoose'/, `${file} imports a driver`);
  }
});

test('services never import express or touch req/res', async () => {
  for (const { file, source } of await importers('services')) {
    assert.doesNotMatch(source, /from 'express'/, `${file} imports express`);
    assert.doesNotMatch(source, /\breq\.|\bres\./, `${file} references req/res`);
  }
});

test('repositories never import services or controllers', async () => {
  for (const { file, source } of await importers('repositories')) {
    assert.doesNotMatch(source, /from '\.\.\/(services|controllers|routes)\//, `${file} imports upwards`);
  }
});

test('only config/env.js reads process.env', async () => {
  const offenders = [];

  for (const file of await listSourceFiles()) {
    const source = await readFile(file, 'utf8');
    if (/process\.env/.test(source) && !file.endsWith('src/config/env.js')) offenders.push(path.relative(SRC, file));
  }

  assert.deepEqual(offenders, [], `process.env used outside config/env.js: ${offenders.join(', ')}`);
});

test('only server.js calls listen', async () => {
  const offenders = [];

  for (const file of await listSourceFiles()) {
    const source = await readFile(file, 'utf8');
    if (/\.listen\(/.test(source) && !file.endsWith('src/server.js')) offenders.push(path.relative(SRC, file));
  }

  assert.deepEqual(offenders, []);
});
```

```bash
node --test tests/integration/architecture.test.js
```

```text
✔ controllers never import a database driver or a repository
✔ services never import express or touch req/res
✔ repositories never import services or controllers
✔ only config/env.js reads process.env
✔ only server.js calls listen
pass 5
fail 0
```

> **These tests are unusual and valuable.** They express decisions that code review forgets: no layering
> violations, no scattered `process.env`, no accidental `listen()` in a library file.

---

## 10. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| `app.listen()` inside `app.js` | Tests need ports; parallel suites collide | Split into `app.js` + `server.js` |
| Business logic in controllers | Untestable rules; duplication | Move to services (chapter 11) |
| Queries in controllers | Driver coupling everywhere | Repositories own the SQL |
| `process.env` read in 20 files | Impossible to know the configuration; no validation | `config/env.js` only |
| Services receiving `req` | Cannot run from a job or CLI | Pass plain values + `{ actor }` |
| One `models/` folder with SQL business logic in "model" methods | Rules invisible, untestable | Repositories for queries, services for rules |
| No graceful shutdown | Deploys drop in-flight requests; readiness lies | Handle `SIGTERM`, close the server, then the pools |
| `/health` that queries everything | Health checks become a DoS vector and flap | `/health/live` (cheap) and `/health/ready` (dependencies) |
| Logging without a request id | Cannot correlate lines for one request | `X-Request-Id` + pino HTTP logger |
| Metrics labelled by raw URL | Cardinality explosion; the metrics store dies | Label by route pattern |
| Auto-migrating on boot with N replicas | Concurrent DDL; deadlocks | A migration job before the rollout |
| Secrets in `.env` committed or in the image | Leakage | Secret manager + `.env.example` |
| No request timeouts | Slowloris and stuck sockets | `requestTimeout`, `headersTimeout`, `keepAliveTimeout` |
| Queue jobs without idempotency | Duplicate emails/charges on retry | Unique `jobId` + idempotent handlers |
| `stateless` processes with local files | Uploads vanish on redeploy; replicas disagree | Object storage or a shared volume |
| A single pool size tuned for one instance | N instances × 10 connections exhaust the database | Size the pool per instance against the DB's max connections |
| No `close()` on pools/queues | Leaked connections; hanging shutdown | `container.close()` in the shutdown path |

---

## Exercise 20.1 — Restructure a single-file app

This is a working but unstructured app. Reorganise it into the target layout, keeping behaviour identical.

```js
// File: app.js — 70 lines, one file, everything
import express from 'express';
import jwt from 'jsonwebtoken';
import { Client } from 'pg';

const app = express();
app.use(express.json());

const db = new Client({ connectionString: process.env.DATABASE_URL });
await db.connect();

app.get('/notes', async (req, res) => {
  const result = await db.query('SELECT * FROM notes WHERE author_id = $1', [req.user.id]);
  res.json(result.rows);
});

app.post('/notes', async (req, res) => {
  const { title, content } = req.body;
  if (!title) return res.status(400).json({ message: 'title required' });
  const result = await db.query(
    'INSERT INTO notes (title, content, author_id) VALUES ($1, $2, $3) RETURNING *',
    [title, content, req.user.id],
  );
  res.json(result.rows[0]);
});

app.use((req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  try {
    req.user = jwt.verify(token, 'secret123');
  } catch {
    res.status(401).json({ message: 'unauthorized' });
  }
  next();
});

app.listen(3000);
```

Requirements:

1. The target file tree from §2 (`config`, `routes`, `controllers`, `services`, `repositories`, `database`, `middleware`, `validators`, `utils`, `dtos`, `app.js`, `server.js`, `container.js`).
2. Behaviour preserved *and improved*: validation with field-level 422, the error envelope, `201` + `Location` on create, ownership enforcement, DTOs, request ids, graceful shutdown.
3. The architecture tests from §9 must pass (no `process.env` outside `config`, no `listen()` outside `server.js`, no repository imports in controllers).
4. A test suite that still passes when the database is replaced by an in-memory repository.

<details>
<summary>Solution</summary>

```js
// File: src/config/env.js
import { z } from 'zod';

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(0).max(65_535).default(3000),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  DATABASE_URL: z.url(),
  JWT_SECRET: z.string().min(32, 'must be at least 32 characters to be a real secret'),
  SHUTDOWN_TIMEOUT_MS: z.coerce.number().int().default(15_000),
}).strict();

const parsed = schema.safeParse(process.env);
if (!parsed.success) {
  console.error('Invalid environment configuration:');
  for (const issue of parsed.error.issues) console.error(`  ${issue.path.join('.')}: ${issue.message}`);
  process.exit(1);
}

export const env = Object.freeze({ ...parsed.data, isProduction: parsed.data.NODE_ENV === 'production' });
```

```js
// File: src/errors/AppError.js
export class AppError extends Error {
  constructor(message, { statusCode = 500, code = 'INTERNAL_ERROR', details, cause, isOperational = true } = {}) {
    super(message, { cause });
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.isOperational = isOperational;
    Error.captureStackTrace?.(this, new.target);
  }
}

export class ValidationError extends AppError {
  constructor(message = 'Request validation failed', details) {
    super(message, { statusCode: 422, code: 'VALIDATION_ERROR', details });
  }
}
export class NotFoundError extends AppError {
  constructor(message = 'Not found', details) {
    super(message, { statusCode: 404, code: 'NOT_FOUND', details });
  }
}
export class UnauthorizedError extends AppError {
  constructor(message = 'Authentication required', details) {
    super(message, { statusCode: 401, code: 'UNAUTHENTICATED', details });
  }
}
export class ForbiddenError extends AppError {
  constructor(message = 'Not allowed', details) {
    super(message, { statusCode: 403, code: 'FORBIDDEN', details });
  }
}
export class ConflictError extends AppError {
  constructor(message = 'Conflict', details) {
    super(message, { statusCode: 409, code: 'CONFLICT', details });
  }
}
```

```js
// File: src/errors/normalizeError.js
import { AppError } from './AppError.js';

/**
 * Every thrown value becomes a shape the error handler can trust:
 * AppErrors pass through, everything else is treated as a 500 and hidden from clients.
 */
export function normalizeError(error) {
  if (error instanceof AppError) return error;

  // A single mapping point for driver errors we can name.
  if (error?.code === '23505' || error?.code === '11000') {
    return new AppError('That value already exists', { statusCode: 409, code: 'CONFLICT', details: { constraint: error.constraint } });
  }
  if (error?.type === 'entity.too.large') {
    return new AppError('Payload too large', { statusCode: 413, code: 'PAYLOAD_TOO_LARGE' });
  }
  if (error?.type === 'entity.parse.failed') {
    return new AppError('Request body is not valid JSON', { statusCode: 400, code: 'INVALID_JSON' });
  }
  if (error instanceof SyntaxError && 'body' in error) {
    return new AppError('Request body is not valid JSON', { statusCode: 400, code: 'INVALID_JSON' });
  }

  return new AppError('Internal server error', {
    statusCode: 500,
    code: 'INTERNAL_ERROR',
    cause: error,
    isOperational: false,
  });
}
```

```js
// File: src/utils/logger.js
import { pino } from 'pino';

export function createLogger({ level = 'info', isProduction = true } = {}) {
  return pino({
    level,
    redact: {
      paths: ['req.headers.authorization', 'req.headers.cookie', 'res.headers["set-cookie"]', '*.passwordHash'],
      censor: '[redacted]',
    },
    ...(isProduction ? {} : { transport: { target: 'pino-pretty', options: { colorize: true, translateTime: 'HH:MM:ss' } } }),
  });
}
```

```js
// File: src/database/client.js
import pg from 'pg';

export function createDatabase({ connectionString, logger, max = 10 }) {
  const pool = new pg.Pool({ connectionString, max, idleTimeoutMillis: 30_000, connectionTimeoutMillis: 5_000 });
  pool.on('error', (error) => logger.error({ err: error }, 'idle client error'));

  return {
    query: (text, params) => pool.query(text, params),
    async withTransaction(fn) {
      const client = await pool.connect();
      try {
        await client.query('BEGIN');
        const result = await fn(client);
        await client.query('COMMIT');
        return result;
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      } finally {
        client.release();
      }
    },
    async healthCheck() { await pool.query('SELECT 1'); return { ok: true }; },
    async close() { await pool.end(); },
  };
}
```

```js
// File: src/repositories/noteRepository.js
export function createNoteRepository({ db }) {
  const toDomain = (row) => ({
    id: row.id,
    title: row.title,
    content: row.content,
    authorId: row.author_id,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  });

  return {
    async listByAuthor(authorId, { offset = 0, limit = 20 } = {}) {
      const { rows } = await db.query(
        `SELECT id, title, content, author_id, created_at, updated_at
           FROM notes WHERE author_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3`,
        [authorId, limit, offset],
      );

      const { rows: [{ count }] } = await db.query('SELECT count(*)::int AS count FROM notes WHERE author_id = $1', [authorId]);
      return { items: rows.map(toDomain), total: count };
    },

    async findById(id) {
      const { rows } = await db.query(
        'SELECT id, title, content, author_id, created_at, updated_at FROM notes WHERE id = $1', [id],
      );
      return rows[0] ? toDomain(rows[0]) : null;
    },

    async existsByTitle(title, authorId) {
      const { rowCount } = await db.query('SELECT 1 FROM notes WHERE title = $1 AND author_id = $2', [title, authorId]);
      return rowCount > 0;
    },

    async create({ title, content, authorId }) {
      const { rows } = await db.query(
        `INSERT INTO notes (title, content, author_id) VALUES ($1, $2, $3)
         RETURNING id, title, content, author_id, created_at, updated_at`,
        [title, content, authorId],
      );
      return toDomain(rows[0]);
    },
  };
}
```

```js
// File: src/services/noteService.js
import { ConflictError, ForbiddenError, NotFoundError } from '../errors/AppError.js';

export function createNoteService({ noteRepository, clock, logger }) {
  return {
    async list({ actor, page, limit }) {
      const { items, total } = await noteRepository.listByAuthor(actor.id, { offset: (page - 1) * limit, limit });
      return { items, total, page, limit };
    },

    async create({ title, content }, { actor }) {
      if (await noteRepository.existsByTitle(title, actor.id)) {
        throw new ConflictError('You already have a note with that title', { field: 'title' });
      }

      const note = await noteRepository.create({ title, content, authorId: actor.id });
      logger.info('note created', { noteId: note.id, userId: actor.id });
      return note;
    },

    async getOwned(id, { actor }) {
      const note = await noteRepository.findById(id);
      if (!note) throw new NotFoundError(`Note ${id} not found`);
      if (note.authorId !== actor.id && actor.role !== 'ADMIN') throw new ForbiddenError('Not your note');
      return note;
    },

    /** Somewhere to put `clock`: created_at is a database default, but updates need a timestamp. */
    nowIso() { return clock().toISOString(); },
  };
}
```

```js
// File: src/controllers/noteController.js
import { toNoteDto } from '../dtos/noteDto.js';

export function createNoteController({ noteService }) {
  return {
    async list(req, res, next) {
      try {
        const { page, limit } = req.validated.query;
        const { items, total } = await noteService.list({ actor: req.user, page, limit });
        res.json({
          data: items.map(toNoteDto),
          meta: { page, limit, total, pages: Math.ceil(total / limit) },
        });
      } catch (error) { next(error); }
    },

    async create(req, res, next) {
      try {
        const note = await noteService.create(req.validated.body, { actor: req.user });
        res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: toNoteDto(note) });
      } catch (error) { next(error); }
    },

    async getOne(req, res, next) {
      try {
        const note = await noteService.getOwned(req.params.id, { actor: req.user });
        res.json({ data: toNoteDto(note) });
      } catch (error) { next(error); }
    },
  };
}
```

```js
// File: src/dtos/noteDto.js
export function toNoteDto(note) {
  return {
    id: note.id,
    title: note.title,
    content: note.content,
    authorId: note.authorId,
    createdAt: note.createdAt,
    updatedAt: note.updatedAt,
  };
}
```

```js
// File: src/validators/noteSchemas.js
import { z } from 'zod';

export const createNoteSchema = z.object({
  title: z.string().trim().min(1, 'must not be empty').max(200),
  content: z.string().trim().min(1, 'must not be empty').max(10_000),
}).strict();

export const listNotesQuerySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
}).strict();

export const idParamSchema = z.object({ id: z.uuid('must be a valid UUID') }).strict();
```

```js
// File: src/middleware/validate.js
export function validate(schema, source = 'body') {
  return function validateMiddleware(req, res, next) {
    const result = schema.safeParse(req[source] ?? {});
    if (!result.success) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Request validation failed',
          details: result.error.issues.map((issue) => ({
            field: issue.path.join('.') || source,
            message: issue.message,
            code: issue.code,
          })),
          requestId: req.id,
        },
      });
    }

    req.validated ??= {};
    req.validated[source] = result.data;
    return next();
  };
}
```

```js
// File: src/middleware/auth.js
import jwt from 'jsonwebtoken';
import { UnauthorizedError } from '../errors/AppError.js';

export function createRequireAuth({ secret, algorithms = ['HS256'] }) {
  return function requireAuth(req, res, next) {
    try {
      const [scheme, token] = (req.get('authorization') ?? '').split(' ');
      if (scheme !== 'Bearer' || !token) throw new UnauthorizedError('Authentication is required');

      const claims = jwt.verify(token, secret, { algorithms });
      req.user = { id: claims.sub, role: claims.role ?? 'USER' };
      return next();
    } catch (error) {
      return next(error instanceof UnauthorizedError
        ? error
        : new UnauthorizedError('The access token is invalid', { cause: error }));
    }
  };
}
```

```js
// File: src/middleware/errorHandler.js
import { normalizeError } from '../errors/normalizeError.js';

export function createErrorHandler({ logger, isProduction }) {
  return function errorHandler(error, req, res, next) {
    if (res.headersSent) return next(error);

    const mapped = normalizeError(error);
    const level = mapped.statusCode >= 500 ? 'error' : 'warn';
    logger[level]({ err: error, requestId: req.id, statusCode: mapped.statusCode }, mapped.message);

    return res.status(mapped.statusCode).json({
      error: {
        code: mapped.code,
        message: mapped.statusCode >= 500 && isProduction ? 'Something went wrong' : mapped.message,
        ...(mapped.details && mapped.isOperational ? { details: mapped.details } : {}),
        requestId: req.id,
      },
    });
  };
}
```

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { createNoteSchema, listNotesQuerySchema, idParamSchema } from '../validators/noteSchemas.js';

export function createNoteRouter({ controller, middleware }) {
  const router = Router();

  router.use(middleware.requireAuth);

  router.get('/', validate(listNotesQuerySchema, 'query'), controller.list);
  router.post('/', validate(createNoteSchema), controller.create);
  router.get('/:id', validate(idParamSchema, 'params'), controller.getOne);

  return router;
}
```

```js
// File: src/routes/index.js
import { Router } from 'express';
import { createNoteRouter } from './noteRoutes.js';
import { notFound } from '../middleware/notFound.js';

export function createApiRouter({ controllers, middleware }) {
  const router = Router();
  router.use('/notes', createNoteRouter({ controller: controllers.note, middleware }));
  router.use(notFound);
  return router;
}
```

```js
// File: src/app.js
import express from 'express';
import helmet from 'helmet';
import { randomUUID } from 'node:crypto';
import { createErrorHandler } from './middleware/errorHandler.js';
import { createApiRouter } from './routes/index.js';
import { createRequireAuth } from './middleware/auth.js';
import { createNoteController } from './controllers/noteController.js';
import { createNoteService } from './services/noteService.js';
import { createNoteRepository } from './repositories/noteRepository.js';

/**
 * In the full solution this lives in container.js; the shape is what matters:
 * infrastructure in, controllers out, and no listen().
 */
export function createApp({ config, container }) {
  const app = express();
  app.disable('x-powered-by');
  app.use(helmet());
  app.use(express.json({ limit: '100kb' }));
  app.use((req, res, next) => {
    req.id = req.get('x-request-id') ?? randomUUID();
    res.set('X-Request-Id', req.id);
    next();
  });

  const noteRepository = createNoteRepository({ db: container.database });
  const noteService = createNoteService({ noteRepository, clock: container.clock, logger: container.logger });
  const noteController = createNoteController({ noteService });

  const middleware = { requireAuth: createRequireAuth({ secret: config.JWT_SECRET }) };

  app.get('/health/live', (req, res) => res.json({ status: 'ok' }));
  app.get('/health/ready', async (req, res) => {
    try {
      await container.database.healthCheck();
      return res.json({ status: 'ok' });
    } catch (error) {
      return res.status(503).json({ status: 'unavailable' });
    }
  });

  app.use('/api/v1', createApiRouter({ controllers: { note: noteController }, middleware }));
  app.use(createErrorHandler({ logger: container.logger, isProduction: config.isProduction }));

  return app;
}
```

```js
// File: src/server.js
import { createServer } from 'node:http';
import { createApp } from './app.js';
import { createDatabase } from './database/client.js';
import { createLogger } from './utils/logger.js';
import { env } from './config/env.js';

const logger = createLogger({ level: env.LOG_LEVEL, isProduction: env.isProduction });
const database = createDatabase({ connectionString: env.DATABASE_URL, logger });
const clock = () => new Date();

const app = createApp({ config: env, container: { database, logger, clock } });
const server = createServer(app);

server.requestTimeout = 30_000;
server.headersTimeout = 10_000;
server.keepAliveTimeout = 5_000;

server.listen(env.PORT, '0.0.0.0', () => logger.info({ port: env.PORT }, 'listening'));

async function shutdown(signal) {
  logger.info({ signal }, 'shutting down');
  const force = setTimeout(() => process.exit(1), env.SHUTDOWN_TIMEOUT_MS).unref();

  server.close(async () => {
    await database.close();
    clearTimeout(force);
    process.exit(0);
  });

  server.closeIdleConnections?.();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
```

```bash
# The target tree, filled in
find src -type f -name '*.js' | sort
```

```text
src/app.js
src/config/env.js
src/controllers/noteController.js
src/database/client.js
src/dtos/noteDto.js
src/errors/AppError.js
src/errors/normalizeError.js
src/middleware/auth.js
src/middleware/errorHandler.js
src/middleware/notFound.js
src/middleware/validate.js
src/repositories/noteRepository.js
src/routes/index.js
src/routes/noteRoutes.js
src/server.js
src/services/noteService.js
src/utils/logger.js
src/validators/noteSchemas.js
```

```bash
# Behaviour check (the important part):
node --test                        # the suite still passes with a fake repository
node --test tests/architecture.test.js   # layering rules hold
curl -s localhost:3000/health/live
curl -s -X POST localhost:3000/api/v1/notes -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"title":"","content":"x"}'
```

```text
{"status":"ok"}
{"error":{"code":"VALIDATION_ERROR","message":"Request validation failed",
 "details":[{"field":"title","message":"must not be empty","code":"too_small"}],"requestId":"0f2c…"}}
```

**What changed, and why it matters**

| Before | After | Benefit |
| --- | --- | --- |
| `pg.Client` created in the entry file | `database/client.js` with a pool + health check + `close()` | Testable, closable, tunable |
| `SELECT *` mapped straight to JSON | Repository → domain → DTO | No internal columns leak; the ORM is replaceable |
| `if (!title) 400` | Zod schema → `422` with field details | One error contract |
| `jwt.verify` middleware registered *after* the routes | Middleware order correct, mounted at the router | The auth middleware actually protects the routes |
| `'secret123'` hard-coded | `config/env.js` with a ≥32-char requirement | No secrets in git; fail-fast startup |
| `res.json(rows)` for everything | `201` + `Location`, `{ data, meta }` | A predictable API |
| `app.listen(3000)` in the module | `server.js`, with timeouts and graceful shutdown | Tests without ports; deploys without dropped requests |
| No logging, no request ids | pino + `X-Request-Id` | Requests are traceable |

</details>

---

## Exercise 20.2 — Diagnose the growing app

A team's API has grown to 40 endpoints in one file. They report:

1. A test suite that needs a database and takes 8 minutes.
2. "We replaced Mongo with Postgres — it took five weeks."
3. A production incident: deploy dropped ~2 % of requests.
4. Logs where nobody can find a single request's lines.
5. A memory leak: the process grows until it is OOM-killed every ~36 hours.
6. A developer added a validation rule to `POST /notes` but `PATCH /notes/:id` still accepts the old shape.

For each symptom, name the missing structural element and the concrete change.

<details>
<summary>Solution</summary>

| # | Symptom | Root cause | Structural fix |
| --- | --- | --- | --- |
| 1 | 8-minute suite needing a database | Logic entangled with HTTP and the driver; tests exercise everything end to end | Split `app.js`/`server.js`; move rules to services; inject repositories so unit tests use an in-memory fake; keep one small database suite |
| 2 | A five-week database migration | Queries spread across controllers/routes; no repository boundary | All data access behind `repositories/` returning domain objects; then only repositories change |
| 3 | Deploys dropping 2 % of requests | No graceful shutdown: `SIGTERM` kills in-flight requests | Handle `SIGTERM`: `server.close()`, drain, close pools, exit; set `stop_grace_period`/`terminationGracePeriodSeconds` longer than the drain |
| 4 | Untraceable logs | No request id and no structured logging | `requestId` middleware + pino-http; log `requestId`, `userId`, `route`, `status`, `durationMs`; redact credentials |
| 5 | Memory growth every ~36 h | A likely leak: unbounded caches, listeners added per request, an in-memory rate limiter or session store, or promises accumulating | Move state to Redis; bound every cache with an LRU + TTL; audit `on()` calls for per-request listeners; take heap snapshots (`--heapsnapshot-signal`) to confirm |
| 6 | Rules applied on one endpoint only | Validation duplicated inside handlers instead of shared schemas | `validators/` schemas per resource; `validate(schema, source)` middleware on every route; the architecture test could even assert that every mutating route uses `validate` |

**The general lesson.** Every symptom is a missing *boundary*: process vs app (1, 3), storage vs logic (2),
request vs log (4), ownership of state (5), input vs rule (6). Structure is what makes those boundaries
enforceable — and tests are what keep them from eroding.

</details>

---

## What's next

Every piece now exists: layered structure, validation, authentication, uploads, security, tests, and a
production runtime. The final Express chapter assembles them into one complete, walk-through project —
the notes API, end to end, deployable.

→ [21 — Project: Complete Express API](21-complete-express-project.md)
