# 21 — Project: Complete Express API

> **Where this fits:** Chapters 01–20 taught every piece in isolation. This chapter assembles them into
> one real application: a **notes API** with authentication, roles, search, pagination, validation, a
> layered structure, tests, docs and a production runtime. It deliberately keeps the **data store in
> memory** so nothing here depends on a database — the next section (`03-databases/`) swaps one factory
> function for MongoDB, MySQL and PostgreSQL, and the rest of the application does not change.

---

## 1. What we are building

**`notes-api`** — a multi-user note-taking REST API.

| Feature | Detail |
| --- | --- |
| Accounts | Register, log in, refresh, log out, "who am I" |
| Sessions | Short-lived access token (Bearer) + rotating refresh token in a signed, httpOnly cookie |
| Roles | `USER` and `ADMIN`, enforced per route |
| Notes | Create, read, update, delete, pin, archive |
| Listing | Pagination, sorting, full-text-ish search, tag filter, pinned filter, archived filter |
| Safety | Zod validation, ownership checks, optimistic concurrency (`ETag`/`If-Match`) |
| Cross-cutting | Request ids, structured logs, rate limits, helmet, CORS allowlist, CSRF for cookie routes |
| Ops | `/health/live`, `/health/ready`, `/openapi.json`, `/docs` (Swagger UI, development only) |
| Quality | `node --test` suite with unit + integration tests, no database required |
| Structure | `config / routes / controllers / services / repositories / middleware / validators / utils / docs` |

### 1.1 The API surface

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health/live` | — | Is the process alive? |
| `GET` | `/health/ready` | — | Can it serve traffic (dependencies reachable)? |
| `GET` | `/openapi.json` | — | The OpenAPI 3.1 description |
| `GET` | `/docs` | — | Swagger UI (development only) |
| `POST` | `/api/v1/auth/register` | — | Create an account → `201` + tokens |
| `POST` | `/api/v1/auth/login` | — | Exchange credentials for tokens |
| `POST` | `/api/v1/auth/refresh` | cookie + CSRF | Rotate the refresh token, get a new access token |
| `POST` | `/api/v1/auth/logout` | cookie + CSRF | Revoke the refresh family, clear cookies → `204` |
| `GET` | `/api/v1/auth/me` | Bearer | The current user |
| `GET` | `/api/v1/notes` | Bearer | List your notes (`page`, `limit`, `sort`, `q`, `tag`, `pinned`, `archived`) |
| `POST` | `/api/v1/notes` | Bearer | Create a note → `201` + `Location` |
| `GET` | `/api/v1/notes/:id` | Bearer | One note → `200` + `ETag` |
| `PATCH` | `/api/v1/notes/:id` | Bearer, `If-Match` recommended | Partial update |
| `DELETE` | `/api/v1/notes/:id` | Bearer | Delete → `204` |
| `POST` | `/api/v1/notes/:id/pin` | Bearer | Pin a note |
| `DELETE` | `/api/v1/notes/:id/pin` | Bearer | Unpin |
| `POST` | `/api/v1/notes/:id/archive` | Bearer | Archive |
| `POST` | `/api/v1/notes/:id/unarchive` | Bearer | Unarchive |
| `GET` | `/api/v1/tags` | Bearer | Your tags with note counts |
| `GET` | `/api/v1/admin/users` | Bearer + `ADMIN` | Paginated user list |
| `PATCH` | `/api/v1/admin/users/:id/role` | Bearer + `ADMIN` | Promote or demote a user |
| `GET` | `/api/v1/admin/stats` | Bearer + `ADMIN` | Totals for the dashboard |

### 1.2 Conventions used everywhere

```text
Success:  { "data": …, "meta": { … } }                    meta only where it helps (lists)
Error:    { "error": { "code", "message", "details", "requestId" } }
Status:   200 ok · 201 created + Location · 204 no content · 400 bad JSON · 401 unauthenticated
          403 forbidden · 404 not found · 405 method not allowed · 409 conflict
          412 precondition failed · 422 validation error · 429 rate limited · 500 internal
Headers:  X-Request-Id on every response · ETag on resources · RateLimit-* on limited routes
```

### 1.3 The request flow this project implements

```text
Request
  ↓  app.js           requestId → logger → helmet → cors → json(100kb) → cookieParser
  ↓  routes/          method + path match, then the route's middleware chain
  ↓  middleware/      rateLimit → validate → requireAuth → requireRole
  ↓  controllers/     read req.validated + req.user, call the service, write the HTTP response
  ↓  services/        business rules: ownership, conflicts, concurrency, tokens
  ↓  repositories/    storage: filters, sorting, pagination, revision bumps
  ↓  (in-memory Map store — the only thing the database chapters will replace)
  ↑  repositories/    domain objects back up the same path
  ↑  services/        decisions and side effects (revocation, logging)
  ↑  controllers/     DTOs → { data, meta }, status codes, headers
  ↑  app.js           finish hook logs status + duration, error handler shapes failures
Response
```

---

## 2. Project structure

```text
notes-api/
├── .env.example
├── .gitignore
├── package.json
├── README.md
├── src/
│   ├── app.js                       # builds the Express app (no listen)
│   ├── server.js                    # owns the process: listen, signals, shutdown
│   ├── container.js                 # composition root: wires everything once
│   ├── config/
│   │   ├── env.js                   # validates process.env → frozen config
│   │   └── constants.js             # limits, sort allowlists, roles
│   ├── errors/
│   │   ├── AppError.js              # AppError + typed subclasses
│   │   └── normalizeError.js        # any thrown value → a safe error shape
│   ├── utils/
│   │   ├── logger.js                # pino with redaction
│   │   ├── passwordHasher.js        # scrypt hash/compare
│   │   ├── tokenService.js          # sign/verify access + refresh JWTs
│   │   ├── ids.js                   # injectable id generation
│   │   ├── clock.js                 # injectable time
│   │   ├── pagination.js            # { page, limit, offset } and response meta
│   │   └── etag.js                  # note → ETag value
│   ├── repositories/
│   │   ├── inMemoryUserRepository.js
│   │   ├── inMemoryNoteRepository.js
│   │   └── inMemoryRefreshTokenStore.js
│   ├── services/
│   │   ├── authService.js
│   │   ├── noteService.js
│   │   └── adminService.js
│   ├── dtos/
│   │   ├── userDto.js
│   │   └── noteDto.js
│   ├── validators/
│   │   ├── authSchemas.js
│   │   ├── noteSchemas.js
│   │   └── commonSchemas.js
│   ├── middleware/
│   │   ├── requestId.js
│   │   ├── httpLogger.js
│   │   ├── auth.js                  # authenticate + requireAuth + requireRole + optionalAuth
│   │   ├── validate.js
│   │   ├── rateLimit.js
│   │   ├── csrf.js
│   │   ├── notFound.js
│   │   ├── methodNotAllowed.js
│   │   └── errorHandler.js
│   ├── controllers/
│   │   ├── authController.js
│   │   ├── noteController.js
│   │   └── adminController.js
│   ├── routes/
│   │   ├── index.js
│   │   ├── authRoutes.js
│   │   ├── noteRoutes.js
│   │   ├── tagRoutes.js
│   │   └── adminRoutes.js
│   ├── docs/
│   │   ├── openapi.js               # the OpenAPI 3.1 document
│   │   └── swaggerUi.js             # the /docs HTML page
│   └── dev/
│       └── seed.js                  # demo user + notes (development only)
└── tests/
    ├── support/
    │   ├── harness.js               # createHarness(): frozen clock, counter ids, cookies
    │   └── repositoryStub.js        # a recording stand-in for the note repository
    ├── unit/
    │   └── noteService.test.js
    └── integration/
        ├── auth.routes.test.js
        └── notes.routes.test.js
```

**Layering rule (from chapter 20):** `routes → controllers → services → repositories`; nothing imports
upwards. Only `config/env.js` reads `process.env`, and only `server.js` calls `listen()`.

---

## 3. Setup

```bash
# 1. Create the project and install dependencies.
mkdir notes-api && cd notes-api
npm init -y
npm pkg set type=module engines.node=">=24" main=src/server.js

# 2. Runtime dependencies
npm install express@^5 cors zod jsonwebtoken cookie-parser helmet express-rate-limit pino pino-http

# 3. Development dependencies
npm install --save-dev supertest pino-pretty

# 4. Secrets for local development (never commit these)
cp .env.example .env
node -e "console.log('JWT_SECRET=' + require('node:crypto').randomBytes(48).toString('base64'))" >> .env
```

```text
added 127 packages, and audited 128 packages in 5s
found 0 vulnerabilities
```

The versions that were current when this chapter was written — all of them are the packages' `latest` at
the time, and the lockfile records the exact tree you got:

| Package | Version | Role |
| --- | --- | --- |
| `express` | 5.2.1 | HTTP framework (v5: async errors, no `path-to-regexp` legacy syntax) |
| `zod` | 4.6.5 | Validation, coercion, error formatting |
| `jsonwebtoken` | 9.0.3 | Signing and verifying the access/refresh JWTs |
| `cookie-parser` | 1.4.7 | `req.cookies` and signed cookies |
| `cors` | 2.8.6 | CORS headers with an origin allowlist |
| `helmet` | 8.3.0 | Security headers |
| `express-rate-limit` | 8.7.0 | Per-IP limits (`limit`, not the removed `max`) |
| `pino` | 10.3.1 | Structured logging with redaction |
| `pino-http` | 11.0.0 | One log line per request |
| `supertest` (dev) | 7.2.2 | HTTP assertions against the app object |
| `pino-pretty` (dev) | 13.1.3 | Human-readable logs in development only |

**File:** `package.json`

```json
{
  "name": "notes-api",
  "version": "1.0.0",
  "description": "A complete Express 5 notes API with authentication, roles and tests",
  "type": "module",
  "main": "src/server.js",
  "engines": { "node": ">=24" },
  "scripts": {
    "start": "node src/server.js",
    "dev": "node --watch --env-file=.env src/server.js",
    "test": "NODE_ENV=test node --test",
    "test:watch": "NODE_ENV=test node --test --watch",
    "test:coverage": "NODE_ENV=test node --test --experimental-test-coverage"
  }
}
```

**File:** `.env.example`

```bash
# Copy to .env, then generate real secrets:
#   cp .env.example .env
#   openssl rand -base64 48      # paste the output for each *_SECRET below

NODE_ENV=development
PORT=3000
LOG_LEVEL=debug

# Never reuse a secret across services, and never commit real values.
JWT_SECRET=replace-me-with-the-output-of-openssl-rand-base64-48
JWT_REFRESH_SECRET=replace-me-with-the-output-of-openssl-rand-base64-48
COOKIE_SECRET=replace-me-with-the-output-of-openssl-rand-base64-48

JWT_ISSUER=notes-api
JWT_AUDIENCE=notes-api-clients
ACCESS_TOKEN_TTL=15m
REFRESH_TOKEN_TTL_DAYS=30

ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
RATE_LIMIT_ENABLED=true
TRUST_PROXY=false
SEED_DEMO_DATA=true
SHUTDOWN_TIMEOUT_MS=15000
```

**File:** `.gitignore`

```text
node_modules/
.env
.env.*
!.env.example
coverage/
*.log
var/
.DS_Store
```

---

## 4. Configuration

```js
// File: src/config/env.js
import { z } from 'zod';

/** Environment variables are strings; parse booleans explicitly so "false" is not truthy. */
const booleanish = z.enum(['true', 'false']).transform((value) => value === 'true');

/** A placeholder must never reach production. */
const secret = z
  .string()
  .min(32, 'must be at least 32 characters — generate one with: openssl rand -base64 48')
  .refine((value) => !value.includes('replace-me'), 'still contains the placeholder from .env.example');

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(0).max(65_535).default(3000),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent']).default('info'),

  JWT_SECRET: secret,
  JWT_REFRESH_SECRET: secret,
  COOKIE_SECRET: secret,
  JWT_ISSUER: z.string().default('notes-api'),
  JWT_AUDIENCE: z.string().default('notes-api-clients'),
  ACCESS_TOKEN_TTL: z.string().default('15m'),
  REFRESH_TOKEN_TTL_DAYS: z.coerce.number().int().min(1).max(365).default(30),

  ALLOWED_ORIGINS: z.string().default('http://localhost:5173')
    .transform((value) => value.split(',').map((item) => item.trim()).filter(Boolean)),

  RATE_LIMIT_ENABLED: booleanish.default('true'),
  TRUST_PROXY: booleanish.default('false'),
  SEED_DEMO_DATA: booleanish.default('false'),
  SHUTDOWN_TIMEOUT_MS: z.coerce.number().int().min(1_000).max(120_000).default(15_000),
});
// Never call .strict() here: process.env also holds PATH, HOME, NODE_OPTIONS and dozens more,
// so a strict object would reject every real process. Unknown keys are simply ignored.

const parsed = schema.safeParse(process.env);

if (!parsed.success) {
  // Names and reasons only — never values, which may be secrets.
  console.error('Invalid environment configuration:');
  for (const issue of parsed.error.issues) {
    console.error(`  ${issue.path.join('.') || '(root)'}: ${issue.message}`);
  }
  process.exit(1);
}

export const config = Object.freeze({
  ...parsed.data,
  isProduction: parsed.data.NODE_ENV === 'production',
  isDevelopment: parsed.data.NODE_ENV === 'development',
  isTest: parsed.data.NODE_ENV === 'test',
  refreshTokenTtlMs: parsed.data.REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60 * 1_000,
});
```

```js
// File: src/config/constants.js
/** One place for every limit and allowlist. Magic numbers scattered in code are undebuggable. */
export const PAGINATION = Object.freeze({
  DEFAULT_PAGE: 1,
  DEFAULT_LIMIT: 20,
  MAX_LIMIT: 100,
});

export const NOTE_SORTS = Object.freeze({
  createdAt: 'createdAt',
  updatedAt: 'updatedAt',
  title: 'title',
  pinned: 'pinned',
});

export const ROLES = Object.freeze({ USER: 'USER', ADMIN: 'ADMIN' });

export const COOKIES = Object.freeze({
  refreshToken: 'refreshToken',
  csrfSecret: 'csrfSecret',
  refreshPath: '/api/v1/auth',
});

export const ERROR_CODES = Object.freeze({
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_JSON: 'INVALID_JSON',
  UNAUTHENTICATED: 'UNAUTHENTICATED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  METHOD_NOT_ALLOWED: 'METHOD_NOT_ALLOWED',
  CONFLICT: 'CONFLICT',
  PRECONDITION_FAILED: 'PRECONDITION_FAILED',
  PAYLOAD_TOO_LARGE: 'PAYLOAD_TOO_LARGE',
  CSRF_FAILED: 'CSRF_FAILED',
  TOO_MANY_REQUESTS: 'TOO_MANY_REQUESTS',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
});
```

---

## 5. Errors

```js
// File: src/errors/AppError.js
import { ERROR_CODES } from '../config/constants.js';

/**
 * The only error type the HTTP layer understands.
 * `isOperational` distinguishes "we knew this could happen" (401, 404, 422) from "a bug" (500).
 */
export class AppError extends Error {
  constructor(message, { statusCode = 500, code = ERROR_CODES.INTERNAL_ERROR, details, cause, isOperational = true } = {}) {
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
    super(message, { statusCode: 422, code: ERROR_CODES.VALIDATION_ERROR, details });
  }
}

export class UnauthenticatedError extends AppError {
  constructor(message = 'Authentication is required', details) {
    super(message, { statusCode: 401, code: ERROR_CODES.UNAUTHENTICATED, details });
  }
}

export class ForbiddenError extends AppError {
  constructor(message = 'You are not allowed to do that', details) {
    super(message, { statusCode: 403, code: ERROR_CODES.FORBIDDEN, details });
  }
}

export class NotFoundError extends AppError {
  constructor(message = 'Resource not found', details) {
    super(message, { statusCode: 404, code: ERROR_CODES.NOT_FOUND, details });
  }
}

export class ConflictError extends AppError {
  constructor(message = 'The resource already exists', details) {
    super(message, { statusCode: 409, code: ERROR_CODES.CONFLICT, details });
  }
}

export class PreconditionFailedError extends AppError {
  constructor(message = 'The resource changed on the server', details) {
    super(message, { statusCode: 412, code: ERROR_CODES.PRECONDITION_FAILED, details });
  }
}

export class TooManyRequestsError extends AppError {
  constructor(message = 'Too many requests', details) {
    super(message, { statusCode: 429, code: ERROR_CODES.TOO_MANY_REQUESTS, details });
  }
}
```

```js
// File: src/errors/normalizeError.js
import { AppError } from './AppError.js';

/**
 * Anything can be thrown: an AppError, a driver error, a string, `undefined`.
 * This is the single place that turns it into something safe to serialise.
 */
export function normalizeError(error) {
  if (error instanceof AppError) return error;

  // Errors thrown by express.json()/express.urlencoded() carry a `type`.
  if (error?.type === 'entity.parse.failed') {
    return new AppError('Request body is not valid JSON', { statusCode: 400, code: 'INVALID_JSON' });
  }
  if (error?.type === 'entity.too.large') {
    return new AppError('Payload too large', { statusCode: 413, code: 'PAYLOAD_TOO_LARGE' });
  }
  if (error instanceof SyntaxError && 'body' in error) {
    return new AppError('Request body is not valid JSON', { statusCode: 400, code: 'INVALID_JSON' });
  }

  // Database-shaped errors in the future: unique violation, integrity violation, deadlock.
  if (error?.code === '23505' || error?.code === '11000') {
    return new AppError('That value already exists', { statusCode: 409, code: 'CONFLICT', details: { constraint: error.constraint } });
  }

  // An unknown throw is a bug: hide the message from clients, keep it in the logs.
  return new AppError('Internal server error', {
    statusCode: 500,
    code: 'INTERNAL_ERROR',
    cause: error,
    isOperational: false,
  });
}
```

---

## 6. Utilities

```js
// File: src/utils/logger.js
import { pino } from 'pino';

/**
 * JSON everywhere except local development: pretty-printed logs need the optional `pino-pretty`
 * dependency, which is not installed when you deploy with `npm ci --omit=dev`.
 */
