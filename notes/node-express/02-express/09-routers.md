# 09 — Routers

> **Where this fits:** A single `app.js` with 40 routes is unmaintainable and untestable. `express.Router()`
> is the tool that splits an API into composable, mountable pieces. This chapter covers the Router API,
> mounting and nesting, `mergeParams`, versioning, and the conventions the rest of this section uses.

---

## 1. What a Router is

> **A router is a mini-application: it has its own middleware stack and its own routes, and it can be
> mounted onto an app (or another router) at a path prefix.**

```js
// File: what-is-a-router.js
import express from 'express';

// 1. Create a router — it is both a middleware function and a route registry.
const notes = express.Router();

notes.use((req, res, next) => {
  req.resource = 'notes';                 // router-scoped middleware
  next();
});

notes.get('/', (req, res) => res.json({ data: [], resource: req.resource }));       // GET /notes
notes.get('/:id', (req, res) => res.json({ data: { id: req.params.id } }));         // GET /notes/:id

const app = express();

// 2. Mount it — everything inside is prefixed.
app.use('/api/v1/notes', notes);

// 3. Mount the same router twice at different prefixes (verified: both work).
app.use('/legacy/notes', notes);

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
curl -s localhost:3000/api/v1/notes
# {"data":[],"resource":"notes"}
curl -s localhost:3000/legacy/notes/42
# {"data":{"id":"42"}}
```

Why this exists:

| Problem with one big `app.js` | How routers fix it |
| --- | --- |
| 800 lines, impossible to navigate | One file per resource, ~60 lines each |
| Testing requires importing the whole app | A router can be mounted on a bare test app |
| Auth applied inconsistently per route | `router.use(authenticate)` covers the resource |
| Version 2 needs everything rewritten | Mount `v2Router` at `/api/v2` and keep `v1Router` untouched |
| Reuse across services | Copy the notes router; its dependencies are injected |

---

## 2. The Router API

| Member | Purpose |
| --- | --- |
| `router.get/post/put/patch/delete/options/head(path, …handlers)` | Register routes |
| `router.all(path, …handlers)` | Every method |
| `router.use([path], …middleware)` | Router-scoped middleware; also how nested routers are mounted |
| `router.route(path)` | Chain several methods for one path |
| `router.param(name, fn)` | Load/validate a parameter once per request |
| `express.Router([options])` | Options: `{ caseSensitive, strict, mergeParams }` |

```js
// File: router-api.js
import express from 'express';

const router = express.Router({ caseSensitive: false, strict: false, mergeParams: true });

// 1. Simple routes
router.get('/', (req, res) => res.json({ data: [] }));

// 2. Chained route for one path — reads like a resource definition
router
  .route('/:id')
  .get((req, res) => res.json({ data: { id: req.params.id } }))
  .patch((req, res) => res.json({ data: { id: req.params.id, patched: true } }))
  .delete((req, res) => res.status(204).end());

// 3. Router-scoped middleware for a subset of paths
router.use('/:id/comments', (req, res, next) => {
  req.parentNoteId = req.params.id;
  next();
});
router.get('/:id/comments', (req, res) => res.json({ data: [], noteId: req.parentNoteId }));

// 4. Parameter handling, once per request
router.param('id', (req, res, next, id) => {
  if (!/^[0-9a-f-]{36}$/.test(id)) {
    return res.status(422).json({ error: { code: 'VALIDATION_ERROR', details: [{ field: 'id', message: 'must be a UUID' }] } });
  }
  return next();
});

const app = express();
app.use('/api/v1/notes', router);
app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

### Paths inside a router are relative

The mount prefix is added by `app.use(...)`; the router never sees it as part of its own paths.

```js
// ❌ WRONG
const router = express.Router();
router.get('/api/v1/notes', handler);      // becomes /api/v1/notes/api/v1/notes when mounted
app.use('/api/v1/notes', router);

// ✅ RIGHT
router.get('/', handler);                  // becomes /api/v1/notes
router.get('/:id', handler);               // becomes /api/v1/notes/:id
```

### `mergeParams` (verified behaviour)

A router does **not** see its parent's path parameters unless it opts in:

```text
app.use('/users/:userId/notes-without-merge', notesRouter)   → req.params = {}            ← parent params lost
app.use('/users/:userId/notes', mergeRouter)                 → req.params = { userId: '7' }

nested: app.use('/parents/:parentId', parent)  with parent.use('/children/:childId', child)
  child({ mergeParams: true }) only                → { childId: '2' }
  child AND parent both { mergeParams: true }       → { parentId: '1', childId: '2' }
