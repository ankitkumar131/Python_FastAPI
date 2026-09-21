# 11 — Services

> **Where this fits:** Controllers are HTTP adapters. Repositories talk to the database. **Services are where your application actually lives**: the rules, the invariants, the orchestration and the transactions. If a rule exists in two endpoints, it belongs here.

***

## 1. What a service is

> **A service is a plain JavaScript object (or module) that implements one slice of business logic. It receives plain values, calls repositories or other services, and returns plain values or throws typed errors. It knows nothing about HTTP.**

```js
// File: src/services/noteService.js
import { ConflictError, NotFoundError, ForbiddenError } from '../utils/AppError.js';

export function createNoteService({ noteRepository, logger }) {
  return {
    async list({ page, limit, sort, tags, q }) {
      const { items, total } = await noteRepository.list({
        offset: (page - 1) * limit,
        limit,
        sort,
        tags,
        q,
      });
      return { items, total, page, limit };
    },

    async getById(id) {
      return noteRepository.findById(id);        // null is a valid "not found" answer
    },

    async create(input, { actor }) {
      // A rule that needs data: uniqueness.
      if (await noteRepository.existsByTitle(input.title)) {
        throw new ConflictError('A note with that title already exists', { field: 'title' });
      }

      const now = new Date().toISOString();
      const note = await noteRepository.create({
        title: input.title,
        content: input.content,
        tags: input.tags ?? [],
        pinned: false,
        authorId: actor.id,                      // identity comes from the caller's token
        createdAt: now,
        updatedAt: now,
      });

      logger.info('note created', { noteId: note.id, authorId: actor.id });
      return note;
    },

    async update(id, patch, { actor }) {
      const current = await noteRepository.findById(id);
      if (!current) throw new NotFoundError(`Note ${id} not found`);

      // A rule that needs the data: only the author may edit.
      if (current.authorId !== actor.id && actor.role !== 'ADMIN') {
        throw new ForbiddenError('You can only edit your own notes');
      }

      const next = { ...current, updatedAt: new Date().toISOString() };
      for (const key of ['title', 'content', 'tags', 'pinned']) {
        if (Object.hasOwn(patch, key)) next[key] = patch[key];
      }

      return noteRepository.update(id, next);
    },

    async remove(id, { actor }) {
      const current = await noteRepository.findById(id);
      if (!current) throw new NotFoundError(`Note ${id} not found`);
      if (current.authorId !== actor.id && actor.role !== 'ADMIN') {
        throw new ForbiddenError('You can only delete your own notes');
      }
      await noteRepository.remove(id);
      return true;
    },
  };
}
```

Note what is **absent**: `req`, `res`, status codes, `res.json`, headers, SQL, and the shape of the response body. Every one of those belongs to another layer.

***

## 2. The three layers, and who owns what

```
route ──▶ controller ──▶ service ──▶ repository ──▶ database
  URL      HTTP shape     RULES       queries        storage
```

| Question                            | Controller   | Service             | Repository          |
| ----------------------------------- | ------------ | ------------------- | ------------------- |
| Is `title` a string ≤ 200 chars?    | ✗ middleware | ✗                   | ✗                   |
| Is this email already taken?        | ✗            | **✓**               | ✗ (it only reports) |
| Can this user delete this note?     | ✗            | **✓**               | ✗                   |
| What status code means "conflict"?  | **✓**        | ✗                   | ✗                   |
| Which fields does the client see?   | **✓** (DTO)  | ✗                   | ✗                   |
| What happens when a coupon expires? | ✗            | **✓**               | ✗                   |
| How do we query notes by tag?       | ✗            | ✗                   | **✓**               |
| Is a transaction needed?            | ✗            | **✓** (decides)     | ✓ (executes)        |
| What is logged for an audit trail?  | request info | **✓** domain events | ✗                   |

Rules of thumb:

1. **If it needs data to decide something, it is a rule → service.**
2. **If it needs `req`/`res`, it is HTTP → controller/middleware.**
3. **If it is a query or a write, it is data access → repository.**
4. **If two endpoints must behave identically, the shared code is a service.**

***

## 3. Service anatomy and dependency injection

```js
// File: src/services/userService.js
import { ConflictError, NotFoundError } from '../utils/AppError.js';

export function createUserService({
  userRepository,          // data access
  passwordHasher,          // a policy object: hash() and compare()
  mailer,                  // side effects
  logger = console,
  clock = () => new Date(), // injectable time — makes tests deterministic
}) {
  return {
    async register({ email, password, name }) {
      if (await userRepository.existsByEmail(email)) {
        throw new ConflictError('That email is already registered', { field: 'email' });
      }

      const user = await userRepository.create({
        email,
        name,
        passwordHash: await passwordHasher.hash(password),
        role: 'USER',                          // never client-supplied
        createdAt: clock().toISOString(),
      });

      // Side effects happen AFTER the write, and must never fail the registration.
      void mailer
        .sendWelcome(user)
        .catch((error) => logger.error('welcome email failed', { userId: user.id, error: error.message }));

      return { id: user.id, email: user.email, name: user.name, createdAt: user.createdAt };
    },

    async authenticate({ email, password }) {
      const user = await userRepository.findByEmail(email);

      // Always run a comparison, even for an unknown user, so timing does not reveal existence.
      const hash = user?.passwordHash ?? '$2a$12$invalidinvalidinvalidinvalidinvalidinvalidinvalidinvalidin';
      const ok = await passwordHasher.compare(password, hash);

      if (!user || !ok) return null;            // the controller turns null into 401
      return { id: user.id, role: user.role };
    },

    async getProfile(id) {
      const user = await userRepository.findById(id);
      if (!user) throw new NotFoundError(`User ${id} not found`);
      return { id: user.id, email: user.email, name: user.name, role: user.role };
    },
  };
}
```

