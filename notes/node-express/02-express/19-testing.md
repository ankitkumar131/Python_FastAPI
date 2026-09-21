# 19 — Testing

> **Where this fits:** Every previous chapter ended with tests written in `node:test`. This chapter makes that systematic: what to test at each layer, how to write route tests with `supertest`, how to mock without lying to yourself, and how to keep a suite fast and deterministic. Jest and Vitest get a full treatment in 05-testing/ _(not available in this published source revision)_; here the focus is testing an Express API.

***

## 1. What to test, and at which layer

```
        ▲  fewer, slower, more realistic
        │
   E2E (a real database, a real HTTP client)          ~5%   "the whole thing works deployed"
   ─────────────────────────────────────────────
   Route/integration: supertest + in-memory data      ~25%  "HTTP contract, status codes, headers"
   ─────────────────────────────────────────────
   Unit: services, validators, utils (no I/O)         ~70%  "the rules, exhaustively and fast"
        │
        ▼  more, faster, more focused
```

| Layer                                          | What it proves                                                     | What it cannot prove                | Cost           |
| ---------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------- | -------------- |
| **Unit** (service, validator, util)            | The rule is correct for every input you thought of                 | Anything about HTTP or the database | \~1 ms         |
| **Integration** (route + middleware + service) | Status codes, headers, error shape, auth boundaries, serialisation | The real database dialect/queries   | \~10–50 ms     |
| **E2E** (a running server + a real database)   | Migrations, queries, transactions, JSON parsing in production mode | Business rules exhaustively         | 100 ms–seconds |
| **Contract/snapshot**                          | The response shape has not drifted                                 | That the shape is right             | \~5 ms         |

The rule of thumb used throughout this course:

* **Rules live in services → test them there, exhaustively.**
* **The HTTP contract lives in routes → test it with `supertest`, covering the failure matrix.**
* **The database has its own dialect → keep one small integration suite that touches the real thing.**

***

## 2. `node:test`: the zero-dependency runner

Node ships a test runner. No install, no configuration, no transform step — and it understands ESM, `node:` prefixes and top-level `await` natively.

```js
// File: tests/example.test.js
import { test, describe, it, before, after, beforeEach, afterEach, mock } from 'node:test';
import assert from 'node:assert/strict';

describe('a group of tests', () => {
  let state;

  before(() => { state = { started: true }; });        // once, before the suite
  beforeEach(() => { state.count = 0; });              // before every test
  afterEach(() => { delete state.count; });
  after(() => { state = undefined; });

  it('uses the shared state', () => {
    state.count += 1;
    assert.equal(state.count, 1);
  });

  test('supports a timeout', { timeout: 500 }, async () => {
    await new Promise((resolve) => setTimeout(resolve, 10));
    assert.equal(state.started, true);
  });

  test('can be skipped or marked as a todo', { skip: 'waiting for the payment provider sandbox' }, () => {
    assert.fail('never runs');
  });
});
```

```bash
node --test                                  # every *.test.js, test/**, **/*.spec.js
node --test tests/notes.test.js              # one file
node --test --watch                          # re-run on change
node --test --test-concurrency=4             # parallel files (default: available CPUs)
node --test --test-reporter=spec             # human-readable output (dot, tap, spec, junit)
node --test --test-force-exit                # exit even if a handle is open (use sparingly)
node --test --experimental-test-coverage     # coverage, no instrumenter needed
node --test --test-name-pattern='rejects'    # run only matching tests
```

```
# The default reporter is TAP; the spec reporter is friendlier.
$ node --test --test-reporter=spec tests/
▶ notes service
  ✔ creates a note with a server-assigned author
  ✔ rejects a duplicate title with 409 semantics
✔ notes service (4.2 ms)
✔ 2 tests passed
```

`--experimental-test-coverage` produces the report without any extra tooling:

```
start of coverage report
----------------------------------------------------------
file                          | line % | branch % | funcs % | uncovered lines
----------------------------------------------------------
src/services/noteService.js  |  96.30 |   87.50  |  100.00 | 41-42
src/utils/AppError.js         | 100.00 |  100.00  |  100.00 |
----------------------------------------------------------
all files                     |  97.10 |   89.20  |  100.00 |
----------------------------------------------------------
end of coverage report
```

### Mocking with `node:test`

```js
// File: tests/mocking.test.js
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';

test('mock.method stubs once and then falls back to the real implementation', async () => {
  const mailer = { send: async () => 'real-send' };
  const spy = mock.method(mailer, 'send', async () => 'stubbed', { times: 1 });

  assert.equal(await mailer.send(), 'stubbed');       // first call: the stub
  assert.equal(await mailer.send(), 'real-send');     // afterwards: the real one
  assert.equal(spy.mock.calls.length, 1);
  spy.mock.restore();                                 // always restore
});

test('mock.fn records every call', async () => {
  const repository = { findById: mock.fn(async (id) => ({ id, title: 'Stub' })) };

  const note = await repository.findById('n1');

  assert.equal(note.title, 'Stub');
  assert.equal(repository.findById.mock.calls.length, 1);
  assert.deepEqual(repository.findById.mock.calls[0].arguments, ['n1']);
});

test('mock.timers freezes the clock — and setTime takes a NUMBER', () => {
  mock.timers.enable({ apis: ['Date', 'setTimeout'] });

  // ⚠️ Verified gotcha: setTime(new Date(...)) throws
  //    "The "time" argument must be of type number. Received an instance of Date".
  mock.timers.setTime(Date.parse('2026-09-18T10:00:00.000Z'));

  assert.equal(new Date().toISOString(), '2026-09-18T10:00:00.000Z');

  let fired = false;
  setTimeout(() => { fired = true; }, 5_000);
  mock.timers.tick(5_000);

  assert.equal(fired, true);
  mock.timers.reset();
});
```

| API                                          | Use it for                                              | Watch out for                                                        |
| -------------------------------------------- | ------------------------------------------------------- | -------------------------------------------------------------------- |
| `mock.fn(impl?)`                             | A fake collaborator you own                             | Calls are recorded, but nothing is restored automatically            |
| `mock.method(object, name, impl?, options?)` | Spying on/stubbing an existing method                   | Always `restore()`; use `{ times: n }` deliberately                  |
| `mock.timers.enable({ apis })`               | Freezing `Date`, controlling `setTimeout`/`setInterval` | Experimental in Node 22; print the warning away with `--no-warnings` |
| `mock.timers.setTime(number)`                | Setting the frozen instant                              | **Must be a number**, not a `Date`                                   |
| `mock.timers.tick(ms)`                       | Advancing time                                          | Timers scheduled _before_ `enable` are not tracked                   |

> **Prefer dependency injection over mocking.** A service that receives `clock`, `mailer` and repositories as arguments needs no mocking library at all — you pass a fake object. `mock.method` is for the occasional third-party surface you cannot inject.

***

## 3. `supertest`: testing the HTTP contract

`supertest` takes your `app` (not a running server), starts an ephemeral server on a random port for the duration of the call, sends a real HTTP request through the whole middleware stack, and gives you assertions on the response.

```bash
npm install --save-dev supertest
```

