# 18 — Project: A CRUD API with Node.js Only

> **Where this fits:** This is the section project. Everything from chapters 01–17 comes together in a real, runnable API built with **no frameworks and no dependencies** — routing, middleware, validation, error handling, persistence, tests and graceful shutdown, all hand-written. Then we measure exactly what Express will save us, which is the entire justification for the next section.

***

## 1. What we are building

A **notes API** with:

| Method   | Path                | Purpose                                                  |
| -------- | ------------------- | -------------------------------------------------------- |
| `GET`    | `/health`           | Liveness check                                           |
| `GET`    | `/api/v1/notes`     | List notes (filter by `tag`, search `q`, paginate, sort) |
| `GET`    | `/api/v1/notes/:id` | Fetch one note                                           |
| `POST`   | `/api/v1/notes`     | Create a note                                            |
| `PATCH`  | `/api/v1/notes/:id` | Partially update a note                                  |
| `DELETE` | `/api/v1/notes/:id` | Delete a note                                            |

Plus: request logging with request ids, validation with field-level errors, a consistent error contract, a JSON-file repository with atomic writes, and tests using Node's built-in test runner.

**Constraints (deliberate, to teach the mechanics):** no Express, no body-parser, no validation library, no logging library. Only Node's standard library. Every line exists for a reason you have already seen.

***

## 2. Project structure

```
notes-api/
├── package.json
├── .gitignore
├── .env.example
├── data/                              ← created at runtime, gitignored
│   └── notes.json
├── src/
│   ├── server.js                      ← entry point: starts, handles signals
│   ├── app.js                         ← builds the request handler (testable, no listen)
│   ├── config/
│   │   └── env.js                     ← validated configuration
│   ├── lib/
│   │   ├── http.js                    ← sendJson, readJson, notFound, HttpError
│   │   └── router.js                  ← method+path matching with :params
│   ├── middleware/
│   │   ├── requestContext.js          ← request id + timing
│   │   └── logger.js                  ← structured request logging
│   ├── repositories/
│   │   └── noteRepository.js          ← JSON-file persistence (atomic + serialised)
│   ├── services/
│   │   └── noteService.js             ← business rules
│   ├── validators/
│   │   └── noteSchemas.js             ← hand-written validation (no library)
│   └── routes/
│       └── noteRoutes.js              ← route wiring
└── tests/
    └── notes.test.js                  ← node:test integration tests
```

The layering matters, and it is the same layering Express will use: **route → controller(handler) → service → repository.**

***

## 3. Setup

```bash
mkdir notes-api && cd notes-api
npm init -y
npm pkg set type=module
npm pkg set engines.node=">=22.0.0"
npm pkg set scripts.start="node src/server.js"
npm pkg set scripts.dev="node --watch --env-file-if-exists=.env src/server.js"
npm pkg set scripts.test="node --test tests/"
```

```bash
# .gitignore
node_modules/
data/
.env
*.log
```

```bash
# .env.example
NODE_ENV=development
PORT=3000
HOST=0.0.0.0
LOG_LEVEL=debug
DATA_FILE=./data/notes.json
```

***

## 4. Configuration

```js
// File: src/config/env.js
/**
 * Read and validate configuration once, at startup.
 * Any problem here must stop the process before it accepts a single request.
 */
function readInt(name, fallback, { min, max } = {}) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value)) throw new Error(`${name} must be an integer, received "${raw}"`);
  if (min !== undefined && value < min) throw new Error(`${name} must be >= ${min}`);
  if (max !== undefined && value > max) throw new Error(`${name} must be <= ${max}`);
  return value;
}

function readEnum(name, allowed, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return fallback;
  if (!allowed.includes(raw)) {
    throw new Error(`${name} must be one of ${allowed.join(' | ')}, received "${raw}"`);
  }
  return raw;
}

function readString(name, fallback) {
  const raw = process.env[name];
  return raw === undefined || raw === '' ? fallback : raw;
}

export const env = Object.freeze({
  nodeEnv: readEnum('NODE_ENV', ['development', 'test', 'production'], 'development'),
  host: readString('HOST', '0.0.0.0'),
  port: readInt('PORT', 3000, { min: 0, max: 65535 }),
  logLevel: readEnum('LOG_LEVEL', ['debug', 'info', 'warn', 'error'], 'info'),
  dataFile: readString('DATA_FILE', './data/notes.json'),
  bodyLimitBytes: readInt('BODY_LIMIT_BYTES', 100_000, { min: 1024 }),
});

// Derived flags — computed once so the rest of the app never reads process.env directly.
env.isProduction = env.nodeEnv === 'production';
env.isTest = env.nodeEnv === 'test';
```

***

## 5. HTTP helpers

```js
// File: src/lib/http.js
/**
 * Small helpers that every HTTP server needs. Express provides equivalents
 * (res.json, express.json, next(error)) — here we write them by hand.
 */

/** An error that carries an HTTP status and a machine-readable code. */
export class HttpError extends Error {
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

export class ValidationError extends HttpError {
  constructor(details, message = 'Request validation failed') {
    super(message, { statusCode: 422, code: 'VALIDATION_ERROR', details });
  }
}

export class NotFoundError extends HttpError {
  constructor(message = 'Resource not found') {
    super(message, { statusCode: 404, code: 'NOT_FOUND' });
  }
}

export class BadRequestError extends HttpError {
  constructor(message, code = 'BAD_REQUEST') {
    super(message, { statusCode: 400, code });
  }
}

/** Send a JSON response with the correct Content-Type and Content-Length. */
export function sendJson(res, status, payload, headers = {}) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),   // enables keep-alive without chunking
    ...headers,
  });
  res.end(body);
}

/**
 * Read and parse a JSON request body.
 * Handles: size limits, correct content type, malformed JSON, client disconnects.
 */
export function readJson(req, { limitBytes = 100_000 } = {}) {
  return new Promise((resolve, reject) => {
    const contentType = (req.headers['content-type'] ?? '').split(';')[0].trim().toLowerCase();

    if (contentType !== 'application/json') {
      reject(
        new HttpError(`Content-Type must be application/json, received "${contentType || 'none'}"`, {
          statusCode: 415,
          code: 'UNSUPPORTED_MEDIA_TYPE',
        })
      );
      return;
    }

    const chunks = [];
    let size = 0;

    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > limitBytes) {
        req.destroy();
        reject(
          new HttpError(`Request body exceeds ${limitBytes} bytes`, {
            statusCode: 413,
            code: 'PAYLOAD_TOO_LARGE',
          })
        );
        return;
      }
      chunks.push(chunk);
    });

    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8');
      if (raw.trim() === '') {
        reject(new BadRequestError('Request body must not be empty', 'EMPTY_BODY'));
        return;
      }
      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(new BadRequestError(`Request body is not valid JSON: ${error.message}`, 'INVALID_JSON'));
      }
    });

    req.on('error', reject);
    req.on('aborted', () => reject(new BadRequestError('Client aborted the request', 'REQUEST_ABORTED')));
  });
}

/** ISO 8601 UTC string — the only sane date format for an API. */
export const nowIso = () => new Date().toISOString();
```