**Why dependency injection rather than imports?**

```js
// ❌ Hard-wired: importing the real repository, mailer and clock.
import { userRepository } from '../repositories/userRepository.js';
import { mailer } from '../mailer.js';

export async function register({ email, password }) {
  const user = await userRepository.create({ email, password, createdAt: new Date().toISOString() });
  await mailer.sendWelcome(user);              // a real email in every test!
  return user;
}
```

| Hard-wired imports                                      | Injected dependencies                     |
| ------------------------------------------------------- | ----------------------------------------- |
| Every unit test sends email                             | Tests pass a fake mailer in one line      |
| Tests depend on the database                            | Tests pass an in-memory repository        |
| Time-dependent tests are flaky ("expires in 24h")       | `clock` is passed in; tests control time  |
| Circular import risk between services                   | Composition happens in one container file |
| Cannot reuse the service in a job with different config | Same service, different dependencies      |

```js
// File: src/container.js — the composition root: the ONE place that wires everything together
import { createUserRepository } from './repositories/userRepository.js';
import { createNoteRepository } from './repositories/noteRepository.js';
import { createUserService } from './services/userService.js';
import { createNoteService } from './services/noteService.js';
import { createUserController } from './controllers/userController.js';
import { createNoteController } from './controllers/noteController.js';
import { createPasswordHasher } from './utils/passwordHasher.js';
import { createMailer } from './utils/mailer.js';
import { db } from './database/client.js';
import { logger } from './utils/logger.js';
import { env } from './config/env.js';

export function createContainer({ config = env, log = logger } = {}) {
  // ── Infrastructure ────────────────────────────────────────────────────────────
  const passwordHasher = createPasswordHasher({ rounds: config.bcryptRounds });
  const mailer = createMailer({ apiKey: config.mailApiKey, from: config.mailFrom });

  // ── Repositories ──────────────────────────────────────────────────────────────
  const userRepository = createUserRepository({ db });
  const noteRepository = createNoteRepository({ db });

  // ── Services ──────────────────────────────────────────────────────────────────
  const userService = createUserService({ userRepository, passwordHasher, mailer, logger: log });
  const noteService = createNoteService({ noteRepository, logger: log });

  // ── Controllers ───────────────────────────────────────────────────────────────
  const userController = createUserController({ userService, logger: log });
  const noteController = createNoteController({ noteService, logger: log });

  return { userService, noteService, userController, noteController, userRepository, noteRepository };
}
```

```js
// File: src/app.js (excerpt) — the app receives the container, it does not build it
export function createApp({ config, container, middleware }) {
  const app = express();
  app.use('/api/v1', createApiRouter({ controllers: container, middleware }));
  return app;
}
```

> **Why a container and not a DI framework?** A 30-line function is easier to read, has no decorators or metadata, and shows the entire dependency graph in one screen. Frameworks like NestJS or Awilix add value at a scale this API does not have.

***

## 4. What belongs in a service

| Belongs in a service                        | Example                                                         |
| ------------------------------------------- | --------------------------------------------------------------- |
| Invariants and rules                        | "Tags are lowercased and capped at 10"                          |
| Rules that need data                        | "Email must be unique", "only the author may edit"              |
| State machines                              | `draft → published → archived`, and which transitions are legal |
| Calculations                                | Pricing, discounts, tax, pro-rating, scoring                    |
| Multi-step orchestration                    | Create an order → decrement stock → record a ledger entry       |
| Transactions                                | "All of it, or none of it"                                      |
| Idempotency                                 | "The same key must not create two payments"                     |
| Domain events                               | Emitting `note.created` for other parts of the system           |
| Authorisation that depends on the data      | "Can this user edit _this_ note?"                               |
| Value normalisation that is domain-specific | Slug generation, currency rounding to cents                     |

| Does **not** belong in a service           | Where it goes                                      |
| ------------------------------------------ | -------------------------------------------------- |
| `req.query.limit` parsing                  | Validation middleware                              |
| `res.status(409)`                          | The controller (via `AppError` → error middleware) |
| SQL/`findOne`/`$inc`                       | The repository                                     |
| HTTP status codes as return values         | The controller's mapping table                     |
| Response-shaped objects (`{ data, meta }`) | The controller/DTO                                 |
| `console.log(req.headers)`                 | Structured logging middleware                      |
| Sending a 201 vs 200 decision              | The controller                                     |

***

## 5. Returning versus throwing

Pick one convention and apply it consistently. The convention used here:

| Situation             | Service behaviour                                                   | Controller turns it into     |
| --------------------- | ------------------------------------------------------------------- | ---------------------------- |
| Found                 | return the value                                                    | `200` + DTO                  |
| Not found by id       | **return `null`** (lookup) or **throw `NotFoundError`** (operation) | `404`                        |
| Rule violated         | throw an `AppError` subclass                                        | that status                  |
| Unexpected failure    | let the driver error bubble up                                      | `500` (via `normalizeError`) |
| Deleted nothing       | return `false`                                                      | `404`                        |
| Partially valid input | throw `ValidationError` with `details`                              | `422`                        |

```js
// File: return-vs-throw.js
export function createExampleService({ repository }) {
  return {
    /** LOOKUP: returning null lets the caller decide the outcome. */
    async findById(id) {
      return repository.findById(id);            // null when absent
    },

    /** OPERATION: the caller asked for something specific, so a failure is exceptional. */
    async archive(id) {
      const note = await repository.findById(id);
      if (!note) throw new NotFoundError(`Note ${id} not found`);
      if (note.status === 'archived') throw new ConflictError('Note is already archived');

      return repository.update(id, { ...note, status: 'archived', archivedAt: new Date().toISOString() });
    },

    /** DELETE: a boolean is the honest answer to "did that remove anything?". */
    async remove(id) {
      const removed = await repository.remove(id);
      return removed;                            // controller: true → 204, false → 404
    },
  };
}
```

> **Do not return `undefined`, `null`, `false` and `0` interchangeably.** Each has a meaning: `null` = "looked, nothing there"; `false` = "attempted, changed nothing"; `0` = "counted, found none".

***

## 6. Services calling services, and events

Keep the dependency graph a **tree**, not a spider web:

```
        orderService ──▶ productService
             │           ▲
             ▼           │
        paymentService ──┘           ✔ one direction

        noteService ◀──▶ userService  ✘ circular: neither can be tested or deployed alone
```

```js
// File: src/services/orderService.js (excerpt)
export function createOrderService({ orderRepository, productService, logger }) {
  return {
    async create(input, { actor }) {
      // Delegating a rule to the service that owns it.
      const priced = await productService.priceLines(input.items);

      return orderRepository.create({ ...input, ...priced, userId: actor.id });
    },
  };
}
```

When two services genuinely must react to each other, use **events** rather than a circular import:

```js
// File: src/events/domainEvents.js
import { EventEmitter } from 'node:events';

/** A single, application-wide bus. In a monolith this is enough; later a broker replaces it. */
export const domainEvents = new EventEmitter();

export const EVENTS = Object.freeze({
  USER_REGISTERED: 'user.registered',
  ORDER_PLACED: 'order.placed',
  NOTE_PUBLISHED: 'note.published',
});
```

```js
// File: src/services/orderService.js (excerpt) — publish, do not call
import { domainEvents, EVENTS } from '../events/domainEvents.js';

export function createOrderService({ orderRepository }) {
  return {
    async create(input, { actor }) {
      const order = await orderRepository.create({ ...input, userId: actor.id });

      // Nobody waits for the reaction, and the order does not fail if it throws.
      domainEvents.emit(EVENTS.ORDER_PLACED, { orderId: order.id, userId: actor.id, total: order.total });
      return order;
    },
  };
}
```

```js
// File: src/events/subscribers/onOrderPlaced.js
import { EVENTS } from '../domainEvents.js';

/** Wired once at startup: email, analytics, inventory, whatever the business needs. */
export function registerOrderSubscribers({ domainEvents, mailer, analytics, logger }) {
  domainEvents.on(EVENTS.ORDER_PLACED, async (payload) => {
    try {
      await analytics.track('order_placed', payload);
    } catch (error) {
      logger.error('analytics failed', { orderId: payload.orderId, error: error.message });
    }
  });

  domainEvents.on(EVENTS.ORDER_PLACED, async (payload) => {
    try {
      await mailer.sendOrderConfirmation(payload);
    } catch (error) {
      logger.error('confirmation email failed', { orderId: payload.orderId, error: error.message });
    }
  });
}
```

| Direct call                                | Event                                                    |
| ------------------------------------------ | -------------------------------------------------------- |
| Caller waits; failures propagate           | Fire-and-forget; each subscriber handles its own failure |
| Caller and callee are coupled              | Both sides only know the event name                      |
| Easy to follow                             | Harder to follow (search for the event name)             |
| Right for _required_ work (pricing, stock) | Right for _reactions_ (emails, analytics, webhooks)      |

**Rule:** use events for things that may fail without failing the request. Use direct calls for things that must succeed for the operation to be correct.

***

## 7. Transactions: all-or-nothing

A service decides _what_ must be atomic; the repository _executes_ it.