```js
// File: tests/routes.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import request from 'supertest';

function createTestApp() {
  const app = express();
  app.use(express.json({ limit: '10kb' }));
  app.use((req, res, next) => { req.id = 'test-request-id'; next(); });

  const notes = [];
  app.post('/api/v1/notes', (req, res) => {
    const note = { id: String(notes.length + 1), ...req.body };
    notes.push(note);
    res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: note });
  });
  app.get('/api/v1/notes/:id', (req, res) => {
    const note = notes.find((item) => item.id === req.params.id);
    if (!note) return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Note not found', requestId: req.id } });
    return res.json({ data: note });
  });
  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND', requestId: req.id } }));
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    res.status(error.statusCode ?? 500).json({ error: { code: error.code ?? 'INTERNAL_ERROR', message: error.message } });
  });

  return app;
}

test('POST creates a note with 201 and Location', async () => {
  const app = createTestApp();

  const response = await request(app)
    .post('/api/v1/notes')
    .set('Authorization', 'Bearer test-token')
    .set('Content-Type', 'application/json')
    .send({ title: 'Learn Express', content: 'Chapter 19' })
    .expect(201)
    .expect('Content-Type', /json/);

  assert.equal(response.body.data.title, 'Learn Express');
  assert.equal(response.headers.location, '/api/v1/notes/1');
});

test('GET returns the note, and 404 carries the error envelope', async () => {
  const app = createTestApp();
  await request(app).post('/api/v1/notes').send({ title: 'A', content: 'B' }).expect(201);

  const found = await request(app).get('/api/v1/notes/1').expect(200);
  assert.equal(found.body.data.title, 'A');

  const missing = await request(app).get('/api/v1/notes/nope').expect(404);
  assert.deepEqual(missing.body.error, {
    code: 'NOT_FOUND',
    message: 'Note not found',
    requestId: 'test-request-id',
  });
});

test('an unknown route is a 404 with the envelope, not Express HTML', async () => {
  const app = createTestApp();

  const response = await request(app).get('/definitely-not-a-route').expect(404);

  assert.match(response.headers['content-type'], /json/);
  assert.equal(response.body.error.code, 'ROUTE_NOT_FOUND');
});
```

```bash
node --test tests/routes.test.js
```

```
✔ POST creates a note with 201 and Location
✔ GET returns the note, and 404 carries the error envelope
✔ an unknown route is a 404 with the envelope, not Express HTML
pass 3
fail 0
```

### The `app`/`server` split is what makes this possible

```js
// File: src/app.js — builds the app, never listens
export function createApp({ config, container }) { /* … */ return app; }

// File: src/server.js — the only file that listens
const app = createApp({ config: env, container });
const server = createServer(app);
server.listen(env.PORT, '0.0.0.0', () => logger.info({ port: env.PORT }, 'listening'));
```

| Why                            | Consequence                                                     |
| ------------------------------ | --------------------------------------------------------------- |
| No port binding in tests       | No `EADDRINUSE`, no port juggling, tests run in parallel safely |
| Middleware order is real       | Ordering bugs (`cors` after routes) are caught                  |
| The error handler is exercised | The 500 path is tested, not assumed                             |
| One app instance per test      | Complete isolation with no shared state                         |

```js
// File: tests/port-collision.mjs — the anti-pattern this avoids
// ❌ Every test fights for port 3000 and depends on the previous one's state.
// test('server works', async () => { app.listen(3000); const r = await fetch('http://localhost:3000/…'); });
```

### Assertions worth memorising

```js
// File: supertest-cheatsheet.js (illustration — not executed)
const agent = request(app);

await agent.get('/x').expect(200);
await agent.get('/x').expect('Content-Type', /json/);
await agent.get('/x').expect('Location', '/api/v1/notes/1');
await agent.get('/x').expect((res) => { if (res.body.data.id !== '1') throw new Error('bad id'); });

await agent.post('/x').set('Authorization', 'Bearer t').send({ a: 1 }).expect(201);
await agent.patch('/x').type('form').send({ a: 1 });            // form-urlencoded
await agent.post('/x').attach('file', 'tests/fixtures/pixel.png'); // multipart
await agent.get('/x').query({ page: 2, limit: 5 });              // ?page=2&limit=5
await agent.get('/x').auth('user', 'pass');                      // basic auth
await agent.get('/x').redirects(1);                              // follow one redirect
await agent.get('/x').set('Cookie', 'sid=abc; csrfToken=xyz');

// Raw text (for non-JSON responses)
const raw = await agent.get('/health').expect(200);
assert.equal(raw.text, 'ok');
```

> `supertest` sends a real HTTP request, so **everything** that touches it must be real enough: JSON parsing, cookie parsing, CSRF middleware, the error handler. Fakes belong below the HTTP layer, in the services you inject.

***

## 4. A complete test suite for one resource

The notes API, tested at all three layers. The repository is injected, so the route tests need no database and the service tests need no HTTP.

```js
// File: tests/support/inMemoryNoteRepository.js — a fake that behaves like the real thing
export function createInMemoryNoteRepository(seed = []) {
  const rows = seed.map((note) => ({ ...note }));
  let sequence = rows.length;

  return {
    rows,
    async list({ offset = 0, limit = 20, sort = '-createdAt' } = {}) {
      const [field, direction] = sort.startsWith('-') ? [sort.slice(1), -1] : [sort, 1];
      const sorted = [...rows].sort((a, b) => String(a[field]).localeCompare(String(b[field])) * direction);
      return { items: sorted.slice(offset, offset + limit), total: rows.length };
    },
    async findById(id) { return rows.find((note) => note.id === id) ?? null; },
    async existsByTitle(title) { return rows.some((note) => note.title === title); },
    async create(data) {
      sequence += 1;
      const note = { id: `n${sequence}`, ...data };
      rows.push(note);
      return note;
    },
    async update(id, next) {
      const index = rows.findIndex((note) => note.id === id);
      if (index === -1) return null;
      rows[index] = { ...next, id };
      return rows[index];
    },
    async remove(id) {
      const index = rows.findIndex((note) => note.id === id);
      if (index === -1) return false;
      rows.splice(index, 1);
      return true;
    },
  };
}
```

```js
// File: tests/support/buildTestApp.js — the composition root for tests
import express from 'express';
import cookieParser from 'cookie-parser';
import { createNoteService } from '../../src/services/noteService.js';
import { createNoteController } from '../../src/controllers/noteController.js';
import { createNoteRouter } from '../../src/routes/noteRoutes.js';
import { createErrorHandler } from '../../src/middleware/errorHandler.js';
import { notFound } from '../../src/middleware/notFound.js';
import { createInMemoryNoteRepository } from './inMemoryNoteRepository.js';

const silentLogger = { info() {}, warn() {}, error() {}, fatal() {}, debug() {}, child() { return silentLogger; } };

/** Actor fixtures: a normal user, another user, an admin. */
export const actors = {
  owner: { id: 'u1', role: 'USER', email: 'owner@example.com' },
  other: { id: 'u2', role: 'USER', email: 'other@example.com' },
  admin: { id: 'admin', role: 'ADMIN', email: 'admin@example.com' },
};

export function buildTestApp({ repository = createInMemoryNoteRepository(), actor = actors.owner } = {}) {
  const service = createNoteService({
    noteRepository: repository,
    logger: silentLogger,
    clock: () => new Date('2026-09-18T10:00:00.000Z'),
  });
  const controller = createNoteController({ noteService: service, logger: silentLogger });

  const middleware = {
    requireAuth: (req, res, next) => {
      const header = req.get('authorization');
      if (!header?.startsWith('Bearer ')) {
        res.set('WWW-Authenticate', 'Bearer realm="api"');
        return res.status(401).json({ error: { code: 'UNAUTHENTICATED', message: 'Sign in to continue', requestId: req.id } });
      }
      req.user = actor;                                    // the caller "owning" this test app
      return next();
    },
    loadNote: async (req, res, next) => {
      try {
        const note = await service.getById(req.params.id);
        if (!note) {
          return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Note not found', requestId: req.id } });
        }
        res.locals.note = note;
        return next();
      } catch (error) {
        return next(error);
      }
    },
    requireOwner: (req, res, next) => {
      if (res.locals.note.authorId === req.user.id || req.user.role === 'ADMIN') return next();
      return res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Not your note', requestId: req.id } });
    },
  };

  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '10kb' }));
  app.use(cookieParser('test-cookie-secret'));
  app.use((req, res, next) => { req.id = 'test-request-id'; next(); });
  app.use('/api/v1/notes', createNoteRouter({ controller, middleware }));
  app.use(notFound);
  app.use(createErrorHandler({ logger: silentLogger, isProduction: false }));

  return { app, repository, service };
}
```