export function createLogger({ level = 'info', pretty = false } = {}) {
  return pino({
    level,
    base: { service: 'notes-api' },
    // Redaction is configured here, so no log call can leak credentials by accident.
    redact: {
      paths: [
        'req.headers.authorization',
        'req.headers.cookie',
        'res.headers["set-cookie"]',
        'password',
        'passwordHash',
        'token',
        'refreshToken',
      ],
      censor: '[redacted]',
    },
    ...(pretty
      ? { transport: { target: 'pino-pretty', options: { colorize: true, translateTime: 'HH:MM:ss.l', ignore: 'pid,hostname,service' } } }
      : {}),
  });
}
```

```js
// File: src/utils/passwordHasher.js
import { randomBytes, scrypt as scryptCallback, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';

const scrypt = promisify(scryptCallback);

/**
 * Contract: hash(plain) → string, compare(plain, stored) → boolean.
 * In production prefer argon2id; bcryptjs is a fine portable alternative.
 * Details: 04-authentication/02-password-hashing.md
 */
export function createPasswordHasher({ keyLength = 64 } = {}) {
  return {
    async hash(plain) {
      const salt = randomBytes(16).toString('hex');
      const derived = await scrypt(plain, salt, keyLength);
      return `scrypt$${salt}$${derived.toString('hex')}`;
    },

    /** Constant-time comparison: never use === on hashes. */
    async compare(plain, stored) {
      const [algorithm, salt, expectedHex] = String(stored).split('$');
      if (algorithm !== 'scrypt' || !salt || !expectedHex) return false;

      const derived = await scrypt(plain, salt, expectedHex.length / 2);
      const expected = Buffer.from(expectedHex, 'hex');
      return derived.length === expected.length && timingSafeEqual(derived, expected);
    },
  };
}
```

```js
// File: src/utils/tokenService.js
import jwt from 'jsonwebtoken';
import { randomUUID, createHash } from 'node:crypto';

/**
 * Two different secrets, two different audiences of token:
 *  - access  : 15 minutes, sent on every request, verified by the API
 *  - refresh : 30 days, sent only to /auth/refresh, revocable by jti
 */
export function createTokenService({ secret, refreshSecret, issuer, audience, accessTtl = '15m', refreshTtl = '30d' }) {
  if (typeof secret !== 'string' || secret.length < 32) {
    throw new Error('JWT secret must be at least 32 characters');
  }
  if (secret === refreshSecret) {
    throw new Error('Access and refresh secrets must differ — one leaked secret must not compromise both');
  }

  const accessOptions = { algorithm: 'HS256', issuer, audience, expiresIn: accessTtl };
  const refreshOptions = { algorithm: 'HS256', issuer, audience, expiresIn: refreshTtl };

  return {
    /** Clients use this to schedule a refresh before the token expires. */
    accessTtlSeconds: toSeconds(accessTtl),

    signAccessToken({ sub, role }) {
      return jwt.sign({ role }, secret, { ...accessOptions, subject: String(sub) });
    },

    signRefreshToken({ sub, jti = randomUUID() }) {
      return jwt.sign({ jti }, refreshSecret, { ...refreshOptions, subject: String(sub) });
    },

    /** Throws on a bad signature, a wrong algorithm, a wrong issuer/audience, or expiry. */
    verifyAccessToken(token) {
      return jwt.verify(token, secret, { algorithms: ['HS256'], issuer, audience });
    },

    verifyRefreshToken(token) {
      return jwt.verify(token, refreshSecret, { algorithms: ['HS256'], issuer, audience });
    },
  };
}

const UNIT_SECONDS = { s: 1, m: 60, h: 3_600, d: 86_400 };

/** '15m' → 900. Accepts a number of seconds as well, so tests can pass 1 to force expiry. */
function toSeconds(ttl) {
  if (typeof ttl === 'number') return ttl;
  const match = /^(\d+)([smhd])$/.exec(String(ttl));
  return match ? Number(match[1]) * UNIT_SECONDS[match[2]] : 900;
}

/** Refresh tokens are stored hashed: a leaked store must not hand over live tokens. */
export function hashToken(token) {
  return createHash('sha256').update(token).digest('hex');
}
```

```js
// File: src/utils/ids.js
import { randomUUID } from 'node:crypto';

/**
 * Injected identity so tests are deterministic and a future change (ULID, Snowflake, database-generated)
 * touches one file. `prefix` groups ids by collection, which makes logs readable.
 */
export function createIdFactory({ prefix = 'id', uuid = randomUUID } = {}) {
  return (kind = prefix) => `${kind}_${uuid()}`;
}

/** Used by tests and the in-memory store: note_1, note_2, ... */
export function createCountingIdFactory({ prefix = 'id' } = {}) {
  let counter = 0;
  return (kind = prefix) => `${kind}_${++counter}`;
}
```

```js
// File: src/utils/clock.js
export function createClock({ now = () => new Date() } = {}) {
  return {
    now,
    isoNow: () => now().toISOString(),
  };
}

/** Tests inject a frozen clock; production uses the system clock. */
export const systemClock = createClock();
```

```js
// File: src/utils/pagination.js
import { PAGINATION } from '../config/constants.js';

/** page/limit → a database-friendly offset, clamped to the maximum page size. */
export function toOffset({ page = PAGINATION.DEFAULT_PAGE, limit = PAGINATION.DEFAULT_LIMIT } = {}) {
  const safeLimit = Math.min(Math.max(limit, 1), PAGINATION.MAX_LIMIT);
  const safePage = Math.max(page, 1);
  return { page: safePage, limit: safeLimit, offset: (safePage - 1) * safeLimit };
}

export function buildMeta({ page, limit, total }) {
  return {
    page,
    limit,
    total,
    pages: Math.ceil(total / limit) || 0,
    hasNext: page * limit < total,
    hasPrevious: page > 1,
  };
}
```

```js
// File: src/utils/etag.js
/**
 * An ETag identifies a version of a resource. The note's revision number is bumped on every write,
 * so W/"<id>-<revision>" changes exactly when the representation changes.
 * Weak (W/) because the bytes may be re-serialised (key order, formatting).
 */
export function noteETag(note) {
  return `W/"${note.id}-${note.revision}"`;
}

/** Parses an If-Match header, honouring "*" and rejecting anything that is not our ETag format. */
export function parseIfMatch(headerValue) {
  if (!headerValue) return null;
  const value = String(headerValue).trim();
  if (value === '*') return '*';
  const match = /^W\/"(.+)-(\d+)"$/.exec(value) ?? /^"(.+)-(\d+)"$/.exec(value);
  if (!match) return null;
  return { id: match[1], revision: Number(match[2]) };
}
```

---

## 7. The data layer

Three repositories, one contract each. Everything below them is a `Map`; everything above them does not
know that.

```js
// File: src/repositories/inMemoryUserRepository.js
import { ROLES } from '../config/constants.js';

/**
 * The contract every user repository must satisfy (the MongoDB and SQL chapters implement the same one):
 *   create, findById, findByEmail, list, count, updateRole, deleteById
 */
export function createInMemoryUserRepository({ ids, clock }) {
  const usersById = new Map();
  const idByEmail = new Map();

  const toPublic = (user) => (user ? { ...user } : null);

  return {
    async create({ email, name, passwordHash, role = ROLES.USER }) {
      const normalizedEmail = email.trim().toLowerCase();
      if (idByEmail.has(normalizedEmail)) return null;             // the store enforces the unique key

      const now = clock.isoNow();
      const user = {
        id: ids('user'),
        email: normalizedEmail,
        name,
        passwordHash,
        role,
        createdAt: now,
        updatedAt: now,
      };

      usersById.set(user.id, user);
      idByEmail.set(normalizedEmail, user.id);
      return toPublic(user);
    },

    async findById(id) {
      return toPublic(usersById.get(id) ?? null);
    },

    /** Returns the record *with* the password hash: only the auth service may ask for it. */
    async findByEmail(email) {
      const id = idByEmail.get(String(email).trim().toLowerCase());
      return toPublic(usersById.get(id) ?? null);
    },

    async list({ offset = 0, limit = 20 } = {}) {
      const all = [...usersById.values()].sort((a, b) => a.createdAt.localeCompare(b.createdAt) || a.id.localeCompare(b.id));
      return all.slice(offset, offset + limit).map(toPublic);
    },

    async count() {
      return usersById.size;
    },

    async updateRole(id, role) {
      const user = usersById.get(id);
      if (!user) return null;
      user.role = role;
      user.updatedAt = clock.isoNow();
      return toPublic(user);
    },
  };
}
```

```js
// File: src/repositories/inMemoryNoteRepository.js
import { NOTE_SORTS } from '../config/constants.js';

/**
 * Contract for every note repository:
 *   create, findById, update, remove, list, tagCounts, stats
 */
export function createInMemoryNoteRepository({ ids, clock }) {
  const notes = new Map();

  const toDomain = (note) => (note ? { ...note, tags: [...note.tags] } : null);

  /** Filtering is implemented once; listing and counting both use it. */
  function matches(note, { authorId, q, tag, pinned, archived }) {
    if (note.authorId !== authorId) return false;
    if (archived === undefined ? note.archived : note.archived !== archived) return false;   // default: hide archived
    if (pinned !== undefined && note.pinned !== pinned) return false;
    if (tag && !note.tags.includes(tag.toLowerCase())) return false;

    if (q) {
      const needle = q.toLowerCase();
      if (!note.title.toLowerCase().includes(needle) && !note.content.toLowerCase().includes(needle)) return false;
    }

    return true;
  }

  function compare(field, direction) {
    return (a, b) => {
      const left = field === 'title' ? String(a.title).toLowerCase() : a[field];
      const right = field === 'title' ? String(b.title).toLowerCase() : b[field];

      let result = 0;
      if (left < right) result = -1;
      else if (left > right) result = 1;

      // Stable tie-breaker: without it, paging can repeat or skip rows.
      if (result === 0) result = a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
      return direction === 'desc' ? -result : result;
    };
  }

  /** "-createdAt" means descending; unknown fields fall back to createdAt. */
  function resolveSort(sort) {
    const raw = String(sort ?? '-createdAt');
    const direction = raw.startsWith('-') ? 'desc' : 'asc';
    const requested = raw.replace(/^-/, '');
    const field = NOTE_SORTS[requested] ?? NOTE_SORTS.createdAt;
    return { field, direction };
  }

  return {
    async create({ title, content, tags = [], authorId }) {
      const now = clock.isoNow();
      const note = {
        id: ids('note'),
        title: title.trim(),
        content: content.trim(),
        tags: [...new Set(tags.map((tag) => tag.trim().toLowerCase()).filter(Boolean))],
        pinned: false,
        archived: false,
        revision: 1,
        authorId,
        createdAt: now,
        updatedAt: now,
      };

      notes.set(note.id, note);
      return toDomain(note);
    },

    async findById(id) {
      return toDomain(notes.get(id) ?? null);
    },

    async findByTitle(title, authorId) {
      const needle = title.trim().toLowerCase();
      for (const note of notes.values()) {
        if (note.authorId === authorId && note.title.toLowerCase() === needle) return toDomain(note);
      }
      return null;
    },

    async update(id, patch) {
      const note = notes.get(id);
      if (!note) return null;

      const allowed = ['title', 'content', 'tags', 'pinned', 'archived'];
      for (const key of allowed) {
        if (patch[key] !== undefined) note[key] = patch[key];
      }
      if (patch.tags) note.tags = [...new Set(patch.tags.map((tag) => tag.trim().toLowerCase()).filter(Boolean))];

      note.revision += 1;
      note.updatedAt = clock.isoNow();
      return toDomain(note);
    },

    async remove(id) {
      return notes.delete(id);
    },

    async list({ authorId, offset = 0, limit = 20, sort, q, tag, pinned, archived }) {
      const { field, direction } = resolveSort(sort);
      const filtered = [...notes.values()].filter((note) => matches(note, { authorId, q, tag, pinned, archived }));

      filtered.sort(compare(field, direction));

      // Pinned notes float to the top of the default view, without breaking the requested sort.
      if (!sort) filtered.sort((a, b) => Number(b.pinned) - Number(a.pinned));

      return {
        items: filtered.slice(offset, offset + limit).map(toDomain),
        total: filtered.length,
      };
    },

    async tagCounts(authorId) {
      const counts = new Map();
      for (const note of notes.values()) {
        if (note.authorId !== authorId) continue;
        for (const tag of note.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
      }
      return [...counts.entries()]
        .map(([tag, count]) => ({ tag, count }))
        .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
    },

    async stats() {
      const all = [...notes.values()];
      return {
        notes: all.length,
        pinned: all.filter((note) => note.pinned).length,
        archived: all.filter((note) => note.archived).length,
        tags: new Set(all.flatMap((note) => note.tags)).size,
      };
    },
  };
}
```

```js
// File: src/repositories/inMemoryRefreshTokenStore.js
/**
 * Refresh-token rotation with reuse detection (chapter 14).
 * A "family" is one login: every rotation creates a new token in the same family.
 * Presenting an already-rotated token means the token leaked, so the whole family is revoked.
 */
export function createInMemoryRefreshTokenStore({ clock }) {
  const recordsByHash = new Map();   // tokenHash → record
  const revokedFamilies = new Set();

  return {
    async save({ tokenHash, userId, familyId, expiresAt }) {
      recordsByHash.set(tokenHash, { tokenHash, userId, familyId, expiresAt, rotated: false });
    },

    async find(tokenHash) {
      return recordsByHash.get(tokenHash) ?? null;
    },

    async rotate(tokenHash, replacement) {
      const record = recordsByHash.get(tokenHash);
      if (!record) return;
      record.rotated = true;
      await this.save(replacement);
    },

    async revokeFamily(familyId) {
      revokedFamilies.add(familyId);
      for (const record of recordsByHash.values()) {
        if (record.familyId === familyId) record.rotated = true;
      }
    },

    async isFamilyRevoked(familyId) {
      return revokedFamilies.has(familyId);
    },

    /** Housekeeping: without it, an in-memory store grows forever. */
    async purgeExpired() {
      const now = clock.now().getTime();
      let removed = 0;
      for (const [hash, record] of recordsByHash) {
        if (record.expiresAt <= now) {
          recordsByHash.delete(hash);
          removed += 1;
        }
      }
      return removed;
    },
  };
}
```

---

## 8. Services — where the rules live

```js
// File: src/services/authService.js
import { randomUUID } from 'node:crypto';
import { ConflictError, UnauthenticatedError } from '../errors/AppError.js';
import { hashToken } from '../utils/tokenService.js';
import { ROLES } from '../config/constants.js';

/**
 * A hash of a value nobody can match, used when the account does not exist.
 * Without it, "unknown email" returns in 1 ms and "wrong password" in 80 ms:
 * an attacker can enumerate accounts by timing alone (chapter 13).
 */
const DUMMY_HASH = `scrypt$${'0'.repeat(32)}$${'00'.repeat(64)}`;

export function createAuthService({ userRepository, refreshTokenStore, passwordHasher, tokenService, clock, logger }) {
  async function issueTokens({ user, familyId = randomUUID() }) {
    const accessToken = tokenService.signAccessToken({ sub: user.id, role: user.role });
    const refreshToken = tokenService.signRefreshToken({ sub: user.id });
    const refreshed = tokenService.verifyRefreshToken(refreshToken);

    await refreshTokenStore.save({
      tokenHash: hashToken(refreshToken),
      userId: user.id,
      familyId,
      expiresAt: refreshed.exp * 1_000,
    });

    return { accessToken, refreshToken, familyId, refreshExpiresAt: refreshed.exp * 1_000 };
  }

  return {
    async register({ email, password, name }) {
      const passwordHash = await passwordHasher.hash(password);
      const user = await userRepository.create({ email, name, passwordHash, role: ROLES.USER });

      if (!user) throw new ConflictError('That email address is already registered', { field: 'email' });

      logger.info({ userId: user.id }, 'user registered');
      return { user, ...(await issueTokens({ user })) };
    },

    async login({ email, password }) {
      const user = await userRepository.findByEmail(email);

      // Always run the comparison: same work whether or not the account exists.
      const ok = await passwordHasher.compare(password, user?.passwordHash ?? DUMMY_HASH);
      if (!user || !ok) throw new UnauthenticatedError('Email or password is incorrect');

      logger.info({ userId: user.id }, 'user logged in');
      return { user, ...(await issueTokens({ user })) };
    },

    /** Rotates the refresh token and detects reuse of an already-rotated one. */
    async refresh({ presentedToken }) {
      try {
        tokenService.verifyRefreshToken(presentedToken);
      } catch (error) {
        throw new UnauthenticatedError('The refresh token is invalid or expired', { cause: error });
      }

      const tokenHash = hashToken(presentedToken);
      const record = await refreshTokenStore.find(tokenHash);

      if (!record) throw new UnauthenticatedError('The refresh token is not recognised');
      if (await refreshTokenStore.isFamilyRevoked(record.familyId)) {
        throw new UnauthenticatedError('This session was revoked — log in again');
      }

      if (record.rotated) {
        // The same token was presented twice: assume theft and kill the whole family.
        await refreshTokenStore.revokeFamily(record.familyId);
        logger.warn({ userId: record.userId, familyId: record.familyId }, 'refresh token reuse detected');
        throw new UnauthenticatedError('Refresh token reuse detected — all sessions for this device were revoked');
      }

      const user = await userRepository.findById(record.userId);
      if (!user) throw new UnauthenticatedError('The account no longer exists');

      const { accessToken, refreshToken, refreshExpiresAt } = await issueTokens({ user, familyId: record.familyId });
      await refreshTokenStore.rotate(tokenHash, {
        tokenHash: hashToken(refreshToken),
        userId: user.id,
        familyId: record.familyId,
        expiresAt: refreshExpiresAt,
      });

      return { user, accessToken, refreshToken };
    },

    /** Idempotent: logging out with an unknown or already-revoked token still succeeds. */
    async logout({ presentedToken }) {
      if (!presentedToken) return false;

      const record = await refreshTokenStore.find(hashToken(presentedToken));
      if (record) {
        await refreshTokenStore.revokeFamily(record.familyId);
        logger.info({ userId: record.userId }, 'user logged out');
        return true;
      }

      return false;
    },

    async getProfile(userId) {
      const user = await userRepository.findById(userId);
      if (!user) throw new UnauthenticatedError('The account no longer exists');
      return user;
    },
  };
}
```

```js
// File: src/services/noteService.js
import { ConflictError, ForbiddenError, NotFoundError, PreconditionFailedError } from '../errors/AppError.js';
import { buildMeta, toOffset } from '../utils/pagination.js';
import { noteETag } from '../utils/etag.js';
import { ROLES } from '../config/constants.js';

export function createNoteService({ noteRepository, logger }) {
  /** One place that decides who may touch a note. */
  function assertAccess(note, actor) {
    if (!note) throw new NotFoundError('Note not found');
    if (note.authorId !== actor.id && actor.role !== ROLES.ADMIN) {
      // 403, not 404: the caller proved who they are, they are simply not allowed.
      throw new ForbiddenError('This note belongs to another user');
    }
  }

  return {
    async list({ actor, query }) {
      const { page, limit, offset } = toOffset({ page: query.page, limit: query.limit });

      const { items, total } = await noteRepository.list({
        authorId: actor.id,
        offset,
        limit,
        sort: query.sort,
        q: query.q,
        tag: query.tag,
        pinned: query.pinned,
        archived: query.archived ?? false,       // archived notes are opt-in
      });

      return { items, total, page, limit };
    },

    async create({ input, actor }) {
      // The unique-title rule belongs to the business, not to the HTTP layer.
      if (await noteRepository.findByTitle(input.title, actor.id)) {
        throw new ConflictError('You already have a note with that title', { field: 'title' });
      }

      const note = await noteRepository.create({ ...input, authorId: actor.id });
      logger.info({ noteId: note.id, userId: actor.id }, 'note created');
      return note;
    },

    async get({ id, actor }) {
      const note = await noteRepository.findById(id);
      assertAccess(note, actor);
      return note;
    },

    /**
     * Optimistic concurrency: the client sends the ETag it read in If-Match.
     * Two editors saving at once would otherwise silently overwrite each other.
     */
    async update({ id, input, actor, ifMatchRevision }) {
      const note = await noteRepository.findById(id);
      assertAccess(note, actor);

      if (ifMatchRevision !== undefined && ifMatchRevision !== null && ifMatchRevision !== note.revision) {
        throw new PreconditionFailedError('The note was modified by someone else', {
          expected: ifMatchRevision,
          actual: note.revision,
          etag: noteETag(note),
        });
      }

      if (input.title && input.title.toLowerCase() !== note.title.toLowerCase()) {
        const duplicate = await noteRepository.findByTitle(input.title, actor.id);
        if (duplicate) throw new ConflictError('You already have a note with that title', { field: 'title' });
      }

      const updated = await noteRepository.update(id, input);
      if (!updated) throw new NotFoundError('Note not found');   // deleted between read and write

      return updated;
    },

    async remove({ id, actor }) {
      const note = await noteRepository.findById(id);
      assertAccess(note, actor);

      const removed = await noteRepository.remove(id);
      if (!removed) throw new NotFoundError('Note not found');

      logger.info({ noteId: id, userId: actor.id }, 'note deleted');
      return true;
    },

    async setPinned({ id, actor, pinned }) {
      return this.update({ id, actor, input: { pinned } });
    },

    async setArchived({ id, actor, archived }) {
      return this.update({ id, actor, input: { archived } });
    },

    async tagCounts({ actor }) {
      return noteRepository.tagCounts(actor.id);
    },

    buildMeta,
  };
}
```

```js
// File: src/services/adminService.js
import { ForbiddenError, NotFoundError } from '../errors/AppError.js';
import { ROLES } from '../config/constants.js';
import { toOffset } from '../utils/pagination.js';

export function createAdminService({ userRepository, noteRepository, logger }) {
  return {
    async listUsers({ page, limit }) {
      const { page: safePage, limit: safeLimit, offset } = toOffset({ page, limit });
      const [items, total] = await Promise.all([userRepository.list({ offset, limit: safeLimit }), userRepository.count()]);
      return { items, total, page: safePage, limit: safeLimit };
    },

    async updateUserRole({ targetUserId, role, actor }) {
      if (targetUserId === actor.id) {
        // Preventing self-demotion avoids a locked-out admin in a small team.
        throw new ForbiddenError('You cannot change your own role');
      }
      if (!Object.values(ROLES).includes(role)) {
        throw new ForbiddenError(`Unknown role: ${role}`);
      }

      const updated = await userRepository.updateRole(targetUserId, role);
      if (!updated) throw new NotFoundError('User not found');

      logger.warn({ actorId: actor.id, targetUserId, role }, 'user role changed');
      return updated;
    },

    async stats() {
      const [users, notes] = await Promise.all([userRepository.count(), noteRepository.stats()]);
      return { users, ...notes };
    },
  };
}
```

---

## 9. DTOs — the wire contract

```js
// File: src/dtos/userDto.js
/** Only these fields ever leave the process. Passwords, hashes and internal flags never do. */
export function toUserDto(user) {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    createdAt: user.createdAt,
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
    tags: note.tags,
    pinned: note.pinned,
    archived: note.archived,
    revision: note.revision,
    authorId: note.authorId,
    createdAt: note.createdAt,
    updatedAt: note.updatedAt,
  };
}
```

---

## 10. Validators — the input contract

```js
// File: src/validators/commonSchemas.js
import { z } from 'zod';
import { PAGINATION } from '../config/constants.js';

/** Query values arrive as strings; `"false"` must not be truthy. */
export const booleanQuery = z
  .enum(['true', 'false'])
  .transform((value) => value === 'true');

export const paginationQuery = {
  page: z.coerce.number().int().min(1).default(PAGINATION.DEFAULT_PAGE),
  limit: z.coerce.number().int().min(1).max(PAGINATION.MAX_LIMIT).default(PAGINATION.DEFAULT_LIMIT),
};

/**
 * Identifiers are opaque strings here because the in-memory store generates `note_1`.
 * A SQL chapter swaps this for z.uuid() without touching any other file.
 */
export const idParam = z.string().trim().min(1).max(128);
```

```js
// File: src/validators/authSchemas.js
import { z } from 'zod';
import { ROLES } from '../config/constants.js';

const email = z.email('must be a valid email address').max(254).transform((value) => value.trim().toLowerCase());

const password = z
  .string()
  .min(12, 'must be at least 12 characters')
  .max(200, 'must be at most 200 characters')
  .refine((value) => /[a-z]/.test(value), 'must contain a lowercase letter')
  .refine((value) => /[A-Z]/.test(value), 'must contain an uppercase letter')
  .refine((value) => /\d/.test(value), 'must contain a digit');

export const registerSchema = z.object({
  email,
  password,
  name: z.string().trim().min(1, 'must not be empty').max(100),
}).strict();

export const loginSchema = z.object({
  email,
  password: z.string().min(1, 'must not be empty').max(200),
}).strict();

export const updateRoleSchema = z.object({
  role: z.enum(Object.values(ROLES)),
}).strict();
```

```js
// File: src/validators/noteSchemas.js
import { z } from 'zod';
import { booleanQuery, idParam, paginationQuery } from './commonSchemas.js';

const title = z.string().trim().min(1, 'must not be empty').max(200, 'must be at most 200 characters');
const content = z.string().trim().min(1, 'must not be empty').max(10_000, 'must be at most 10000 characters');
const tags = z
  .array(z.string().trim().min(1).max(30).transform((tag) => tag.toLowerCase()))
  .max(10, 'at most 10 tags')
  .transform((list) => [...new Set(list)]);

export const createNoteSchema = z.object({
  title,
  content,
  tags: tags.optional().default([]),
}).strict();

/** Every field optional, but at least one must be present — otherwise PATCH is a no-op. */
export const updateNoteSchema = z
  .object({
    title: title.optional(),
    content: content.optional(),
    tags: tags.optional(),
    pinned: z.boolean().optional(),
    archived: z.boolean().optional(),
  })
  .strict()
  .refine((value) => Object.keys(value).length > 0, 'provide at least one field to update');

export const listNotesQuerySchema = z.object({
  ...paginationQuery,
  sort: z.enum(['createdAt', '-createdAt', 'updatedAt', '-updatedAt', 'title', '-title', 'pinned', '-pinned']).optional(),
  q: z.string().trim().min(1).max(200).optional(),
  tag: z.string().trim().min(1).max(30).transform((tag) => tag.toLowerCase()).optional(),
  pinned: booleanQuery.optional(),
  archived: booleanQuery.optional(),
}).strict();

export const noteIdParamsSchema = z.object({ id: idParam }).strict();

export const listUsersQuerySchema = z.object({ ...paginationQuery }).strict();
```

---

## 11. Middleware — cross-cutting concerns

```js
// File: src/middleware/requestId.js
import { randomUUID } from 'node:crypto';

/**
 * Every log line and every error carries the same id, so one request is traceable end to end.
 * An inbound id is honoured (so a gateway's id survives) but sanitised: it ends up in headers and logs.
 */
export function requestId(req, res, next) {
  const inbound = req.get('x-request-id');
  const id = inbound && /^[A-Za-z0-9._-]{1,100}$/.test(inbound) ? inbound : randomUUID();

  req.id = id;
  res.setHeader('X-Request-Id', id);
  next();
}
```

```js
// File: src/middleware/httpLogger.js
import { pinoHttp } from 'pino-http';

export function createHttpLogger({ logger }) {
  return pinoHttp({
    logger,
    // Reuse the id from our own middleware instead of letting pino generate a second one.
    genReqId: (req, res) => req.id ?? res.getHeader('x-request-id'),
    /**
     * The request logger records OUTCOMES; the error handler records FAILURES at error level.
     * Returning 'error' here would produce a second, misleading entry ("failed with status code 500")
     * for every 5xx, right next to the real one.
     */
    customLogLevel: (req, res) => (res.statusCode >= 400 ? 'warn' : 'info'),
    customSuccessMessage: (req, res) => `${req.method} ${req.url} -> ${res.statusCode}`,
    customErrorMessage: (req, res, error) => `${req.method} ${req.url} -> ${res.statusCode} (${error?.message})`,
    customProps: (req) => ({ requestId: req.id, userId: req.user?.id ?? null }),
    autoLogging: {
      // Liveness probes would otherwise dominate the log volume.
      ignore: (req) => req.url === '/health/live' || req.url === '/health/ready',
    },
  });
}
```

```js
// File: src/middleware/auth.js
import { ForbiddenError, UnauthenticatedError } from '../errors/AppError.js';

/**
 * Verifies the Bearer token and loads the *current* user record, so a role change or a deleted
 * account takes effect immediately instead of when the token expires.
 */
export function createAuthenticate({ tokenService, userRepository }) {
  return async function authenticate(req, res, next) {
    try {
      const header = req.get('authorization') ?? '';
      const [scheme, token] = header.split(' ');

      if (scheme !== 'Bearer' || !token) throw new UnauthenticatedError('Provide a Bearer access token');

      let claims;
      try {
        claims = tokenService.verifyAccessToken(token);
      } catch (error) {
        throw new UnauthenticatedError('The access token is invalid or expired', { cause: error });
      }

      const user = await userRepository.findById(String(claims.sub));
      if (!user) throw new UnauthenticatedError('The account no longer exists');

      req.user = { id: user.id, email: user.email, name: user.name, role: user.role };
      req.auth = { claims };
      return next();
    } catch (error) {
      return next(error);
    }
  };
}

/** Guards a route: the middleware above must have run first. */
export function requireAuth(req, res, next) {
  if (!req.user) return next(new UnauthenticatedError());
  return next();
}

/** Role-based access control. Usage: requireRole('ADMIN') or requireRole('ADMIN', 'USER'). */
export function requireRole(...roles) {
  return function requireRoleMiddleware(req, res, next) {
    if (!req.user) return next(new UnauthenticatedError());
    if (!roles.includes(req.user.role)) {
      return next(new ForbiddenError(`This endpoint requires one of: ${roles.join(', ')}`));
    }
    return next();
  };
}

/** Populates req.user when a token is present but never rejects: public endpoints with personalisation. */
export function createOptionalAuth({ tokenService, userRepository }) {
  const authenticate = createAuthenticate({ tokenService, userRepository });
  return (req, res, next) => authenticate(req, res, (error) => next(error?.statusCode === 401 ? undefined : error));
}
```

```js
// File: src/middleware/validate.js
/**
 * Replaces req.body/query/params with parsed, coerced, strictly-validated data in `req.validated`.
 * Controllers read req.validated.* only — never the raw input.
 */
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
// File: src/middleware/rateLimit.js
import { rateLimit } from 'express-rate-limit';
import { TooManyRequestsError } from '../errors/AppError.js';

/**
 * Limits are per IP by default. Behind a proxy, configure TRUST_PROXY, or every request looks
 * like it came from the load balancer and one client can exhaust the limit for everyone.
 * With several instances, move the store to Redis (chapter 18).
 */
export function createLimiters({ enabled }) {
  const base = {
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    skip: () => !enabled,
    // Uniform error envelope instead of the library's default body.
    handler: (req, res, next, options) => {
      next(new TooManyRequestsError(`Too many requests — retry after ${Math.ceil(options.windowMs / 1000)}s`));
    },
  };

  return {
    global: rateLimit({ ...base, windowMs: 60_000, limit: 300 }),
    auth: rateLimit({ ...base, windowMs: 15 * 60_000, limit: 10 }),
    register: rateLimit({ ...base, windowMs: 60 * 60_000, limit: 10 }),
  };
}
```

```js
// File: src/middleware/csrf.js
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { COOKIES, ERROR_CODES } from '../config/constants.js';
import { AppError } from '../errors/AppError.js';

/**
 * Double-submit cookie (chapter 15). The refresh token lives in a cookie, so a browser sends it
 * automatically — a malicious site could therefore trigger /auth/refresh. The defence: a value the
 * attacker cannot read (a SameSite cookie plus a secret echoed in a custom header).
 * Remove this only if tokens are never stored in cookies.
 */
const cookieOptions = ({ isProduction }) => ({
  httpOnly: false,            // the SPA must be able to read it
  sameSite: 'lax',
  secure: isProduction,
  path: '/',
  maxAge: 24 * 60 * 60 * 1_000,
});

/** Global middleware: hand out a secret to every client that does not have one yet. */
export function createCsrfCookieIssuer({ isProduction }) {
  return function issueCsrfCookie(req, res, next) {
    if (!req.cookies?.[COOKIES.csrfSecret]) {
      const secret = randomBytes(32).toString('hex');
      res.cookie(COOKIES.csrfSecret, secret, cookieOptions({ isProduction }));
      req.cookies = { ...req.cookies, [COOKIES.csrfSecret]: secret };
    }

    return next();
  };
}

/**
 * Route middleware for cookie-authenticated mutations only.
 * Bearer-token routes do not need it: an attacker's page cannot set an Authorization header.
 */
export function requireCsrfToken() {
  return function requireCsrfTokenMiddleware(req, res, next) {
    const secret = req.cookies?.[COOKIES.csrfSecret];
    const provided = req.get('x-csrf-token');

    if (!secret || !provided || !safeEqualStrings(secret, provided)) {
      // Its own code, so a client can tell "log in again" (401) from "reload the page and retry" (403).
      return next(new AppError('CSRF token is missing or invalid', { statusCode: 403, code: ERROR_CODES.CSRF_FAILED }));
    }

    return next();
  };
}

function safeEqualStrings(a, b) {
  const left = Buffer.from(String(a));
  const right = Buffer.from(String(b));
  return left.length === right.length && timingSafeEqual(left, right);
}
```

```js
// File: src/middleware/notFound.js
import { NotFoundError } from '../errors/AppError.js';

export function notFound(req, res, next) {
  next(new NotFoundError(`Cannot ${req.method} ${req.originalUrl}`));
}
```

```js
// File: src/middleware/methodNotAllowed.js
import { AppError } from '../errors/AppError.js';
import { ERROR_CODES } from '../config/constants.js';

/**
 * Turns a URL pattern into a matcher. `:id` becomes "one path segment".
 * Only the paths listed here can produce a 405 — unknown URLs fall through to the 404 handler.
 */
export function compileAllowList(entries) {
  return entries.map(({ path, methods }) => ({
    regex: new RegExp(`^${path.replace(/:[A-Za-z0-9_]+/g, '[^/]+').replace(/\/$/, '')}/?$`),
    methods: methods.map((method) => method.toUpperCase()),
    path,
  }));
}

export function createMethodNotAllowed(entries) {
  const routes = compileAllowList(entries);

  return function methodNotAllowed(req, res, next) {
    const match = routes.find((route) => route.regex.test(req.path));

    if (match && !match.methods.includes(req.method)) {
      res.setHeader('Allow', match.methods.join(', '));
      return next(new AppError(`Method ${req.method} is not allowed for ${req.originalUrl}`, {
        statusCode: 405,
        code: ERROR_CODES.METHOD_NOT_ALLOWED,
        details: { allow: match.methods },
      }));
    }

    return next();
  };
}
```

```js
// File: src/middleware/errorHandler.js
import { normalizeError } from '../errors/normalizeError.js';

/** The single place that turns a thrown value into an HTTP response. */
export function createErrorHandler({ logger, isProduction }) {
  return function errorHandler(error, req, res, next) {
    // A response already started streaming: we cannot change the status now.
    if (res.headersSent) return next(error);

    const mapped = normalizeError(error);
    const level = mapped.statusCode >= 500 ? 'error' : 'warn';

    logger[level]({
      err: error,
      requestId: req.id,
      statusCode: mapped.statusCode,
      code: mapped.code,
      method: req.method,
      url: req.originalUrl,
      userId: req.user?.id ?? null,
    }, mapped.message);

    const isServerError = mapped.statusCode >= 500;
    // Development keeps the real message to make debugging possible; production never leaks it.
    const message = !isServerError
      ? mapped.message
      : isProduction
        ? 'Something went wrong'
        : String(error?.message ?? mapped.message);

    const body = {
      error: {
        code: mapped.code,
        message,
        ...(mapped.details !== undefined ? { details: mapped.details } : {}),
        requestId: req.id,
      },
    };

    return res.status(mapped.statusCode).json(body);
  };
}
```

---

## 12. Controllers — HTTP in, HTTP out

```js
// File: src/controllers/authController.js
import { toUserDto } from '../dtos/userDto.js';
import { COOKIES } from '../config/constants.js';

export function createAuthController({ authService, config, tokenService }) {
  /** The refresh token never appears in a response body: cookie only, httpOnly, signed. */
  function setRefreshCookie(res, refreshToken) {
    res.cookie(COOKIES.refreshToken, refreshToken, {
      httpOnly: true,
      signed: true,
      sameSite: 'strict',
      secure: config.isProduction,
      path: COOKIES.refreshPath,
      maxAge: config.refreshTokenTtlMs,
    });
  }

  function setCsrfCookie(res, req) {
    // The CSRF middleware already issued one if it was missing.
    return req.cookies?.[COOKIES.csrfSecret];
  }

  return {
    async register(req, res, next) {
      try {
        const { email, password, name } = req.validated.body;
        const { user, accessToken, refreshToken } = await authService.register({ email, password, name });

        setRefreshCookie(res, refreshToken);
        // 201 + Location: the created resource is the caller's own profile.
        res.status(201).location('/api/v1/auth/me').json({
          data: {
            user: toUserDto(user),
            accessToken,
            tokenType: 'Bearer',
            expiresIn: tokenService.accessTtlSeconds,
          },
          meta: { csrfToken: setCsrfCookie(res, req) },
        });
      } catch (error) { next(error); }
    },

    async login(req, res, next) {
      try {
        const { accessToken, refreshToken, user } = await authService.login(req.validated.body);

        setRefreshCookie(res, refreshToken);
        res.json({
          data: {
            user: toUserDto(user),
            accessToken,
            tokenType: 'Bearer',
            expiresIn: tokenService.accessTtlSeconds,
          },
          meta: { csrfToken: setCsrfCookie(res, req) },
        });
      } catch (error) { next(error); }
    },

    async refresh(req, res, next) {
      try {
        const presentedToken = req.signedCookies?.[COOKIES.refreshToken];
        if (!presentedToken) {
          return res.status(401).json({
            error: { code: 'UNAUTHENTICATED', message: 'No refresh token cookie was sent', requestId: req.id },
          });
        }

        const { user, accessToken, refreshToken } = await authService.refresh({ presentedToken });
        setRefreshCookie(res, refreshToken);

        return res.json({
          data: {
            user: toUserDto(user),
            accessToken,
            tokenType: 'Bearer',
            expiresIn: tokenService.accessTtlSeconds,
          },
        });
      } catch (error) { return next(error); }
    },

    async logout(req, res, next) {
      try {
        const presentedToken = req.signedCookies?.[COOKIES.refreshToken];
        await authService.logout({ presentedToken });

        res.clearCookie(COOKIES.refreshToken, { path: COOKIES.refreshPath });
        return res.status(204).end();
      } catch (error) { return next(error); }
    },

    async me(req, res, next) {
      try {
        const user = await authService.getProfile(req.user.id);
        return res.json({ data: toUserDto(user) });
      } catch (error) { return next(error); }
    },
  };
}
```

```js
// File: src/controllers/noteController.js
import { toNoteDto } from '../dtos/noteDto.js';
import { noteETag, parseIfMatch } from '../utils/etag.js';

export function createNoteController({ noteService }) {
  return {
    async list(req, res, next) {
      try {
        const { items, total, page, limit } = await noteService.list({ actor: req.user, query: req.validated.query });
        return res.json({ data: items.map(toNoteDto), meta: { page, limit, total, pages: Math.ceil(total / limit) || 0, hasNext: page * limit < total } });
      } catch (error) { return next(error); }
    },

    async create(req, res, next) {
      try {
        const note = await noteService.create({ input: req.validated.body, actor: req.user });

        res.setHeader('ETag', noteETag(note));
        return res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: toNoteDto(note) });
      } catch (error) { return next(error); }
    },

    async getOne(req, res, next) {
      try {
        const note = await noteService.get({ id: req.validated.params.id, actor: req.user });

        res.setHeader('ETag', noteETag(note));
        return res.json({ data: toNoteDto(note) });
      } catch (error) { return next(error); }
    },

    async update(req, res, next) {
      try {
        const ifMatch = parseIfMatch(req.get('if-match'));
        const note = await noteService.update({
          id: req.validated.params.id,
          input: req.validated.body,
          actor: req.user,
          ifMatchRevision: ifMatch === '*' ? undefined : ifMatch?.revision,
        });

        res.setHeader('ETag', noteETag(note));
        return res.json({ data: toNoteDto(note) });
      } catch (error) { return next(error); }
    },

    async remove(req, res, next) {
      try {
        await noteService.remove({ id: req.validated.params.id, actor: req.user });
        return res.status(204).end();
      } catch (error) { return next(error); }
    },

    async pin(req, res, next) {
      try {
        const note = await noteService.setPinned({ id: req.validated.params.id, actor: req.user, pinned: true });
        res.setHeader('ETag', noteETag(note));
        return res.json({ data: toNoteDto(note) });
      } catch (error) { return next(error); }
    },

    async unpin(req, res, next) {
      try {
        const note = await noteService.setPinned({ id: req.validated.params.id, actor: req.user, pinned: false });
        res.setHeader('ETag', noteETag(note));
        return res.json({ data: toNoteDto(note) });
      } catch (error) { return next(error); }
    },

    async archive(req, res, next) {
      try {
        const note = await noteService.setArchived({ id: req.validated.params.id, actor: req.user, archived: true });
        res.setHeader('ETag', noteETag(note));
        return res.json({ data: toNoteDto(note) });
      } catch (error) { return next(error); }
    },

    async unarchive(req, res, next) {
      try {
        const note = await noteService.setArchived({ id: req.validated.params.id, actor: req.user, archived: false });
        res.setHeader('ETag', noteETag(note));
        return res.json({ data: toNoteDto(note) });
      } catch (error) { return next(error); }
    },

    async tags(req, res, next) {
      try {
        const tags = await noteService.tagCounts({ actor: req.user });
        return res.json({ data: tags, meta: { total: tags.length } });
      } catch (error) { return next(error); }
    },
  };
}
```

```js
// File: src/controllers/adminController.js
import { toUserDto } from '../dtos/userDto.js';