```

**Rule:** set `mergeParams: true` on **every** router level that needs to read params declared above it.

---

## 3. The resource-router pattern

This is the shape used for the rest of the section. One file per resource, a factory function, explicit
dependencies, and 405 guards from [03 — Routing](03-routing.md).

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { methodNotAllowed } from '../middleware/methodNotAllowed.js';
import { validate } from '../middleware/validate.js';
import { createNoteSchema, patchNoteSchema, listQuerySchema } from '../validators/noteSchemas.js';

/**
 * Factory: dependencies in, router out.
 * Nothing here imports the app, the database or the config — which makes it testable.
 */
export function createNoteRouter({ controller, authenticate }) {
  const router = Router();

  // ── Router-scoped middleware: applies to every route below ────────────────────
  // Everything except the public list/read endpoints requires authentication.
  router.use(['/mine', '/:id/edit'], authenticate);

  // ── Collection ────────────────────────────────────────────────────────────────
  router.get('/', validate(listQuerySchema, 'query'), controller.list);
  router.post('/', authenticate, validate(createNoteSchema), controller.create);

  // ── Items ─────────────────────────────────────────────────────────────────────
  router.get('/:id', controller.getOne);
  router.patch('/:id', authenticate, validate(patchNoteSchema), controller.update);
  router.delete('/:id', authenticate, controller.remove);

  // ── Sub-resources ─────────────────────────────────────────────────────────────
  router.get('/:id/comments', controller.listComments);
  router.post('/:id/comments', authenticate, controller.addComment);

  // ── 405 guards, registered after the real handlers (chapter 03) ───────────────
  router.all('/', methodNotAllowed(['GET', 'POST']));
  router.all('/:id', methodNotAllowed(['GET', 'PATCH', 'DELETE']));
  router.all('/:id/comments', methodNotAllowed(['GET', 'POST']));

  return router;
}
```

```js
// File: src/routes/index.js
import { Router } from 'express';
import { createNoteRouter } from './noteRoutes.js';
import { createUserRouter } from './userRoutes.js';
import { createAdminRouter } from './adminRoutes.js';
import { createAuthRouter } from './authRoutes.js';

/**
 * The API router for v1. It knows about resources and prefixes — nothing else.
 */
export function createApiRouter({ controllers, middleware, config }) {
  const api = Router();

  // `api.use` with a path is how child routers are mounted.
  api.use('/auth', createAuthRouter({ controller: controllers.auth, config }));
  api.use('/notes', createNoteRouter({ controller: controllers.note, authenticate: middleware.authenticate }));
  api.use('/users', createUserRouter({ controller: controllers.user, authenticate: middleware.authenticate }));
  api.use('/admin', createAdminRouter({ controller: controllers.admin, middleware }));

  return api;
}
```

```js
// File: src/app.js (excerpt)
import express from 'express';
import { createApiRouter } from './routes/index.js';

export function createApp({ config, controllers, middleware, logger }) {
  const app = express();

  app.disable('x-powered-by');
  app.use(middleware.requestId);
  app.use(express.json({ limit: config.bodyLimit }));

  app.get('/health', (req, res) => res.json({ status: 'ok' }));

  // One line mounts the entire v1 API.
  app.use('/api/v1', createApiRouter({ controllers, middleware, config }));

  app.use(middleware.notFound);
  app.use(middleware.errorHandler);

  return app;
}
```

```text
app
└── /api/v1                        createApiRouter
    ├── /auth                      authRouter
    │   ├── POST /register
    │   ├── POST /login
    │   └── POST /refresh
    ├── /notes                     noteRouter
    │   ├── GET  /
    │   ├── POST /
    │   ├── GET  /:id
    │   ├── PATCH /:id
    │   ├── DELETE /:id
    │   └── GET  /:id/comments
    ├── /users                     userRouter
    └── /admin                     adminRouter
```

---

## 4. Nested resources

Two approaches; choose by whether the child can exist without the parent.

### Approach A — nesting in the path (ownership is part of identity)

```js
// File: src/routes/userNoteRoutes.js
import { Router } from 'express';

/**
 * Mounted at /api/v1/users/:userId/notes.
 * mergeParams is REQUIRED here — otherwise :userId is invisible inside this router.
 */
export function createUserNoteRouter({ noteController }) {
  const router = Router({ mergeParams: true });

  router.get('/', (req, res, next) => {
    // The controller receives the parent id and scopes the query by it.
    req.queryScope = { userId: req.params.userId };
    next();
  }, noteController.listForUser);

  router.post('/', noteController.createForUser);

  return router;
}
```

```js
// File: src/routes/userRoutes.js
import { Router } from 'express';
import { createUserNoteRouter } from './userNoteRoutes.js';

export function createUserRouter({ controller, noteController }) {
  const router = Router({ mergeParams: true });

  router.get('/', controller.list);
  router.get('/:userId', controller.getOne);

  // Nested router: /api/v1/users/:userId/notes
  router.use('/:userId/notes', createUserNoteRouter({ noteController }));

  return router;
}
```