```js
// File: src/repositories/orderRepository.js (PostgreSQL example — details in 03-databases)
export function createOrderRepository({ db }) {
  return {
    async createWithStockDecrement({ userId, items, subtotal, discount, total }) {
      // One transaction: either the order and every stock decrement happen, or nothing does.
      return db.withTransaction(async (client) => {
        const order = await client.query(
          `INSERT INTO orders (user_id, subtotal, discount, total, status)
           VALUES ($1, $2, $3, $4, 'pending') RETURNING *`,
          [userId, subtotal, discount, total],
        );

        for (const item of items) {
          // Conditional update: the WHERE clause is the concurrency guard.
          const result = await client.query(
            `UPDATE products
                SET stock = stock - $2
              WHERE id = $1 AND stock >= $2
          RETURNING stock`,
            [item.productId, item.quantity],
          );

          if (result.rowCount === 0) {
            // Throwing inside withTransaction rolls everything back.
            throw new ConflictError('Insufficient stock', { productId: item.productId });
          }

          await client.query(
            `INSERT INTO order_items (order_id, product_id, quantity, unit_price)
             VALUES ($1, $2, $3, $4)`,
            [order.id, item.productId, item.quantity, item.unitPrice],
          );
        }

        return order.rows[0];
      });
    },
  };
}
```

```js
// File: src/database/client.js (the helper that makes transactions safe)
export function createDatabase({ pool, logger }) {
  return {
    async query(text, params) {
      return pool.query(text, params);
    },

    /** BEGIN → run → COMMIT, or ROLLBACK on any error. Connection and client are always released. */
    async withTransaction(fn) {
      const client = await pool.connect();
      try {
        await client.query('BEGIN');
        const result = await fn(client);
        await client.query('COMMIT');
        return result;
      } catch (error) {
        await client.query('ROLLBACK');
        logger.warn('transaction rolled back', { message: error.message });
        throw error;
      } finally {
        client.release();
      }
    },
  };
}
```

| Principle                                        | Why                                                         |
| ------------------------------------------------ | ----------------------------------------------------------- |
| The **service** decides transactional boundaries | "These three writes must be atomic" is a business statement |
| The **repository** owns `BEGIN`/`COMMIT`         | Data-layer mechanics; the service must not manage clients   |
| Constraints are the final guard (`stock >= 0`)   | Application checks race; database constraints do not        |
| Keep transactions **short**                      | Long transactions hold locks and block other requests       |
| Never do HTTP calls inside a transaction         | A slow third party would hold a lock for seconds            |

***

## 8. Testing services

Services are the highest-value unit tests in the codebase: they hold the rules, and with injected dependencies they need no server, no database and no network.

```js
// File: tests/userService.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createUserService } from '../src/services/userService.js';
import { ConflictError, NotFoundError } from '../src/utils/AppError.js';

/** In-memory repository: the real read/write semantics, none of the I/O. */
function createFakeUserRepository(seed = []) {
  const users = seed.map((user) => ({ ...user }));
  let sequence = users.length;

  return {
    users,
    async existsByEmail(email) { return users.some((user) => user.email === email); },
    async findByEmail(email) { return users.find((user) => user.email === email) ?? null; },
    async findById(id) { return users.find((user) => user.id === id) ?? null; },
    async create(data) {
      sequence += 1;
      const user = { id: `u${sequence}`, ...data };
      users.push(user);
      return user;
    },
  };
}

/** A fake hasher: fast and deterministic. The real one is tested separately. */
const fakeHasher = {
  hash: async (plain) => `hashed:${plain}`,
  compare: async (plain, hash) => hash === `hashed:${plain}`,
};

function build(seed) {
  const sent = [];
  const errors = [];
  const service = createUserService({
    userRepository: createFakeUserRepository(seed),
    passwordHasher: fakeHasher,
    mailer: { sendWelcome: async (user) => { sent.push(user.id); } },
    logger: { error: (...args) => errors.push(args), info() {} },
    clock: () => new Date('2026-09-18T10:00:00.000Z'),     // deterministic time
  });
  return { service, sent, errors };
}

test('register creates a user with a hashed password and a server-assigned role', async () => {
  const { service } = build();
  const user = await service.register({ email: 'ankit@example.com', password: 'supersecret', name: 'Ankit' });

  assert.equal(user.email, 'ankit@example.com');
  assert.equal(user.createdAt, '2026-09-18T10:00:00.000Z');
  assert.equal(user.password, undefined);          // never returned
  assert.equal(user.role, undefined);              // not part of the returned shape either
});

test('register rejects a duplicate email with 409 semantics', async () => {
  const { service } = build();
  await service.register({ email: 'taken@example.com', password: 'supersecret', name: 'A' });

  await assert.rejects(
    () => service.register({ email: 'taken@example.com', password: 'supersecret', name: 'B' }),
    (error) => {
      assert.ok(error instanceof ConflictError);
      assert.equal(error.statusCode, 409);
      assert.deepEqual(error.details, { field: 'email' });
      return true;
    },
  );
});

test('a failing welcome email never fails the registration', async () => {
  const errors = [];
  const service = createUserService({
    userRepository: createFakeUserRepository(),
    passwordHasher: fakeHasher,
    mailer: { sendWelcome: async () => { throw new Error('SMTP down'); } },
    logger: { error: (...args) => errors.push(args), info() {} },
  });

  const user = await service.register({ email: 'a@b.com', password: 'supersecret', name: 'A' });
  assert.equal(user.email, 'a@b.com');             // registration succeeded

  await new Promise((resolve) => setTimeout(resolve, 0));   // let the detached catch run
  assert.equal(errors.length, 1);                            // and the failure was logged
  assert.match(errors[0][0], /welcome email failed/);
});

test('authenticate returns null for an unknown user and for a wrong password', async () => {
  const { service } = build();
  await service.register({ email: 'u@example.com', password: 'supersecret', name: 'U' });

  assert.equal(await service.authenticate({ email: 'nobody@example.com', password: 'supersecret' }), null);
  assert.equal(await service.authenticate({ email: 'u@example.com', password: 'wrong-password' }), null);

  const ok = await service.authenticate({ email: 'u@example.com', password: 'supersecret' });
  assert.equal(ok.email, undefined);               // returns only what a token needs
  assert.equal(typeof ok.id, 'string');
});

test('getProfile throws NotFoundError for a missing user', async () => {
  const { service } = build();
  await assert.rejects(() => service.getProfile('missing'), NotFoundError);
});

test('the hasher is never passed a plain password by the service', async () => {
  const hashed = [];
  const service = createUserService({
    userRepository: createFakeUserRepository(),
    passwordHasher: { hash: async (plain) => { hashed.push(plain); return fakeHasher.hash(plain); }, compare: fakeHasher.compare },
    mailer: { sendWelcome: async () => {} },
    logger: { error() {}, info() {} },
  });

  await service.register({ email: 'a@b.com', password: 'plain-text-password', name: 'A' });

  assert.deepEqual(hashed, ['plain-text-password']);   // the service delegates hashing
});
```