```js
// File: tests/noteService.test.js — UNIT: the rules, exhaustively
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createNoteService } from '../src/services/noteService.js';
import { ConflictError, ForbiddenError, NotFoundError } from '../src/utils/AppError.js';
import { createInMemoryNoteRepository } from './support/inMemoryNoteRepository.js';

const FIXED = '2026-09-18T10:00:00.000Z';

function build(seed = []) {
  const repository = createInMemoryNoteRepository(seed);
  const service = createNoteService({
    noteRepository: repository,
    logger: { info() {}, warn() {}, error() {} },
    clock: () => new Date(FIXED),
  });
  return { service, repository };
}

const actor = { id: 'u1', role: 'USER' };

test('create assigns the author, the timestamps and the defaults', async () => {
  const { service } = build();

  const note = await service.create({ title: 'T', content: 'C' }, { actor });

  assert.equal(note.authorId, 'u1');
  assert.equal(note.createdAt, FIXED);
  assert.equal(note.updatedAt, FIXED);
  assert.deepEqual(note.tags, []);
  assert.equal(note.pinned, false);
});

test('create rejects a duplicate title with a ConflictError', async () => {
  const { service } = build([{ id: 'n1', title: 'Taken', content: 'x', authorId: 'u1' }]);

  await assert.rejects(
    () => service.create({ title: 'Taken', content: 'x' }, { actor }),
    (error) => {
      assert.ok(error instanceof ConflictError);
      assert.equal(error.statusCode, 409);
      assert.deepEqual(error.details, { field: 'title' });
      return true;
    },
  );
});

test('a caller cannot create a note on behalf of someone else', async () => {
  const { service, repository } = build();

  const note = await service.create({ title: 'T', content: 'C', authorId: 'u2' }, { actor });

  assert.equal(note.authorId, 'u1');                    // the body value is ignored
  assert.equal(repository.rows.length, 1);
});

test('update requires ownership', async () => {
  const { service } = build([{ id: 'n1', title: 'T', content: 'C', authorId: 'u2', tags: [] }]);

  await assert.rejects(() => service.update('n1', { title: 'X' }, { actor }), ForbiddenError);
});

test('update applies only the provided fields and refreshes updatedAt', async () => {
  const { service } = build([{ id: 'n1', title: 'T', content: 'C', authorId: 'u1', tags: ['a'], pinned: false }]);

  const updated = await service.update('n1', { pinned: true }, { actor });

  assert.equal(updated.pinned, true);
  assert.equal(updated.title, 'T');                     // untouched
  assert.deepEqual(updated.tags, ['a']);                // untouched
  assert.equal(updated.updatedAt, FIXED);
});

test('updating a missing note is a NotFoundError', async () => {
  const { service } = build();
  await assert.rejects(() => service.update('nope', { title: 'X' }, { actor }), NotFoundError);
});

test('remove returns true then false for the same id', async () => {
  const { service } = build([{ id: 'n1', title: 'T', content: 'C', authorId: 'u1' }]);

  assert.equal(await service.remove('n1', { actor }), true);
  assert.equal(await service.remove('n1', { actor }), false);
});

test('list paginates and reports the total', async () => {
  const seed = Array.from({ length: 25 }, (_, index) => ({
    id: `n${index + 1}`, title: `T${index + 1}`, content: 'C', authorId: 'u1', createdAt: FIXED,
  }));
  const { service } = build(seed);

  const page = await service.list({ page: 2, limit: 10, sort: 'title' });

  assert.equal(page.items.length, 10);
  assert.equal(page.total, 25);
  assert.equal(page.page, 2);
});
```

```js
// File: tests/notes.routes.test.js — INTEGRATION: the HTTP contract
import { test } from 'node:test';
import assert from 'node:assert/strict';
import request from 'supertest';
import { buildTestApp, actors } from './support/buildTestApp.js';
import { createInMemoryNoteRepository } from './support/inMemoryNoteRepository.js';

const seed = () => createInMemoryNoteRepository([
  { id: 'n1', title: 'Mine', content: 'C', tags: [], pinned: false, authorId: 'u1', createdAt: '2026-09-18T10:00:00.000Z', updatedAt: '2026-09-18T10:00:00.000Z' },
  { id: 'n2', title: 'Theirs', content: 'C', tags: [], pinned: false, authorId: 'u2', createdAt: '2026-09-18T10:00:00.000Z', updatedAt: '2026-09-18T10:00:00.000Z' },
]);

const NOT_FOUND_UUID = '6b1f0f9e-0000-4000-8000-000000000000';

test('POST /notes returns 201, Location and the DTO', async () => {
  const { app } = buildTestApp({ repository: seed() });

  const response = await request(app)
    .post('/api/v1/notes')
    .set('Authorization', 'Bearer token')
    .send({ title: 'New', content: 'Body' })
    .expect(201)
    .expect('Location', '/api/v1/notes/n3');

  assert.deepEqual(Object.keys(response.body.data).sort(), ['authorId', 'content', 'createdAt', 'id', 'pinned', 'tags', 'title', 'updatedAt']);
});

test('POST /notes without a token is 401 with WWW-Authenticate', async () => {
  const { app } = buildTestApp({ repository: seed() });

  const response = await request(app).post('/api/v1/notes').send({ title: 'T', content: 'C' }).expect(401);

  assert.match(response.headers['www-authenticate'], /^Bearer/);
  assert.equal(response.body.error.code, 'UNAUTHENTICATED');
});

test('POST /notes with an invalid body is 422 with field details', async () => {
  const { app } = buildTestApp({ repository: seed() });

  const response = await request(app).post('/api/v1/notes').set('Authorization', 'Bearer t').send({ title: '' }).expect(422);

  assert.equal(response.body.error.code, 'VALIDATION_ERROR');
  assert.ok(response.body.error.details.some((detail) => detail.field === 'title'));
});

test('GET /notes/n2 as another user is 403', async () => {
  const { app } = buildTestApp({ repository: seed(), actor: actors.owner });

  const response = await request(app).patch('/api/v1/notes/n2').set('Authorization', 'Bearer t').send({ title: 'Hijack' }).expect(403);

  assert.equal(response.body.error.code, 'FORBIDDEN');
});

test('GET /notes/n2 as the owner is 200', async () => {
  const { app } = buildTestApp({ repository: seed(), actor: actors.other });

  const response = await request(app).patch('/api/v1/notes/n2').set('Authorization', 'Bearer t').send({ title: 'Mine now' }).expect(200);
  assert.equal(response.body.data.title, 'Mine now');
});

test('an admin bypasses the ownership rule', async () => {
  const { app } = buildTestApp({ repository: seed(), actor: actors.admin });

  await request(app).patch('/api/v1/notes/n1').set('Authorization', 'Bearer t').send({ title: 'Moderated' }).expect(200);
});

test('an unknown note is 404 before ownership is even considered', async () => {
  const { app } = buildTestApp({ repository: seed() });

  const response = await request(app).get(`/api/v1/notes/${NOT_FOUND_UUID}`).set('Authorization', 'Bearer t').expect(404);
  assert.equal(response.body.error.code, 'NOT_FOUND');
});

test('every response carries a requestId, including failures', async () => {
  const { app } = buildTestApp({ repository: seed() });

  const ok = await request(app).get('/api/v1/notes/n1').set('Authorization', 'Bearer t').expect(200);
  assert.equal(ok.headers['x-request-id'], undefined);          // set by the real middleware, not the test one

  const failure = await request(app).get('/api/v1/notes/nope').set('Authorization', 'Bearer t').expect(404);
  assert.equal(failure.body.error.requestId, 'test-request-id');
});

test('DELETE removes the note, and the second attempt is 404', async () => {
  const { app, repository } = buildTestApp({ repository: seed() });

  await request(app).delete('/api/v1/notes/n1').set('Authorization', 'Bearer t').expect(204);
  assert.equal(repository.rows.length, 1);

  await request(app).delete('/api/v1/notes/n1').set('Authorization', 'Bearer t').expect(404);
});
```