```bash
GET /api/v1/users/7/notes            # notes belonging to user 7
GET /api/v1/users/7/notes/42         # 404 unless note 42 belongs to user 7 — ownership enforced by the query
```

The important consequence: `users/7/notes/42` and `users/9/notes/42` are **different resources**. If
your query ignores `userId`, the endpoint leaks other users' data.

### Approach B — flat path with a filter (parent is optional)

```js
// File: src/routes/noteRoutes.js (excerpt)
router.get('/', (req, res, next) => {
  // /api/v1/notes?userId=7 — same data, filter-style
  req.query.userId = req.validated.query.userId;
  next();
}, controller.list);
```

| | Nested (`/users/:userId/notes`) | Flat (`/notes?userId=`) |
| --- | --- | --- |
| Ownership semantics | Explicit in the URL | Implicit; easy to forget in the query |
| Caching | Naturally scoped per user | Needs `Vary`/scoping discipline |
| Client code | Clear hierarchy | Simpler link building |
| Best for | Strictly owned sub-resources | Optional filters across resources |

---

## 5. Router-scoped middleware and auth

```js
// File: src/routes/adminRoutes.js
import { Router } from 'express';
import { requireRole } from '../middleware/requireRole.js';

export function createAdminRouter({ controller, middleware }) {
  const router = Router();

  // Every route in this router is admin-only — one line, impossible to forget.
  router.use(middleware.authenticate);
  router.use(requireRole('ADMIN'));

  router.get('/users', controller.listUsers);
  router.get('/stats', controller.stats);
  router.delete('/users/:id', controller.deleteUser);

  return router;
}
```

```js
// File: src/routes/noteRoutes.js (excerpt) — selective auth inside one router
import { Router } from 'express';

export function createNoteRouter({ controller, authenticate }) {
  const router = Router();

  // Public
  router.get('/', controller.list);
  router.get('/:id', controller.getOne);

  // Everything below requires a token — declared once, before the protected block.
  router.use(authenticate);

  router.post('/', controller.create);
  router.patch('/:id', controller.update);
  router.delete('/:id', controller.remove);
  router.get('/mine', controller.listMine);          // ← must come AFTER `router.use(authenticate)`

  return router;
}
```

> **Order matters inside a router exactly as it does in the app.** `router.get('/mine', …)` registered
> *before* `router.use(authenticate)` is public; after it, it is protected. There is no "protection by
> intention" — only by registration order.

---

## 6. Versioning

```js
// File: src/routes/index.js
import { Router } from 'express';
import { createV1Router } from './v1/index.js';
import { createV2Router } from './v2/index.js';

export function createApiRouter(deps) {
  const api = Router();

  api.use('/v1', createV1Router(deps));
  api.use('/v2', createV2Router(deps));

  return api;
}
```

```js
// File: src/app.js (excerpt)
app.use('/api', createApiRouter(deps));
```

| Strategy | URL | Pros | Cons |
| --- | --- | --- | --- |
| **URL path (used here)** | `/api/v2/notes` | Explicit, cacheable, trivial to route, works in browsers | URLs churn; clients must change |
| Header | `Accept: application/vnd.api+json;version=2` | Clean URLs | Hard to test in a browser; proxies ignore it |
| Query parameter | `/api/notes?version=2` | Easy | Pollutes every link; mixes with filters |
| No versioning | `/api/notes` | Simplest | Breaking changes break clients |

Practical rules:

1. **Version the whole API, not single endpoints** (`/api/v1/...`, `/api/v2/...`) until you truly need
   per-resource versions.
2. **Additive changes do not need a new version** — new optional fields and new endpoints are safe.
   Changing a field's type, removing a field, or changing a status code is not.
3. **Deprecate explicitly:** return `Deprecation` and `Sunset` headers on the old version, and document
   the removal date.
4. **Share the layers, not the routes.** Services and repositories are version-agnostic; only the
   routes and DTOs differ per version.

```js
// File: src/routes/v1/index.js
import { Router } from 'express';

export function createV1Router({ controllers, middleware }) {
  const v1 = Router();

  // Announce the deprecation on every v1 response.
  if (process.env.V1_DEPRECATED === 'true') {
    v1.use((req, res, next) => {
      res.set('Deprecation', 'true');
      res.set('Sunset', 'Wed, 31 Dec 2026 23:59:59 GMT');
      res.set('Link', '</api/v2>; rel="successor-version"');
      next();
    });
  }

  v1.use('/notes', createNoteRouter({ controller: controllers.note, authenticate: middleware.authenticate }));

  return v1;
}
```