```bash
node --test tests/userService.test.js
```

```
✔ register creates a user with a hashed password and a server-assigned role
✔ register rejects a duplicate email with 409 semantics
✔ a failing welcome email never fails the registration
✔ authenticate returns null for an unknown user and for a wrong password
✔ getProfile throws NotFoundError for a missing user
✔ the hasher is never passed a plain password by the service
pass 6
fail 0
```

These six tests cover the rules of the user domain in \~4 ms, with no server, no database and no network — and they will still pass when the repository becomes Mongo, MySQL or Postgres.

***

## 9. Common mistakes

| Mistake                                          | Symptom                                                                   | Fix                                                  |
| ------------------------------------------------ | ------------------------------------------------------------------------- | ---------------------------------------------------- |
| Service methods take `(req, res)`                | Unusable from jobs/CLIs; tests need fakes for HTTP objects                | Pass plain values: `(input, { actor })`              |
| Service returns `{ status: 409 }`                | HTTP leaks into the domain                                                | Throw `AppError` subclasses                          |
| Service builds the response envelope             | The same data needs different shapes per endpoint                         | Return domain values; map in the controller/DTO      |
| Business rules duplicated in controllers         | Rules drift; one endpoint allows what another forbids                     | Move the rule into the service                       |
| Repository contains rules                        | Rules multiply across queries and are invisible                           | Rules in the service, queries in the repository      |
| `new Date()` / `Date.now()` scattered everywhere | Untestable time-dependent logic                                           | Inject a `clock`                                     |
| Service sends email _before_ committing          | Emails for orders that were rolled back                                   | Side effects after the write, ideally via events     |
| `await mailer.send(...)` on the response path    | A slow SMTP server slows every request, and its failure fails the request | Fire-and-forget with a logged `catch`                |
| Two services importing each other                | Circular imports, untestable, fragile                                     | One direction, or an event bus                       |
| One service for everything                       | A 900-line "everything service"                                           | Split by domain (user, note, order, payment)         |
| Silent failures (`catch {}`)                     | Bugs disappear; data goes missing                                         | Log with context, or rethrow typed errors            |
| `check-then-act` without a constraint            | Race conditions create duplicates under concurrency                       | Add a unique index and handle `23505`/`11000`        |
| Long transactions around HTTP calls              | Lock contention and timeouts                                              | Keep transactions to database work only              |
| Returning raw repository rows                    | Internal fields leak; API shape depends on the schema                     | Map to DTOs (controller) or domain objects (service) |

***

## Exercise 11.1 — Implement the user service rules

Implement `userService` with these rules, and unit-test every one of them:

| Rule                                                      | Behaviour                                                                         |
| --------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Email is normalised (trim + lowercase)                    | `" A@B.com "` and `"a@b.com"` are the same account                                |
| Email must be unique                                      | `ConflictError` (409) with `{ field: 'email' }`                                   |
| Password is never stored or returned in plain text        | Hash via the injected hasher; the returned shape has no `password`/`passwordHash` |
| The role is assigned by the server                        | Always `USER` on registration                                                     |
| An unknown email or a wrong password both yield `null`    | The controller maps `null` to `401`                                               |
| A failed welcome email must not fail the registration     | It is logged, not thrown                                                          |
| `getProfile` throws `NotFoundError` when the user is gone | 404                                                                               |
| `createdAt` comes from the injected clock                 | Deterministic tests                                                               |

<details>

<summary>Solution</summary>