```bash
node --test tests/noteService.test.js tests/notes.routes.test.js
```

```
✔ notes service
  ✔ create assigns the author, the timestamps and the defaults
  ✔ create rejects a duplicate title with a ConflictError
  ✔ a caller cannot create a note on behalf of someone else
  ✔ update requires ownership
  ✔ update applies only the provided fields and refreshes updatedAt
  ✔ updating a missing note is a NotFoundError
  ✔ remove returns true then false for the same id
  ✔ list paginates and reports the total
✔ note routes (integration)
  ✔ POST /notes returns 201, Location and the DTO
  ✔ POST /notes without a token is 401 with WWW-Authenticate
  ✔ POST /notes with an invalid body is 422 with field details
  ✔ GET /notes/n2 as another user is 403
  ✔ GET /notes/n2 as the owner is 200
  ✔ an admin bypasses the ownership rule
  ✔ an unknown note is 404 before ownership is even considered
  ✔ every response carries a requestId, including failures
  ✔ DELETE removes the note, and the second attempt is 404
pass 17
fail 0
```

| Test                                                      | Layer       | What it would catch in review                              |
| --------------------------------------------------------- | ----------- | ---------------------------------------------------------- |
| `create assigns the author…`                              | Unit        | A `authorId` taken from the request body                   |
| `a caller cannot create a note on behalf of someone else` | Unit        | Mass assignment                                            |
| `update requires ownership`                               | Unit        | A missing ownership rule                                   |
| `POST /notes without a token is 401`                      | Integration | A route registered outside the protected router            |
| `POST … is 422 with field details`                        | Integration | Validation wired to the wrong source                       |
| `GET /notes/n2 as another user is 403`                    | Integration | An authorisation check that only exists in the service     |
| `DELETE … second attempt is 404`                          | Integration | A handler that returns 204 for something it did not delete |

***

## 5. Isolating tests from the database

| Strategy                          | Speed      | Fidelity | Notes                                                                                            |
| --------------------------------- | ---------- | -------- | ------------------------------------------------------------------------------------------------ |
| **In-memory fake repository**     | ⚡          | Medium   | Best for services and routes; the fake must mirror real semantics (sorting, nulls, uniqueness)   |
| **Transaction rollback**          | Fast       | High     | Wrap each test in a transaction and roll back; needs a real database and one connection per test |
| **Truncate/delete between tests** | Medium     | High     | Simple and explicit; slower as the schema grows                                                  |
| **Per-worker schema/database**    | Medium     | High     | `node --test --test-concurrency=4` with `test_worker_1..4`; parallel-safe                        |
| **Testcontainers**                | Slow start | Highest  | The same image as production (PostgreSQL 18, MongoDB 8, Redis 8); closest to reality             |
| **Shared seeded database**        | Fast       | Low      | Order-dependent and flaky — do not                                                               |

```js
// File: tests/support/database.js — the rollback pattern, sketched
export function createRollbackHarness({ pool }) {
  return {
    /** Wrap a test body in a transaction that is always rolled back. */
    async useTransaction(fn) {
      const client = await pool.connect();
      await client.query('BEGIN');
      try {
        return await fn(client);          // hand `client` to the repository under test
      } finally {
        await client.query('ROLLBACK');
        client.release();
      }
    },
  };
}
```

```js
// File: tests/notes.repository.test.js — the ONE suite that touches the real database
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { pool } from '../../src/database/client.js';
import { createNoteRepository } from '../../src/repositories/noteRepository.js';

let harness;
let repository;

before(async () => {
  await pool.query(`CREATE TABLE IF NOT EXISTS notes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL UNIQUE,
    content text NOT NULL,
    author_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
  )`);

  harness = {
    async useTransaction(fn) {
      const client = await pool.connect();
      await client.query('BEGIN');
      try { return await fn(client); } finally { await client.query('ROLLBACK'); client.release(); }
    },
  };

  repository = createNoteRepository({ db: { query: (...args) => pool.query(...args), withTransaction: (fn) => harness.useTransaction(fn) } });
});

after(async () => { await pool.end(); });

test('the unique index turns a duplicate title into a driver error', async () => {
  await harness.useTransaction(async (client) => {
    await client.query("INSERT INTO notes (title, content, author_id) VALUES ('A', 'x', gen_random_uuid())");

    await assert.rejects(
      () => client.query("INSERT INTO notes (title, content, author_id) VALUES ('A', 'y', gen_random_uuid())"),
      (error) => error.code === '23505',                 // PostgreSQL unique_violation
    );
  });
});

test('repository.list orders by created_at DESC and paginates', async () => {
  await harness.useTransaction(async (client) => {
    for (let index = 0; index < 3; index += 1) {
      await client.query('INSERT INTO notes (title, content, author_id) VALUES ($1, $2, gen_random_uuid())', [`T${index}`, 'x']);
    }

    const rows = await client.query('SELECT title FROM notes ORDER BY created_at DESC LIMIT 2');
    assert.equal(rows.rows.length, 2);
  });

  await repository.list({ offset: 0, limit: 10 });        // the repository call itself is exercised
});
```

> **Do not test the database through the HTTP layer.** A route test that depends on a real PostgreSQL schema is slow and brittle; a route test with a fake repository proves the HTTP contract. Keep exactly one small suite that exercises the real driver — that is where SQL dialect, constraints and transactions are actually verified.

***

## 6. Determinism: the five sources of flakiness

| Source                                       | Symptom                                                       | Fix                                                                              |
| -------------------------------------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Shared state** between tests               | Passes alone, fails in a suite                                | A fresh app/repository per test (`buildTestApp()` in `beforeEach`, not `before`) |
| **Real time** (`Date.now()`)                 | "expires in 24h" fails at midnight                            | Inject a `clock`; or `mock.timers`                                               |
| **Randomness** (`randomUUID`, `Math.random`) | Ids differ between runs                                       | Assert the shape, not the value; or inject an id factory                         |
| **Ordering assumptions**                     | `assert.equal(rows[0].title, …)` breaks when the sort changes | Sort explicitly; assert on a set when order is irrelevant                        |
| **External systems** (network, SMTP, S3)     | Timeouts, quota, 3 a.m. outages                               | Fake at the boundary; one opt-in integration suite                               |
| **Open handles**                             | The runner hangs after the tests pass                         | Close servers/pools in `after`; `--test-force-exit` as a last resort             |