export function createAdminController({ adminService }) {
  return {
    async listUsers(req, res, next) {
      try {
        const { items, total, page, limit } = await adminService.listUsers(req.validated.query);
        return res.json({
          data: items.map(toUserDto),
          meta: { page, limit, total, pages: Math.ceil(total / limit) || 0 },
        });
      } catch (error) { return next(error); }
    },

    async updateRole(req, res, next) {
      try {
        const user = await adminService.updateUserRole({
          targetUserId: req.validated.params.id,
          role: req.validated.body.role,
          actor: req.user,
        });

        return res.json({ data: toUserDto(user) });
      } catch (error) { return next(error); }
    },

    async stats(req, res, next) {
      try {
        return res.json({ data: await adminService.stats() });
      } catch (error) { return next(error); }
    },
  };
}
```

---

## 13. Routes — the URL surface

```js
// File: src/routes/authRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { loginSchema, registerSchema } from '../validators/authSchemas.js';

export function createAuthRouter({ controller, middleware, limiters }) {
  const router = Router();

  router.post('/register', limiters.register, validate(registerSchema), controller.register);
  router.post('/login', limiters.auth, validate(loginSchema), controller.login);

  // Cookie-authenticated routes: same-site CSRF checking is applied here, not globally,
  // because Bearer-token routes are not vulnerable to CSRF.
  router.post('/refresh', middleware.requireCsrf, controller.refresh);
  router.post('/logout', middleware.requireCsrf, controller.logout);

  router.get('/me', middleware.authenticate, middleware.requireAuth, controller.me);

  return router;
}
```

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { createNoteSchema, listNotesQuerySchema, noteIdParamsSchema, updateNoteSchema } from '../validators/noteSchemas.js';

export function createNoteRouter({ controller, middleware }) {
  const router = Router();

  // Authenticate once for the whole resource.
  router.use(middleware.authenticate, middleware.requireAuth);

  router.route('/')
    .get(validate(listNotesQuerySchema, 'query'), controller.list)
    .post(validate(createNoteSchema), controller.create);

  router.route('/:id')
    .get(validate(noteIdParamsSchema, 'params'), controller.getOne)
    .patch(validate(noteIdParamsSchema, 'params'), validate(updateNoteSchema), controller.update)
    .delete(validate(noteIdParamsSchema, 'params'), controller.remove);

  router.post('/:id/pin', validate(noteIdParamsSchema, 'params'), controller.pin);
  router.delete('/:id/pin', validate(noteIdParamsSchema, 'params'), controller.unpin);
  router.post('/:id/archive', validate(noteIdParamsSchema, 'params'), controller.archive);
  router.post('/:id/unarchive', validate(noteIdParamsSchema, 'params'), controller.unarchive);

  return router;
}
```