```js
// File: src/services/userService.js
import { ConflictError, NotFoundError } from '../utils/AppError.js';

const normaliseEmail = (email) => String(email).trim().toLowerCase();

export function createUserService({
  userRepository,
  passwordHasher,
  mailer = { sendWelcome: async () => {} },
  logger = console,
  clock = () => new Date(),
}) {
  const toPublicUser = (user) => ({
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    createdAt: user.createdAt,
  });

  return {
    async register({ email, password, name }) {
      const normalisedEmail = normaliseEmail(email);

      if (await userRepository.existsByEmail(normalisedEmail)) {
        throw new ConflictError('That email is already registered', { field: 'email' });
      }

      let user;
      try {
        user = await userRepository.create({
          email: normalisedEmail,
          name: String(name).trim(),
          passwordHash: await passwordHasher.hash(password),
          role: 'USER',                                  // server-assigned, never from input
          createdAt: clock().toISOString(),
        });
      } catch (error) {
        // The database is the real guard: a concurrent registration can slip past the check above.
        if (error.code === '23505' || error.code === 'ER_DUP_ENTRY' || error.code === 11000) {
          throw new ConflictError('That email is already registered', { field: 'email' });
        }
        throw error;
      }

      // Deliberately not awaited: the registration is already committed.
      void Promise.resolve()
        .then(() => mailer.sendWelcome(toPublicUser(user)))
        .catch((error) => logger.error('welcome email failed', { userId: user.id, error: error.message }));

      return toPublicUser(user);
    },

    async authenticate({ email, password }) {
      const user = await userRepository.findByEmail(normaliseEmail(email));

      // Compare against a dummy hash when the user is unknown, so timing is similar.
      const DUMMY_HASH = '$2a$12$0000000000000000000000000000000000000000000000000000';
      const hash = user?.passwordHash ?? DUMMY_HASH;
      const matches = await passwordHasher.compare(password, hash);

      if (!user || !matches) return null;
      return { id: user.id, role: user.role, email: user.email };
    },

    async getProfile(id) {
      const user = await userRepository.findById(id);
      if (!user) throw new NotFoundError(`User ${id} not found`);
      return toPublicUser(user);
    },
  };
}
```

```js
// File: tests/userService.rules.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createUserService } from '../src/services/userService.js';
import { ConflictError, NotFoundError } from '../src/utils/AppError.js';

function createFakeRepository(seed = []) {
  const users = seed.map((user) => ({ ...user }));
  let sequence = users.length;
  return {
    users,
    async existsByEmail(email) { return users.some((u) => u.email === email); },
    async findByEmail(email) { return users.find((u) => u.email === email) ?? null; },
    async findById(id) { return users.find((u) => u.id === id) ?? null; },
    async create(data) { sequence += 1; const user = { id: `u${sequence}`, ...data }; users.push(user); return user; },
  };
}

const hasher = {
  hash: async (plain) => `hashed:${plain}`,
  compare: async (plain, hash) => hash === `hashed:${plain}`,
};

const FIXED_TIME = new Date('2026-09-18T10:00:00.000Z');

function build({ mailer, repository } = {}) {
  const errors = [];
  const service = createUserService({
    userRepository: repository ?? createFakeRepository(),
    passwordHasher: hasher,
    mailer: mailer ?? { sendWelcome: async () => {} },
    logger: { error: (...args) => errors.push(args), info() {} },
    clock: () => FIXED_TIME,
  });
  return { service, errors };
}

test('email is normalised before storage and lookup', async () => {
  const { service } = build();
  const created = await service.register({ email: '  A@B.com ', password: 'supersecret', name: ' Ankit ' });

  assert.equal(created.email, 'a@b.com');
  assert.equal(created.name, 'Ankit');

  const again = await service.authenticate({ email: 'A@B.COM', password: 'supersecret' });
  assert.equal(again.id, created.id);                       // the same account
});

test('the returned user never contains a password or hash', async () => {
  const { service } = build();
  const created = await service.register({ email: 'a@b.com', password: 'supersecret', name: 'A' });

  assert.deepEqual(Object.keys(created).sort(), ['createdAt', 'email', 'id', 'name', 'role']);
  assert.equal(JSON.stringify(created).includes('supersecret'), false);
  assert.equal(JSON.stringify(created).includes('hashed:'), false);
});

test('the role is always USER, whatever the caller intended', async () => {
  const repository = createFakeRepository();
  const service = createUserService({
    userRepository: repository,
    passwordHasher: hasher,
    mailer: { sendWelcome: async () => {} },
    logger: { error() {}, info() {} },
    clock: () => FIXED_TIME,
  });

  await service.register({ email: 'a@b.com', password: 'supersecret', name: 'A', role: 'ADMIN' });

  assert.equal(repository.users[0].role, 'USER');
});

test('createdAt comes from the injected clock', async () => {
  const { service } = build();
  const created = await service.register({ email: 'a@b.com', password: 'supersecret', name: 'A' });
  assert.equal(created.createdAt, FIXED_TIME.toISOString());
});

test('a duplicate email is a ConflictError with a field', async () => {
  const { service } = build();
  await service.register({ email: 'a@b.com', password: 'supersecret', name: 'A' });

  await assert.rejects(
    () => service.register({ email: 'A@B.COM', password: 'supersecret', name: 'B' }),
    (error) => {
      assert.ok(error instanceof ConflictError);
      assert.equal(error.statusCode, 409);
      assert.deepEqual(error.details, { field: 'email' });
      return true;
    },
  );
});

test('a driver-level unique violation is translated too', async () => {
  const repository = createFakeRepository();
  repository.existsByEmail = async () => false;               // simulate the race
  repository.create = async () => { throw Object.assign(new Error('duplicate key'), { code: '23505' }); };

  const { service } = build({ repository });

  await assert.rejects(
    () => service.register({ email: 'a@b.com', password: 'supersecret', name: 'A' }),
    ConflictError,
  );
});

test('an unknown email and a wrong password both yield null', async () => {
  const { service } = build();
  await service.register({ email: 'a@b.com', password: 'supersecret', name: 'A' });

  assert.equal(await service.authenticate({ email: 'nobody@example.com', password: 'supersecret' }), null);
  assert.equal(await service.authenticate({ email: 'a@b.com', password: 'nope' }), null);
});

test('a failing welcome email is logged, not thrown', async () => {
  const { service, errors } = build({ mailer: { sendWelcome: async () => { throw new Error('SMTP down'); } } });

  const created = await service.register({ email: 'a@b.com', password: 'supersecret', name: 'A' });
  assert.equal(created.email, 'a@b.com');

  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(errors.length, 1);
  assert.match(errors[0][0], /welcome email failed/);
});

test('getProfile throws NotFoundError for a missing user', async () => {
  const { service } = build();
  await assert.rejects(() => service.getProfile('nope'), NotFoundError);
});
```