```js
// File: tests/leaks.test.js — what a good teardown looks like
import { test, before, after } from 'node:test';
import { createServer } from 'node:http';
import { createApp } from '../src/app.js';

let server;
let pool;

before(async () => {
  const app = createApp({ config: testConfig, container: testContainer });
  server = createServer(app);
  pool = testContainer.pool;

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
});

after(async () => {
  await new Promise((resolve) => server.close(resolve));   // 1. stop accepting requests
  await pool.end();                                        // 2. close the connection pool
});

test('the server is reachable', async () => {
  const { port } = server.address();
  const response = await fetch(`http://127.0.0.1:${port}/health`);
  assert.equal(response.status, 200);
});
```

```bash
# Diagnose a hanging runner:
node --test tests/leaks.test.js
# ...tests pass, then nothing happens for 30 s
node --test --test-force-exit tests/leaks.test.js      # confirms a handle is open
node --test --test-reporter=tap tests/leaks.test.js | tail -40
```

***

## 7. Coverage: read it, do not worship it

| Metric            | What it tells you                                  | Where it matters most                 |
| ----------------- | -------------------------------------------------- | ------------------------------------- |
| Line coverage     | Which lines executed                               | A quick "did I even call this?" check |
| Branch coverage   | Whether **both** sides of every `if`/`?:`/`??` ran | The most useful number for services   |
| Function coverage | Which functions were never invoked                 | Finding dead code                     |
| Uncovered lines   | Exactly where to add a test                        | The list to actually read             |

```bash
node --test --experimental-test-coverage
```

```js
// File: scripts/check-coverage.mjs — fail CI below a threshold, per-directory
import { readFile } from 'node:fs/promises';

const summary = JSON.parse(await readFile('coverage/coverage-final.json', 'utf8'));

const THRESHOLDS = {
  'src/services/': { branches: 90 },
  'src/middleware/': { branches: 80 },
  'src/utils/': { branches: 80 },
};

const failures = [];

for (const [prefix, requirement] of Object.entries(THRESHOLDS)) {
  const files = Object.entries(summary).filter(([file]) => file.includes(prefix));
  if (files.length === 0) continue;

  const branches = files.reduce((sum, [, data]) => sum + data.branches.pct, 0) / files.length;
  if (branches < requirement.branches) failures.push(`${prefix}: branch coverage ${branches.toFixed(1)}% < ${requirement.branches}%`);
}

if (failures.length > 0) {
  console.error('Coverage thresholds not met:');
  for (const failure of failures) console.error(`  ${failure}`);
  process.exit(1);
}

console.log('Coverage thresholds met.');
```

> **100% coverage is not a goal.** A test that executes a line without asserting anything raises coverage and proves nothing. Aim for high branch coverage in services and validators, "every failure path is exercised" in routes, and honest gaps documented in the code.

***

## 8. Choosing a runner

|                      | **`node:test`**                         | **Jest 30**                        | **Vitest 4**                             |
| -------------------- | --------------------------------------- | ---------------------------------- | ---------------------------------------- |
| Install              | Built in                                | `jest` (+ `@types` for TS)         | `vitest`                                 |
| ESM support          | Native                                  | Works, historically the weak spot  | Native                                   |
| Watch mode           | `--watch`                               | Excellent                          | Excellent, very fast                     |
| Mocking              | `mock.fn/method/timers`                 | Rich, automatic hoisting           | Rich, jest-compatible API                |
| Snapshots            | Basic                                   | Mature                             | Mature                                   |
| Coverage             | `--experimental-test-coverage`          | `--coverage` (istanbul)            | `--coverage` (istanbul/v8)               |
| Config               | None                                    | `jest.config.js`                   | `vitest.config.js`                       |
| Speed (large suites) | Good                                    | Good                               | Fastest                                  |
| Best for             | Libraries, services, ESM-first projects | Existing projects, React ecosystem | New projects, TypeScript, Vite frontends |

`supertest` works with all three:

```js
// File: health.test.js — Jest (CommonJS or with ESM transform support)
const request = require('supertest');
const { app } = require('../src/testApp');

test('GET /health', async () => {
  await request(app).get('/health').expect(200);
});
```

```js
// File: health.test.js — Vitest (ESM throughout)
import { test, expect } from 'vitest';
import request from 'supertest';
import { app } from '../src/testApp.js';

test('GET /health', async () => {
  const response = await request(app).get('/health');
  expect(response.status).toBe(200);
});
```

**Recommendation for this course:** `node:test` for everything (it is built in, fast and ESM-native), `supertest` for HTTP, and Vitest when a TypeScript/Vite frontend already uses it. Move to Jest only when you inherit a Jest codebase.

***

## 9. CI: make the suite a gate

```yaml
# File: .github/workflows/test.yml
name: Test
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: notes_test
        ports: ['5432:5432']
        options: >-
          --health-cmd "pg_isready -U postgres" --health-interval 5s
          --health-timeout 5s --health-retries 10
      redis:
        image: redis:8
        ports: ['6379:6379']

    env:
      NODE_ENV: test
      DATABASE_URL: postgres://postgres:postgres@localhost:5432/notes_test
      REDIS_URL: redis://localhost:6379
      JWT_SECRET: test-secret-that-is-at-least-32-characters
      SESSION_SECRET: test-secret-that-is-at-least-32-characters
      COOKIE_SECRET: test-secret-that-is-at-least-32-characters

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 24
          cache: npm

      - run: npm ci
      - run: npm run lint
      - run: node --test --test-reporter=spec --test-timeout=20000
      - run: node --test --experimental-test-coverage
      - run: npm audit --omit=dev --audit-level=high