```js
// File: src/routes/tagRoutes.js
import { Router } from 'express';

export function createTagRouter({ controller, middleware }) {
  const router = Router();

  router.get('/', middleware.authenticate, middleware.requireAuth, controller.tags);

  return router;
}
```

```js
// File: src/routes/adminRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { updateRoleSchema } from '../validators/authSchemas.js';
import { listUsersQuerySchema, noteIdParamsSchema } from '../validators/noteSchemas.js';

export function createAdminRouter({ controller, middleware }) {
  const router = Router();

  router.use(middleware.authenticate, middleware.requireAuth, middleware.requireRole('ADMIN'));

  router.get('/users', validate(listUsersQuerySchema, 'query'), controller.listUsers);
  router.patch('/users/:id/role', validate(noteIdParamsSchema, 'params'), validate(updateRoleSchema), controller.updateRole);
  router.get('/stats', controller.stats);

  return router;
}
```

```js
// File: src/routes/index.js
import { Router } from 'express';
import { createAuthRouter } from './authRoutes.js';
import { createNoteRouter } from './noteRoutes.js';
import { createTagRouter } from './tagRoutes.js';
import { createAdminRouter } from './adminRoutes.js';
import { createMethodNotAllowed } from '../middleware/methodNotAllowed.js';
import { notFound } from '../middleware/notFound.js';

/**
 * The API surface, with the method allowlist that powers 405 responses.
 * Paths are relative to the mount point `/api/v1`.
 */
export const API_ALLOWED_METHODS = Object.freeze([
  { path: '/auth/register', methods: ['POST'] },
  { path: '/auth/login', methods: ['POST'] },
  { path: '/auth/refresh', methods: ['POST'] },
  { path: '/auth/logout', methods: ['POST'] },
  { path: '/auth/me', methods: ['GET'] },
  { path: '/notes', methods: ['GET', 'POST'] },
  { path: '/notes/:id', methods: ['GET', 'PATCH', 'DELETE'] },
  { path: '/notes/:id/pin', methods: ['POST', 'DELETE'] },
  { path: '/notes/:id/archive', methods: ['POST'] },
  { path: '/notes/:id/unarchive', methods: ['POST'] },
  { path: '/tags', methods: ['GET'] },
  { path: '/admin/users', methods: ['GET'] },
  { path: '/admin/users/:id/role', methods: ['PATCH'] },
  { path: '/admin/stats', methods: ['GET'] },
]);

export function createApiRouter({ controllers, middleware, limiters }) {
  const router = Router();

  router.use('/auth', createAuthRouter({ controller: controllers.auth, middleware, limiters }));
  router.use('/notes', createNoteRouter({ controller: controllers.note, middleware }));
  router.use('/tags', createTagRouter({ controller: controllers.note, middleware }));
  router.use('/admin', createAdminRouter({ controller: controllers.admin, middleware }));

  // Order matters: 405 before 404, or the 404 handler swallows every unmatched method.
  router.use(createMethodNotAllowed(API_ALLOWED_METHODS));
  router.use(notFound);

  return router;
}
```

---

## 14. API documentation

```js
// File: src/docs/openapi.js
/**
 * A hand-written OpenAPI 3.1 document. Keep it next to the code and let CI diff it:
 * a stale contract is worse than no contract.
 */
export function createOpenApiDocument({ config }) {
  const bearer = [{ bearerAuth: [] }];
  const envelope = (schema) => ({
    type: 'object',
    properties: { data: schema, meta: { type: 'object', additionalProperties: true } },
    required: ['data'],
  });
  const errorResponse = (description) => ({
    description,
    content: { 'application/json': { schema: { $ref: '#/components/schemas/Error' } } },
  });

  return {
    openapi: '3.1.0',
    info: {
      title: 'Notes API',
      version: '1.0.0',
      description: 'A complete Express 5 notes API: authentication, roles, search, pagination and tests.',
    },
    servers: [{ url: `http://localhost:${config.PORT}`, description: 'Local development' }],
    tags: [{ name: 'auth' }, { name: 'notes' }, { name: 'tags' }, { name: 'admin' }, { name: 'system' }],
    security: bearer,
    paths: {
      '/health/live': {
        get: { tags: ['system'], summary: 'Liveness', security: [], responses: { 200: { description: 'Process is alive' } } },
      },
      '/api/v1/auth/register': {
        post: {
          tags: ['auth'], summary: 'Create an account', security: [],
          requestBody: { required: true, content: { 'application/json': { schema: { $ref: '#/components/schemas/Register' } } } },
          responses: { 201: { description: 'Created' }, 409: errorResponse('Email already registered'), 422: errorResponse('Validation failed') },
        },
      },
      '/api/v1/auth/login': {
        post: {
          tags: ['auth'], summary: 'Log in', security: [],
          requestBody: { required: true, content: { 'application/json': { schema: { $ref: '#/components/schemas/Login' } } } },
          responses: { 200: { description: 'Access token + refresh cookie' }, 401: errorResponse('Bad credentials'), 429: errorResponse('Too many attempts') },
        },
      },
      '/api/v1/auth/refresh': {
        post: {
          tags: ['auth'], summary: 'Rotate the refresh token', security: [],
          parameters: [{ $ref: '#/components/parameters/CsrfToken' }],
          responses: { 200: { description: 'New access token' }, 401: errorResponse('Invalid, expired or reused token'), 403: errorResponse('CSRF failure') },
        },
      },
      '/api/v1/auth/logout': {
        post: {
          tags: ['auth'], summary: 'Revoke this session', security: [],
          parameters: [{ $ref: '#/components/parameters/CsrfToken' }],
          responses: { 204: { description: 'Logged out' }, 403: errorResponse('CSRF failure') },
        },
      },
      '/api/v1/auth/me': {
        get: { tags: ['auth'], summary: 'The current user', responses: { 200: { description: 'The user' }, 401: errorResponse('Unauthenticated') } },
      },
      '/api/v1/notes': {
        get: {
          tags: ['notes'], summary: 'List notes',
          parameters: [
            { name: 'page', in: 'query', schema: { type: 'integer', minimum: 1, default: 1 } },
            { name: 'limit', in: 'query', schema: { type: 'integer', minimum: 1, maximum: 100, default: 20 } },
            { name: 'sort', in: 'query', schema: { type: 'string', enum: ['createdAt', '-createdAt', 'updatedAt', '-updatedAt', 'title', '-title', 'pinned', '-pinned'] } },
            { name: 'q', in: 'query', schema: { type: 'string', maxLength: 200 } },
            { name: 'tag', in: 'query', schema: { type: 'string' } },
            { name: 'pinned', in: 'query', schema: { type: 'boolean' } },
            { name: 'archived', in: 'query', schema: { type: 'boolean', default: false } },
          ],
          responses: { 200: { description: 'A page of notes', content: { 'application/json': { schema: envelope({ type: 'array', items: { $ref: '#/components/schemas/Note' } }) } } }, 401: errorResponse('Unauthenticated') },
        },
        post: {
          tags: ['notes'], summary: 'Create a note',
          requestBody: { required: true, content: { 'application/json': { schema: { $ref: '#/components/schemas/NoteInput' } } } },
          responses: { 201: { description: 'Created' }, 409: errorResponse('Duplicate title'), 422: errorResponse('Validation failed') },
        },
      },
      '/api/v1/notes/{id}': {
        parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'string' } }],
        get: { tags: ['notes'], summary: 'Read one note', responses: { 200: { description: 'The note' }, 403: errorResponse('Someone else\'s note'), 404: errorResponse('Not found') } },
        patch: {
          tags: ['notes'], summary: 'Update a note',
          parameters: [{ name: 'If-Match', in: 'header', schema: { type: 'string' }, description: 'The ETag you last read' }],
          requestBody: { required: true, content: { 'application/json': { schema: { $ref: '#/components/schemas/NotePatch' } } } },
          responses: { 200: { description: 'Updated' }, 412: errorResponse('Revision mismatch'), 422: errorResponse('Validation failed') },
        },
        delete: { tags: ['notes'], summary: 'Delete a note', responses: { 204: { description: 'Deleted' }, 404: errorResponse('Not found') } },
      },
      '/api/v1/notes/{id}/pin': {
        parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'string' } }],
        post: { tags: ['notes'], summary: 'Pin a note', responses: { 200: { description: 'Pinned' } } },
        delete: { tags: ['notes'], summary: 'Unpin a note', responses: { 200: { description: 'Unpinned' } } },
      },
      '/api/v1/notes/{id}/archive': {
        parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'string' } }],
        post: { tags: ['notes'], summary: 'Archive a note', responses: { 200: { description: 'Archived' } } },
      },
      '/api/v1/notes/{id}/unarchive': {
        parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'string' } }],
        post: { tags: ['notes'], summary: 'Unarchive a note', responses: { 200: { description: 'Unarchived' } } },
      },
      '/api/v1/tags': {
        get: { tags: ['tags'], summary: 'Your tags with counts', responses: { 200: { description: 'Tag counts' } } },
      },
      '/api/v1/admin/users': {
        get: { tags: ['admin'], summary: 'List users (ADMIN)', responses: { 200: { description: 'Users' }, 403: errorResponse('Requires ADMIN') } },
      },
      '/api/v1/admin/users/{id}/role': {
        parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'string' } }],
        patch: {
          tags: ['admin'], summary: 'Change a user role (ADMIN)',
          requestBody: { required: true, content: { 'application/json': { schema: { type: 'object', properties: { role: { type: 'string', enum: ['USER', 'ADMIN'] } }, required: ['role'] } } } },
          responses: { 200: { description: 'Updated' }, 403: errorResponse('Requires ADMIN'), 404: errorResponse('User not found') },
        },
      },
      '/api/v1/admin/stats': {
        get: { tags: ['admin'], summary: 'Totals (ADMIN)', responses: { 200: { description: 'Stats' }, 403: errorResponse('Requires ADMIN') } },
      },
    },
    components: {
      securitySchemes: {
        bearerAuth: { type: 'http', scheme: 'bearer', bearerFormat: 'JWT', description: 'The access token from /auth/login' },
      },
      parameters: {
        CsrfToken: { name: 'X-CSRF-Token', in: 'header', required: true, schema: { type: 'string' }, description: 'The csrfToken from the login response meta' },
      },
      schemas: {
        Register: {
          type: 'object', additionalProperties: false,
          required: ['email', 'password', 'name'],
          properties: {
            email: { type: 'string', format: 'email' },
            password: { type: 'string', minLength: 12, description: 'At least one lowercase, one uppercase and one digit' },
            name: { type: 'string', minLength: 1, maxLength: 100 },
          },
        },
        Login: {
          type: 'object', additionalProperties: false,
          required: ['email', 'password'],
          properties: { email: { type: 'string', format: 'email' }, password: { type: 'string' } },
        },
        NoteInput: {
          type: 'object', additionalProperties: false,
          required: ['title', 'content'],
          properties: {
            title: { type: 'string', minLength: 1, maxLength: 200 },
            content: { type: 'string', minLength: 1, maxLength: 10000 },
            tags: { type: 'array', maxItems: 10, items: { type: 'string', maxLength: 30 } },
          },
        },
        NotePatch: {
          type: 'object', additionalProperties: false, minProperties: 1,
          properties: {
            title: { type: 'string' },
            content: { type: 'string' },
            tags: { type: 'array', items: { type: 'string' } },
            pinned: { type: 'boolean' },
            archived: { type: 'boolean' },
          },
        },
        Note: {
          type: 'object',
          properties: {
            id: { type: 'string' },
            title: { type: 'string' },
            content: { type: 'string' },
            tags: { type: 'array', items: { type: 'string' } },
            pinned: { type: 'boolean' },
            archived: { type: 'boolean' },
            revision: { type: 'integer' },
            authorId: { type: 'string' },
            createdAt: { type: 'string', format: 'date-time' },
            updatedAt: { type: 'string', format: 'date-time' },
          },
        },
        Error: {
          type: 'object',
          required: ['error'],
          properties: {
            error: {
              type: 'object',
              required: ['code', 'message'],
              properties: {
                code: { type: 'string', examples: ['VALIDATION_ERROR'] },
                message: { type: 'string' },
                details: {},
                requestId: { type: 'string' },
              },
            },
          },
        },
      },
    },
  };
}
```

```js
// File: src/docs/swaggerUi.js
/**
 * Swagger UI from a CDN, served only in development. The page fetches the spec from the same origin,
 * so no CORS setup and no extra dependency is needed.
 * In production publish the spec instead: /openapi.json, Redocly, Postman, or a docs portal.
 */
export const SWAGGER_UI_HTML = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Notes API — API docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js" crossorigin></script>
    <script>
      window.ui = SwaggerUIBundle({
        url: '/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        persistAuthorization: true,
      });
    </script>
  </body>
</html>`;
```

---

## 15. Wiring it together

### 15.1 The composition root

```js
// File: src/container.js
import { createLogger } from './utils/logger.js';
import { createClock } from './utils/clock.js';
import { createIdFactory } from './utils/ids.js';
import { createPasswordHasher } from './utils/passwordHasher.js';
import { createTokenService } from './utils/tokenService.js';
import { createInMemoryUserRepository } from './repositories/inMemoryUserRepository.js';
import { createInMemoryNoteRepository } from './repositories/inMemoryNoteRepository.js';
import { createInMemoryRefreshTokenStore } from './repositories/inMemoryRefreshTokenStore.js';
import { createAuthService } from './services/authService.js';
import { createNoteService } from './services/noteService.js';
import { createAdminService } from './services/adminService.js';
import { createAuthController } from './controllers/authController.js';
import { createNoteController } from './controllers/noteController.js';
import { createAdminController } from './controllers/adminController.js';
import { createAuthenticate, createOptionalAuth, requireAuth, requireRole } from './middleware/auth.js';
import { requireCsrfToken } from './middleware/csrf.js';
import { createLimiters } from './middleware/rateLimit.js';
import { createApiRouter } from './routes/index.js';

/**
 * The composition root. Everything is created once, here, and injected downwards.
 * `overrides` exists for tests: the same wiring, with a frozen clock, counting ids or a fake repository.
 */
export function createContainer({ config, overrides = {} }) {
  const logger = overrides.logger ?? createLogger({ level: config.LOG_LEVEL, pretty: config.NODE_ENV === 'development' });
  const clock = overrides.clock ?? createClock();
  const ids = overrides.ids ?? createIdFactory();

  const userRepository = overrides.userRepository ?? createInMemoryUserRepository({ ids, clock });
  const noteRepository = overrides.noteRepository ?? createInMemoryNoteRepository({ ids, clock });
  const refreshTokenStore = overrides.refreshTokenStore ?? createInMemoryRefreshTokenStore({ clock });

  const passwordHasher = overrides.passwordHasher ?? createPasswordHasher();
  const tokenService = overrides.tokenService ?? createTokenService({
    secret: config.JWT_SECRET,
    refreshSecret: config.JWT_REFRESH_SECRET,
    issuer: config.JWT_ISSUER,
    audience: config.JWT_AUDIENCE,
    accessTtl: config.ACCESS_TOKEN_TTL,
    refreshTtl: `${config.REFRESH_TOKEN_TTL_DAYS}d`,
  });

  const authService = createAuthService({ userRepository, refreshTokenStore, passwordHasher, tokenService, clock, logger });
  const noteService = createNoteService({ noteRepository, logger });
  const adminService = createAdminService({ userRepository, noteRepository, logger });

  const controllers = {
    auth: createAuthController({ authService, config, tokenService }),
    note: createNoteController({ noteService }),
    admin: createAdminController({ adminService }),
  };

  const middleware = {
    authenticate: createAuthenticate({ tokenService, userRepository }),
    optionalAuth: createOptionalAuth({ tokenService, userRepository }),
    requireAuth,
    requireRole,
    requireCsrf: requireCsrfToken(),
  };

  const limiters = createLimiters({ enabled: config.RATE_LIMIT_ENABLED });
  const apiRouter = createApiRouter({ controllers, middleware, limiters });

  // Housekeeping: prune expired refresh tokens once an hour. unref() so this timer
  // never keeps the process alive during shutdown.
  const cleanup = setInterval(() => {
    refreshTokenStore.purgeExpired().then((removed) => {
      if (removed > 0) logger.debug({ removed }, 'purged expired refresh tokens');
    });
  }, 60 * 60 * 1_000);
  cleanup.unref?.();

  return {
    logger,
    clock,
    ids,
    userRepository,
    noteRepository,
    refreshTokenStore,
    passwordHasher,
    tokenService,
    services: { authService, noteService, adminService },
    controllers,
    middleware,
    limiters,
    apiRouter,

    /** Release every resource this container opened. A database pool would be closed here. */
    async close() {
      clearInterval(cleanup);
    },
  };
}
```

| What it does | Why it matters |
| --- | --- |
| Creates every object exactly once | One logger, one store, one token service per process |
| Injects dependencies downwards | `noteService` receives `noteRepository`; it never imports a concrete store |
| Exposes `overrides` | Tests swap the clock, the ids or a whole repository without touching production code |
| Owns the timers | The refresh-token cleanup interval is created and cleared here, not in a route |
| Owns `close()` | Shutdown is a container concern: close the pool, the cache, the queues |

### 15.2 The app

```js
// File: src/app.js
import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import cookieParser from 'cookie-parser';
import { requestId } from './middleware/requestId.js';
import { createHttpLogger } from './middleware/httpLogger.js';
import { createCsrfCookieIssuer } from './middleware/csrf.js';
import { notFound } from './middleware/notFound.js';
import { createErrorHandler } from './middleware/errorHandler.js';
import { createOpenApiDocument } from './docs/openapi.js';
import { SWAGGER_UI_HTML } from './docs/swaggerUi.js';

/**
 * Origins are compared exactly — never with `.includes(origin)` on a string (chapter 16).
 * An unknown origin gets no CORS headers at all, and the browser refuses to expose the response.
 */
export function createCorsOptions({ allowedOrigins, isProduction }) {
  return {
    origin(origin, callback) {
      if (!origin) return callback(null, true);          // curl, health probes, same-origin
      if (allowedOrigins.includes(origin)) return callback(null, true);
      return callback(null, false);
    },
    credentials: true,                                    // the refresh cookie travels with the request
    methods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token', 'X-Request-Id', 'If-Match'],
    exposedHeaders: ['X-Request-Id', 'ETag', 'Location', 'RateLimit', 'RateLimit-Policy'],
    maxAge: isProduction ? 600 : 0,
  };
}

/**
 * Builds the Express app. No listening, no signals, no process concerns: this function is
 * what tests call, which is why the whole suite runs without opening a port.
 */
export function createApp({ config, container }) {
  const app = express();
  const { logger, apiRouter } = container;

  app.disable('x-powered-by');
  if (config.TRUST_PROXY) app.set('trust proxy', 1);

  // Security and cross-cutting concerns first: they must also cover error responses.
  app.use(helmet());
  app.use(cors(createCorsOptions({ allowedOrigins: config.ALLOWED_ORIGINS, isProduction: config.isProduction })));
  app.use(requestId);
  app.use(createHttpLogger({ logger }));

  // Body parsing with a hard limit: an unbounded JSON body is a one-line denial of service.
  app.use(express.json({ limit: '100kb', strict: true }));
  app.use(express.urlencoded({ extended: false, limit: '100kb' }));
  app.use(cookieParser(config.COOKIE_SECRET));
  app.use(createCsrfCookieIssuer({ isProduction: config.isProduction }));

  // Liveness and readiness are deliberately paired: the first is cheap, the second touches dependencies.
  app.get('/health/live', (req, res) => res.json({ status: 'ok' }));
  app.get('/health/ready', (req, res) => res.json({ status: 'ok', checks: { store: { kind: 'in-memory', ok: true } } }));

  if (!config.isProduction) {
    app.get('/openapi.json', (req, res) => res.json(createOpenApiDocument({ config })));

    app.get('/docs', (req, res) => {
      // This page loads Swagger UI from a CDN, so it needs a looser policy than the API itself.
      // With no internet access, `npm i swagger-ui-dist` and serve that folder instead.
      res.set('Content-Security-Policy', "default-src 'none'; script-src 'self' https://unpkg.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'");
      res.type('html').send(SWAGGER_UI_HTML);
    });
  }

  app.use('/api/v1', apiRouter);

  // Terminators. Order matters: the 404 handler would swallow a 405 if it ran first.
  app.use(notFound);
  app.use(createErrorHandler({ logger, isProduction: config.isProduction }));

  return app;
}
```