```bash
node --test tests/userService.rules.test.js
```

```
✔ email is normalised before storage and lookup
✔ the returned user never contains a password or hash
✔ the role is always USER, whatever the caller intended
✔ createdAt comes from the injected clock
✔ a duplicate email is a ConflictError with a field
✔ a driver-level unique violation is translated too
✔ an unknown email and a wrong password both yield null
✔ a failing welcome email is logged, not thrown
✔ getProfile throws NotFoundError for a missing user
pass 9
fail 0
```

**Design notes**

| Decision                                      | Reason                                                                                          |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Normalisation at the service boundary         | Every caller (API, admin tool, seed script) gets the same behaviour                             |
| `role: 'USER'` hard-coded                     | A client-supplied role is a privilege escalation; promotion is a separate, authorised operation |
| The database constraint is the real guarantee | The `existsByEmail` check is advisory; only a unique index prevents duplicates                  |
| `DUMMY_HASH` for unknown users                | Prevents user enumeration by response timing                                                    |
| Fire-and-forget email with a `.catch`         | A mail outage must not fail a registration                                                      |
| The clock is injected                         | `createdAt` is deterministic in tests, and "freeze time" needs no libraries                     |

</details>

***

## Exercise 11.2 — Find the boundary violations

```js
// File: services/orderService.js
import express from 'express';
import { Order } from '../models/Order.js';

const router = express.Router();

router.post('/orders', async (req, res) => {
  const { items } = req.body;
  if (!items?.length) return res.status(400).json({ message: 'items required' });

  let total = 0;
  for (const item of items) {
    const product = await Product.findById(item.productId);
    total += product.price * item.quantity;
    product.stock -= item.quantity;
    await product.save();
  }

  const order = new Order({ userId: req.user.id, items, total, status: 'pending' });
  await order.save();

  await sendEmail(req.user.email, 'Order placed');
  res.json(order);
});

export default router;
```

Which layer does each part belong to, and what is the correct decomposition?

<details>

<summary>Solution</summary>

| #  | Part                                          | Current layer     | Belongs in                                       | Why                                                                              |
| -- | --------------------------------------------- | ----------------- | ------------------------------------------------ | -------------------------------------------------------------------------------- |
| 1  | `express.Router()` and the route path         | "service" file    | `routes/orderRoutes.js`                          | A service must not know about URLs                                               |
| 2  | `req.body.items?.length` check                | inline            | validation middleware                            | Shape validation, reusable, returns 422 with details                             |
| 3  | `Product.findById` inside a loop              | the route handler | repository + service                             | Data access belongs in a repository; N+1 queries are a service-level design flaw |
| 4  | `total += product.price * item.quantity`      | handler           | service                                          | Pricing is a business rule                                                       |
| 5  | `product.stock -= item.quantity; save()`      | handler           | repository, inside a transaction                 | Two writes must be atomic, and stock must not go negative                        |
| 6  | `new Order(...)`                              | handler           | repository                                       | Persistence model construction                                                   |
| 7  | `req.user.id`                                 | handler           | passed as `{ actor }`                            | Identity is HTTP-adjacent input; the service takes plain values                  |
| 8  | `sendEmail(...)` awaited before responding    | handler           | after commit, via an event or a detached promise | Third-party failure must not fail the order, and latency must not be added       |
| 9  | `res.json(order)` raw document                | handler           | controller + DTO                                 | Leaks internals; the contract must be explicit                                   |
| 10 | `res.status(400)` / `res.json(200)`           | handler           | controller (`201` + `Location`)                  | Status decisions are HTTP concerns — and `200` was simply wrong                  |
| 11 | No error handling at all                      | handler           | controller `try/catch` + `next(error)`           | One error contract                                                               |
| 12 | The file mixes routing, rules and persistence | —                 | four files                                       | Separation of concerns                                                           |