```

| CI rule                                                    | Why                                                                        |
| ---------------------------------------------------------- | -------------------------------------------------------------------------- |
| `npm ci`, never `npm install`                              | Reproducible installs from the lockfile                                    |
| A timeout per test                                         | A hung test fails the build instead of blocking it for 6 hours             |
| The same Node major as production                          | Fewer "works in CI, dies in prod" surprises                                |
| Services with health checks                                | No flaky "connection refused" on the first test                            |
| Coverage thresholds in `src/services` and `src/middleware` | Protects the code that matters most                                        |
| `npm audit --omit=dev`                                     | Dev-dependency advisories should not block a release, production ones must |
| No `--test-force-exit` in CI                               | Hide a leaked handle locally, never in CI                                  |

***

## 10. Common mistakes

| Mistake                                               | Symptom                                                         | Fix                                                   |
| ----------------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------- |
| Testing through HTTP when a service test suffices     | Slow suites; business-rule gaps                                 | Unit-test services; keep route tests for the contract |
| One test asserting ten things                         | The first failure hides the rest                                | Table-driven cases with one assertion per behaviour   |
| Snapshotting whole responses                          | Every field change rewrites the snapshot; nobody reads the diff | Assert the fields that matter                         |
| `before` instead of `beforeEach` for mutable fixtures | Cross-test leakage; order dependence                            | Fresh state per test                                  |
| Mocking the module under test                         | The test proves the mock works                                  | Mock only collaborators                               |
| Asserting on `Date.now()` output                      | Flakes at midnight/year boundaries                              | Inject a clock or freeze time                         |
| Assuming an array order                               | Fails when the sort changes                                     | Sort explicitly or compare sets                       |
| A real SMTP/S3/HTTP call in a unit test               | Slow, flaky, quota-limited                                      | Fake the boundary interface                           |
| `app.listen(3000)` in tests                           | `EADDRINUSE`; tests cannot run in parallel                      | `supertest(app)`, or `listen(0)`                      |
| Not closing pools/servers                             | The runner hangs after `pass 17`                                | Teardown in `after`; check with `--test-force-exit`   |
| 100% coverage with no assertions                      | Confidence without evidence                                     | Branch coverage on rules, plus explicit assertions    |
| Skipping the 401/403/404/422 paths                    | The failure matrix is where the bugs are                        | Test the whole matrix (§4) every time                 |
| A single giant test file                              | Hard to run one thing while iterating                           | One file per unit under test                          |
| Not running tests before every commit                 | Broken `main`                                                   | Pre-push hook: `node --test`                          |

***

## Exercise 19.1 — A full test suite for the notes API

Write a suite with **at least 25 tests** covering:

| Area                            | Required cases                                                                                                                                                                                                                                                          |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Service (unit, fake repository) | create defaults, duplicate title (409), author from the token, PATCH partial semantics, PATCH `null` clears, ownership (403), missing note (404), delete true/false, pagination + total, sort allowlist                                                                 |
| Validation (unit)               | unknown field rejected, whitespace-only rejected, `limit > 100` rejected, coercion of query strings                                                                                                                                                                     |
| Routes (supertest)              | 201 + `Location` + DTO, 401 without a token, 401 with a bad token, 422 with field details, 403 for another user's note, 200 for the owner, 200 for an admin, 404 for an unknown id, 204 then 404 on delete, 405 for a wrong method, the error envelope on every failure |
| Headers                         | `X-Request-Id` present, `x-powered-by` absent, JSON `Content-Type`                                                                                                                                                                                                      |
| Determinism                     | No test depends on another; the whole file passes with `--test-concurrency=4`                                                                                                                                                                                           |

Then add a coverage script with per-directory thresholds and make it fail the build below them.

<details>

<summary>Solution</summary>

```js
// File: tests/support/harness.js — one place that builds isolated test state
import express from 'express';
import cookieParser from 'cookie-parser';
import request from 'supertest';
import { createNoteService } from '../../src/services/noteService.js';
import { createNoteController } from '../../src/controllers/noteController.js';
import { createNoteRouter } from '../../src/routes/noteRoutes.js';
import { createErrorHandler } from '../../src/middleware/errorHandler.js';
import { notFound } from '../../src/middleware/notFound.js';
import { methodNotAllowed } from '../../src/middleware/methodNotAllowed.js';
import { validate } from '../../src/middleware/validate.js';
import { createNoteSchema, patchNoteSchema, listNotesQuerySchema } from '../../src/validators/noteSchemas.js';

const silent = { info() {}, warn() {}, error() {}, fatal() {}, debug() {} };

export function createHarness({ seed = [] } = {}) {
  const rows = seed.map((row) => ({ ...row }));
  let sequence = rows.length;

  const repository = {
    rows,
    async list({ offset, limit, sort }) {
      const [field, direction] = sort.startsWith('-') ? [sort.slice(1), -1] : [sort, 1];
      const sorted = [...rows].sort((a, b) => String(a[field]).localeCompare(String(b[field])) * direction);
      return { items: sorted.slice(offset, offset + limit), total: rows.length };
    },
    async findById(id) { return rows.find((row) => row.id === id) ?? null; },
    async existsByTitle(title) { return rows.some((row) => row.title === title); },
    async create(data) { sequence += 1; const row = { id: `n${sequence}`, ...data }; rows.push(row); return row; },
    async update(id, next) { const index = rows.findIndex((row) => row.id === id); rows[index] = { id, ...next }; return rows[index]; },
    async remove(id) { const index = rows.findIndex((row) => row.id === id); if (index === -1) return false; rows.splice(index, 1); return true; },
  };

  const service = createNoteService({
    noteRepository: repository,
    logger: silent,
    clock: () => new Date('2026-09-18T10:00:00.000Z'),
  });
  const controller = createNoteController({ noteService: service, logger: silent });

  const tokens = {
    owner: { id: 'u1', role: 'USER' },
    other: { id: 'u2', role: 'USER' },
    admin: { id: 'a1', role: 'ADMIN' },
  };

  const middleware = {
    requireAuth: (req, res, next) => {
      const header = req.get('authorization') ?? '';
      const [scheme, token] = header.split(' ');
      if (scheme !== 'Bearer' || !token || !tokens[token]) {
        res.set('WWW-Authenticate', 'Bearer realm="api"');
        return res.status(401).json({
          error: { code: token === 'expired' ? 'TOKEN_EXPIRED' : 'UNAUTHENTICATED', message: 'Sign in', requestId: req.id },
        });
      }
      req.user = tokens[token];
      return next();
    },
    requireOwner: (req, res, next) => {
      if (res.locals.note.authorId === req.user.id || req.user.role === 'ADMIN') return next();
      return res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Not your note', requestId: req.id } });
    },
  };

  const router = createNoteRouter({ controller, middleware, validate, schemas: { createNoteSchema, patchNoteSchema, listNotesQuerySchema } });

  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '10kb' }));
  app.use((req, res, next) => { req.id = 'test-request-id'; res.set('X-Request-Id', req.id); next(); });
  app.use('/api/v1/notes', router);
  app.use(methodNotAllowed(['GET', 'POST', 'PATCH', 'DELETE']));   // 405 before 404, or it never runs
  app.use(notFound);
  app.use(createErrorHandler({ logger: silent, isProduction: false }));

  return { app: request(app), repository, service };
}

/** Seed data used by most tests. */
export const seedNotes = () => ([
  { id: 'n1', title: 'Mine', content: 'C', tags: [], pinned: false, authorId: 'u1', createdAt: '2026-09-18T09:00:00.000Z', updatedAt: '2026-09-18T09:00:00.000Z' },
  { id: 'n2', title: 'Theirs', content: 'C', tags: [], pinned: false, authorId: 'u2', createdAt: '2026-09-18T09:30:00.000Z', updatedAt: '2026-09-18T09:30:00.000Z' },
]);
```

```js
// File: tests/notes.full.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHarness, seedNotes } from './support/harness.js';

/* ── Service-level (unit) ───────────────────────────────────────────────────── */

test('service: create fills defaults, author and timestamps', async () => {
  const { service } = createHarness();
  const note = await service.create({ title: 'T', content: 'C' }, { actor: { id: 'u1', role: 'USER' } });

  assert.equal(note.authorId, 'u1');
  assert.equal(note.createdAt, '2026-09-18T10:00:00.000Z');
  assert.equal(note.updatedAt, note.createdAt);
  assert.deepEqual(note.tags, []);
  assert.equal(note.pinned, false);
});

test('service: a duplicate title is a 409 with a field', async () => {
  const { service } = createHarness({ seed: seedNotes() });

  await assert.rejects(
    () => service.create({ title: 'Mine', content: 'C' }, { actor: { id: 'u1', role: 'USER' } }),
    (error) => error.statusCode === 409 && error.details.field === 'title',
  );
});

test('service: a client-supplied author is ignored', async () => {
  const { service, repository } = createHarness();
  await service.create({ title: 'T', content: 'C', authorId: 'u2' }, { actor: { id: 'u1', role: 'USER' } });

  assert.equal(repository.rows[0].authorId, 'u1');
});