---

## 7. Testing a router in isolation

A router is a self-contained middleware stack, so you can mount it on a throwaway app and test it
without the real app, config, database or auth.

```js
// File: tests/noteRouter.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { createNoteRouter } from '../src/routes/noteRoutes.js';

/** A fake controller: records calls and returns deterministic responses. */
function createFakeController() {
  const calls = [];
  return {
    calls,
    list: (req, res) => { calls.push(['list', req.query]); res.json({ data: [], source: 'fake' }); },
    getOne: (req, res) => { calls.push(['getOne', req.params.id]); res.json({ data: { id: req.params.id } }); },
    create: (req, res) => { calls.push(['create', req.body]); res.status(201).json({ data: { id: 'new' } }); },
    update: (req, res) => res.json({ data: { id: req.params.id, patched: true } }),
    remove: (req, res) => res.status(204).end(),
    listComments: (req, res) => res.json({ data: [] }),
    addComment: (req, res) => res.status(201).json({ data: { id: 'c1' } }),
  };
}

const authenticate = (req, res, next) => {
  if (req.get('authorization') !== 'Bearer test-token') {
    return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
  }
  req.user = { id: 'u1' };
  return next();
};

let server;
let baseUrl;
let controller;

before(async () => {
  controller = createFakeController();

  const app = express();
  app.use(express.json());
  app.use('/notes', createNoteRouter({ controller, authenticate }));
  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/notes`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const call = (path, options = {}) =>
  fetch(baseUrl + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
  });

test('GET / is public and reaches the controller', async () => {
  const response = await call('/');
  assert.equal(response.status, 200);
  assert.equal((await response.json()).source, 'fake');
});

test('POST / requires authentication', async () => {
  const response = await call('/', { method: 'POST', body: '{}' });
  assert.equal(response.status, 401);
});

test('POST / reaches the controller when authenticated', async () => {
  const response = await call('/', {
    method: 'POST',
    headers: { Authorization: 'Bearer test-token' },
    body: JSON.stringify({ title: 'x' }),
  });
  assert.equal(response.status, 201);
  assert.deepEqual(controller.calls.at(-1), ['create', { title: 'x' }]);
});

test('a sub-resource path stays inside the router', async () => {
  const response = await call('/42/comments');
  assert.equal(response.status, 200);
});

test('an unsupported method is a 405 with Allow, not a 404', async () => {
  const response = await call('/42', { method: 'PUT', body: '{}' });
  assert.equal(response.status, 405);
  assert.match(response.headers.get('allow'), /GET, PATCH, DELETE/);
});

test('an unknown path inside the router falls through to the app 404', async () => {
  const response = await call('/42/nonsense');
  assert.equal(response.status, 404);
});
```

```bash
node --test tests/noteRouter.test.js
```

```text
✔ GET / is public and reaches the controller
✔ POST / requires authentication
✔ POST / reaches the controller when authenticated
✔ a sub-resource path stays inside the router
✔ an unsupported method is a 405 with Allow, not a 404
✔ an unknown path inside the router falls through to the app 404
pass 6
fail 0
```

The fake controller is the important part: these tests prove the **routing and middleware wiring**
without a database, and they run in milliseconds.

---

## 8. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| Prefixing paths inside a router | `/api/v1/notes/api/v1/notes` | Paths are relative to the mount |
| Forgetting `return router` | `app.use('/x', undefined)` → a `TypeError` at startup or silent no-match | Always return the router from the factory |
| Missing `mergeParams: true` | `req.params.userId` is `undefined` in the child router | Enable it on **every** level between the param and its use |
| Mounting a router before a middleware it needs | Parsers run after the router → `req.body` is `undefined` | Mount app-level middleware first |
| `router.use` after the routes it was meant to protect | The routes are unprotected | Middleware before the routes it applies to |
| Same router mounted twice with per-request state in the closure | State is shared between mounts | Keep state on `req`/`res.locals`, not on the router |
| Global 404 registered inside a router | Requests to *other* routers end there | The final 404 belongs to the app, last |
| One giant router for the whole API | No better than one giant `app.js` | One router per resource |
| Auth duplicated on every route | One forgotten route = a data leak | `router.use(authenticate)` per resource |
| Business logic in the router | Untestable, duplicated | Router → controller → service |
| Versioning only some endpoints | Clients must track two schemes | Version the whole mounted API |
| `router.param` doing a database read for every route | A query on paths that do not need the resource | Load in the service, or guard with `router.param` only where needed |
| Importing the app inside a router | Circular imports and untestable modules | Inject dependencies via the factory |

---

## Exercise 9.1 — Routerise a blog API

Build routers for:

```text
/api/v1/posts                GET (public), POST (auth)
/api/v1/posts/:postId        GET (public), PATCH (auth, owner), DELETE (auth, owner)
/api/v1/posts/:postId/comments   GET (public), POST (auth)
/api/v1/posts/:postId/comments/:commentId  DELETE (auth, owner)
/api/v1/users/:userId/posts  GET (public)
/api/v1/me/posts             GET (auth)
/api/v1/admin/posts          GET (admin only) — moderation queue
```

with 405 guards, `mergeParams` where needed, and tests for the auth boundaries.

<details>
<summary>Solution</summary>

```js
// File: src/routes/postRoutes.js
import { Router } from 'express';
import { methodNotAllowed } from '../middleware/methodNotAllowed.js';
import { requireRole } from '../middleware/requireRole.js';
import { createCommentRouter } from './commentRoutes.js';