**Correct decomposition**

```js
// File: src/repositories/productRepository.js
export function createProductRepository({ db }) {
  return {
    /** One query for many ids — no N+1. */
    async findByIds(ids) {
      return db.query('SELECT id, name, price, stock FROM products WHERE id = ANY($1)', [ids]);
    },
  };
}
```

```js
// File: src/repositories/orderRepository.js
export function createOrderRepository({ db }) {
  return {
    /** Order + line items + stock decrements, atomically. */
    async createWithItems({ userId, lines, total }) {
      return db.withTransaction(async (client) => {
        const order = await client.query(
          `INSERT INTO orders (user_id, total, status) VALUES ($1, $2, 'pending') RETURNING *`,
          [userId, total],
        );

        for (const line of lines) {
          const updated = await client.query(
            `UPDATE products SET stock = stock - $2 WHERE id = $1 AND stock >= $2 RETURNING id`,
            [line.productId, line.quantity],
          );
          if (updated.rowCount === 0) throw new ConflictError('Insufficient stock', { productId: line.productId });

          await client.query(
            `INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES ($1, $2, $3, $4)`,
            [order.rows[0].id, line.productId, line.quantity, line.unitPrice],
          );
        }

        return order.rows[0];
      });
    },
  };
}
```

```js
// File: src/services/orderService.js
import { ConflictError, NotFoundError } from '../utils/AppError.js';
import { domainEvents, EVENTS } from '../events/domainEvents.js';

export function createOrderService({ productRepository, orderRepository, logger }) {
  /** Pure function: pricing has no I/O, so it is trivially testable. */
  function price(lines) {
    return lines.reduce((total, line) => total + line.unitPrice * line.quantity, 0);
  }

  return {
    async create({ items }, { actor }) {
      const products = await productRepository.findByIds(items.map((item) => item.productId));
      const byId = new Map(products.map((product) => [product.id, product]));

      const lines = items.map((item) => {
        const product = byId.get(item.productId);
        if (!product) throw new NotFoundError(`Product ${item.productId} not found`);
        if (product.stock < item.quantity) {
          throw new ConflictError(`Not enough stock for ${product.name}`, {
            productId: product.id,
            available: product.stock,
            requested: item.quantity,
          });
        }
        return { productId: product.id, quantity: item.quantity, unitPrice: product.price };
      });

      const total = price(lines);
      const order = await orderRepository.createWithItems({ userId: actor.id, lines, total });

      logger.info('order created', { orderId: order.id, userId: actor.id, total });
      domainEvents.emit(EVENTS.ORDER_PLACED, { orderId: order.id, userId: actor.id, total });

      return order;
    },
  };
}
```

```js
// File: src/controllers/orderController.js
import { toOrderDto } from '../dtos/orderDto.js';

export function createOrderController({ orderService }) {
  return {
    async create(req, res, next) {
      try {
        const order = await orderService.create(req.validated.body, { actor: req.user });
        res.status(201).location(`/api/v1/orders/${order.id}`).json({ data: toOrderDto(order) });
      } catch (error) {
        next(error);
      }
    },
  };
}
```

```js
// File: src/routes/orderRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { createOrderSchema } from '../validators/orderSchemas.js';

export function createOrderRouter({ controller, authenticate }) {
  const router = Router();
  router.post('/', authenticate, validate(createOrderSchema), controller.create);
  return router;
}
```

```js
// File: src/events/subscribers/onOrderPlaced.js
export function registerOrderSubscribers({ domainEvents, mailer, logger }) {
  domainEvents.on(EVENTS.ORDER_PLACED, async (payload) => {
    try {
      await mailer.sendOrderConfirmation(payload);
    } catch (error) {
      logger.error('order email failed', { orderId: payload.orderId, error: error.message });
    }
  });
}
```

**The before/after in one table**

| Concern      | Before                           | After                                    |
| ------------ | -------------------------------- | ---------------------------------------- |
| Routing      | inside the service file          | `orderRoutes.js`                         |
| Validation   | inline `if` returning `400`      | schema → `422` with `details`            |
| Pricing      | inline in the handler            | pure function in the service             |
| Persistence  | five `await`s inside the handler | repositories, one transaction            |
| N+1 queries  | one per item                     | one `findByIds`                          |
| Stock safety | decrement without a guard        | `WHERE stock >= $2` inside a transaction |
| Identity     | `req.user.id` used directly      | passed as `{ actor }`                    |
| Email        | awaited before the response      | event subscriber, after commit           |
| Response     | raw document, `200`              | DTO, `201` + `Location`                  |
| Errors       | none                             | `AppError` → one error middleware        |

</details>

***

## What's next

Services own the rules; middleware and schemas own the input. Next: validation with Zod — the same rules applied at the boundary, with field-level error details.

→ [12 — Validation](12-validation.md)