***

## 6. The router

```js
// File: src/lib/router.js
/**
 * A method+path router with :params, built from scratch.
 * This is the file Express replaces entirely (`app.get('/notes/:id', handler)`).
 */
export function createRouter() {
  const routes = [];

  const register = (method) => (pattern, handler) => {
    routes.push({
      method,
      segments: pattern.split('/').filter(Boolean),
      handler,
    });
  };

  return {
    get: register('GET'),
    post: register('POST'),
    patch: register('PATCH'),
    put: register('PUT'),
    delete: register('DELETE'),
    options: register('OPTIONS'),

    /** Returns { handler, params } or null. */
    match(method, pathname) {
      const parts = pathname.split('/').filter(Boolean);

      for (const route of routes) {
        if (route.method !== method) continue;
        if (route.segments.length !== parts.length) continue;

        const params = {};
        let matched = true;

        for (let index = 0; index < route.segments.length; index += 1) {
          const segment = route.segments[index];
          if (segment.startsWith(':')) {
            params[segment.slice(1)] = decodeURIComponent(parts[index]);
          } else if (segment !== parts[index]) {
            matched = false;
            break;
          }
        }

        if (matched) return { handler: route.handler, params };
      }

      return null;
    },

    /** Which methods are allowed for this path — used to produce a correct 405. */
    allowedMethods(pathname) {
      const parts = pathname.split('/').filter(Boolean);
      return [...new Set(
        routes
          .filter((route) => {
            if (route.segments.length !== parts.length) return false;
            return route.segments.every((segment, index) =>
              segment.startsWith(':') ? true : segment === parts[index]
            );
          })
          .map((route) => route.method)
      )];
    },
  };
}
```

***

## 7. Persistence

```js
// File: src/repositories/noteRepository.js
import { readFile, writeFile, rename, mkdir } from 'node:fs/promises';
import path from 'node:path';

/**
 * JSON-file persistence with three properties that matter:
 *   1. Atomic writes (temp file + rename) — a crash cannot corrupt the store.
 *   2. Serialised writes — concurrent requests cannot lose each other's updates.
 *   3. In-process cache — reads do not hit the disk repeatedly.
 *
 * This is the layer that a database will replace, with no change above it.
 */
export function createNoteRepository({ filePath, logger }) {
  let cache = null;
  let writeChain = Promise.resolve();

  async function load() {
    if (cache !== null) return cache;
    try {
      const raw = await readFile(filePath, 'utf8');
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) throw new Error('Store must contain a JSON array');
      cache = parsed;
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
      cache = [];
      await mkdir(path.dirname(filePath), { recursive: true });
      await persist();
    }
    return cache;
  }

  function persist() {
    writeChain = writeChain.then(async () => {
      const tempPath = `${filePath}.${process.pid}.tmp`;
      await writeFile(tempPath, `${JSON.stringify(cache, null, 2)}\n`, 'utf8');
      await rename(tempPath, filePath);
    });
    return writeChain;
  }

  const clone = (value) => (value === null || value === undefined ? value : structuredClone(value));

  return {
    /** List with filtering, sorting and pagination — the shape a DB query would take. */
    async list({ tag, q, sort = '-createdAt', page = 1, limit = 20 } = {}) {
      const notes = await load();

      let filtered = notes;
      if (tag) filtered = filtered.filter((note) => note.tags?.includes(tag));
      if (q) {
        const needle = q.toLowerCase();
        filtered = filtered.filter(
          (note) =>
            note.title.toLowerCase().includes(needle) ||
            note.content.toLowerCase().includes(needle)
        );
      }

      const comparators = {
        createdAt: (a, b) => a.createdAt.localeCompare(b.createdAt),
        '-createdAt': (a, b) => b.createdAt.localeCompare(a.createdAt),
        title: (a, b) => a.title.localeCompare(b.title),
        '-title': (a, b) => b.title.localeCompare(a.title),
      };
      const sorted = [...filtered].sort(comparators[sort] ?? comparators['-createdAt']);

      const offset = (page - 1) * limit;
      return {
        items: sorted.slice(offset, offset + limit).map(clone),
        total: sorted.length,
      };
    },

    async findById(id) {
      const notes = await load();
      return clone(notes.find((note) => note.id === id) ?? null);
    },

    async create(note) {
      const notes = await load();
      notes.push(note);
      await persist();
      return clone(note);
    },

    async update(id, patch) {
      const notes = await load();
      const index = notes.findIndex((note) => note.id === id);
      if (index === -1) return null;

      notes[index] = {
        ...notes[index],
        ...patch,
        id: notes[index].id,                 // id is immutable
        createdAt: notes[index].createdAt,   // createdAt is immutable
        updatedAt: new Date().toISOString(),
      };

      await persist();
      logger.debug('note updated', { id });
      return clone(notes[index]);
    },

    async remove(id) {
      const notes = await load();
      const index = notes.findIndex((note) => note.id === id);
      if (index === -1) return false;
      notes.splice(index, 1);
      await persist();
      return true;
    },
  };
}
```

***

## 8. Validation (hand-written, on purpose)