**The middleware order, line by line, and why each position is forced:**

| # | Line | Why it is here |
| --- | --- | --- |
| 1 | `app.disable('x-powered-by')` | Removes free reconnaissance (`X-Powered-By: Express`). |
| 2 | `app.set('trust proxy', 1)` | Behind a proxy, `req.ip` is the proxy until you opt in. Skipped by default (`TRUST_PROXY=false`), because trusting a header you do not control lets anyone spoof their IP. |
| 3 | `helmet()` | Security headers must also apply to error responses, so they run before anything can fail. |
| 4 | `cors(...)` | Must run *before* the routes so the preflight `OPTIONS` never reaches a route handler. `credentials: true` is required for the refresh cookie, which is why the origin is an explicit allowlist and never `*`. |
| 5 | `requestId` | Everything after it (including the logger and the error handler) can use `req.id`. |
| 6 | `httpLogger` | Needs `req.id` and must wrap the whole request so it can log the final `statusCode` on `finish`. |
| 7 | `express.json({ limit: '100kb' })` | Parsing precedes validation, but it is a global attack surface: the limit and `strict: true` are the point. |
| 8 | `express.urlencoded({ extended: false })` | Forms are an optional extra here; `extended: false` avoids prototype-pollution surprises. |
| 9 | `cookieParser(secret)` | `req.signedCookies` is what makes the refresh cookie tamper-evident. |
| 10 | CSRF cookie issuer | Every client gets a CSRF secret before any route runs; enforcement happens per route. |
| 11 | `/health/live`, `/health/ready` | Registered before auth and rate limits: a probe must never be blocked, and it must not require credentials. |
| 12 | `/openapi.json`, `/docs` (dev only) | Documentation is an attack surface and a leak, so it is compiled out of production. |
| 13 | `/api/v1` router | The application surface. Unmatched paths inside it get the API's own 404/405 envelope. |
| 14 | `notFound` | Any path that reached this point matched nothing. |
| 15 | `createErrorHandler(...)` | Last, always four arguments, always the only place that serialises errors. |

### 15.3 The process

```js
// File: src/server.js
import { createServer } from 'node:http';
import { createApp } from './app.js';
import { createContainer } from './container.js';
import { config } from './config/env.js';
import { seedDemoData } from './dev/seed.js';

const container = createContainer({ config });
const app = createApp({ config, container });
const server = createServer(app);

// The cheapest denial-of-service protection that exists. `headersTimeout` must stay below `requestTimeout`.
server.requestTimeout = 30_000;
server.headersTimeout = 10_000;
server.keepAliveTimeout = 5_000;
server.maxHeadersCount = 100;

if (config.isDevelopment && config.SEED_DEMO_DATA) {
  const { demoUser, adminUser, notes, credentials } = await seedDemoData({ container });
  container.logger.info(
    { demo: demoUser.email, admin: adminUser.email, notes, credentials },
    'development data seeded — these generated credentials are valid for this run only',
  );
}

server.listen(config.PORT, '0.0.0.0', () => {
  container.logger.info(
    { port: config.PORT, env: config.NODE_ENV, pid: process.pid },
    `notes-api listening on http://localhost:${config.PORT}`,
  );
});

let shuttingDown = false;

/**
 * Graceful shutdown: stop accepting new connections, let in-flight requests finish,
 * release resources, then exit. Without this, every deploy drops requests (chapter 20).
 */
async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;

  container.logger.info({ signal }, 'shutdown started');

  const forceExit = setTimeout(() => {
    container.logger.error('shutdown timed out — forcing exit');
    process.exit(1);
  }, config.SHUTDOWN_TIMEOUT_MS);
  forceExit.unref();

  server.close(async (error) => {
    if (error) {
      container.logger.error({ err: error }, 'error while closing the server');
      clearTimeout(forceExit);
      process.exit(1);
    }

    await container.close();
    clearTimeout(forceExit);
    container.logger.info('shutdown complete');
    process.exit(0);
  });

  // Keep-alive sockets would otherwise hold the process open until they idle out.
  server.closeIdleConnections?.();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('unhandledRejection', (reason) => {
  container.logger.fatal({ err: reason }, 'unhandledRejection');
  shutdown('unhandledRejection');
});
```

| Concern | Implementation | What would break without it |
| --- | --- | --- |
| Slow clients | `requestTimeout`, `headersTimeout` | A few slow sockets hold every worker |
| Response timeouts | `keepAliveTimeout` slightly above the proxy's | Sporadic `502`s from connection races |
| Startup seeding | `config.SEED_DEMO_DATA` in development only | Demo data in production |
| Graceful shutdown | `server.close()`, then `container.close()`, then `exit` | Dropped in-flight requests on every deploy |
| Force exit | `SHUTDOWN_TIMEOUT_MS` timer with `unref()` | A leaked socket blocks the process forever |
| Crash visibility | `unhandledRejection` → `fatal` + shutdown | Silent zombie processes |

### 15.4 Development data

```js
// File: src/dev/seed.js
import { randomBytes } from 'node:crypto';
import { ROLES } from '../config/constants.js';

const SAMPLES = [
  { title: 'Welcome to the notes API', content: 'POST /api/v1/notes creates your own notes.', tags: ['welcome'] },
  { title: 'Pagination', content: 'Try /api/v1/notes?page=1&limit=2&sort=-createdAt', tags: ['api', 'howto'] },
  { title: 'Search', content: 'Try /api/v1/notes?q=pagination', tags: ['api', 'howto'] },
  { title: 'Filtering', content: 'Try /api/v1/notes?tag=api or ?pinned=true', tags: ['api'] },
  { title: 'Optimistic concurrency', content: 'Send If-Match with the ETag you last read.', tags: ['api', 'etag'] },
];

/**
 * Development-only sample data so the API is explorable on the first run.
 * Passwords are random per run and returned to the caller, which logs them once:
 * no credentials live in the repository, and nothing is logged that is not asked for.
 */
export async function seedDemoData({ container }) {
  const { userRepository, noteRepository, passwordHasher } = container;
  const credentials = [];

  async function createUser({ email, name, role }) {
    const password = randomBytes(9).toString('base64url');
    const passwordHash = await passwordHasher.hash(password);
    const user = await userRepository.create({ email, name, passwordHash, role });

    credentials.push({ email, password, role });
    return user;
  }

  const demoUser = await createUser({ email: 'demo@example.com', name: 'Demo User', role: ROLES.USER });
  const adminUser = await createUser({ email: 'admin@example.com', name: 'Demo Admin', role: ROLES.ADMIN });

  const notes = [];
  for (const sample of SAMPLES) {
    notes.push(await noteRepository.create({ ...sample, authorId: demoUser.id }));
  }

  // One pinned note, so `?pinned=true` has something to return.
  await noteRepository.update(notes[0].id, { pinned: true });

  return { demoUser, adminUser, notes: notes.length, credentials };
}
```

Note that the generated password is *not* redacted, while every field named `password` or `token` in a
request would be: pino's `redact` paths are exact. `credentials[].password` is a different path from
`password`, and that is deliberate here — the whole point of the seed is to print a usable credential,
once, in a development process.

---

## 16. Running it

```bash
# 1. Install
npm install

# 2. Configure (see .env.example). Generate real secrets:
cp .env.example .env
node -e "const c=require('crypto');console.log('JWT_SECRET='+c.randomBytes(48).toString('base64'))"
# repeat for JWT_REFRESH_SECRET and COOKIE_SECRET

# 3. Run with auto-restart and the .env file loaded
npm run dev
```

```text
[10:00:03.114] INFO: development data seeded — these generated credentials are valid for this run only
    demo: "demo@example.com"
    admin: "admin@example.com"
    notes: 5
    credentials: [
      { "email": "demo@example.com", "password": "RGze13mF68no", "role": "USER" },
      { "email": "admin@example.com", "password": "LsayyKum_HoS", "role": "ADMIN" }
    ]
[10:00:03.121] INFO: notes-api listening on http://localhost:3000
    port: 3000
    env: "development"
```

```text
# Invalid configuration, checked before the server starts (never prints values)
$ JWT_SECRET=short node src/server.js
Invalid environment configuration:
  JWT_SECRET: must be at least 32 characters — generate one with: openssl rand -base64 48
  JWT_REFRESH_SECRET: Required
```

```bash
# 4. A first request
curl -s http://localhost:3000/health/live

# 5. Stop it: Ctrl+C (SIGINT) triggers the same graceful path as SIGTERM in production
```

```text
{"status":"ok"}

$ kill -TERM <pid>
[10:14:22.001] INFO: shutdown started
    signal: "SIGTERM"
[10:14:22.004] INFO: shutdown complete
```

**Production shape** (the full deploy story is `07-deployment/`):

```bash
NODE_ENV=production node src/server.js     # no .env file: the platform injects the variables
```

```text
# In production the demo seed, /docs and /openapi.json are gone, and 5xx bodies are generic:
$ curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3000/docs
404
```

| What changes | Development | Production |
| --- | --- | --- |
| `.env` file | loaded via `--env-file` | injected by the platform/secret manager |
| Pretty logs | `pino-pretty` (devDependency) | single-line JSON on stdout |
| Demo data | `SEED_DEMO_DATA=true` | never |
| `/docs`, `/openapi.json` | served | `404` (publish the spec from CI instead) |
| Error details | real message + `details` | `Something went wrong` for 5xx, details in logs |
| CORS preflight cache | `Access-Control-Max-Age: 0` | `600` |
| Cookie `Secure` flag | off over plain HTTP | required |

---

## 17. Testing the API by hand

Three tools, three purposes: **curl** for exactness, **Postman/Insomnia** for exploration and collections,
**Swagger UI** for a browsable contract. All commands below assume `jq` for readable JSON
(`brew install jq` / `apt install jq`) and a server on `http://localhost:3000`.

### 17.1 Health, docs and the spec (browser-friendly)

```bash
curl -s http://localhost:3000/health/live; echo
curl -s http://localhost:3000/health/ready; echo
curl -s -o /dev/null -w 'GET /docs -> %{http_code} %{content_type}\n' http://localhost:3000/docs
curl -s http://localhost:3000/openapi.json | jq -c '.info'
```

```text
{"status":"ok"}
{"status":"ok","checks":{"store":{"kind":"in-memory","ok":true}}}
GET /docs -> 200 text/html; charset=utf-8
{"title":"Notes API","version":"1.0.0","description":"A complete Express 5 notes API: authentication, roles, search, pagination and tests."}
```

Open `http://localhost:3000/docs` in a browser to get Swagger UI: every endpoint is listed, **Authorize**
accepts the Bearer token from `/auth/login`, and *Try it out* sends real requests. In Postman,
**Import → Link** `http://localhost:3000/openapi.json` creates the whole collection, folders included.

### 17.2 Register, inspect the cookies, and read your profile

```bash
BASE=http://localhost:3000
JAR=/tmp/notes-api.cookies

REG=$(curl -s -D /tmp/register.headers -c "$JAR" -X POST $BASE/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"ada@example.com","password":"CorrectHorse1","name":"Ada Lovelace"}')
echo "$REG" | jq
TOKEN=$(echo "$REG" | jq -r .data.accessToken)
CSRF=$(echo "$REG" | jq -r .meta.csrfToken)

grep -iE '^(HTTP|location|set-cookie)' /tmp/register.headers
```

```text
HTTP/1.1 201 Created
Location: /api/v1/auth/me
Set-Cookie: csrfSecret=ec246a907e...a2cf; Max-Age=86400; Path=/; SameSite=Lax
Set-Cookie: refreshToken=s%3AeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...; Max-Age=2592000; Path=/api/v1/auth; HttpOnly; SameSite=Strict
```

```json
{
  "data": {
    "user": {
      "id": "user_45729933-01e4-4bf5-a4db-4e3d88a9a7c9",
      "email": "ada@example.com",
      "name": "Ada Lovelace",
      "role": "USER",
      "createdAt": "2026-09-18T06:58:58.648Z"
    },
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiVVNFUiIsImlhdCI6MTc4OTcxNDczOCwiZXhwIjoxNzg5NzE1NjM4LCJhdWQiOiJub3Rlcy1hcGktY2xpZW50cyIsImlzcyI6Im5vdGVzLWFwaSIsInN1YiI6InVzZXJfNDU3Mjk5MzMtMDFlNC00YmY1LWE0ZGItNGUzZDg4YTlhN2M5In0.k1onnEOi4chqX0_fG0V361X-9F-nzz3poy7Np3A2Ojk",
    "tokenType": "Bearer",
    "expiresIn": 900
  },
  "meta": {
    "csrfToken": "be5c1e45bc6c53b2ce1189478ef4e74f74954af53d579e783e59dfaeb86ba952"
  }
}
```

Three things to notice, because they are the security design in one response:

| Observation | Meaning |
| --- | --- |
| The refresh token is **not** in the body | A response body can end up in a log, a browser cache or a crash report |
| `refreshToken` is `HttpOnly` and `Path=/api/v1/auth` | JavaScript cannot read it, and it is only ever sent to two endpoints |
| `csrfToken` is in the body and in a readable cookie | The client echoes it in `X-CSRF-Token`; a cross-site attacker can do neither |

```bash
curl -s $BASE/api/v1/auth/me -H "Authorization: Bearer $TOKEN" | jq
```

```json
{
  "data": {
    "id": "user_45729933-01e4-4bf5-a4db-4e3d88a9a7c9",
    "email": "ada@example.com",
    "name": "Ada Lovelace",
    "role": "USER",
    "createdAt": "2026-09-18T06:58:58.648Z"
  }
}
```

### 17.3 Create, read, list, filter

```bash
CREATED=$(curl -s -D /tmp/create.headers -X POST $BASE/api/v1/notes \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Middleware order","content":"requestId, logger, helmet, cors, json, cookieParser.","tags":["Express","middleware"]}')

grep -iE '^(HTTP|location|etag|x-request-id)' /tmp/create.headers
echo "$CREATED" | jq
NOTE_ID=$(echo "$CREATED" | jq -r .data.id)
ETAG=$(grep -i '^etag' /tmp/create.headers | tr -d '\r' | cut -d' ' -f2-)
```

```text
HTTP/1.1 201 Created
X-Request-Id: f2fe5303-88fc-443c-b5bf-3cc71edc7169
ETag: W/"note_7ac290df-fafd-46cc-83ba-0b669cb1b38f-1"
Location: /api/v1/notes/note_7ac290df-fafd-46cc-83ba-0b669cb1b38f
```

```json
{
  "data": {
    "id": "note_7ac290df-fafd-46cc-83ba-0b669cb1b38f",
    "title": "Middleware order",
    "content": "requestId, logger, helmet, cors, json, cookieParser.",
    "tags": ["express", "middleware"],
    "pinned": false,
    "archived": false,
    "revision": 1,
    "authorId": "user_45729933-01e4-4bf5-a4db-4e3d88a9a7c9",
    "createdAt": "2026-09-18T06:58:58.801Z",
    "updatedAt": "2026-09-18T06:58:58.801Z"
  }
}
```

```bash
curl -s "$BASE/api/v1/notes?page=1&limit=2&sort=-createdAt" -H "Authorization: Bearer $TOKEN" \
  | jq '{titles: [.data[].title], meta}'
curl -s "$BASE/api/v1/notes?q=middleware" -H "Authorization: Bearer $TOKEN" | jq -c '{total: .meta.total}'
curl -s "$BASE/api/v1/notes?tag=express&pinned=true" -H "Authorization: Bearer $TOKEN" | jq -c '{total: .meta.total}'
```

```text
{
  "titles": ["Middleware order"],
  "meta": { "page": 1, "limit": 2, "total": 1, "pages": 1, "hasNext": false }
}
{"total":1}
{"total":0}
```

```bash
# Query strings are validated like everything else: an unknown sort field or an oversized page
# is a 422 with the field named, never a silently ignored parameter.
curl -s "$BASE/api/v1/notes?sort=password" -H "Authorization: Bearer $TOKEN" | jq -c '.error.details[0]'
curl -s "$BASE/api/v1/notes?limit=1000" -H "Authorization: Bearer $TOKEN" | jq -c '.error.details[0]'
```

```text
{"field":"sort","message":"Invalid option: expected one of \"createdAt\"|\"-createdAt\"|\"updatedAt\"|\"-updatedAt\"|\"title\"|\"-title\"|\"pinned\"|\"-pinned\"","code":"invalid_value"}
{"field":"limit","message":"Too big: expected number to be <=100","code":"too_big"}
```

### 17.4 Update with optimistic concurrency

```bash
curl -s -X PATCH $BASE/api/v1/notes/$NOTE_ID \
  -H "Authorization: Bearer $TOKEN" -H "If-Match: $ETAG" -H 'Content-Type: application/json' \
  -d '{"title":"Middleware order (final)"}' | jq -c '{title: .data.title, revision: .data.revision}'

# The same, stale ETag now means "someone else wrote first":
curl -s -X PATCH $BASE/api/v1/notes/$NOTE_ID \
  -H "Authorization: Bearer $TOKEN" -H "If-Match: $ETAG" -H 'Content-Type: application/json' \
  -d '{"content":"lost update"}' | jq
```

```text
{"title":"Middleware order (final)","revision":2}
```

```json
{
  "error": {
    "code": "PRECONDITION_FAILED",
    "message": "The note was modified by someone else",
    "details": {
      "expected": 1,
      "actual": 2,
      "etag": "W/\"note_7ac290df-fafd-46cc-83ba-0b669cb1b38f-2\""
    },
    "requestId": "e508df6e-efbe-4723-a168-7ab18758d3dd"
  }
}
```

The client can retry immediately: `details.etag` is the current version, and `details.actual` is the
revision to send back in `If-Match`.

### 17.5 Every failure mode in one screen

```bash
# 422 — two problems reported at once
curl -s -X POST $BASE/api/v1/notes -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"content":"no title","colour":"red"}' | jq -c '.error'

# 409 — the same author may not have two notes with one title
curl -s -X POST $BASE/api/v1/notes -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Middleware order (final)","content":"duplicate"}' | jq -c '.error'

# 404 — the id does not exist
curl -s $BASE/api/v1/notes/note_404 -H "Authorization: Bearer $TOKEN" | jq -c '.error'

# 405 + Allow — the path exists, the method does not
curl -s -D /tmp/405.headers -o /tmp/405.json -X PUT $BASE/api/v1/notes -H "Authorization: Bearer $TOKEN"
grep -iE '^(HTTP|allow)' /tmp/405.headers; jq -c '.error' /tmp/405.json

# 400 — malformed JSON never reaches a handler
curl -s -X POST $BASE/api/v1/auth/login -H 'Content-Type: application/json' -d '{"email": ' | jq -c '.error'

# 401 — no token at all
curl -s -X POST $BASE/api/v1/notes -H 'Content-Type: application/json' \
  -d '{"title":"anonymous","content":"x"}' | jq -c '.error'
```