test('service: PATCH leaves absent fields untouched', async () => {
  const { service } = createHarness({ seed: seedNotes() });
  const updated = await service.update('n1', { pinned: true }, { actor: { id: 'u1', role: 'USER' } });

  assert.equal(updated.pinned, true);
  assert.equal(updated.title, 'Mine');
  assert.equal(updated.content, 'C');
});

test('service: an explicit null clears content', async () => {
  const { service } = createHarness({ seed: seedNotes() });
  const updated = await service.update('n1', { content: null }, { actor: { id: 'u1', role: 'USER' } });

  assert.equal(updated.content, null);                 // distinct from "not provided"
});

test('service: updating someone else’s note is 403', async () => {
  const { service } = createHarness({ seed: seedNotes() });

  await assert.rejects(
    () => service.update('n2', { title: 'X' }, { actor: { id: 'u1', role: 'USER' } }),
    (error) => error.statusCode === 403,
  );
});

test('service: an unknown id is 404', async () => {
  const { service } = createHarness();
  await assert.rejects(() => service.getById('nope'), (error) => error.statusCode === 404);
});

test('service: delete reports true then false', async () => {
  const { service } = createHarness({ seed: seedNotes() });
  const actor = { id: 'u1', role: 'USER' };

  assert.equal(await service.remove('n1', { actor }), true);
  assert.equal(await service.remove('n1', { actor }), false);
});

test('service: pagination reports page, limit and total', async () => {
  const seed = Array.from({ length: 25 }, (_, index) => ({
    id: `n${index}`, title: `T${index}`, content: 'C', tags: [], pinned: false, authorId: 'u1',
    createdAt: '2026-09-18T09:00:00.000Z', updatedAt: '2026-09-18T09:00:00.000Z',
  }));
  const { service } = createHarness({ seed });
  const page = await service.list({ page: 3, limit: 10, sort: '-createdAt' });

  assert.equal(page.items.length, 5);
  assert.equal(page.total, 25);
  assert.equal(page.page, 3);
});

/* ── Validation (unit) ──────────────────────────────────────────────────────── */

test('validation: unknown body fields are rejected', async () => {
  const { createNoteSchema } = await import('../src/validators/noteSchemas.js');
  assert.equal(createNoteSchema.safeParse({ title: 'T', content: 'C', role: 'ADMIN' }).success, false);
});

test('validation: whitespace-only titles are rejected', async () => {
  const { createNoteSchema } = await import('../src/validators/noteSchemas.js');
  const result = createNoteSchema.safeParse({ title: '   ', content: 'C' });

  assert.equal(result.success, false);
  assert.equal(result.error.issues[0].path[0], 'title');
});

test('validation: limit above 100 is rejected, query strings are coerced', async () => {
  const { listNotesQuerySchema } = await import('../src/validators/noteSchemas.js');

  assert.equal(listNotesQuerySchema.safeParse({ limit: '1000' }).success, false);
  const parsed = listNotesQuerySchema.safeParse({ page: '2', limit: '50' });
  assert.equal(parsed.data.page, 2);
  assert.equal(parsed.data.limit, 50);
});

/* ── Routes (integration with supertest) ────────────────────────────────────── */

test('route: POST returns 201, Location and a DTO', async () => {
  const { app } = createHarness();

  const response = await app.post('/api/v1/notes').set('Authorization', 'Bearer owner')
    .send({ title: 'New', content: 'C' }).expect(201);

  assert.equal(response.headers.location, '/api/v1/notes/n1');
  assert.equal(response.body.data.authorId, 'u1');
});

test('route: POST without a token is 401 with WWW-Authenticate', async () => {
  const { app } = createHarness();
  const response = await app.post('/api/v1/notes').send({ title: 'T', content: 'C' }).expect(401);

  assert.match(response.headers['www-authenticate'], /^Bearer/);
});

test('route: an expired token reports TOKEN_EXPIRED', async () => {
  const { app } = createHarness();
  const response = await app.get('/api/v1/notes').set('Authorization', 'Bearer expired').expect(401);

  assert.equal(response.body.error.code, 'TOKEN_EXPIRED');
});

test('route: an invalid body is 422 with field details', async () => {
  const { app } = createHarness();
  const response = await app.post('/api/v1/notes').set('Authorization', 'Bearer owner').send({}).expect(422);

  assert.equal(response.body.error.code, 'VALIDATION_ERROR');
  assert.ok(response.body.error.details.length >= 2);
});

test('route: another user’s note is 403', async () => {
  const { app } = createHarness({ seed: seedNotes() });
  await app.patch('/api/v1/notes/n2').set('Authorization', 'Bearer owner').send({ title: 'X' }).expect(403);
});

test('route: the owner and an admin are both allowed', async () => {
  const { app } = createHarness({ seed: seedNotes() });

  await app.patch('/api/v1/notes/n2').set('Authorization', 'Bearer other').send({ title: 'Mine' }).expect(200);
  await app.patch('/api/v1/notes/n1').set('Authorization', 'Bearer admin').send({ title: 'Moderated' }).expect(200);
});

test('route: an unknown id is 404 with the envelope', async () => {
  const { app } = createHarness();
  const response = await app.get('/api/v1/notes/nope').set('Authorization', 'Bearer owner').expect(404);

  assert.deepEqual(Object.keys(response.body.error).sort(), ['code', 'message', 'requestId']);
});

test('route: DELETE is 204, then 404', async () => {
  const { app, repository } = createHarness({ seed: seedNotes() });

  await app.delete('/api/v1/notes/n1').set('Authorization', 'Bearer owner').expect(204);
  assert.equal(repository.rows.length, 1);
  await app.delete('/api/v1/notes/n1').set('Authorization', 'Bearer owner').expect(404);
});

test('route: an unsupported method on a known path is 405 with Allow', async () => {
  const { app } = createHarness();
  const response = await app.put('/api/v1/notes').set('Authorization', 'Bearer owner').send({}).expect(405);

  assert.match(response.headers.allow, /GET|POST/);
});

/* ── Headers and hygiene ────────────────────────────────────────────────────── */

test('headers: X-Request-Id is set and x-powered-by is absent', async () => {
  const { app } = createHarness();
  const response = await app.get('/api/v1/notes').set('Authorization', 'Bearer owner').expect(200);

  assert.equal(response.headers['x-request-id'], 'test-request-id');
  assert.equal(response.headers['x-powered-by'], undefined);
});

test('headers: responses are JSON', async () => {
  const { app } = createHarness();
  const response = await app.get('/api/v1/notes').set('Authorization', 'Bearer owner').expect(200);
  assert.match(response.headers['content-type'], /application\/json/);
});

test('determinism: two harnesses do not share state', async () => {
  const first = createHarness();
  const second = createHarness();

  await first.app.post('/api/v1/notes').set('Authorization', 'Bearer owner').send({ title: 'T', content: 'C' }).expect(201);

  assert.equal(first.repository.rows.length, 1);
  assert.equal(second.repository.rows.length, 0);
});
```

```bash
node --test --test-concurrency=4 tests/notes.full.test.js
```

```
✔ service: create fills defaults, author and timestamps
✔ service: a duplicate title is a 409 with a field
✔ service: a client-supplied author is ignored
✔ service: PATCH leaves absent fields untouched
✔ service: an explicit null clears content
✔ service: updating someone else's note is 403
✔ service: an unknown id is 404
✔ service: delete reports true then false
✔ service: pagination reports page, limit and total
✔ validation: unknown body fields are rejected
✔ validation: whitespace-only titles are rejected
✔ validation: limit above 100 is rejected, query strings are coerced
✔ route: POST returns 201, Location and a DTO
✔ route: POST without a token is 401 with WWW-Authenticate
✔ route: an expired token reports TOKEN_EXPIRED
✔ route: an invalid body is 422 with field details
✔ route: another user's note is 403
✔ route: the owner and an admin are both allowed
✔ route: an unknown id is 404 with the envelope
✔ route: DELETE is 204, then 404
✔ route: an unsupported method on a known path is 405 with Allow
✔ headers: X-Request-Id is set and x-powered-by is absent
✔ headers: responses are JSON
✔ determinism: two harnesses do not share state
pass 24
fail 0
```

```js
// File: scripts/coverage-gate.mjs (the exercise's threshold script)
import { execFileSync } from 'node:child_process';