```js
// File: src/validators/noteSchemas.js
import { ValidationError } from '../lib/http.js';

/**
 * Hand-written validation so you can see what schema libraries do for you.
 * Every validator returns { value, errors } — never throws for bad input.
 */

const MAX_TITLE = 200;
const MAX_CONTENT = 10_000;
const MAX_TAGS = 10;

export function validateCreateNote(input) {
  const errors = [];
  const value = {};

  if (input === null || typeof input !== 'object' || Array.isArray(input)) {
    return { errors: [{ field: 'body', message: 'must be a JSON object' }], value: null };
  }

  // title: required, non-empty string, length-bounded
  if (typeof input.title !== 'string' || input.title.trim().length === 0) {
    errors.push({ field: 'title', message: 'is required and must be a non-empty string' });
  } else if (input.title.trim().length > MAX_TITLE) {
    errors.push({ field: 'title', message: `must be at most ${MAX_TITLE} characters` });
  } else {
    value.title = input.title.trim();
  }

  // content: required string
  if (typeof input.content !== 'string' || input.content.trim().length === 0) {
    errors.push({ field: 'content', message: 'is required and must be a non-empty string' });
  } else if (input.content.length > MAX_CONTENT) {
    errors.push({ field: 'content', message: `must be at most ${MAX_CONTENT} characters` });
  } else {
    value.content = input.content;
  }

  // tags: optional array of short lowercase strings
  if (input.tags !== undefined) {
    if (!Array.isArray(input.tags)) {
      errors.push({ field: 'tags', message: 'must be an array of strings' });
    } else if (input.tags.length > MAX_TAGS) {
      errors.push({ field: 'tags', message: `must contain at most ${MAX_TAGS} items` });
    } else if (input.tags.some((tag) => typeof tag !== 'string' || tag.trim().length === 0)) {
      errors.push({ field: 'tags', message: 'must contain only non-empty strings' });
    } else {
      value.tags = [...new Set(input.tags.map((tag) => tag.trim().toLowerCase()))];
    }
  } else {
    value.tags = [];
  }

  // pinned: optional boolean
  if (input.pinned !== undefined) {
    if (typeof input.pinned !== 'boolean') {
      errors.push({ field: 'pinned', message: 'must be a boolean' });
    } else {
      value.pinned = input.pinned;
    }
  } else {
    value.pinned = false;
  }

  // Unknown keys are REJECTED, not ignored: a typo'd field is a client bug worth reporting.
  const allowed = new Set(['title', 'content', 'tags', 'pinned']);
  for (const key of Object.keys(input)) {
    if (!allowed.has(key)) errors.push({ field: key, message: 'is not a supported field' });
  }

  return { value: errors.length === 0 ? value : null, errors };
}

export function validateUpdateNote(input) {
  const errors = [];

  if (input === null || typeof input !== 'object' || Array.isArray(input)) {
    return { errors: [{ field: 'body', message: 'must be a JSON object' }], value: null };
  }

  const value = {};
  const allowed = new Set(['title', 'content', 'tags', 'pinned']);

  for (const key of Object.keys(input)) {
    if (!allowed.has(key)) errors.push({ field: key, message: 'is not a supported field' });
  }

  // PATCH semantics: only fields that are PRESENT are applied.
  if (Object.hasOwn(input, 'title')) {
    if (typeof input.title !== 'string' || input.title.trim().length === 0) {
      errors.push({ field: 'title', message: 'must be a non-empty string' });
    } else if (input.title.trim().length > MAX_TITLE) {
      errors.push({ field: 'title', message: `must be at most ${MAX_TITLE} characters` });
    } else {
      value.title = input.title.trim();
    }
  }

  if (Object.hasOwn(input, 'content')) {
    if (typeof input.content !== 'string' || input.content.trim().length === 0) {
      errors.push({ field: 'content', message: 'must be a non-empty string' });
    } else if (input.content.length > MAX_CONTENT) {
      errors.push({ field: 'content', message: `must be at most ${MAX_CONTENT} characters` });
    } else {
      value.content = input.content;
    }
  }

  if (Object.hasOwn(input, 'tags')) {
    if (!Array.isArray(input.tags) || input.tags.some((tag) => typeof tag !== 'string')) {
      errors.push({ field: 'tags', message: 'must be an array of strings' });
    } else {
      value.tags = [...new Set(input.tags.map((tag) => tag.trim().toLowerCase()))].slice(0, MAX_TAGS);
    }
  }

  if (Object.hasOwn(input, 'pinned')) {
    if (typeof input.pinned !== 'boolean') errors.push({ field: 'pinned', message: 'must be a boolean' });
    else value.pinned = input.pinned;
  }

  if (errors.length === 0 && Object.keys(value).length === 0) {
    errors.push({ field: 'body', message: 'must contain at least one field to update' });
  }

  return { value: errors.length === 0 ? value : null, errors };
}

export function validateListQuery(searchParams) {
  const errors = [];
  const allowed = new Set(['tag', 'q', 'sort', 'page', 'limit']);

  for (const key of searchParams.keys()) {
    if (!allowed.has(key)) errors.push({ field: key, message: 'is not a supported query parameter' });
  }

  const parsePositiveInt = (name, fallback, max) => {
    const raw = searchParams.get(name);
    if (raw === null) return fallback;
    const value = Number(raw);
    if (!Number.isInteger(value) || value < 1) {
      errors.push({ field: name, message: 'must be a positive integer' });
      return fallback;
    }
    if (max !== undefined && value > max) {
      errors.push({ field: name, message: `must be at most ${max}` });
      return fallback;
    }
    return value;
  };

  const sorts = new Set(['createdAt', '-createdAt', 'title', '-title']);
  const sort = searchParams.get('sort') ?? '-createdAt';
  if (!sorts.has(sort)) {
    errors.push({ field: 'sort', message: `must be one of ${[...sorts].join(', ')}` });
  }

  const value = {
    tag: searchParams.get('tag') ?? undefined,
    q: searchParams.get('q')?.trim() || undefined,
    sort: sorts.has(sort) ? sort : '-createdAt',
    page: parsePositiveInt('page', 1),
    limit: parsePositiveInt('limit', 20, 100),   // ← always cap the page size
  };

  return { value: errors.length === 0 ? value : null, errors };
}

/** Throw a ValidationError (for use in handlers) — keeps handler code tidy. */
export function assertValid({ errors }) {
  if (errors.length > 0) throw new ValidationError(errors);
}
```

***

## 9. Service layer

```js
// File: src/services/noteService.js
import { randomUUID } from 'node:crypto';
import { NotFoundError } from '../lib/http.js';

/**
 * Business rules live here — not in the HTTP layer, not in the repository.
 * Rules in this service:
 *   - A note's id and createdAt never change.
 *   - A deleted note is gone for good (no soft delete in this project).
 *   - Listing caps the page size at 100 (enforced in validation, re-asserted here).
 */
export function createNoteService({ repository, logger }) {
  const MAX_LIMIT = 100;

  return {
    async list(query) {
      const limit = Math.min(query.limit ?? 20, MAX_LIMIT);
      const { items, total } = await repository.list({ ...query, limit });
      const page = query.page ?? 1;

      return {
        items: items.map(toNoteDto),
        meta: {
          page,
          limit,
          total,
          totalPages: Math.max(1, Math.ceil(total / limit)),
          hasNext: page * limit < total,
        },
      };
    },

    async getById(id) {
      const note = await repository.findById(id);
      if (!note) throw new NotFoundError(`Note ${id} not found`);
      return toNoteDto(note);
    },

    async create(input) {
      const now = new Date().toISOString();
      const note = {
        id: randomUUID(),
        title: input.title,
        content: input.content,
        tags: input.tags ?? [],
        pinned: input.pinned ?? false,
        createdAt: now,
        updatedAt: now,
      };

      const created = await repository.create(note);
      logger.info('note created', { id: created.id, title: created.title });
      return toNoteDto(created);
    },

    async update(id, patch) {
      const updated = await repository.update(id, patch);
      if (!updated) throw new NotFoundError(`Note ${id} not found`);
      logger.info('note updated', { id, fields: Object.keys(patch) });
      return toNoteDto(updated);
    },

    async remove(id) {
      const removed = await repository.remove(id);
      if (!removed) throw new NotFoundError(`Note ${id} not found`);
      logger.info('note deleted', { id });
      return { id };
    },
  };
}

/** Never leak repository internals to clients: an explicit DTO is the contract. */
function toNoteDto(note) {
  return {
    id: note.id,
    title: note.title,
    content: note.content,
    tags: note.tags,
    pinned: note.pinned,
    createdAt: note.createdAt,
    updatedAt: note.updatedAt,
  };
}
```