```text
{"code":"VALIDATION_ERROR","message":"Request validation failed","details":[{"field":"title","message":"Invalid input: expected string, received undefined","code":"invalid_type"},{"field":"body","message":"Unrecognized key: \"colour\"","code":"unrecognized_keys"}],"requestId":"cc5dfcb0-1134-4056-aec0-482b7104166d"}
{"code":"CONFLICT","message":"You already have a note with that title","details":{"field":"title"},"requestId":"47cf1ed9-541d-49da-93d0-acbe97b9ddda"}
{"code":"NOT_FOUND","message":"Note not found","requestId":"93e2d787-6710-4e56-8ed1-52da39fe53ca"}
HTTP/1.1 405 Method Not Allowed
Allow: GET, POST
{"code":"METHOD_NOT_ALLOWED","message":"Method PUT is not allowed for /api/v1/notes","details":{"allow":["GET","POST"]},"requestId":"1b29640a-2e55-4a73-9f36-7e718b4aea9b"}
{"code":"INVALID_JSON","message":"Request body is not valid JSON","requestId":"e96cbedb-3bbf-4e3f-a2a7-f07b00af0bc4"}
{"code":"UNAUTHENTICATED","message":"Provide a Bearer access token","requestId":"dab0d2c1-bd63-4a18-a3d0-91dd5adcb6e8"}
```

### 17.6 Authorisation: 403 from two different places

```bash
GRACE=$(curl -s -X POST $BASE/api/v1/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"grace@example.com","password":"CorrectHorse1","name":"Grace Hopper"}' | jq -r .data.accessToken)

# Coarse: the route requires ADMIN
curl -s $BASE/api/v1/admin/stats -H "Authorization: Bearer $GRACE" | jq -c '.error'

# Fine-grained: the resource belongs to someone else
curl -s $BASE/api/v1/notes/$NOTE_ID -H "Authorization: Bearer $GRACE" | jq -c '.error'
```

```text
{"code":"FORBIDDEN","message":"This endpoint requires one of: ADMIN","requestId":"789ff514-a883-43da-9172-4ea6823acb87"}
{"code":"FORBIDDEN","message":"This note belongs to another user","requestId":"0288b776-3c18-49d9-b327-d4dccde6adb2"}
```

The first is a **middleware** decision (role), the second a **service** decision (ownership). Both must
exist: a middleware can only answer "may this kind of user call this kind of endpoint?", never "may this
user touch this row?".

### 17.7 Refresh rotation and reuse detection

```bash
cp "$JAR" /tmp/old.cookies     # what an attacker who stole the cookie would hold

curl -s -D - -o /dev/null -b "$JAR" -c "$JAR" -X POST $BASE/api/v1/auth/refresh \
  -H "X-CSRF-Token: $CSRF" | grep -iE '^(HTTP|set-cookie)'

# Replaying the OLD token is the signature of theft:
curl -s -b /tmp/old.cookies -X POST $BASE/api/v1/auth/refresh -H "X-CSRF-Token: $CSRF" | jq -c '.error'

# The entire family is revoked, so the newest token stops working too:
curl -s -b "$JAR" -X POST $BASE/api/v1/auth/refresh -H "X-CSRF-Token: $CSRF" | jq -c '.error'

# Missing CSRF header (an attacker's page cannot set a custom header):
curl -s -b "$JAR" -X POST $BASE/api/v1/auth/refresh | jq -c '.error'
```

```text
HTTP/1.1 200 OK
Set-Cookie: refreshToken=s%3AeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI3ZjEzM2IyYy02OWJmLTQ4N2MtYWIyOC0wMjlmODcwNzAyNmUi...; Max-Age=2592000; Path=/api/v1/auth; HttpOnly; SameSite=Strict
{"code":"UNAUTHENTICATED","message":"Refresh token reuse detected — all sessions for this device were revoked","requestId":"321b5627-ca7b-4549-a669-a63720fb3f8a"}
{"code":"UNAUTHENTICATED","message":"This session was revoked — log in again","requestId":"0321ff05-0e11-455f-90b6-5df86e0b1f55"}
{"code":"CSRF_FAILED","message":"CSRF token is missing or invalid","requestId":"b5306596-66c2-46da-8550-4a9f315d304d"}
```

### 17.8 Admin endpoints and rate limiting

```bash
ADMIN_TOKEN=$(curl -s -X POST $BASE/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<the seeded admin password>"}' | jq -r .data.accessToken)

curl -s $BASE/api/v1/admin/stats -H "Authorization: Bearer $ADMIN_TOKEN" | jq -c
curl -s "$BASE/api/v1/admin/users?limit=2" -H "Authorization: Bearer $ADMIN_TOKEN" | jq -c '{emails: [.data[].email], meta}'

# Ten login attempts are allowed per 15 minutes per IP; the eleventh is a 429
for i in $(seq 1 11); do
  curl -s -o /dev/null -w '%{http_code} ' -X POST $BASE/api/v1/auth/login \
    -H 'Content-Type: application/json' -d '{"email":"nobody@example.com","password":"WrongHorse1"}'
done; echo
curl -s -D /tmp/rl.headers -o /tmp/rl.json -X POST $BASE/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"email":"nobody@example.com","password":"WrongHorse1"}'
grep -iE '^(HTTP|ratelimit|retry-after)' /tmp/rl.headers; jq -c '.error' /tmp/rl.json
```

```text
{"data":{"users":4,"notes":6,"pinned":1,"archived":0,"tags":6}}
{"emails":["demo@example.com","admin@example.com"],"meta":{"page":1,"limit":2,"total":4,"pages":2}}
401 401 401 401 401 401 401 401 401 429 429
HTTP/1.1 429 Too Many Requests
RateLimit: "10-in-15min"; r=0; t=900
RateLimit-Policy: "10-in-15min"; q=10; w=900; pk=:MTJjYTE3YjQ5YWYy:
Retry-After: 900
{"code":"TOO_MANY_REQUESTS","message":"Too many requests — retry after 900s","requestId":"86b50195-cc73-4e67-865c-a7621ed5d1bb"}
```

The 429 keeps the same error envelope as everything else: the limiter's `handler` calls `next(error)`
instead of writing its own body, so clients parse one shape.

### 17.9 CORS, seen from the outside

```bash
# A preflight from an allowed origin
curl -s -o /dev/null -D - -X OPTIONS $BASE/api/v1/notes \
  -H 'Origin: http://localhost:5173' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: authorization,content-type' | grep -iE '^(HTTP|access-control|vary)'

# An unknown origin gets no CORS headers at all (the browser then refuses to expose the response)
curl -s -o /dev/null -D - $BASE/health/live -H 'Origin: https://evil.example' | grep -ci 'access-control-allow-origin'
```

```text
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: http://localhost:5173
Vary: Origin
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET,POST,PATCH,DELETE,OPTIONS
Access-Control-Allow-Headers: Content-Type,Authorization,X-CSRF-Token,X-Request-Id,If-Match
Access-Control-Expose-Headers: X-Request-Id,ETag,Location,RateLimit,RateLimit-Policy
0
```

> `Vary: Origin` is what stops a cache from serving one origin's response (with its CORS headers) to
> another origin. Without it, a CDN can leak a response across origins.

### 17.10 Logout

```bash
curl -s -o /dev/null -w 'logout -> %{http_code}\n' -b "$JAR" -X POST $BASE/api/v1/auth/logout -H "X-CSRF-Token: $CSRF"
curl -s -b "$JAR" -X POST $BASE/api/v1/auth/refresh -H "X-CSRF-Token: $CSRF" | jq -c '.error'
```

```text
logout -> 204
{"code":"UNAUTHENTICATED","message":"This session was revoked — log in again","requestId":"c77d0598-9c74-40d2-a185-ceef0f55418a"}
```

---

## 18. The automated test suite

The rule from chapter 19 applies: **the routes are tested through HTTP, the rules are tested directly.**
`node --test` needs no configuration; `supertest` talks to the app object without a port.

```bash
npm test                    # NODE_ENV=test node --test
npm run test:watch
npm run test:coverage       # NODE_ENV=test node --test --experimental-test-coverage
```

### 18.1 The harness

```js
// File: tests/support/harness.js
import request from 'supertest';
import { createApp } from '../../src/app.js';
import { createContainer } from '../../src/container.js';
import { createClock } from '../../src/utils/clock.js';
import { createCountingIdFactory } from '../../src/utils/ids.js';

export const FROZEN_TIME = '2026-09-18T10:00:00.000Z';
export const VALID_PASSWORD = 'CorrectHorse1';

/**
 * A full application, wired with a frozen clock and counter ids: same code paths as production,
 * no port, no network, no database (chapter 19).
 */
export function createHarness({ rateLimitEnabled = false, overrides = {} } = {}) {
  const config = {
    NODE_ENV: 'test',
    PORT: 0,
    LOG_LEVEL: 'silent',
    JWT_SECRET: 'test-access-secret-that-is-long-enough-000001',
    JWT_REFRESH_SECRET: 'test-refresh-secret-that-is-long-enough-00002',
    COOKIE_SECRET: 'test-cookie-secret-that-is-long-enough-000003',
    JWT_ISSUER: 'notes-api',
    JWT_AUDIENCE: 'notes-api-clients',
    ACCESS_TOKEN_TTL: '15m',
    REFRESH_TOKEN_TTL_DAYS: 30,
    refreshTokenTtlMs: 30 * 24 * 60 * 60 * 1_000,
    ALLOWED_ORIGINS: ['http://localhost:5173'],
    RATE_LIMIT_ENABLED: rateLimitEnabled,
    TRUST_PROXY: false,
    SEED_DEMO_DATA: false,
    SHUTDOWN_TIMEOUT_MS: 1_000,
    isProduction: false,
    isDevelopment: false,
    isTest: true,
  };

  const clock = overrides.clock ?? createClock({ now: () => new Date(FROZEN_TIME) });
  const container = createContainer({
    config,
    overrides: { clock, ids: createCountingIdFactory(), ...overrides },
  });

  const app = createApp({ config, container });

  return {
    app,
    container,
    config,
    clock,
    client: () => request(app),          // stateless: no cookie jar
    agent: () => request.agent(app),     // stateful: keeps the refresh and csrf cookies
    FROZEN_TIME,
  };
}

/** Registers a user and returns everything a test needs to act as them. */
export async function registerUser(client, {
  email = 'ada@example.com',
  name = 'Ada Lovelace',
  password = VALID_PASSWORD,
} = {}) {
  const response = await client.post('/api/v1/auth/register').send({ email, password, name }).expect(201);

  return {
    user: response.body.data.user,
    accessToken: response.body.data.accessToken,
    csrfToken: response.body.meta.csrfToken,
    auth: `Bearer ${response.body.data.accessToken}`,
  };
}

export async function createNote(client, auth, body = {}) {
  const payload = { title: 'First note', content: 'Something worth writing down.', tags: [], ...body };
  const response = await client.post('/api/v1/notes').set('Authorization', auth).send(payload).expect(201);
  return response.body.data;
}
```

| Detail | Why it is there |
| --- | --- |
| `config` is a plain object | The test never depends on the machine's environment variables |
| `LOG_LEVEL: 'silent'` | A test run that prints a thousand log lines hides the failures |
| Frozen clock | `createdAt`/`updatedAt` assertions are exact, not "approximately now" |
| Counting ids | `note_2` beats a UUID when a test fails at 3 a.m. |
| `client()` vs `agent()` | `agent` keeps cookies: exactly what a browser does for refresh/logout |
| `rateLimitEnabled: false` | One test asserting `429` needs limits; the other 34 must not trip them |

```js
// File: tests/support/repositoryStub.js
/**
 * A recording stand-in for the note repository. Unit tests assert on the arguments the service
 * passes down (the contract) instead of on a database — the promise of the repository boundary.
 */
export function createNoteRepositoryStub({ notes = [] } = {}) {
  const state = notes.map((note) => ({ ...note }));
  const calls = { create: [], update: [], list: [], remove: [], findByTitle: [], findById: [] };

  return {
    calls,
    repository: {
      async create(input) {
        calls.create.push(input);
        return { id: `note_${state.length + 1}`, pinned: false, archived: false, revision: 1, tags: [], ...input };
      },
      async findById(id) {
        calls.findById.push(id);
        return state.find((note) => note.id === id) ?? null;
      },
      async findByTitle(title, authorId) {
        calls.findByTitle.push({ title, authorId });
        return state.find((note) => note.authorId === authorId && note.title.toLowerCase() === title.toLowerCase()) ?? null;
      },
      async update(id, patch) {
        calls.update.push({ id, patch });
        const found = state.find((note) => note.id === id);
        return found ? { ...found, ...patch, revision: found.revision + 1 } : null;
      },
      async remove(id) {
        calls.remove.push(id);
        return state.some((note) => note.id === id);
      },
      async list(query) {
        calls.list.push(query);
        return { items: state, total: state.length };
      },
      async tagCounts() {
        return [];
      },
      async stats() {
        return { notes: state.length, pinned: 0, archived: 0, tags: 0 };
      },
    },
  };
}
```

### 18.2 Unit tests for the service

```js
// File: tests/unit/noteService.test.js
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { createNoteService } from '../../src/services/noteService.js';
import { createNoteRepositoryStub } from '../support/repositoryStub.js';

const ADA = { id: 'user_1', role: 'USER' };
const ADMIN = { id: 'user_9', role: 'ADMIN' };

function build({ notes = [] } = {}) {
  const { repository, calls } = createNoteRepositoryStub({ notes });
  const service = createNoteService({ noteRepository: repository, logger: { info() {}, warn() {} } });
  return { service, calls };
}

const note = (overrides = {}) => ({
  id: 'note_1',
  title: 'Draft',
  content: 'Body',
  tags: [],
  pinned: false,
  archived: false,
  revision: 1,
  authorId: ADA.id,
  createdAt: '2026-09-18T10:00:00.000Z',
  updatedAt: '2026-09-18T10:00:00.000Z',
  ...overrides,
});

describe('noteService.list', () => {
  it('translates page and limit into an offset', async () => {
    const { service, calls } = build();

    await service.list({ actor: ADA, query: { page: 3, limit: 10 } });

    assert.deepEqual(calls.list[0], {
      authorId: 'user_1',
      offset: 20,
      limit: 10,
      sort: undefined,
      q: undefined,
      tag: undefined,
      pinned: undefined,
      archived: false,
    });
  });

  it('hides archived notes by default and includes them on request', async () => {
    const { service, calls } = build();

    await service.list({ actor: ADA, query: {} });
    await service.list({ actor: ADA, query: { archived: true } });

    assert.equal(calls.list[0].archived, false);
    assert.equal(calls.list[1].archived, true);
  });
});

describe('noteService.create', () => {
  it('refuses a duplicate title for the same author', async () => {
    const { service } = build({ notes: [note({ title: 'Draft' })] });

    await assert.rejects(
      () => service.create({ input: { title: 'draft', content: 'x' }, actor: ADA }),
      (error) => error.statusCode === 409 && error.details.field === 'title',
    );
  });

  it('stamps the note with the actor id', async () => {
    const { service, calls } = build();

    const created = await service.create({ input: { title: 'Fresh', content: 'x' }, actor: ADA });

    assert.equal(created.authorId, 'user_1');
    assert.equal(calls.create[0].authorId, 'user_1');
  });
});

describe('noteService access rules', () => {
  it('returns 404 for a missing note and 403 for someone else note', async () => {
    const { service } = build({ notes: [note()] });

    await assert.rejects(() => service.get({ id: 'note_404', actor: ADA }), (error) => error.statusCode === 404);
    await assert.rejects(() => service.get({ id: 'note_1', actor: { id: 'user_2', role: 'USER' } }), (error) => error.statusCode === 403);
  });

  it('lets an ADMIN read any note', async () => {
    const { service } = build({ notes: [note()] });

    const found = await service.get({ id: 'note_1', actor: ADMIN });
    assert.equal(found.id, 'note_1');
  });
});

describe('noteService.update', () => {
  it('rejects a stale If-Match revision with 412 and reports the current one', async () => {
    const { service } = build({ notes: [note({ revision: 5 })] });

    await assert.rejects(
      () => service.update({ id: 'note_1', input: { content: 'new' }, actor: ADA, ifMatchRevision: 4 }),
      (error) => error.statusCode === 412 && error.details.actual === 5,
    );
  });

  it('accepts the current revision and returns the updated note', async () => {
    const { service } = build({ notes: [note({ revision: 5 })] });

    const updated = await service.update({ id: 'note_1', input: { content: 'new' }, actor: ADA, ifMatchRevision: 5 });

    assert.equal(updated.content, 'new');
    assert.equal(updated.revision, 6);
  });
});
```

```text
$ node --test tests/unit/noteService.test.js
▶ noteService.list
  ✔ translates page and limit into an offset (1.151851ms)
  ✔ hides archived notes by default and includes them on request (0.221477ms)
▶ noteService.create
  ✔ refuses a duplicate title for the same author (0.926729ms)
  ✔ stamps the note with the actor id (0.311119ms)
▶ noteService access rules
  ✔ returns 404 for a missing note and 403 for someone else note (0.375772ms)
  ✔ lets an ADMIN read any note (0.188865ms)
▶ noteService.update
  ✔ rejects a stale If-Match revision with 412 and reports the current one (0.354675ms)
  ✔ accepts the current revision and returns the updated note (0.200174ms)
ℹ tests 8
ℹ pass 8
ℹ fail 0
```

### 18.3 Integration tests for the routes

```js
// File: tests/integration/auth.routes.test.js
import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createHarness, registerUser, VALID_PASSWORD } from '../support/harness.js';

describe('POST /api/v1/auth/register', () => {
  let harness;

  beforeEach(() => { harness = createHarness(); });

  it('creates a user, returns an access token and sets an httpOnly refresh cookie', async () => {
    const response = await harness.client()
      .post('/api/v1/auth/register')
      .send({ email: 'grace@example.com', password: VALID_PASSWORD, name: 'Grace Hopper' })
      .expect(201);

    assert.equal(response.body.data.user.email, 'grace@example.com');
    assert.equal(response.body.data.user.role, 'USER');
    assert.equal(response.body.data.tokenType, 'Bearer');
    assert.ok(response.body.data.accessToken.split('.').length === 3, 'a JWT has three parts');

    // The refresh token must never be readable by JavaScript or by the response body.
    assert.equal(response.body.data.refreshToken, undefined);

    const cookies = response.headers['set-cookie'].join(';');
    assert.match(cookies, /refreshToken=s%3A/);
    assert.match(cookies, /HttpOnly/i);
    assert.match(cookies, /Path=\/api\/v1\/auth/);
    assert.match(cookies, /csrfSecret=/);
  });

  it('rejects a duplicate email with 409', async () => {
    const client = harness.client();
    await registerUser(client);

    const response = await client
      .post('/api/v1/auth/register')
      .send({ email: 'ada@example.com', password: VALID_PASSWORD, name: 'Someone else' })
      .expect(409);

    assert.equal(response.body.error.code, 'CONFLICT');
  });

  it('reports every weak-password rule at once with 422', async () => {
    const response = await harness.client()
      .post('/api/v1/auth/register')
      .send({ email: 'weak@example.com', password: 'short', name: 'Weak' })
      .expect(422);

    assert.equal(response.body.error.code, 'VALIDATION_ERROR');
    assert.match(response.body.error.requestId, /[0-9a-f-]{8}/);
    // Every rule that failed is reported at once, each with the field it belongs to.
    const details = response.body.error.details;
    assert.deepEqual([...new Set(details.map((detail) => detail.field))], ['password']);
    const messages = details.map((detail) => detail.message).join(' | ');
    assert.match(messages, /at least 12 characters/);
    assert.match(messages, /uppercase letter/);
    assert.match(messages, /digit/);
  });
});

describe('POST /api/v1/auth/login', () => {
  let harness;

  beforeEach(() => { harness = createHarness(); });

  it('answers with the same 401 for an unknown email and a wrong password', async () => {
    const client = harness.client();
    await registerUser(client);

    const wrongPassword = await client.post('/api/v1/auth/login').send({ email: 'ada@example.com', password: 'WrongHorse1' }).expect(401);
    const unknownEmail = await client.post('/api/v1/auth/login').send({ email: 'nobody@example.com', password: 'WrongHorse1' }).expect(401);

    assert.equal(wrongPassword.body.error.message, unknownEmail.body.error.message);
    assert.equal(wrongPassword.body.error.code, 'UNAUTHENTICATED');
  });

  it('returns an access token for correct credentials', async () => {
    const client = harness.client();
    await registerUser(client);

    const response = await client.post('/api/v1/auth/login').send({ email: 'ada@example.com', password: VALID_PASSWORD }).expect(200);

    assert.equal(response.body.data.user.email, 'ada@example.com');
    assert.equal(response.body.data.expiresIn, 900);
    assert.ok(response.body.meta.csrfToken);
  });
});

describe('GET /api/v1/auth/me', () => {
  it('requires a Bearer token', async () => {
    const harness = createHarness();

    await harness.client().get('/api/v1/auth/me').expect(401);
    await harness.client().get('/api/v1/auth/me').set('Authorization', 'Bearer not-a-token').expect(401);
  });

  it('returns the current user without any secret fields', async () => {
    const harness = createHarness();
    const { auth } = await registerUser(harness.client());

    const response = await harness.client().get('/api/v1/auth/me').set('Authorization', auth).expect(200);

    assert.deepEqual(Object.keys(response.body.data).sort(), ['createdAt', 'email', 'id', 'name', 'role']);
  });
});

describe('POST /api/v1/auth/refresh', () => {
  /** Cookie values are shown raw by the response headers, which is exactly what a client stores. */
  function cookiesFrom(response) {
    const raw = response.headers['set-cookie'] ?? [];
    const pick = (name) => raw.find((cookie) => cookie.startsWith(`${name}=`))?.split(';')[0];
    return { refresh: pick('refreshToken'), csrf: pick('csrfSecret') };
  }

  it('rotates the refresh token and rejects a token that was already used', async () => {
    const harness = createHarness();
    const agent = harness.agent();

    const registered = await agent
      .post('/api/v1/auth/register')
      .send({ email: 'ada@example.com', password: VALID_PASSWORD, name: 'Ada Lovelace' })
      .expect(201);

    const csrfToken = registered.body.meta.csrfToken;
    const firstCookies = cookiesFrom(registered);

    const first = await agent.post('/api/v1/auth/refresh').set('X-CSRF-Token', csrfToken).expect(200);
    assert.ok(first.body.data.accessToken);

    // Replaying the previous refresh token is the signature of a stolen token.
    const replay = await harness.client()
      .post('/api/v1/auth/refresh')
      .set('Cookie', `${firstCookies.refresh}; ${firstCookies.csrf}`)
      .set('X-CSRF-Token', csrfToken)
      .expect(401);

    assert.match(replay.body.error.message, /reuse|revoked/i);
  });

  it('requires the CSRF token', async () => {
    const harness = createHarness();
    const agent = harness.agent();
    await registerUser(agent);

    const response = await agent.post('/api/v1/auth/refresh').expect(403);
    assert.equal(response.body.error.code, 'CSRF_FAILED');
  });
});

describe('POST /api/v1/auth/logout', () => {
  it('revokes the session and clears the cookie', async () => {
    const harness = createHarness();
    const agent = harness.agent();
    const { csrfToken } = await registerUser(agent);

    const response = await agent.post('/api/v1/auth/logout').set('X-CSRF-Token', csrfToken).expect(204);
    assert.match(response.headers['set-cookie'].join(';'), /refreshToken=;/);

    await agent.post('/api/v1/auth/refresh').set('X-CSRF-Token', csrfToken).expect(401);
  });
});

describe('role-based access control', () => {
  it('refuses a USER on an ADMIN endpoint', async () => {
    const harness = createHarness();
    const { auth } = await registerUser(harness.client());

    const response = await harness.client().get('/api/v1/admin/stats').set('Authorization', auth).expect(403);
    assert.equal(response.body.error.code, 'FORBIDDEN');
  });
});
```