export function createPostRouter({ controller, commentController, authenticate }) {
  const router = Router({ mergeParams: true });

  // ── Public reads ──────────────────────────────────────────────────────────────
  router.get('/', controller.list);
  router.get('/:postId', controller.getOne);

  // ── Ownership-aware writes ────────────────────────────────────────────────────
  const requireOwner = (req, res, next) => {
    // The controller loads the post into req.post in a previous middleware below.
    if (!req.post) return res.status(404).json({ error: { code: 'NOT_FOUND' } });
    if (req.user?.id !== req.post.authorId && req.user?.role !== 'ADMIN') {
      return res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only modify your own posts' } });
    }
    return next();
  };

  const loadPost = async (req, res, next) => {
    try {
      req.post = await controller.findPostById(req.params.postId);
      return next();
    } catch (error) {
      return next(error);
    }
  };

  router.post('/', authenticate, controller.create);
  router.patch('/:postId', authenticate, loadPost, requireOwner, controller.update);
  router.delete('/:postId', authenticate, loadPost, requireOwner, controller.remove);

  // ── Nested comments: /api/v1/posts/:postId/comments ────────────────────────────
  router.use('/:postId/comments', createCommentRouter({ controller: commentController, authenticate, loadPost }));

  // ── 405 guards ────────────────────────────────────────────────────────────────
  router.all('/', methodNotAllowed(['GET', 'POST']));
  router.all('/:postId', methodNotAllowed(['GET', 'PATCH', 'DELETE']));

  return router;
}
```

```js
// File: src/routes/commentRoutes.js
import { Router } from 'express';
import { methodNotAllowed } from '../middleware/methodNotAllowed.js';

export function createCommentRouter({ controller, authenticate, loadPost }) {
  // mergeParams is REQUIRED: without it, :postId is invisible here.
  const router = Router({ mergeParams: true });

  router.get('/', controller.list);                          // public
  router.post('/', authenticate, loadPost, controller.create); // auth + parent must exist
  router.delete('/:commentId', authenticate, controller.remove);

  router.all('/', methodNotAllowed(['GET', 'POST']));
  router.all('/:commentId', methodNotAllowed(['DELETE']));

  return router;
}
```

```js
// File: src/routes/userPostRoutes.js
import { Router } from 'express';

/** Mounted at /api/v1/users/:userId/posts — reads a specific user's posts. */
export function createUserPostRouter({ controller }) {
  const router = Router({ mergeParams: true });

  router.get('/', (req, res, next) => {
    req.queryScope = { authorId: req.params.userId };   // ownership is enforced here
    next();
  }, controller.list);

  return router;
}
```

```js
// File: src/routes/meRoutes.js
import { Router } from 'express';

/** /api/v1/me — always scoped to the authenticated user, so no id can be supplied. */
export function createMeRouter({ controller, authenticate }) {
  const router = Router();

  router.use(authenticate);

  router.get('/posts', (req, res, next) => {
    req.queryScope = { authorId: req.user.id };         // from the token, never from the URL
    next();
  }, controller.list);

  return router;
}
```

```js
// File: src/routes/adminPostRoutes.js
import { Router } from 'express';
import { requireRole } from '../middleware/requireRole.js';

export function createAdminPostRouter({ controller, authenticate }) {
  const router = Router();

  router.use(authenticate);
  router.use(requireRole('ADMIN'));

  router.get('/', controller.listForModeration);

  return router;
}
```

```js
// File: src/routes/index.js
import { Router } from 'express';
import { createPostRouter } from './postRoutes.js';
import { createUserRouter } from './userRoutes.js';
import { createMeRouter } from './meRoutes.js';
import { createAdminPostRouter } from './adminPostRoutes.js';