***

## 10. Routes and middleware

```js
// File: src/routes/noteRoutes.js
import { readJson, sendJson, NotFoundError } from '../lib/http.js';
import {
  validateCreateNote,
  validateUpdateNote,
  validateListQuery,
  assertValid,
} from '../validators/noteSchemas.js';

/** Route definitions for /api/v1/notes — the same shape Express will use. */
export function registerNoteRoutes(router, { noteService, config }) {
  const base = '/api/v1/notes';

  // List
  router.get(base, async (req, res, ctx) => {
    const validated = validateListQuery(ctx.url.searchParams);
    assertValid(validated);
    const { items, meta } = await noteService.list(validated.value);
    sendJson(res, 200, { data: items, meta });
  });

  // Read one
  router.get(`${base}/:id`, async (req, res, ctx) => {
    const note = await noteService.getById(ctx.params.id);
    sendJson(res, 200, { data: note });
  });

  // Create
  router.post(base, async (req, res, _ctx) => {
    const body = await readJson(req, { limitBytes: config.bodyLimitBytes });
    const validated = validateCreateNote(body);
    assertValid(validated);

    const note = await noteService.create(validated.value);
    sendJson(res, 201, { data: note }, { Location: `${base}/${note.id}` });
  });

  // Partial update
  router.patch(`${base}/:id`, async (req, res, ctx) => {
    const body = await readJson(req, { limitBytes: config.bodyLimitBytes });
    const validated = validateUpdateNote(body);
    assertValid(validated);

    const note = await noteService.update(ctx.params.id, validated.value);
    sendJson(res, 200, { data: note });
  });

  // Delete
  router.delete(`${base}/:id`, async (req, res, ctx) => {
    const result = await noteService.remove(ctx.params.id);
    sendJson(res, 200, { data: result });
  });

  // A route that always 404s, purely to demonstrate the error path:
  router.get(`${base}/:id/raw`, async () => {
    throw new NotFoundError('Raw note export is not implemented yet');
  });
}
```

```js
// File: src/middleware/logger.js
const LEVELS = { error: 50, warn: 40, info: 30, debug: 20 };

/** Structured logger with child loggers — the minimum for debugging production. */
export function createLogger({ level = 'info', base = {} } = {}) {
  const threshold = LEVELS[level] ?? LEVELS.info;

  const write = (name, message, context = {}) => {
    if (LEVELS[name] < threshold) return;
    const line = `${JSON.stringify({ level: name, time: new Date().toISOString(), message, ...base, ...context })}\n`;
    (name === 'error' || name === 'warn' ? process.stderr : process.stdout).write(line);
  };

  return {
    error: (message, context) => write('error', message, context),
    warn: (message, context) => write('warn', message, context),
    info: (message, context) => write('info', message, context),
    debug: (message, context) => write('debug', message, context),
    child: (childBase) => createLogger({ level, base: { ...base, ...childBase } }),
  };
}

/** Attach a request id and a start time to every request. */
export function createRequestContext({ logger }) {
  return function requestContext(req, res, ctx) {
    ctx.requestId = crypto.randomUUID();
    ctx.startedAt = process.hrtime.bigint();
    ctx.log = logger.child({ requestId: ctx.requestId });

    res.setHeader('X-Request-Id', ctx.requestId);
    return ctx;
  };
}

/** Log one line per completed request — the raw material for all later debugging. */
export function logRequest(req, res, ctx, { statusCode }) {
  const durationMs = Number(process.hrtime.bigint() - ctx.startedAt) / 1e6;

  ctx.log.info('request completed', {
    method: req.method,
    path: ctx.url.pathname,
    query: Object.fromEntries(ctx.url.searchParams),
    status: statusCode,
    durationMs: Number(durationMs.toFixed(2)),
    userAgent: req.headers['user-agent'],
  });
}
```

***

## 11. The app (no `listen` — so it can be tested)

```js
// File: src/app.js
import { createServer } from 'node:http';
import path from 'node:path';
import { createRouter } from './lib/router.js';
import { createNoteRepository } from './repositories/noteRepository.js';
import { createNoteService } from './services/noteService.js';
import { registerNoteRoutes } from './routes/noteRoutes.js';
import { createLogger, createRequestContext, logRequest } from './middleware/logger.js';
import { sendJson, HttpError } from './lib/http.js';

/**
 * Build the HTTP handler without starting it.
 * Tests import this and call `server.listen(0)` — the essential testability pattern.
 */
export function createApp({ config, logger = createLogger({ level: config.logLevel }) }) {
  const repository = createNoteRepository({
    filePath: path.resolve(config.dataFile),
    logger,
  });

  const noteService = createNoteService({ repository, logger });
  const router = createRouter();

  // --- routes -----------------------------------------------------------------
  router.get('/health', async (req, res) => {
    sendJson(res, 200, { status: 'ok', uptimeSeconds: Number(process.uptime().toFixed(1)) });
  });

  registerNoteRoutes(router, { noteService, config });

  // --- middleware -----------------------------------------------------------------
  const requestContext = createRequestContext({ logger });

  const handler = async (req, res) => {
    const ctx = {
      params: {},
      url: new URL(req.url, `http://${req.headers.host ?? 'localhost'}`),
      requestId: undefined,
      startedAt: undefined,
      log: logger,
    };

    let statusForLogging = 500;

    // Wrap the response so we can log the final status without editing every handler.
    const originalWriteHead = res.writeHead.bind(res);
    res.writeHead = (statusCode, ...rest) => {
      statusForLogging = statusCode;
      return originalWriteHead(statusCode, ...rest);
    };

    try {
      requestContext(req, res, ctx);

      const matched = router.match(req.method, ctx.url.pathname);

      if (!matched) {
        const allowed = router.allowedMethods(ctx.url.pathname);
        if (allowed.length > 0) {
          res.setHeader('Allow', allowed.join(', '));
          statusForLogging = 405;
          return sendJson(res, 405, {
            error: {
              code: 'METHOD_NOT_ALLOWED',
              message: `${req.method} is not allowed for ${ctx.url.pathname}`,
              allowed,
              requestId: ctx.requestId,
            },
          });
        }

        statusForLogging = 404;
        return sendJson(res, 404, {
          error: {
            code: 'ROUTE_NOT_FOUND',
            message: `${req.method} ${ctx.url.pathname} not found`,
            requestId: ctx.requestId,
          },
        });
      }

      ctx.params = matched.params;
      await matched.handler(req, res, ctx);
      return undefined;
    } catch (error) {
      const statusCode = error instanceof HttpError ? error.statusCode : 500;
      statusForLogging = statusCode;

      // Log the real error; never send internals to the client.
      ctx.log[statusCode >= 500 ? 'error' : 'warn']('request failed', {
        method: req.method,
        path: ctx.url.pathname,
        status: statusCode,
        code: error.code,
        message: error.message,
        stack: statusCode >= 500 ? error.stack : undefined,
      });

      if (res.headersSent) {
        res.destroy();
        return undefined;
      }

      return sendJson(res, statusCode, {
        error: {
          code: error.code ?? 'INTERNAL_ERROR',
          message: statusCode >= 500 && config.isProduction ? 'Something went wrong' : error.message,
          details: error.details,
          requestId: ctx.requestId,
        },
      });
    } finally {
      if (ctx.startedAt !== undefined) {
        logRequest(req, res, ctx, { statusCode: statusForLogging });
      }
    }
  };

  return { handler, router, repository, noteService };
}