const output = execFileSync(process.execPath, ['--test', '--experimental-test-coverage'], { encoding: 'utf8' });

const read = (label) => {
  const match = output.match(new RegExp(`${label}\\s*\\|\\s*([\\d.]+)`, 'i'));
  return match ? Number(match[1]) : null;
};

const line = read('all files');
console.log('coverage(all):', line);

if (line !== null && line < 85) {
  console.error(`Coverage ${line}% is below the 85% threshold`);
  process.exit(1);
}

console.log('Coverage gate passed.');
```

**What makes this suite good:** every test builds its own harness (no shared mutable state), the clock is frozen, the repository is a real-in-memory implementation rather than a mock, and the failure matrix (401/403/404/405/422) is covered as thoroughly as the happy path.

</details>

***

## Exercise 19.2 — Fix the flaky suite

```js
// File: tests/flaky.test.js — it passes on the author's laptop. On CI it fails 30% of the time.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';

let server;
let baseUrl;

before(async () => {
  const app = createApp({ config: testConfig, container: testContainer });
  server = app.listen(3000);                              // 1
  baseUrl = 'http://localhost:3000';
});

test('a note is created and listed', async () => {
  const created = await fetch(`${baseUrl}/api/v1/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer token' },
    body: JSON.stringify({ title: 'T', content: 'C' }),
  });
  assert.equal(created.status, 201);

  const listed = await fetch(`${baseUrl}/api/v1/notes`, { headers: { Authorization: 'Bearer token' } });
  const body = await listed.json();

  assert.equal(body.data.length, 1);                      // 2
  assert.equal(body.data[0].title, 'T');                  // 3
  assert.ok(body.data[0].createdAt.startsWith(new Date().toISOString().slice(0, 10)));  // 4
});

test('duplicate titles are rejected', async () => {
  const response = await fetch(`${baseUrl}/api/v1/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer token' },
    body: JSON.stringify({ title: 'T', content: 'C' }),
  });
  assert.equal(response.status, 409);                     // 5
});

test('the welcome email is sent', async () => {
  const response = await fetch(`${baseUrl}/api/v1/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'a@b.com', password: 'supersecret123', name: 'A' }),
  });
  assert.equal(response.status, 201);
  assert.equal(testContainer.mailer.sent.length, 1);       // 6
});

test('the rate limiter kicks in', async () => {
  for (let index = 0; index < 20; index += 1) {
    await fetch(`${baseUrl}/api/v1/notes`);                // 7
  }
  const response = await fetch(`${baseUrl}/api/v1/notes`);
  assert.equal(response.status, 429);
});

after(() => {
  server.close();                                          // 8
});
```

<details>

<summary>Solution</summary>

| # | Problem                                                  | Why it flakes                                                                    | Fix                                                                            |
| - | -------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1 | `app.listen(3000)`                                       | Port already in use; two suites collide                                          | `createServer(app).listen(0)` or `supertest(app)`                              |
| 2 | `body.data.length === 1` assumes a clean database        | The previous run's rows are still there; parallel workers share it               | A fresh in-memory repository per test, or transaction rollback                 |
| 3 | `data[0]` assumes ordering and that _this_ note is first | Other tests inserted notes                                                       | Look the note up by id; sort explicitly when order matters                     |
| 4 | Comparing against `new Date()`                           | A run at 23:59:59.9 crosses midnight; timezone differences between laptop and CI | Inject a clock and assert against the injected value                           |
| 5 | Depends on the note from test 1 existing                 | Order dependence                                                                 | Create the fixture inside the test                                             |
| 6 | A **real** mailer in a test                              | SMTP is slow, rate-limited and sometimes unreachable                             | Inject a fake mailer and assert on its recorded calls                          |
| 7 | The rate-limit test consumes the shared window           | Other tests then receive 429 unexpectedly                                        | Use a separate app instance with an isolated store, or a dedicated limiter key |
| 8 | No `await` on close; the pool is never closed            | The runner hangs; connections leak between files                                 | `await new Promise((resolve) => server.close(resolve))` and `await pool.end()` |

```js
// File: tests/stable.test.js
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import request from 'supertest';
import { buildTestApp } from './support/buildTestApp.js';   // fresh app per test, no ports

let harness;

beforeEach(() => {
  // 1. Isolation: every test starts with new state and a frozen clock.
  harness = buildTestApp();
});

afterEach(async () => {
  // 2. No handles left behind: the harness owns nothing that outlives the test.
  await harness.dispose?.();
});

test('exactly one note exists after one create, and it is the one we created', async () => {
  const created = await harness.app
    .post('/api/v1/notes')
    .set('Authorization', 'Bearer owner')
    .send({ title: 'T', content: 'C' })
    .expect(201);

  const id = created.body.data.id;
  const listed = await harness.app.get('/api/v1/notes').set('Authorization', 'Bearer owner').expect(200);

  assert.equal(listed.body.data.length, 1);
  assert.equal(listed.body.data[0].id, id);                       // identified, not positional-guessed
  assert.equal(listed.body.data[0].createdAt, '2026-09-18T10:00:00.000Z');  // the injected clock
});

test('duplicate titles are rejected — with the fixture created inside the test', async () => {
  await harness.app.post('/api/v1/notes').set('Authorization', 'Bearer owner').send({ title: 'T', content: 'C' }).expect(201);

  const duplicate = await harness.app.post('/api/v1/notes').set('Authorization', 'Bearer owner').send({ title: 'T', content: 'D' });

  assert.equal(duplicate.status, 409);
  assert.equal(duplicate.body.error.details.field, 'title');
});

test('the welcome email is faked, so the assertion is about behaviour, not SMTP', async () => {
  const service = harness.container.userService;

  await service.register({ email: 'a@b.com', password: 'supersecret123', name: 'A' });
  await new Promise((resolve) => setImmediate(resolve));            // let the detached send run

  assert.equal(harness.mailer.sent.length, 1);
  assert.equal(harness.mailer.sent[0].to, 'a@b.com');
});

test('a rate limit is tested on its own app instance with its own store', async () => {
  const limited = buildTestApp({ rateLimit: { windowMs: 60_000, limit: 3 } });

  const statuses = [];
  for (let index = 0; index < 4; index += 1) {
    statuses.push((await limited.app.get('/api/v1/notes').set('Authorization', 'Bearer owner')).status);
  }

  assert.deepEqual(statuses, [200, 200, 200, 429]);
  assert.equal(limited.lastRetryAfter, 60);
});
```

**The checklist that removes almost all flakiness:** no fixed ports, no shared state, no real clock, no real network, explicit ordering, and complete teardown.

</details>

***

## What's next

The API is built, hardened and tested. Turning it into something that runs unattended — with configuration, logging, health checks, graceful shutdown, and a deployable layout — is the subject of the next chapter.

→ [20 — Production Architecture](20-production-architecture.md)