```js
// File: tests/integration/notes.routes.test.js
import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createHarness, registerUser, createNote } from '../support/harness.js';

describe('POST /api/v1/notes', () => {
  let harness;
  let auth;

  beforeEach(async () => {
    harness = createHarness();
    ({ auth } = await registerUser(harness.client()));
  });

  it('creates a note with 201, a Location header and an ETag', async () => {
    const response = await harness.client()
      .post('/api/v1/notes')
      .set('Authorization', auth)
      .send({ title: 'Shopping list', content: 'Buy milk', tags: ['Home', 'home'] })
      .expect(201);

    assert.equal(response.body.data.title, 'Shopping list');
    assert.deepEqual(response.body.data.tags, ['home'], 'tags are lowercased and de-duplicated');
    assert.equal(response.body.data.revision, 1);
    assert.equal(response.body.data.pinned, false);
    assert.equal(response.headers.location, `/api/v1/notes/${response.body.data.id}`);
    assert.match(response.headers.etag, /^W\/"note_2-1"$/);
  });

  it('rejects a payload with no title and an unknown field with 422', async () => {
    const response = await harness.client()
      .post('/api/v1/notes')
      .set('Authorization', auth)
      .send({ content: 'No title here', colour: 'red' })
      .expect(422);

    assert.equal(response.body.error.code, 'VALIDATION_ERROR');
    assert.ok(response.body.error.details.some((detail) => detail.field === 'title'));
  });

  it('refuses a duplicate title for the same author with 409', async () => {
    const client = harness.client();
    await createNote(client, auth, { title: 'Unique' });

    const response = await client
      .post('/api/v1/notes')
      .set('Authorization', auth)
      .send({ title: 'Unique', content: 'Twice' })
      .expect(409);

    assert.equal(response.body.error.details.field, 'title');
  });

  it('requires authentication', async () => {
    await harness.client().post('/api/v1/notes').send({ title: 'Anon', content: 'x' }).expect(401);
  });
});

describe('GET /api/v1/notes', () => {
  let harness;
  let auth;

  beforeEach(async () => {
    harness = createHarness();
    const client = harness.client();
    ({ auth } = await registerUser(client));

    await createNote(client, auth, { title: 'Node streams', content: 'Pipes and buffers', tags: ['node'] });
    await createNote(client, auth, { title: 'Express routing', content: 'Routers and params', tags: ['node', 'express'] });
    await createNote(client, auth, { title: 'Shopping list', content: 'Milk and bread', tags: ['home'] });
  });

  it('paginates and reports meta', async () => {
    const response = await harness.client()
      .get('/api/v1/notes?page=1&limit=2&sort=title')
      .set('Authorization', auth)
      .expect(200);

    assert.equal(response.body.data.length, 2);
    assert.deepEqual(response.body.meta, { page: 1, limit: 2, total: 3, pages: 2, hasNext: true });
    assert.deepEqual(response.body.data.map((note) => note.title), ['Express routing', 'Node streams']);
  });

  it('searches title and content', async () => {
    const response = await harness.client().get('/api/v1/notes?q=milk').set('Authorization', auth).expect(200);
    assert.deepEqual(response.body.data.map((note) => note.title), ['Shopping list']);
  });

  it('filters by tag', async () => {
    const response = await harness.client().get('/api/v1/notes?tag=express').set('Authorization', auth).expect(200);
    assert.deepEqual(response.body.data.map((note) => note.title), ['Express routing']);
  });

  it('rejects an unknown sort field and an oversized limit', async () => {
    await harness.client().get('/api/v1/notes?sort=password').set('Authorization', auth).expect(422);
    await harness.client().get('/api/v1/notes?limit=1000').set('Authorization', auth).expect(422);
  });

  it('never returns another user notes', async () => {
    const other = await registerUser(harness.client(), { email: 'grace@example.com', name: 'Grace' });
    const response = await harness.client().get('/api/v1/notes').set('Authorization', other.auth).expect(200);

    assert.deepEqual(response.body.data, []);
    assert.equal(response.body.meta.total, 0);
  });
});

describe('GET /api/v1/notes/:id', () => {
  it('answers 404 for an unknown id and 403 for someone else note', async () => {
    const harness = createHarness();
    const client = harness.client();
    const ada = await registerUser(client);
    const note = await createNote(client, ada.auth, { title: 'Ada private' });

    await client.get('/api/v1/notes/note_999').set('Authorization', ada.auth).expect(404);

    const grace = await registerUser(client, { email: 'grace@example.com', name: 'Grace' });
    const forbidden = await client.get(`/api/v1/notes/${note.id}`).set('Authorization', grace.auth).expect(403);
    assert.equal(forbidden.body.error.code, 'FORBIDDEN');
  });
});

describe('PATCH /api/v1/notes/:id', () => {
  it('updates fields, bumps the revision and enforces If-Match', async () => {
    const harness = createHarness();
    const client = harness.client();
    const { auth } = await registerUser(client);
    const note = await createNote(client, auth, { title: 'Draft' });

    const updated = await client
      .patch(`/api/v1/notes/${note.id}`)
      .set('Authorization', auth)
      .set('If-Match', `W/"${note.id}-1"`)
      .send({ title: 'Final', content: 'Ready to publish' })
      .expect(200);

    assert.equal(updated.body.data.title, 'Final');
    assert.equal(updated.body.data.revision, 2);

    // A stale ETag means someone else wrote in between: refuse instead of overwriting.
    const stale = await client
      .patch(`/api/v1/notes/${note.id}`)
      .set('Authorization', auth)
      .set('If-Match', `W/"${note.id}-1"`)
      .send({ content: 'Lost update' })
      .expect(412);

    assert.equal(stale.body.error.code, 'PRECONDITION_FAILED');
    assert.equal(stale.body.error.details.actual, 2);

    // An empty patch is meaningless: catch it in validation, not in the service.
    await client.patch(`/api/v1/notes/${note.id}`).set('Authorization', auth).send({}).expect(422);
  });
});

describe('pin, archive and delete', () => {
  it('pins, unpins, archives and deletes a note', async () => {
    const harness = createHarness();
    const client = harness.client();
    const { auth } = await registerUser(client);
    const note = await createNote(client, auth, { title: 'Lifecycle', tags: ['demo'] });

    const pinned = await client.post(`/api/v1/notes/${note.id}/pin`).set('Authorization', auth).expect(200);
    assert.equal(pinned.body.data.pinned, true);

    const pinnedOnly = await client.get('/api/v1/notes?pinned=true').set('Authorization', auth).expect(200);
    assert.equal(pinnedOnly.body.meta.total, 1);

    const unpinned = await client.delete(`/api/v1/notes/${note.id}/pin`).set('Authorization', auth).expect(200);
    assert.equal(unpinned.body.data.pinned, false);

    const archived = await client.post(`/api/v1/notes/${note.id}/archive`).set('Authorization', auth).expect(200);
    assert.equal(archived.body.data.archived, true);

    // Archived notes are hidden unless explicitly requested.
    assert.equal((await client.get('/api/v1/notes').set('Authorization', auth).expect(200)).body.meta.total, 0);
    assert.equal((await client.get('/api/v1/notes?archived=true').set('Authorization', auth).expect(200)).body.meta.total, 1);

    await client.delete(`/api/v1/notes/${note.id}`).set('Authorization', auth).expect(204);
    await client.get(`/api/v1/notes/${note.id}`).set('Authorization', auth).expect(404);
  });

  it('lists tags with counts', async () => {
    const harness = createHarness();
    const client = harness.client();
    const { auth } = await registerUser(client);

    await createNote(client, auth, { title: 'One', tags: ['node', 'api'] });
    await createNote(client, auth, { title: 'Two', tags: ['node'] });

    const response = await client.get('/api/v1/tags').set('Authorization', auth).expect(200);

    assert.deepEqual(response.body.data, [{ tag: 'node', count: 2 }, { tag: 'api', count: 1 }]);
  });
});

describe('method and route handling', () => {
  it('answers 405 with an Allow header for a known path with the wrong method', async () => {
    const harness = createHarness();
    const { auth } = await registerUser(harness.client());

    const response = await harness.client().put('/api/v1/notes').set('Authorization', auth).expect(405);

    assert.equal(response.body.error.code, 'METHOD_NOT_ALLOWED');
    assert.equal(response.headers.allow, 'GET, POST');
  });

  it('answers 404 with the error envelope for an unknown path', async () => {
    const harness = createHarness();

    const response = await harness.client().get('/api/v1/nope').expect(404);
    assert.equal(response.body.error.code, 'NOT_FOUND');
  });

  it('answers 400 for malformed JSON', async () => {
    const harness = createHarness();

    const response = await harness.client()
      .post('/api/v1/auth/login')
      .set('Content-Type', 'application/json')
      .send('{"email": ')
      .expect(400);

    assert.equal(response.body.error.code, 'INVALID_JSON');
  });
});
```

```text
$ npm test
ℹ tests 35
ℹ suites 16
ℹ pass 35
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 1950.013137
```

### 18.4 What the suite proves

| Group | Tests | Guarantee |
| --- | --- | --- |
| Registration | 3 | Cookies are `HttpOnly` and scoped; duplicates are `409`; every password rule is reported |
| Login | 2 | Unknown email and wrong password are indistinguishable; `expiresIn` is exposed |
| `GET /me` | 2 | No token and a garbage token are both `401`; no secret field leaks |
| Refresh | 2 | Rotation happens, replay is detected, CSRF is required |
| Logout | 1 | The cookie is cleared and the session is dead |
| RBAC | 1 | A `USER` cannot reach an `ADMIN` endpoint |
| Create a note | 4 | `201` + `Location` + `ETag`, tags normalised, `422` details, `409` duplicates, `401` without a token |
| List, search, filter | 5 | `meta` shape, two-field search, tag filter, `422` for bad query values, no cross-user leakage |
| Ownership | 1 | `404` for an unknown id, `403` for someone else's note |
| Update and concurrency | 1 | Partial update, revision bump, `412` with `details.actual` on a stale `If-Match` |
| Lifecycle | 2 | Pin/unpin/archive/delete, hidden-archive default, tag counts |
| Protocol | 3 | `405` + `Allow`, `404` envelope, `400` for malformed JSON |
| Service rules (unit) | 8 | Offset math, archive default, ownership, revisions — with no HTTP and no server at all |

Groups sum to the 35 tests reported above; the unit ones exist because a rule that only has an HTTP test
is a rule you cannot change quickly.

---

## 19. Line-by-line: the request path of `POST /api/v1/notes`

```text
curl -X POST /api/v1/notes -H 'Authorization: Bearer eyJ...' -d '{"title":"Middleware order","content":"..."}'
  │
  ├─ app.js: helmet()                  security headers queued on the response
  ├─ app.js: cors()                    Vary: Origin always; ACAO only for an allowlisted origin
  ├─ app.js: requestId                 req.id = inbound or new UUID; X-Request-Id set
  ├─ app.js: httpLogger                starts the pino child logger for this request
  ├─ app.js: express.json({limit})     parses the body. 100kb exceeded -> 413, bad JSON -> 400
  ├─ app.js: cookieParser              req.cookies and req.signedCookies available
  ├─ app.js: csrf issuer               no csrfSecret cookie yet? issue one
  ├─ routes/index.js                   mount /auth, /notes, /tags, /admin under /api/v1
  ├─ routes/noteRoutes.js              POST / -> validate(createNoteSchema) -> controller.create
  │    └─ middleware/validate.js       Zod parse. Failure -> 422 with every issue. Success ->
  │                                    req.validated.body = parsed, coerced, unknown keys stripped
  ├─ noteRoutes.js: router.use(...)    authenticate then requireAuth run BEFORE the route handler
  │    └─ middleware/auth.js           verifyAccessToken -> claims; findById -> the CURRENT user
  │                                    (deleted account or changed role takes effect immediately)
  ├─ controllers/noteController.js     noteService.create({ input: req.validated.body, actor: req.user })
  ├─ services/noteService.js           findByTitle() -> 409; create() -> repository
  ├─ repositories/inMemoryNoteRepository.js
  │                                    build the document, push to the Map, return a domain object
  ├─ controllers/noteController.js     201 + Location + ETag, body = { data: toNoteDto(note) }
  └─ app.js: httpLogger on finish      INFO POST /api/v1/notes -> 201 (durationMs, requestId, userId)
```

What each layer is *not* allowed to do:

| Layer | May do | Must never do |
| --- | --- | --- |
| Route | Choose middleware and handlers | Contain logic, touch data |
| Middleware | Inspect and annotate the request | Read or write domain data directly (it calls a service) |
| Controller | Map HTTP ⇄ service, set status and headers | Contain business rules, import a repository |
| Service | Decide, orchestrate, throw typed errors | Know about `req`, `res` or the storage engine |
| Repository | Query, filter, sort, map rows to domain objects | Decide permissions or business rules |
| DTO | Choose exactly which fields leave | Contain logic or I/O |

---

## 20. Common mistakes (and what this project does instead)

| Mistake | Symptom | Fix used here |
| --- | --- | --- |
| `app.listen()` inside `app.js` | Port collisions, `EADDRINUSE` in parallel tests | `createApp()` returns the app; `server.js` listens |
| Reading `process.env` in ten files | "Which config does this use?" | `config/env.js` validates once and exports a frozen object |
| `.strict()` on the env schema | Startup fails with `Unrecognized keys: PATH, HOME, …` | Unknown keys are ignored; only the declared ones are validated |
| Storing the refresh token in `localStorage` | Any XSS steals a 30-day session | `HttpOnly`, `SameSite=Strict`, signed cookie scoped to `/api/v1/auth` |
| Putting the access token in a cookie "to make it easier" | CSRF protection becomes mandatory on every route | Bearer header for the API, cookie only for the two refresh endpoints |
| `if (!req.body.title) return res.status(400)` | Ad-hoc validation, inconsistent errors, fields left unvalidated | One Zod schema per resource, `validate(schema, source)` |
| Passing `req` into a service | The service can never be called from a job or a CLI | Services take plain objects and `{ actor }` |
| `SELECT *`-style "return the whole object" | Internal fields (`passwordHash`) leak over the wire | `toUserDto`/`toNoteDto` are the only shapes that leave |
| Authorisation in the controller only | A new endpoint forgets the rule | Role checks in middleware, ownership in the service |
| `res.status(403)` for "not yours" when the resource is secret | Existence is revealed to strangers | `403` here (the caller is authenticated), `404` when the id is unknown |
| Trusting an inbound `X-Request-Id` blindly | Log injection, absurd header values | Length- and charset-validated before it is echoed or logged |
| One `Map` shared across `await` points without care | Interleaved requests mutate each other's data | The repository owns the store; services never touch it |
| Timers created without `unref()` | The process never exits on `SIGTERM` | `setInterval(...).unref()` and `clearInterval` in `close()` |
| Rate limiting only the login route | Credential stuffing over `/register` and expensive endpoints | A limiter per sensitive route plus a global cap |
| `Access-Control-Allow-Origin: *` with credentials | Browsers reject it; or worse, you reflect any origin | Explicit allowlist, `Vary: Origin`, and `credentials: true` |
| Catching errors with `res.status(500).json(...)` in every controller | Logging and envelope drift | One `errorHandler`, typed `AppError`s |
| A 405 handler *after* the 404 handler | Every 405 becomes a 404 | `methodNotAllowed` runs before `notFound`, inside the router |
| Returning `200` for `delete` | Clients cannot tell success from a no-op | `204` with no body |
| PATCH that replaces the whole document | Concurrent editors silently overwrite each other | Partial updates plus `If-Match`/`ETag` |
| A test suite that needs a database for a rule change | Slow, flaky, feared | Unit tests against a repository stub; HTTP tests against the app |

---

## Exercise 21.1 — Add a per-user summary endpoint

Add `GET /api/v1/notes/summary` that returns the caller's totals:

```json
{
  "data": { "total": 12, "pinned": 2, "archived": 3, "tags": ["api", "express", "node"] },
  "meta": { "cached": false }
}
```

Requirements:

1. `total`, `pinned` and `archived` count **only the caller's notes**; `tags` is the sorted, distinct list.
2. Implement it in the repository (`summaryFor(authorId)`), not by fetching every note into the controller.
3. Register it in the method allowlist so `POST /api/v1/notes/summary` returns `405` with `Allow: GET`.
4. Keep it out of the `:id` route's reach — `/notes/summary` must not be parsed as an id.
5. Add at least two tests: the happy path and the "other user's notes are not counted" case.

<details>
<summary>Solution</summary>

```js
// File: src/repositories/inMemoryNoteRepository.js (excerpt) — the returned object gains this method
export const noteRepositoryMethods = {
  /** One pass over the store: counting, not fetching. A SQL version is a single aggregate query. */
  async summaryFor(authorId) {
    let total = 0;
    let pinned = 0;
    let archived = 0;
    const tags = new Set();

    for (const note of notes.values()) {
      if (note.authorId !== authorId) continue;
      total += 1;
      if (note.pinned) pinned += 1;
      if (note.archived) archived += 1;
      for (const tag of note.tags) tags.add(tag);
    }

    return { total, pinned, archived, tags: [...tags].sort() };
  },
};
```

```js
// File: src/services/noteService.js (excerpt) — the returned object gains this method
export const noteServiceMethods = {
  async summary({ actor }) {
    // The service decides *whose* summary; the repository decides how to compute it.
    return noteRepository.summaryFor(actor.id);
  },
};
```

```js
// File: src/controllers/noteController.js (excerpt) — the returned object gains this method
export const noteControllerMethods = {
  async summary(req, res, next) {
    try {
      const summary = await noteService.summary({ actor: req.user });
      return res.json({ data: summary, meta: { cached: false } });
    } catch (error) { return next(error); }
  },
};
```