/** Convenience for tests and scripts: an http.Server ready to listen. */
export function createHttpServer(options) {
  const { handler } = createApp(options);
  return createServer(handler);
}
```

***

## 12. The entry point

```js
// File: src/server.js
import { once } from 'node:events';
import { createHttpServer } from './app.js';
import { env } from './config/env.js';
import { createLogger } from './middleware/logger.js';

const logger = createLogger({ level: env.logLevel, base: { service: 'notes-api' } });

async function main() {
  const server = createHttpServer({ config: env, logger });

  // Never let a slow or malicious client hold a socket forever.
  server.keepAliveTimeout = 65_000;
  server.headersTimeout = 66_000;
  server.requestTimeout = 30_000;

  server.on('clientError', (error, socket) => {
    logger.warn('client error', { code: error.code, message: error.message });
    if (socket.writable) socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
    socket.destroy();
  });

  server.listen(env.port, env.host);
  await once(server, 'listening');

  logger.info('server started', {
    url: `http://${env.host}:${env.port}`,
    env: env.nodeEnv,
    pid: process.pid,
    dataFile: env.dataFile,
  });

  // --- graceful shutdown --------------------------------------------------------
  let shuttingDown = false;

  const shutdown = (reason) => {
    if (shuttingDown) return;
    shuttingDown = true;
    logger.info('shutdown initiated', { reason });

    server.close(() => {
      logger.info('server closed, exiting');
      process.exit(0);
    });

    server.closeIdleConnections?.();

    // Safety net: never hang indefinitely.
    setTimeout(() => {
      logger.error('forced exit after 10s');
      process.exit(1);
    }, 10_000).unref();
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));

  process.on('uncaughtException', (error) => {
    logger.error('uncaught exception', { message: error.message, stack: error.stack });
    shutdown('uncaughtException');
  });

  process.on('unhandledRejection', (reason) => {
    logger.error('unhandled rejection', {
      message: reason instanceof Error ? reason.message : String(reason),
      stack: reason instanceof Error ? reason.stack : undefined,
    });
    shutdown('unhandledRejection');
  });
}

main().catch((error) => {
  logger.error('failed to start', { message: error.message, stack: error.stack });
  process.exit(1);
});
```

***

## 13. Run it

```bash
npm run dev
```

```
{"level":"info","time":"2026-09-18T10:15:30.001Z","message":"server started","service":"notes-api","url":"http://0.0.0.0:3000","env":"development","pid":41283,"dataFile":"./data/notes.json"}
```

### Exercise every endpoint with `curl`

```bash
# Health
curl -s localhost:3000/health
# {"status":"ok","uptimeSeconds":3.2}

# Create a note (note the Location header)
curl -s -i -X POST localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' \
  -d '{"title":"Learn Node","content":"Finish chapter 18","tags":["node","backend"],"pinned":true}' | head -6