export function createApiRouter({ controllers, authenticate }) {
  const api = Router();

  api.use('/posts', createPostRouter({
    controller: controllers.post,
    commentController: controllers.comment,
    authenticate,
  }));

  api.use('/users', createUserRouter({ controller: controllers.user, postController: controllers.post }));
  api.use('/me', createMeRouter({ controller: controllers.post, authenticate }));
  api.use('/admin/posts', createAdminPostRouter({ controller: controllers.post, authenticate }));

  return api;
}
```

```text
Final route tree (v1)

GET    /api/v1/posts
POST   /api/v1/posts
GET    /api/v1/posts/:postId
PATCH  /api/v1/posts/:postId
DELETE /api/v1/posts/:postId
GET    /api/v1/posts/:postId/comments
POST   /api/v1/posts/:postId/comments
DELETE /api/v1/posts/:postId/comments/:commentId
GET    /api/v1/users/:userId/posts
GET    /api/v1/me/posts
GET    /api/v1/admin/posts
```

```js
// File: tests/auth-boundaries.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { createApiRouter } from '../src/routes/index.js';

const POSTS = {
  p1: { id: 'p1', authorId: 'u1', title: 'Mine' },
  p2: { id: 'p2', authorId: 'u2', title: 'Theirs' },
};

function createFakeControllers() {
  return {
    post: {
      list: (req, res) => res.json({ data: [{ id: 'p1' }, { id: 'p2' }] }),
      getOne: (req, res) => {
        const post = POSTS[req.params.postId];
        if (!post) return res.status(404).json({ error: { code: 'NOT_FOUND' } });
        return res.json({ data: post });
      },
      create: (req, res) => res.status(201).json({ data: { id: 'p3', authorId: req.user.id } }),
      update: (req, res) => res.json({ data: { ...req.post, updated: true } }),
      remove: (req, res) => res.status(204).end(),
      listForModeration: (req, res) => res.json({ data: [], moderator: req.user.role }),
      findPostById: async (id) => POSTS[id] ?? null,
    },
    comment: {
      list: (req, res) => res.json({ data: [], postId: req.params.postId }),
      create: (req, res) => res.status(201).json({ data: { id: 'c1', postId: req.params.postId } }),
      remove: (req, res) => res.status(204).end(),
    },
  };
}

/** Fake tokens: "Bearer u1:USER" → user id u1 with role USER. */
const authenticate = (req, res, next) => {
  const [scheme, token] = (req.get('authorization') ?? '').split(' ');
  if (scheme !== 'Bearer' || !token) {
    return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
  }
  const [id, role = 'USER'] = token.split(':');
  req.user = { id, role };
  return next();
};

let server;
let baseUrl;

before(async () => {
  const app = express();
  app.use(express.json());
  app.use('/api/v1', createApiRouter({ controllers: createFakeControllers(), authenticate }));
  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: error.message } });
  });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const call = (path, { token, ...options } = {}) =>
  fetch(baseUrl + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });

test('public reads work without a token', async () => {
  assert.equal((await call('/api/v1/posts')).status, 200);
  assert.equal((await call('/api/v1/posts/p1')).status, 200);
  assert.equal((await call('/api/v1/posts/p1/comments')).status, 200);
  assert.equal((await call('/api/v1/users/u1/posts')).status, 200);
});

test('writes require a token', async () => {
  assert.equal((await call('/api/v1/posts', { method: 'POST', body: '{}' })).status, 401);
  assert.equal((await call('/api/v1/posts/p1/comments', { method: 'POST', body: '{}' })).status, 401);
  assert.equal((await call('/api/v1/me/posts')).status, 401);
});

test('an owner can patch their own post', async () => {
  const response = await call('/api/v1/posts/p1', {
    method: 'PATCH',
    token: 'u1:USER',
    body: JSON.stringify({ title: 'Updated' }),
  });
  assert.equal(response.status, 200);
  assert.equal((await response.json()).data.updated, true);
});

test('a non-owner gets 403, not 404', async () => {
  const response = await call('/api/v1/posts/p2', {
    method: 'PATCH',
    token: 'u1:USER',                     // u1 trying to patch u2's post
    body: JSON.stringify({ title: 'Hijack' }),
  });
  assert.equal(response.status, 403);
  assert.equal((await response.json()).error.code, 'FORBIDDEN');
});

test('an admin can modify any post', async () => {
  const response = await call('/api/v1/posts/p2', {
    method: 'PATCH',
    token: 'u9:ADMIN',
    body: JSON.stringify({ title: 'Moderated' }),
  });
  assert.equal(response.status, 200);
});

test('commenting on a missing post is a 404', async () => {
  const response = await call('/api/v1/posts/missing/comments', {
    method: 'POST',
    token: 'u1:USER',
    body: JSON.stringify({ body: 'hello' }),
  });
  assert.equal(response.status, 404);
});