```js
// File: src/routes/noteRoutes.js (excerpt) — registration order is the whole point
export function registerNoteRoutes({ router, controller, middleware }) {
  router.use(middleware.authenticate, middleware.requireAuth);

  // BEFORE '/:id', or "summary" is captured as an id: Express matches in registration order,
  // and ':id' matches any single segment — including the literal word "summary".
  router.get('/summary', controller.summary);

  router.route('/:id')
    .get(validate(noteIdParamsSchema, 'params'), controller.getOne)
    .patch(validate(noteIdParamsSchema, 'params'), validate(updateNoteSchema), controller.update)
    .delete(validate(noteIdParamsSchema, 'params'), controller.remove);

  return router;
}
```

```js
// File: src/routes/index.js (excerpt) — one more entry in the method allowlist
export const API_ALLOWED_METHODS_EXCERPT = [
  { path: '/notes', methods: ['GET', 'POST'] },
  // Literal paths come BEFORE parameterised ones, exactly like the routes themselves.
  // Reversed, '/notes/:id' matches '/notes/summary' first and reports "Allow: GET, PATCH, DELETE".
  { path: '/notes/summary', methods: ['GET'] },
  { path: '/notes/:id', methods: ['GET', 'PATCH', 'DELETE'] },
];
```

```js
// File: tests/integration/notes.routes.test.js (added tests)
describe('GET /api/v1/notes/summary', () => {
  it("counts only the caller's notes", async () => {
    const harness = createHarness();
    const client = harness.client();
    const ada = await registerUser(client);

    await createNote(client, ada.auth, { title: 'One', tags: ['node', 'api'] });
    await createNote(client, ada.auth, { title: 'Two', tags: ['node'] });
    const third = await createNote(client, ada.auth, { title: 'Three', tags: [] });

    await client.post(`/api/v1/notes/${third.id}/pin`).set('Authorization', ada.auth).expect(200);
    await client.post(`/api/v1/notes/${third.id}/archive`).set('Authorization', ada.auth).expect(200);

    const grace = await registerUser(client, { email: 'grace@example.com', name: 'Grace' });
    await createNote(client, grace.auth, { title: 'Grace note', tags: ['grace'] });

    const response = await client.get('/api/v1/notes/summary').set('Authorization', ada.auth).expect(200);

    assert.deepEqual(response.body.data, { total: 3, pinned: 1, archived: 1, tags: ['api', 'node'] });
    assert.equal(response.body.meta.cached, false);
  });

  it('is not advertised for POST, and does not shadow the :id route', async () => {
    const harness = createHarness();
    const client = harness.client();
    const { auth } = await registerUser(client);

    const notAllowed = await client.post('/api/v1/notes/summary').set('Authorization', auth).expect(405);
    assert.equal(notAllowed.headers.allow, 'GET');

    const note = await createNote(client, auth, { title: 'Still reachable' });
    const byId = await client.get(`/api/v1/notes/${note.id}`).set('Authorization', auth).expect(200);
    assert.equal(byId.body.data.title, 'Still reachable');
  });
});
```

```text
$ npm test
ℹ tests 37
ℹ pass 37
ℹ fail 0
```

Order matters in **three** places now — routes, the method allowlist and the route table in your docs.
A literal path registered after a parameterised one is unreachable, and the 405 for it would be wrong.

**Review notes:** the tempting shortcut is `const notes = await noteRepository.list({...})` in the
controller and then counting in JavaScript. It works, and it is wrong for two reasons: it moves a data
question into the HTTP layer, and it fetches N rows to produce one number — with a database that is the
difference between a 2 ms aggregate and a 200 ms full scan on every dashboard load.

</details>

---

## Exercise 21.2 — Add cursor pagination next to offset pagination

`?page=3` is easy to build and easy to corrupt: insert a note while a client is paging and an item is
skipped or repeated. Add **cursor pagination** without removing offset pagination:

1. Offset mode keeps `page`, `pages` and `hasNext`, and **also** reports `meta.nextCursor`, so a client
   can switch to cursor mode half-way through.
2. `GET /api/v1/notes?cursor=<value>&limit=2` → the next page, strictly after that pair, with
   `meta.nextCursor` and no `page`/`pages`.
3. A malformed cursor is a `422` naming the `cursor` field.
4. `page` and `cursor` together is a `422` — two sources of truth is a bug waiting to happen.
5. Keep the default sortable order stable (`-createdAt`) and prove with a test that inserting a note in
   the middle does **not** make a cursor page skip an item.

<details>
<summary>Solution</summary>

```js
// File: src/validators/commonSchemas.js (changed) — the rule needs to know what the client sent
export const paginationQuery = {
  // No .default() here: a default makes "did the client send this?" unanswerable, and the
  // page-vs-cursor rule below needs to know exactly that. toOffset() applies the defaults instead.
  page: z.coerce.number().int().min(1).optional(),
  limit: z.coerce.number().int().min(1).max(PAGINATION.MAX_LIMIT).optional(),
};
```

```js
// File: src/utils/pagination.js (added helpers)
/** A cursor is an opaque string: the client must not parse or construct it. */
export function encodeCursor({ updatedAt, id }) {
  return Buffer.from(`${updatedAt}|${id}`, 'utf8').toString('base64url');
}

export function decodeCursor(cursor) {
  const [value, id] = Buffer.from(String(cursor), 'base64url').toString('utf8').split('|');
  if (!value || !id) return null;

  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return null;

  return { updatedAt: value, id, timestamp };
}
```

```js
// File: src/repositories/inMemoryNoteRepository.js (excerpt) — the returned object gains this method
export const noteRepositoryMethods = {
  async list({ authorId, offset = 0, limit = 20, sort, q, tag, pinned, archived, after }) {
    const { field, direction } = resolveSort(sort);
    const filtered = [...notes.values()].filter((note) => matches(note, { authorId, q, tag, pinned, archived }));

    filtered.sort(compare(field, direction));

    // Cursor mode: drop everything up to and including the cursor position, then take `limit`.
    const start = after
      ? filtered.findIndex((note) => note.updatedAt === after.updatedAt && note.id === after.id) + 1
      : offset;

    const page = filtered.slice(start, start + limit);
    const last = page.at(-1);

    return {
      items: page.map(toDomain),
      total: filtered.length,
      nextCursor: page.length === limit && last ? encodeCursor({ updatedAt: last.updatedAt, id: last.id }) : null,
    };
  },
};
```

```js
// File: src/validators/noteSchemas.js (query schema)
export const listNotesQuerySchema = z.object({
  ...paginationQuery,
  cursor: z.string().trim().min(1).max(256).optional(),
  // ...
}).strict()
  .refine((query) => !(query.cursor && query.page), 'use either page or cursor, not both');
```

```js
// File: src/middleware/validate.js (excerpt) — a 422 must name a field, even for a cross-field rule
export const toValidationDetails = ({ issues, source }) =>
  issues.map((issue) => ({
    field: issue.path.join('.') || (issue.code === 'custom' ? 'query' : source),
    message: issue.message,
    code: issue.code,
  }));
```

```js
// File: src/services/noteService.js (excerpt) — the returned object gains this method
export const noteServiceMethods = {
  async list({ actor, query }) {
    const { page, limit, offset } = toOffset({ page: query.page, limit: query.limit });

    const after = query.cursor ? decodeCursor(query.cursor) : null;
    if (query.cursor && !after) {
      throw new ValidationError('The cursor is not valid', { field: 'cursor', received: query.cursor });
    }

    const { items, total, nextCursor } = await noteRepository.list({
      authorId: actor.id,
      offset: after ? 0 : offset,
      after,
      limit,
      sort: query.sort,
      q: query.q,
      tag: query.tag,
      pinned: query.pinned,
      archived: query.archived ?? false,
    });

    // Two shapes, on purpose: a cursor response has no page numbers to report.
    return query.cursor
      ? { items, total, limit, nextCursor }
      : { items, total, page, limit, nextCursor };
  },
};
```

```js
// File: src/controllers/noteController.js (excerpt) — the returned object gains this method
export const noteControllerMethods = {
  async list(req, res, next) {
    try {
      const result = await noteService.list({ actor: req.user, query: req.validated.query });
      const meta = result.page === undefined
        ? { limit: result.limit, total: result.total, nextCursor: result.nextCursor }
        : {
            page: result.page,
            limit: result.limit,
            total: result.total,
            pages: Math.ceil(result.total / result.limit) || 0,
            hasNext: result.page * result.limit < result.total,
            nextCursor: result.nextCursor,
          };

      return res.json({ data: result.items.map(toNoteDto), meta });
    } catch (error) { return next(error); }
  },
};
```

Two existing assertions change with the new contract, and that is expected work, not a broken test:

```js
// File: tests/unit/noteService.test.js (changed assertion)
    assert.deepEqual(calls.list[0], {
      authorId: 'user_1',
      offset: 20,
      after: null,                 // the service now always tells the repository where to start
      limit: 10,
      // ...
    });
```

```js
// File: tests/integration/notes.routes.test.js (changed assertion)
    const { nextCursor, ...meta } = response.body.meta;
    assert.deepEqual(meta, { page: 1, limit: 2, total: 3, pages: 2, hasNext: true });
    assert.match(nextCursor, /^[A-Za-z0-9_-]+$/);   // opaque, but present while more rows exist
```

```js
// File: tests/integration/notes.routes.test.js (the test that matters)
it('does not skip an item when the list changes between cursor pages', async () => {
  const harness = createHarness();
  const client = harness.client();
  const { auth } = await registerUser(client);

  await createNote(client, auth, { title: 'A' });
  await createNote(client, auth, { title: 'B' });
  await createNote(client, auth, { title: 'C' });

  const first = await client.get('/api/v1/notes?limit=2').set('Authorization', auth).expect(200);
  assert.deepEqual(first.body.data.map((note) => note.title), ['C', 'B']);

  // A new note arrives while the client is paging: with ?page=2 this is where rows get skipped.
  await createNote(client, auth, { title: 'D' });

  const second = await client
    .get(`/api/v1/notes?limit=2&cursor=${first.body.meta.nextCursor}`)
    .set('Authorization', auth)
    .expect(200);

  assert.deepEqual(second.body.data.map((note) => note.title), ['A']);
  assert.equal(second.body.meta.nextCursor, null);

  await client.get('/api/v1/notes?cursor=!!!not-a-cursor').set('Authorization', auth).expect(422);
  await client.get('/api/v1/notes?page=1&cursor=abc').set('Authorization', auth).expect(422);
});
```

```text
$ npm test
ℹ tests 38
ℹ pass 38
ℹ fail 0
```

**Why both?** Offset pagination is what a UI needs ("page 3 of 12", jump to page 7). Cursor pagination is
what a feed or an export needs (stable, no duplicates, no skipped rows, and — with a database — `WHERE
(updated_at, id) > ($1, $2)` uses the index instead of scanning `OFFSET` rows).

</details>

---

## Exercise 21.3 — Swap the storage engine without touching the app

The promise of the repository layer is that storage is replaceable. Prove it: implement
`createJsonFileNoteRepository` that persists notes to `var/notes.json` (`node:fs/promises`), run the
**whole existing test suite** against it, and change exactly one line of production wiring.

Requirements:

1. The new repository must satisfy the same contract: `create`, `findById`, `findByTitle`, `update`,
   `remove`, `list`, `tagCounts`, `stats`, plus `summaryFor` if you solved 21.1.
2. Writes must be atomic (`write temp file → rename`), so a crash cannot leave a half-written file.
3. It must survive a restart: load the file at construction, write after every mutation.
4. No `.js` file under `src/services/`, `src/controllers/` or `src/routes/` may change.
5. Tests must use a temporary file (`node:fs` + `node:os`), never the developer's `var/notes.json`.

<details>
<summary>Solution</summary>

```js
// File: src/repositories/jsonFileNoteRepository.js
import { readFile, writeFile, rename, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { NOTE_SORTS } from '../config/constants.js';

/**
 * Same contract as the in-memory repository — this is the whole point of the exercise.
 * A real database repository differs in the queries, not in the interface the app sees.
 */
export function createJsonFileNoteRepository({ filePath, ids, clock, logger }) {
  let notes = new Map();
  let loaded = false;

  const toDomain = (note) => (note ? { ...note, tags: [...note.tags] } : null);
  const toStored = (note) => ({ ...note });

  async function load() {
    if (loaded) return;
    loaded = true;

    try {
      const raw = await readFile(filePath, 'utf8');
      notes = new Map(JSON.parse(raw).map((note) => [note.id, note]));
      logger?.debug({ filePath, notes: notes.size }, 'note store loaded');
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;         // a corrupt file must not be silently ignored
      notes = new Map();
    }
  }

  /** Atomic write: readers see either the old file or the new one, never a truncated one. */
  async function persist() {
    await mkdir(dirname(filePath), { recursive: true });
    const temporary = `${filePath}.${process.pid}.tmp`;

    await writeFile(temporary, JSON.stringify([...notes.values()], null, 2), 'utf8');
    await rename(temporary, filePath);                  // rename is atomic on the same filesystem
  }

  function matches(note, { authorId, q, tag, pinned, archived }) {
    if (note.authorId !== authorId) return false;
    if (archived === undefined ? note.archived : note.archived !== archived) return false;
    if (pinned !== undefined && note.pinned !== pinned) return false;
    if (tag && !note.tags.includes(tag.toLowerCase())) return false;

    if (q) {
      const needle = q.toLowerCase();
      if (!note.title.toLowerCase().includes(needle) && !note.content.toLowerCase().includes(needle)) return false;
    }

    return true;
  }

  function resolveSort(sort) {
    const raw = String(sort ?? '-createdAt');
    const direction = raw.startsWith('-') ? 'desc' : 'asc';
    return { field: NOTE_SORTS[raw.replace(/^-/, '')] ?? NOTE_SORTS.createdAt, direction };
  }

  function compare(field, direction) {
    return (a, b) => {
      const left = field === 'title' ? String(a.title).toLowerCase() : a[field];
      const right = field === 'title' ? String(b.title).toLowerCase() : b[field];
      let result = left < right ? -1 : left > right ? 1 : 0;
      if (result === 0) result = a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
      return direction === 'desc' ? -result : result;
    };
  }

  return {
    async create({ title, content, tags = [], authorId }) {
      await load();
      const now = clock.isoNow();
      const note = {
        id: ids('note'),
        title: title.trim(),
        content: content.trim(),
        tags: [...new Set(tags.map((tag) => tag.trim().toLowerCase()).filter(Boolean))],
        pinned: false,
        archived: false,
        revision: 1,
        authorId,
        createdAt: now,
        updatedAt: now,
      };

      notes.set(note.id, note);
      await persist();
      return toDomain(note);
    },

    async findById(id) {
      await load();
      return toDomain(notes.get(id) ?? null);
    },

    async findByTitle(title, authorId) {
      await load();
      const needle = title.trim().toLowerCase();
      for (const note of notes.values()) {
        if (note.authorId === authorId && note.title.toLowerCase() === needle) return toDomain(note);
      }
      return null;
    },

    async update(id, patch) {
      await load();
      const note = notes.get(id);
      if (!note) return null;

      for (const key of ['title', 'content', 'tags', 'pinned', 'archived']) {
        if (patch[key] !== undefined) note[key] = patch[key];
      }
      if (patch.tags) note.tags = [...new Set(patch.tags.map((tag) => tag.trim().toLowerCase()).filter(Boolean))];

      note.revision += 1;
      note.updatedAt = clock.isoNow();
      await persist();
      return toDomain(note);
    },

    async remove(id) {
      await load();
      const removed = notes.delete(id);
      if (removed) await persist();
      return removed;
    },

    async list({ authorId, offset = 0, limit = 20, sort, q, tag, pinned, archived }) {
      await load();
      const { field, direction } = resolveSort(sort);
      const filtered = [...notes.values()].filter((note) => matches(note, { authorId, q, tag, pinned, archived }));

      filtered.sort(compare(field, direction));
      if (!sort) filtered.sort((a, b) => Number(b.pinned) - Number(a.pinned));

      return { items: filtered.slice(offset, offset + limit).map(toDomain), total: filtered.length };
    },

    async tagCounts(authorId) {
      await load();
      const counts = new Map();
      for (const note of notes.values()) {
        if (note.authorId !== authorId) continue;
        for (const tag of note.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
      }
      return [...counts.entries()].map(([tag, count]) => ({ tag, count })).sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
    },

    async stats() {
      await load();
      const all = [...notes.values()];
      return {
        notes: all.length,
        pinned: all.filter((note) => note.pinned).length,
        archived: all.filter((note) => note.archived).length,
        tags: new Set(all.flatMap((note) => note.tags)).size,
      };
    },

    async summaryFor(authorId) {
      await load();
      let total = 0;
      let pinned = 0;
      let archived = 0;
      const tags = new Set();

      for (const note of notes.values()) {
        if (note.authorId !== authorId) continue;
        total += 1;
        if (note.pinned) pinned += 1;
        if (note.archived) archived += 1;
        for (const tag of note.tags) tags.add(tag);
      }

      return { total, pinned, archived, tags: [...tags].sort() };
    },

    /** Used by tests to inspect what was actually written. */
    async persistNow() {
      await load();
      await persist();
    },
  };
}
```

```js
// File: src/container.js — the one line that changes
import { createJsonFileNoteRepository } from './repositories/jsonFileNoteRepository.js';

  // before: const noteRepository = overrides.noteRepository ?? createInMemoryNoteRepository({ ids, clock });
  const noteRepository = overrides.noteRepository ?? createJsonFileNoteRepository({
    filePath: config.NOTES_FILE ?? 'var/notes.json',
    ids,
    clock,
    logger,
  });
```

```js
// File: tests/support/fileHarness.js — a new file, not a change to the existing harness
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createClock } from '../../src/utils/clock.js';
import { createCountingIdFactory } from '../../src/utils/ids.js';
import { createJsonFileNoteRepository } from '../../src/repositories/jsonFileNoteRepository.js';
import { createHarness, FROZEN_TIME } from './harness.js';

/**
 * The same application with one dependency replaced. Every route test could run against this harness
 * unchanged — that is the repository contract doing its job.
 */
export async function createFileHarness() {
  const tempDirectory = await mkdtemp(join(tmpdir(), 'notes-api-'));
  const clock = createClock({ now: () => new Date(FROZEN_TIME) });
  const ids = createCountingIdFactory();

  const noteRepository = createJsonFileNoteRepository({
    filePath: join(tempDirectory, 'notes.json'),
    ids,
    clock,
  });

  return { ...createHarness({ overrides: { clock, ids, noteRepository } }), tempDirectory };
}
```

```js
// File: tests/integration/jsonFilePersistence.test.js
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { createFileHarness } from '../support/fileHarness.js';
import { registerUser, createNote } from '../support/harness.js';

describe('json file repository', () => {
  it('persists a note to disk and reads it back through the API', async () => {
    const harness = await createFileHarness();
    const client = harness.client();
    const { auth } = await registerUser(client);

    const note = await createNote(client, auth, { title: 'Durable', tags: ['fs'] });
    await harness.container.noteRepository.persistNow();

    const onDisk = JSON.parse(await readFile(join(harness.tempDirectory, 'notes.json'), 'utf8'));
    assert.equal(onDisk.length, 1);
    assert.equal(onDisk[0].title, 'Durable');

    const fetched = await client.get(`/api/v1/notes/${note.id}`).set('Authorization', auth).expect(200);
    assert.equal(fetched.body.data.tags[0], 'fs');
  });
});
```

```text
$ npm test
ℹ tests 39
ℹ suites 19
ℹ pass 39
ℹ fail 0

$ grep -rE "inMemory|jsonFile" src/services src/controllers src/routes
(no output — the application layer does not know which store is in use)
```

**The lesson.** Swapping storage was a one-line change in `container.js` plus a new file. That is what
`repositories/` buys you, and it is exactly what the next section does for real: `03-databases/` adds a
MongoDB repository and a SQL repository, and the controllers, services, routes, validators and tests in
this chapter stay as they are.

</details>

---

## 21. What's next

You now have a complete, tested, documented Express API whose only missing piece is durability.

```text
03-databases/01-database-fundamentals   what a database guarantees that a Map cannot
03-databases/02-mongodb                  the same repositories, backed by MongoDB + Mongoose
03-databases/03-mysql                    the same repositories, backed by MySQL
03-databases/04-postgresql               transactions, constraints, indexes
03-databases/05-redis                    sessions, rate-limit stores, caching
04-authentication/                       password hashing, JWT, OAuth, RBAC in depth
05-testing/                              Jest, Vitest, Supertest, mocking, test databases
06-docker/ & 07-deployment/              package and ship exactly what you just built
08-projects/                             five progressive applications, including the production one
```

→ 03-databases/01-database-fundamentals/01-database-basics.md *(not available in this published source revision)*