```

```http
HTTP/1.1 201 Created
X-Request-Id: 8f3c1d2a-4b5e-4c6d-8e7f-1a2b3c4d5e6f
Location: /api/v1/notes/3f2b1a90-…
Content-Type: application/json; charset=utf-8
```

```bash
# Capture the id for later calls
NOTE_ID=$(curl -s -X POST localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' \
  -d '{"title":"Second note","content":"With tags","tags":["node"]}' | node -e "
    let raw='';process.stdin.on('data',c=>raw+=c).on('end',()=>console.log(JSON.parse(raw).data.id));")

# List with filtering and pagination
curl -s "localhost:3000/api/v1/notes?tag=node&limit=5&sort=-createdAt" | head -c 400

# Read one
curl -s localhost:3000/api/v1/notes/$NOTE_ID

# Partial update (PATCH semantics: only `pinned` changes)
curl -s -X PATCH localhost:3000/api/v1/notes/$NOTE_ID \
  -H 'Content-Type: application/json' -d '{"pinned":false}'

# Delete
curl -s -X DELETE localhost:3000/api/v1/notes/$NOTE_ID

# --- the failure paths, which are the point ---
curl -s localhost:3000/api/v1/notes/does-not-exist                    # 404 NOT_FOUND
curl -s -X PUT localhost:3000/api/v1/notes/$NOTE_ID -i | head -3      # 405 with Allow header
curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: application/json' -d '{}'   # 422
curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: application/json' -d '{bad json'   # 400
curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: text/plain' -d 'hello'      # 415
curl -s "localhost:3000/api/v1/notes?limit=99999"                     # 422 (limit cap)
curl -s "localhost:3000/api/v1/notes?nonsense=1"                      # 422 (unknown param)
curl -s localhost:3000/api/v1/nope                                     # 404 ROUTE_NOT_FOUND
```

Sample error responses:

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Request validation failed",
             "details": [ { "field": "title", "message": "is required and must be a non-empty string" } ],
             "requestId": "8f3c1d2a-…" } }
```

```json
{ "error": { "code": "METHOD_NOT_ALLOWED", "message": "PUT is not allowed for /api/v1/notes/3f2b…",
             "allowed": ["GET", "PATCH", "DELETE"], "requestId": "8f3c1d2a-…" } }
```

***

## 14. Tests with the built-in runner

```js
// File: tests/notes.test.js
import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { rm, mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { once } from 'node:events';
import { createHttpServer } from '../src/app.js';

/** Test configuration — an isolated temp data file per run. */
const testConfig = {
  nodeEnv: 'test',
  isProduction: false,
  isTest: true,
  logLevel: 'error',       // keep the output readable
  bodyLimitBytes: 10_000,
  dataFile: '',
};

let server;
let baseUrl;
let tempDir;

before(async () => {
  tempDir = await mkdtemp(path.join(tmpdir(), 'notes-api-'));
  testConfig.dataFile = path.join(tempDir, 'notes.json');

  server = createHttpServer({ config: testConfig });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  server.close();
  await once(server, 'close');
  await rm(tempDir, { recursive: true, force: true });
});

/** Small helper so tests read like intent, not like fetch plumbing. */
async function api(pathname, { method = 'GET', body, headers = {} } = {}) {
  const response = await fetch(`${baseUrl}${pathname}`, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    body: body === undefined ? undefined : typeof body === 'string' ? body : JSON.stringify(body),
  });

  const text = await response.text();
  return {
    status: response.status,
    headers: response.headers,
    body: text.length > 0 ? JSON.parse(text) : null,
  };
}

test('health endpoint reports ok', async () => {
  const { status, body } = await api('/health');
  assert.equal(status, 200);
  assert.equal(body.status, 'ok');
  assert.equal(typeof body.uptimeSeconds, 'number');
});

test('creating a note returns 201, a Location header and a DTO', async () => {
  const { status, body, headers } = await api('/api/v1/notes', {
    method: 'POST',
    body: { title: '  First note  ', content: 'Body text', tags: ['Node', 'node'], pinned: true },
  });

  assert.equal(status, 201);
  assert.ok(headers.get('location')?.startsWith('/api/v1/notes/'));
  assert.equal(body.data.title, 'First note');           // trimmed
  assert.deepEqual(body.data.tags, ['node']);            // lowercased + de-duplicated
  assert.equal(body.data.pinned, true);
  assert.equal(body.data.id, body.data.createdAt ? body.data.id : undefined);
  assert.ok(Date.parse(body.data.createdAt) > 0);
});

test('validation failures return 422 with field-level details', async () => {
  const { status, body } = await api('/api/v1/notes', { method: 'POST', body: { title: '' } });

  assert.equal(status, 422);
  assert.equal(body.error.code, 'VALIDATION_ERROR');
  const fields = body.error.details.map((detail) => detail.field);
  assert.ok(fields.includes('title'));
  assert.ok(fields.includes('content'));
});

test('unknown body fields are rejected rather than silently ignored', async () => {
  const { status, body } = await api('/api/v1/notes', {
    method: 'POST',
    body: { title: 'T', content: 'C', nonsense: true },
  });

  assert.equal(status, 422);
  assert.ok(body.error.details.some((detail) => detail.field === 'nonsense'));
});

test('malformed JSON is a 400, not a 500', async () => {
  const { status, body } = await api('/api/v1/notes', { method: 'POST', body: '{not json' });
  assert.equal(status, 400);
  assert.equal(body.error.code, 'INVALID_JSON');
});

test('the wrong content type is a 415', async () => {
  const { status, body } = await api('/api/v1/notes', {
    method: 'POST',
    body: 'title=x',
    headers: { 'Content-Type': 'text/plain' },
  });
  assert.equal(status, 415);
  assert.equal(body.error.code, 'UNSUPPORTED_MEDIA_TYPE');
});

test('reading a missing note is a 404 with a request id', async () => {
  const { status, body } = await api('/api/v1/notes/00000000-0000-0000-0000-000000000000');
  assert.equal(status, 404);
  assert.equal(body.error.code, 'NOT_FOUND');
  assert.equal(typeof body.error.requestId, 'string');
});

test('PATCH updates only the provided fields and is idempotent', async () => {
  const created = await api('/api/v1/notes', {
    method: 'POST',
    body: { title: 'Patch me', content: 'Original content', tags: ['a'] },
  });
  const id = created.body.data.id;

  const patched = await api(`/api/v1/notes/${id}`, { method: 'PATCH', body: { title: 'Patched' } });
  assert.equal(patched.status, 200);
  assert.equal(patched.body.data.title, 'Patched');
  assert.equal(patched.body.data.content, 'Original content');   // untouched
  assert.deepEqual(patched.body.data.tags, ['a']);               // untouched

  const again = await api(`/api/v1/notes/${id}`, { method: 'PATCH', body: { title: 'Patched' } });
  assert.equal(again.body.data.title, 'Patched');                 // same result
});

test('an empty PATCH body is rejected', async () => {
  const created = await api('/api/v1/notes', {
    method: 'POST',
    body: { title: 'Empty patch', content: 'x' },
  });
  const { status, body } = await api(`/api/v1/notes/${created.body.data.id}`, {
    method: 'PATCH',
    body: {},
  });
  assert.equal(status, 422);
  assert.ok(body.error.details.some((detail) => detail.field === 'body'));
});

test('deleting twice: 200 then 404', async () => {
  const created = await api('/api/v1/notes', {
    method: 'POST',
    body: { title: 'Delete me', content: 'x' },
  });
  const id = created.body.data.id;

  const first = await api(`/api/v1/notes/${id}`, { method: 'DELETE' });
  assert.equal(first.status, 200);

  const second = await api(`/api/v1/notes/${id}`, { method: 'DELETE' });
  assert.equal(second.status, 404);
});

test('listing paginates, caps the limit, filters and sorts', async () => {
  await Promise.all(
    ['Alpha', 'Beta', 'Gamma'].map((title) =>
      api('/api/v1/notes', { method: 'POST', body: { title, content: `${title} body`, tags: ['list'] } })
    )
  );

  const page1 = await api('/api/v1/notes?tag=list&limit=2&page=1&sort=title');
  assert.equal(page1.status, 200);
  assert.equal(page1.body.data.length, 2);
  assert.equal(page1.body.data[0].title, 'Alpha');
  assert.ok(page1.body.meta.total >= 3);
  assert.equal(page1.body.meta.limit, 2);
  assert.equal(page1.body.meta.hasNext, true);

  const oversized = await api('/api/v1/notes?limit=9999');
  assert.equal(oversized.status, 422);

  const unknownParam = await api('/api/v1/notes?bogus=1');
  assert.equal(unknownParam.status, 422);
});

test('an unsupported method returns 405 with an Allow header', async () => {
  const { status, headers, body } = await api('/api/v1/notes/xyz', { method: 'PUT', body: {} });
  assert.equal(status, 405);
  assert.ok(headers.get('allow')?.includes('PATCH'));
  assert.equal(body.error.code, 'METHOD_NOT_ALLOWED');
});

test('data persists across requests (the repository really writes)', async () => {
  const created = await api('/api/v1/notes', {
    method: 'POST',
    body: { title: 'Persisted', content: 'still here' },
  });

  // Read it back through a fresh query.
  const fetched = await api(`/api/v1/notes/${created.body.data.id}`);
  assert.equal(fetched.status, 200);
  assert.equal(fetched.body.data.title, 'Persisted');
});

test('concurrent creates do not lose data', async () => {
  const before = (await api('/api/v1/notes?limit=100')).body.meta.total;

  await Promise.all(
    Array.from({ length: 10 }, (_, index) =>
      api('/api/v1/notes', { method: 'POST', body: { title: `Concurrent ${index}`, content: 'x' } })
    )
  );

  const after = (await api('/api/v1/notes?limit=100')).body.meta.total;
  assert.equal(after, before + 10);      // the serialised write queue did its job
});
```

```bash
npm test
```

```
▶ notes-api
  ✔ health endpoint reports ok (12.4ms)
  ✔ creating a note returns 201, a Location header and a DTO (8.1ms)
  ✔ validation failures return 422 with field-level details (3.2ms)
  ✔ unknown body fields are rejected rather than silently ignored (2.8ms)
  ✔ malformed JSON is a 400, not a 500 (2.1ms)
  ✔ the wrong content type is a 415 (2.0ms)
  ✔ reading a missing note is a 404 with a request id (1.9ms)
  ✔ PATCH updates only the provided fields and is idempotent (5.4ms)
  ✔ an empty PATCH body is rejected (3.1ms)
  ✔ deleting twice: 200 then 404 (4.2ms)
  ✔ listing paginates, caps the limit, filters and sorts (7.8ms)
  ✔ an unsupported method returns 405 with an Allow header (2.2ms)
  ✔ data persists across requests (the repository really writes) (3.0ms)
  ✔ concurrent creates do not lose data (11.6ms)
  pass 14
  fail 0
```

***

## 15. What we built, and what Express will change

Count what you had to write yourself:

| Concern                                          | Lines here                  | Express equivalent                   |
| ------------------------------------------------ | --------------------------- | ------------------------------------ |
| Routing with `:params`                           | 70                          | `app.get('/notes/:id', handler)`     |
| Body parsing with limits and content-type checks | 60                          | `express.json({ limit })`            |
| JSON responses                                   | 12                          | `res.json()` / `res.status()`        |
| 404/405 handling                                 | 35                          | one `app.use()` + optional 405 logic |
| Error classification and formatting              | 45                          | an error middleware                  |
| Request ids and logging                          | 50                          | `pino-http` + a 5-line middleware    |
| Middleware chaining                              | manual (inside the handler) | `app.use()`                          |
| Validation                                       | 150 (hand-written)          | `zod` schema (\~15 lines)            |
| Configuration                                    | 40                          | same (this code is genuinely yours)  |
| Repository                                       | 90                          | same (a database driver replaces it) |

**Roughly 250 lines of pure HTTP plumbing disappear.** What remains — configuration, validation, business rules, persistence, error _decisions_ — is the actual work, and it is the same code in both versions. That is the honest argument for a framework: **it does not write your application, it removes the boilerplate around it.**

***

## 16. Exercises

### Exercise 18.1 — Add a nested resource (beginner)

Add `GET /api/v1/notes/:id/tags` returning the note's tags, with `404` when the note does not exist.

<details>

<summary>Solution</summary>

```js
// File: src/routes/noteRoutes.js (added)
router.get(`${base}/:id/tags`, async (req, res, ctx) => {
  // Reuse the service so ownership/not-found logic stays in one place.
  const note = await noteService.getById(ctx.params.id);
  sendJson(res, 200, { data: note.tags, meta: { count: note.tags.length, noteId: note.id } });
});
```

Test it:

```bash
curl -s localhost:3000/api/v1/notes/$NOTE_ID/tags
# {"data":["node"],"meta":{"count":1,"noteId":"…"}}
curl -s -i localhost:3000/api/v1/notes/missing/tags | head -1   # HTTP/1.1 404 Not Found
```

**Why this is the right implementation:** it calls `noteService.getById` rather than reaching into the repository, so the "does this note exist?" rule and the DTO shape stay in one place. If a future rule adds ownership checks, this endpoint inherits it for free.

</details>

### Exercise 18.2 — Add soft delete (intermediate)

Instead of removing a note, mark it `deletedAt`. Deleted notes must be excluded from list and read results (unless `?includeDeleted=true` is passed by an admin), and the endpoint should return `204` for deletion.

<details>

<summary>Solution</summary>

```js
// File: src/services/noteService.js (changed parts)
export function createNoteService({ repository, logger }) {
  const MAX_LIMIT = 100;

  return {
    async list(query, { includeDeleted = false } = {}) {
      const limit = Math.min(query.limit ?? 20, MAX_LIMIT);
      const { items, total } = await repository.list({
        ...query,
        limit,
        includeDeleted,                        // pushed down to the repository filter
      });

      const page = query.page ?? 1;
      return {
        items: items.map(toNoteDto),
        meta: { page, limit, total, totalPages: Math.max(1, Math.ceil(total / limit)), hasNext: page * limit < total },
      };
    },

    async getById(id, { includeDeleted = false } = {}) {
      const note = await repository.findById(id);
      if (!note || (!includeDeleted && note.deletedAt)) throw new NotFoundError(`Note ${id} not found`);
      return toNoteDto(note);
    },

    async softDelete(id) {
      const updated = await repository.update(id, { deletedAt: new Date().toISOString() });
      if (!updated || updated.deletedAt !== undefined) { /* handled below */ }
      if (!updated) throw new NotFoundError(`Note ${id} not found`);
      logger.info('note soft-deleted', { id });
      return { id };
    },

    async restore(id) {
      const note = await repository.findById(id);
      if (!note) throw new NotFoundError(`Note ${id} not found`);
      if (!note.deletedAt) throw new ConflictError(`Note ${id} is not deleted`);
      const restored = await repository.update(id, { deletedAt: null });
      logger.info('note restored', { id });
      return toNoteDto(restored);
    },
  };
}

function toNoteDto(note) {
  return {
    id: note.id,
    title: note.title,
    content: note.content,
    tags: note.tags,
    pinned: note.pinned,
    createdAt: note.createdAt,
    updatedAt: note.updatedAt,
    deletedAt: note.deletedAt ?? null,
  };
}
```

```js
// File: src/repositories/noteRepository.js (changed parts — shown inside the returned object)
const changedMethods = {
  async list({ tag, q, sort = '-createdAt', page = 1, limit = 20, includeDeleted = false } = {}) {
    const notes = await load();

    const filtered = includeDeleted ? notes : notes.filter((note) => !note.deletedAt);
    // …the rest is unchanged…
    return { items: filtered, total: filtered.length };
  },

async update(id, patch) {
  const notes = await load();
  const index = notes.findIndex((note) => note.id === id);
  if (index === -1) return null;

  // `null` must be able to clear a field (e.g. deletedAt for restore), so apply
  // every key explicitly — including undefined-free nulls.
  const next = { ...notes[index] };
  for (const [key, value] of Object.entries(patch)) {
    if (key === 'id' || key === 'createdAt') continue;   // immutable
    next[key] = value;
  }
  next.updatedAt = new Date().toISOString();
  notes[index] = next;

  await persist();
  return clone(next);
  },
};
```

```js
// File: src/routes/noteRoutes.js (changed)
// DELETE now soft-deletes and returns 204 with no body.
router.delete(`${base}/:id`, async (req, res, ctx) => {
  await noteService.softDelete(ctx.params.id);
  res.writeHead(204);
  res.end();
});

// Admin-only restore, with an explicit authorisation check.
router.post(`${base}/:id/restore`, async (req, res, ctx) => {
  if (req.headers['x-role'] !== 'admin') {
    throw new ForbiddenError('Only admins can restore notes');
  }
  const note = await noteService.restore(ctx.params.id);
  sendJson(res, 200, { data: note });
});

// Listing can include deleted notes for admins only.
router.get(base, async (req, res, ctx) => {
  const validated = validateListQuery(ctx.url.searchParams);
  assertValid(validated);

  const includeDeleted =
    ctx.url.searchParams.get('includeDeleted') === 'true' && req.headers['x-role'] === 'admin';

  const { items, meta } = await noteService.list(validated.value, { includeDeleted });
  sendJson(res, 200, { data: items, meta: { ...meta, includeDeleted } });
});
```

**Design points worth noticing**

| Point                                                                  | Why                                                                                                                        |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Soft delete changes the _repository filter_, not the shape of the data | Every read path must respect it, or deleted notes leak                                                                     |
| `204` is the correct status for a body-less delete                     | The client asked for removal; there is nothing to return                                                                   |
| Restore is a `POST` action on the resource                             | It is a state transition, not a CRUD operation                                                                             |
| `includeDeleted` is gated by a role check                              | Otherwise it is an information-disclosure endpoint                                                                         |
| `deletedAt: null` must be distinguishable from "absent"                | This is the PATCH null-vs-absent problem from [00-web-fundamentals/06](../00-web-fundamentals/06-json-and-data-formats.md) |
| Concurrency: two soft-deletes are harmless (idempotent)                | State transitions that set an absolute value are naturally idempotent                                                      |

**Follow-up:** add a `deletedAt` filter to `list` (`?deletedOnly=true`) for admins, and a TTL job that hard-deletes notes deleted more than 30 days ago.

</details>

### Exercise 18.3 — Add ETag/caching support (advanced)

Return an `ETag` header for `GET /api/v1/notes/:id`, and respond `304 Not Modified` when the client sends a matching `If-None-Match`.

<details>

<summary>Solution</summary>

```js
// File: src/lib/http.js (added helpers)
import { createHash } from 'node:crypto';

/** A strong ETag over the serialised body — changes whenever the content changes. */
export function computeEtag(payload) {
  const body = JSON.stringify(payload);
  return `"${createHash('sha256').update(body).digest('base64url').slice(0, 27)}"`;
}

/**
 * Send a JSON response with ETag support.
 * Returns 304 (no body) when the client's If-None-Match matches.
 */
export function sendJsonWithEtag(req, res, status, payload) {
  const etag = computeEtag(payload);
  const ifNoneMatch = req.headers['if-none-match'];

  if (ifNoneMatch && ifNoneMatch.split(',').map((v) => v.trim()).includes(etag)) {
    res.writeHead(304, { ETag: etag, 'Cache-Control': 'private, max-age=0, must-revalidate' });
    res.end();
    return { status: 304, etag, notModified: true };
  }

  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    ETag: etag,
    'Cache-Control': 'private, max-age=0, must-revalidate',
    Vary: 'Accept-Encoding, Authorization',
  });
  res.end(body);
  return { status, etag, notModified: false };
}
```

```js
// File: src/routes/noteRoutes.js (changed GET one)
router.get(`${base}/:id`, async (req, res, ctx) => {
  const note = await noteService.getById(ctx.params.id);
  sendJsonWithEtag(req, res, 200, { data: note });
});
```

```bash
# First request: capture the ETag
ETAG=$(curl -s -D - -o /dev/null localhost:3000/api/v1/notes/$NOTE_ID | grep -i etag | tr -d '\r' | cut -d' ' -f2)

# Second request with If-None-Match → 304, no body
curl -s -i -H "If-None-Match: $ETAG" localhost:3000/api/v1/notes/$NOTE_ID | head -4
```

```http
HTTP/1.1 304 Not Modified
ETag: "3f2b1a90c8d7e6f5a4b3c2d1e0"
Cache-Control: private, max-age=0, must-revalidate
```

**Design discussion**

| Decision                           | Reason                                                                      |
| ---------------------------------- | --------------------------------------------------------------------------- |
| Hash of the serialised body        | The value must change whenever the response changes; a hash guarantees that |
| `private` cache directive          | The response is per-user, so shared (CDN) caches must not store it          |
| `must-revalidate`                  | Clients must ask before reusing a stale copy — correct for mutable data     |
| `Vary: Authorization`              | Different tokens get different content; caches must not mix them            |
| `304` has no body                  | Per the specification, and clients rely on it                               |
| Strong (not weak) ETag             | We can guarantee byte-identical content for the same version                |
| `If-None-Match` compared as a list | Clients may send several ETags; handle them all                             |

**Why this matters at scale:** a mobile client polling a list of notes with ETags stops downloading unchanged bodies entirely — less bandwidth, less server work, and a better battery profile. It is one of the few optimisations that is free once implemented.

**Follow-up:** add a `Last-Modified` header with `If-Modified-Since` support, and apply the same treatment to list endpoints keyed on the newest `updatedAt` in the page.

</details>

***

## Section summary

You have built, from nothing but Node's standard library:

* an HTTP server with correct status codes, headers and content negotiation,
* a router with path parameters,
* a request body reader with size limits and proper error mapping,
* structured logging with request ids,
* hand-written validation with field-level errors,
* a repository with atomic writes and a concurrency-safe write queue,
* graceful shutdown and process-level safety nets, and
* an integration test suite using the built-in test runner.

**Now measure the cost:** roughly 250 lines exist only to translate HTTP into function calls. In the next section, Express removes those 250 lines — and understanding exactly which 250 they are is why you will use the framework _correctly_ instead of hoping it works.

→ [02 — Express: Introduction](../02-express/01-introduction.md)