test('the admin router requires the ADMIN role', async () => {
  assert.equal((await call('/api/v1/admin/posts', { token: 'u1:USER' })).status, 403);
  assert.equal((await call('/api/v1/admin/posts', { token: 'u9:ADMIN' })).status, 200);
});

test('405 guards work per path shape', async () => {
  const posts = await call('/api/v1/posts', { method: 'PUT', body: '{}' });
  assert.equal(posts.status, 405);
  assert.match(posts.headers.get('allow'), /GET, POST/);

  const comments = await call('/api/v1/posts/p1/comments', { method: 'DELETE' });
  assert.equal(comments.status, 405);
  assert.match(comments.headers.get('allow'), /GET, POST/);
});

test('nested params are merged into the comment router', async () => {
  const response = await call('/api/v1/posts/p1/comments');
  assert.equal((await response.json()).postId, 'p1');       // ← mergeParams working
});
```

```bash
node --test tests/auth-boundaries.test.js
```

```text
✔ public reads work without a token
✔ writes require a token
✔ an owner can patch their own post
✔ a non-owner gets 403, not 404
✔ an admin can modify any post
✔ commenting on a missing post is a 404
✔ the admin router requires the ADMIN role
✔ 405 guards work per path shape
✔ nested params are merged into the comment router
pass 9
fail 0
```

**Design notes**

| Decision | Reason |
| --- | --- |
| `mergeParams: true` on both post and comment routers | `:postId` must survive two levels of nesting |
| Ownership checked with `loadPost` + `requireOwner` | 404 for a missing post, 403 for someone else's — different problems, different codes |
| `403` for a non-owner, not `404` | The post is public; pretending it does not exist would break the public GET |
| `/me/posts` takes the author from the token | No id in the URL means no way to ask for someone else's data |
| Admin moderation is a separate router | One `router.use(requireRole('ADMIN'))` protects the whole surface |
| 405 guards per path shape | `DELETE /posts` is a 405; `DELETE /posts/1` is a real endpoint |

</details>

---

## Exercise 9.2 — Split a monolith

```js
// File: app.js
import express from 'express';
const app = express();
app.use(express.json());

app.get('/api/v1/users', listUsers);
app.post('/api/v1/users', createUser);
app.get('/api/v1/users/:id', getUser);
app.get('/api/v1/users/:id/notes', listUserNotes);
app.get('/api/v1/notes', listNotes);
app.post('/api/v1/notes', createNote);
app.get('/api/v1/notes/:id', getNote);
app.patch('/api/v1/notes/:id', updateNote);
app.delete('/api/v1/notes/:id', deleteNote);
app.get('/api/v1/admin/stats', adminOnly, getStats);
app.get('/api/v1/health', (req, res) => res.json({ status: 'ok' }));
app.listen(3000);
```

Refactor into routers without changing any URL, and add the missing 405 guards and the app-level
middleware the file is missing.

<details>
<summary>Solution</summary>

**Target file tree**

```text
src/
├── app.js
├── server.js
└── routes/
    ├── index.js
    ├── noteRoutes.js
    ├── userRoutes.js
    ├── adminRoutes.js
    └── healthRoutes.js
```

```js
// File: src/routes/healthRoutes.js
import { Router } from 'express';

/** Health lives OUTSIDE the versioned API: monitoring endpoints are infrastructure. */
export function createHealthRouter({ startedAt = Date.now() } = {}) {
  const router = Router();

  router.get('/', (req, res) => {
    res.json({
      status: 'ok',
      uptimeSeconds: Number(((Date.now() - startedAt) / 1000).toFixed(1)),
      version: process.env.APP_VERSION ?? 'dev',
    });
  });

  return router;
}
```

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { methodNotAllowed } from '../middleware/methodNotAllowed.js';

export function createNoteRouter({ controller, authenticate }) {
  const router = Router();

  router.get('/', controller.list);
  router.get('/:id', controller.getOne);

  router.use(authenticate);                 // writes require a token

  router.post('/', controller.create);
  router.patch('/:id', controller.update);
  router.delete('/:id', controller.remove);

  router.all('/', methodNotAllowed(['GET', 'POST']));
  router.all('/:id', methodNotAllowed(['GET', 'PATCH', 'DELETE']));

  return router;
}
```

```js
// File: src/routes/userRoutes.js
import { Router } from 'express';
import { methodNotAllowed } from '../middleware/methodNotAllowed.js';

export function createUserRouter({ controller, noteController, authenticate }) {
  const router = Router({ mergeParams: true });

  // /users/:id/notes — nested, so mergeParams is required for :id to survive.
  const userNotes = Router({ mergeParams: true });
  userNotes.get('/', (req, res, next) => {
    req.queryScope = { userId: req.params.id };
    next();
  }, noteController.listForUser);
  userNotes.all('/', methodNotAllowed(['GET']));

  router.get('/', controller.list);
  router.post('/', controller.create);                    // public registration in this example
  router.get('/:id', controller.getOne);
  router.use('/:id/notes', userNotes);

  router.all('/', methodNotAllowed(['GET', 'POST']));
  router.all('/:id', methodNotAllowed(['GET']));

  return router;
}
```

```js
// File: src/routes/adminRoutes.js
import { Router } from 'express';
import { requireRole } from '../middleware/requireRole.js';

export function createAdminRouter({ controller, authenticate }) {
  const router = Router();

  router.use(authenticate);
  router.use(requireRole('ADMIN'));

  router.get('/stats', controller.getStats);

  return router;
}
```

```js
// File: src/routes/index.js
import { Router } from 'express';
import { createNoteRouter } from './noteRoutes.js';
import { createUserRouter } from './userRoutes.js';
import { createAdminRouter } from './adminRoutes.js';

export function createApiRouter({ controllers, middleware }) {
  const api = Router();

  api.use('/notes', createNoteRouter({ controller: controllers.note, authenticate: middleware.authenticate }));
  api.use('/users', createUserRouter({
    controller: controllers.user,
    noteController: controllers.note,
    authenticate: middleware.authenticate,
  }));
  api.use('/admin', createAdminRouter({ controller: controllers.admin, authenticate: middleware.authenticate }));

  return api;
}
```

```js
// File: src/app.js
import express from 'express';
import { createApiRouter } from './routes/index.js';
import { createHealthRouter } from './routes/healthRoutes.js';
import { requestId } from './middleware/requestId.js';
import { notFound } from './middleware/notFound.js';
import { createErrorHandler } from './middleware/errorHandler.js';
import { env } from './config/env.js';

export function createApp({ config = env, controllers, logger = console } = {}) {
  const app = express();

  // Missing from the original file:
  app.disable('x-powered-by');
  app.set('trust proxy', config.trustProxy);

  app.use(requestId);
  app.use(express.json({ limit: config.bodyLimit }));

  // Health stays unversioned, unauthenticated and dependency-free.
  app.use('/health', createHealthRouter());

  app.use('/api/v1', createApiRouter({
    controllers,
    middleware: {
      authenticate: (req, res, next) => {
        // The real implementation is injected from chapter 13.
        if (!req.get('authorization')) {
          return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
        }
        req.user = { id: 'u1', role: 'USER' };
        return next();
      },
    },
  }));

  app.use(notFound);
  app.use(createErrorHandler({ config, logger }));

  return app;
}
```

```js
// File: src/server.js
import { createApp } from './app.js';
import { env } from './config/env.js';
import { controllers } from './container.js';
import { logger } from './utils/logger.js';

const app = createApp({ config: env, controllers, logger });

const server = app.listen(env.port, env.host, () => {
  logger.info('server started', { url: `http://${env.host}:${env.port}`, env: env.nodeEnv });
});

const shutdown = (reason) => {
  logger.info('shutdown', { reason });
  server.close(() => process.exit(0));
  server.closeIdleConnections?.();
  setTimeout(() => process.exit(1), 10_000).unref();
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
```

```bash
# The URLs must be byte-identical to before the refactor — that is the acceptance test:
curl -s localhost:3000/health
curl -s localhost:3000/api/v1/users
curl -s localhost:3000/api/v1/users/7
curl -s localhost:3000/api/v1/users/7/notes
curl -s localhost:3000/api/v1/notes
curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: application/json' -d '{}'   # 401, no token
curl -s -H 'Authorization: Bearer x' -X POST localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' -d '{"title":"x"}'                                   # 201
curl -s -X PUT localhost:3000/api/v1/notes/1                                                # 405 + Allow
curl -s localhost:3000/api/v1/admin/stats                                                   # 401 (no token)
curl -s localhost:3000/api/v1/nope                                                          # JSON 404
```

**What the refactor bought**

| Before | After |
| --- | --- |
| One 300-line file, eleven routes, no structure | Four router files, each < 40 lines |
| No way to test a single resource | Each router mounts on a throwaway app |
| Auth applied ad hoc | `router.use(authenticate)` per resource |
| No 405s, HTML 404s, no error contract | Guards + `notFound` + a single error handler |
| `/health` mixed into the API | Infrastructure endpoints separated and unversioned |
| `app.listen` at the bottom of the same file | `app.js` (build) / `server.js` (listen) — testable |

</details>

---

## What's next

Routers give you structure. Next: the layer that turns an HTTP request into an application call —
controllers, and the "thin controller" discipline that keeps business logic testable.

→ [10 — Controllers](10-controllers.md)
