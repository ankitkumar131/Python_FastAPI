# 10 — Controllers

> **Where this fits:** Routers map URLs to functions. Those functions are controllers, and their only job
> is translating HTTP into application calls and results back into HTTP. Get this boundary right and the
> rest of the codebase becomes testable; get it wrong and business logic ends up tangled with `req`/`res`.

---

## 1. What a controller is (and is not)

> **A controller is the HTTP adapter: it reads the validated request, calls the service layer, and turns
> the result — or the error — into a response.**

```text
      HTTP                         Application                      Data
┌──────────────────┐        ┌────────────────────┐        ┌──────────────────┐
│ route + middleware│  ───▶ │ CONTROLLER          │  ───▶ │ service → repo    │
│ (URL → function)  │        │ req/res → call → res│        │ (rules, data)     │
└──────────────────┘        └────────────────────┘        └──────────────────┘
```

| The controller DOES | The controller does NOT |
| --- | --- |
| Read `req.validated`, `req.params`, `req.user` | Validate input shapes (middleware does that) |
| Call **one** service method per request | Contain business rules ("a note cannot be pinned when…") |
| Choose the status code, headers and body shape | Talk to the database, ORM or driver |
| Map domain results to DTOs | Know about SQL, Mongo, or connection pools |
| Forward errors to `next(error)` | Write logs full of `req`/`res` internals |
| Set `Location`, `ETag`, `Cache-Control` | Send emails, schedule jobs, compute heavy aggregates inline |

The enforcement rule that keeps this honest: **a service must never receive `req` or `res`, and a
controller must never receive a database handle.** If either import appears, the boundary is broken.

---

## 2. Controller anatomy

```js
// File: src/controllers/noteController.js
import { NotFoundError, ConflictError } from '../utils/AppError.js';

/**
 * Factory: the controller receives its service as a parameter.
 * Nothing here imports a database, a config file or the app.
 */
export function createNoteController({ noteService, logger }) {
  return {
    /** GET /api/v1/notes */
    async list(req, res, next) {
      try {
        const { items, meta } = await noteService.list(req.validated.query);
        res.json({ data: items, meta });
      } catch (error) {
        next(error);                       // one line: forward everything
      }
    },

    /** GET /api/v1/notes/:id */
    async getOne(req, res, next) {
      try {
        const note = await noteService.getById(req.params.id);
        if (!note) throw new NotFoundError(`Note ${req.params.id} not found`);
        res.json({ data: note });
      } catch (error) {
        next(error);
      }
    },

    /** POST /api/v1/notes */
    async create(req, res, next) {
      try {
        const note = await noteService.create(req.validated.body, { actor: req.user });
        logger.info('note created', { noteId: note.id, userId: req.user?.id });

        // 201 + Location is the complete answer to "create".
        res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: note });
      } catch (error) {
        next(error);
      }
    },

    /** PATCH /api/v1/notes/:id */
    async update(req, res, next) {
      try {
        const note = await noteService.update(req.params.id, req.validated.body);
        if (!note) throw new NotFoundError(`Note ${req.params.id} not found`);
        res.json({ data: note });
      } catch (error) {
        next(error);
      }
    },

    /** DELETE /api/v1/notes/:id */
    async remove(req, res, next) {
      try {
        await noteService.remove(req.params.id);
        res.status(204).end();             // success with nothing to say
      } catch (error) {
        next(error);
      }
    },
  };
}
```

Line by line, the shape is always the same:

```text
async method(req, res, next) {
  try {
    <read validated input>            req.validated.*, req.params, req.user
    <call ONE service method>         never business rules, never a query
    <map the result to HTTP>          status, headers, DTO, envelope
  } catch (error) {
    next(error)                       the error middleware owns the response shape
  }
}
```

> **Why `try/catch` when Express 5 forwards rejections automatically?** Two reasons: it makes the
> controller portable to Express 4, and it documents that every path either responds or forwards. If you
> prefer, drop it — but never do both `res.json()` *and* fall through into code that responds again.

---

## 3. Reading input — the validated request only

Middleware from [06 — Params, Query and Body](06-params-query-body.md) and
[12 — Validation](12-validation.md) stores parsed input in `req.validated`. Controllers should read
**only** that, plus `req.params` (validated in `router.param`) and `req.user` (set by authentication).

```js
// File: src/controllers/reading-input.js
import { createNoteController } from './noteController.js';

/** A validation middleware from chapter 12. */
export function validate(schema, source = 'body') {
  return (req, res, next) => {
    const parsed = schema.safeParse(req[source] ?? {});
    if (!parsed.success) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          details: parsed.error.issues.map((issue) => ({
            field: issue.path.join('.') || source,
            message: issue.message,
          })),
        },
      });
    }
    req.validated ??= {};
    req.validated[source] = parsed.data;
    return next();
  };
}
```

| Source | Read from | Why |
| --- | --- | --- |
| Body | `req.validated.body` | Raw `req.body` is attacker-controlled and untyped |
| Query | `req.validated.query` | Raw `req.query` is all strings, arrays or nested objects |
| Path params | `req.params` (after `router.param` validation) | Format-checked, so the service can trust the shape |
| Identity | `req.user` (from the token) | **Never** from the body or query — that is how privilege escalation happens |
| Request id | `req.id` | For logs and error payloads |
| Context | `req.ip`, `req.get('user-agent')` | Audit trails |

```js
// ❌ EVERY ONE OF THESE IS A BUG
const limit = req.query.limit;                             // '10' * 2 === 20, but '10' + 1 === '101'
const role = req.body.role;                                // mass assignment / privilege escalation
const userId = req.body.userId ?? req.user.id;             // a client-supplied identity
const rows = await db.notes.find({ id: req.params.id });   // a database call inside a controller
if (note.tags.length > 10) throw new Error('too many tags'); // a business rule inside a controller
```
```js
// ✅ THE CONTROLLER READS ONLY VALIDATED, TRUSTED VALUES
const { limit, page, sort, tags, q } = req.validated.query;
const actor = req.user;
const note = await noteService.list({ limit, page, sort, tags, q, actor });
```

---

## 4. Mapping results to HTTP

The controller owns the status codes. Keep the mapping explicit rather than clever:

| Service outcome | Controller response |
| --- | --- |
| Value returned | `200` + `{ data }` |
| Resource created | `201` + `Location` + `{ data }` |
| List returned | `200` + `{ data, meta }` |
| Deleted / nothing to return | `204` (no body) |
| `null`/`undefined` for a by-id lookup | `throw new NotFoundError(...)` → 404 |
| Service throws `AppError` | `next(error)` → that status |
| Accepted for async processing | `202` + `Location` of the job + `{ data: { jobId } }` |

```js
// File: src/controllers/status-mapping.js
import { NotFoundError, ConflictError } from '../utils/AppError.js';

export function createBookmarkController({ bookmarkService }) {
  return {
    async create(req, res, next) {
      try {
        const bookmark = await bookmarkService.create(req.validated.body, { actor: req.user });

        // A service may report "created vs already existed" without knowing about HTTP.
        if (bookmark.alreadyExisted) {
          return res.status(200).json({ data: bookmark.dto, meta: { replayed: true } });
        }
        return res.status(201).location(`/api/v1/bookmarks/${bookmark.dto.id}`).json({ data: bookmark.dto });
      } catch (error) {
        return next(error);
      }
    },

    async list(req, res, next) {
      try {
        const { items, total, page, limit } = await bookmarkService.list(req.validated.query);

        res.set('X-Total-Count', String(total));                       // common for tables
        return res.json({
          data: items,
          meta: { page, limit, total, totalPages: Math.ceil(total / limit), hasNext: page * limit < total },
        });
      } catch (error) {
        return next(error);
      }
    },

    async remove(req, res, next) {
      try {
        const removed = await bookmarkService.remove(req.params.id, { actor: req.user });
        if (!removed) throw new NotFoundError(`Bookmark ${req.params.id} not found`);
        return res.status(204).end();
      } catch (error) {
        return next(error);
      }
    },
  };
}
```

### DTOs: the response is a contract, not a database row

```js
// File: src/dtos/noteDto.js
/**
 * A DTO (data transfer object) converts a database/document object into the exact shape
 * clients are promised. It is the ONLY place that decides which fields are public.
 */
export function toNoteDto(note) {
  return {
    id: note.id,
    title: note.title,
    content: note.content,
    tags: note.tags ?? [],
    pinned: Boolean(note.pinned),
    author: note.author ? { id: note.author.id, name: note.author.name } : null,
    createdAt: note.createdAt,
    updatedAt: note.updatedAt,
    // Deliberately omitted: authorEmail, internalFlags, deletedAt, version, passwordHash…
  };
}

export function toNoteListDto(notes) {
  return notes.map(toNoteDto);
}
```

| Without a DTO | With a DTO |
| --- | --- |
| Changing a column name breaks the API | The contract is explicit and stable |
| `SELECT *` / the whole document leaks to clients | Only whitelisted fields are ever serialised |
| Every layer invents its own shape | One place to add computed fields |
| Tests assert on database internals | Tests assert on the documented contract |

> **The DTO is a security control, not a nicety.** `return user` returns `passwordHash`, reset tokens,
> internal flags and whatever a future migration adds. `return toUserDto(user)` returns exactly seven
> fields, forever.

---

## 5. The controller should stay thin — a size test

```js
// File: fatController.js
// ❌ FAT CONTROLLER: validation, uniqueness, hashing, persistence and side effects all in HTTP code.
import { createHash } from 'node:crypto';
import { Note, Activity } from './models.js';
import { mailer } from './mailer.js';

export const noteController = {
  async create(req, res) {
    const { title, content, tags } = req.body;
    if (!title || title.length > 200) return res.status(422).json({ error: 'bad title' });
    if (tags && tags.length > 10) return res.status(422).json({ error: 'too many tags' });

    const existing = await Note.findOne({ title });
    if (existing) return res.status(409).json({ error: 'duplicate' });

    const hash = createHash('sha256').update(content).digest('hex');
    const note = await Note.create({ title, content, tags, contentHash: hash, authorId: req.user.id });

    await Activity.create({ type: 'note.created', noteId: note.id, userId: req.user.id });
    await mailer.send(req.user.email, 'Note created', note.title);

    return res.status(201).json({ data: note });
  },
};
```

```js
// File: src/controllers/noteController.js
// ✅ THIN CONTROLLER: seven lines of HTTP translation; everything else is delegated.
export const noteController = {
  async create(req, res, next) {
    try {
      const note = await noteService.create(req.validated.body, { actor: req.user });
      return res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: note });
    } catch (error) {
      return next(error);
    }
  },
};
```

If a controller is longer than ~30 lines, the extra code belongs in a service:

| What crept in | Where it belongs | Why |
| --- | --- | --- |
| Shape checks (`title.length`) | Validation middleware | Reusable across endpoints, returns 422 with details |
| Uniqueness checks | Service + database constraint | Needs data access; a race can still violate it |
| Hashing, timestamps, ids | Service | Not HTTP concerns |
| Side effects (email, activity log) | Service (or an event emitted by it) | Must be reusable from jobs and CLIs |
| Permission checks | Middleware (coarse) or service (data-dependent) | "Can this user edit *this* note?" needs the note |
| Retries, timeouts | Service | Business resilience, not HTTP |

---

## 6. Testing controllers

Two complementary levels. Unit tests use fake `req`/`res`; integration tests mount the real router.

```js
// File: tests/noteController.unit.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createNoteController } from '../src/controllers/noteController.js';
import { NotFoundError } from '../src/utils/AppError.js';

/** Minimal Express-like request/response fakes. */
function createContext({ params = {}, validated = {}, user } = {}) {
  const req = { params, validated, user, id: 'test-request-id', get: () => undefined };

  const res = {
    statusCode: 200,
    headers: {},
    body: undefined,
    finished: false,
    status(code) { this.statusCode = code; return this; },
    set(name, value) { this.headers[name] = value; return this; },
    location(value) { this.headers.Location = value; return this; },
    json(payload) { this.body = payload; this.finished = true; return this; },
    end() { this.finished = true; return this; },
  };

  let forwarded = null;
  const next = (error) => { forwarded = error ?? 'next-called-without-error'; };

  return { req, res, next, forwarded: () => forwarded };
}

function createFakeService(overrides = {}) {
  return {
    list: async () => ({ items: [], meta: { total: 0 } }),
    getById: async () => null,
    create: async (input) => ({ id: 'n1', ...input }),
    update: async () => null,
    remove: async () => true,
    ...overrides,
  };
}

const logger = { info() {}, error() {}, warn() {} };

test('list returns 200 with data and meta', async () => {
  const service = createFakeService({
    list: async (query) => ({ items: [{ id: 'n1' }], meta: { total: 1, query } }),
  });
  const controller = createNoteController({ noteService: service, logger });
  const ctx = createContext({ validated: { query: { limit: 20 } } });

  await controller.list(ctx.req, ctx.res, ctx.next);

  assert.equal(ctx.res.statusCode, 200);
  assert.equal(ctx.res.body.data.length, 1);
  assert.equal(ctx.res.body.meta.total, 1);
  assert.equal(ctx.forwarded(), null);
});

test('getOne forwards NotFoundError when the service returns null', async () => {
  const controller = createNoteController({ noteService: createFakeService(), logger });
  const ctx = createContext({ params: { id: 'missing' } });

  await controller.getOne(ctx.req, ctx.res, ctx.next);

  assert.ok(ctx.forwarded() instanceof NotFoundError);
  assert.equal(ctx.res.finished, false);          // nothing was sent
});

test('create returns 201 with a Location header', async () => {
  const controller = createNoteController({ noteService: createFakeService(), logger });
  const ctx = createContext({ validated: { body: { title: 'New' } }, user: { id: 'u1' } });

  await controller.create(ctx.req, ctx.res, ctx.next);

  assert.equal(ctx.res.statusCode, 201);
  assert.equal(ctx.res.headers.Location, '/api/v1/notes/n1');
  assert.equal(ctx.res.body.data.title, 'New');
});

test('remove returns 204 with no body', async () => {
  const controller = createNoteController({ noteService: createFakeService(), logger });
  const ctx = createContext({ params: { id: 'n1' } });

  await controller.remove(ctx.req, ctx.res, ctx.next);

  assert.equal(ctx.res.statusCode, 204);
  assert.equal(ctx.res.body, undefined);
});

test('a service failure is forwarded, never converted into a 200', async () => {
  const boom = new Error('database exploded');
  const service = createFakeService({ list: async () => { throw boom; } });
  const controller = createNoteController({ noteService: service, logger });
  const ctx = createContext({ validated: { query: {} } });

  await controller.list(ctx.req, ctx.res, ctx.next);

  assert.equal(ctx.forwarded(), boom);
  assert.equal(ctx.res.finished, false);
});
```

```bash
node --test tests/noteController.unit.test.js
```

```text
✔ list returns 200 with data and meta
✔ getOne forwards NotFoundError when the service returns null
✔ create returns 201 with a Location header
✔ remove returns 204 with no body
✔ a service failure is forwarded, never converted into a 200
pass 5
fail 0
```

| What unit tests prove | What they do not prove |
| --- | --- |
| Status/header/body decisions | That the route is wired correctly |
| Error forwarding behaviour | That validation middleware ran |
| DTO shape | That auth actually rejects bad tokens |

That second column is the job of the integration tests in
[19 — Testing](19-testing.md), which mount the real router and hit it over HTTP.

---

## 7. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| Business logic in the controller | Copy-pasted rules, untestable, drifts between endpoints | Move it to a service |
| Database calls in the controller | Controller needs a DB to be tested | Call the repository through a service |
| Passing `req`/`res` into a service | The service cannot be used from a job, queue or CLI | Pass plain values (`input`, `{ actor }`, `context`) |
| Returning the raw database row | Leaks internal fields; every schema change breaks clients | Always map through a DTO |
| Reading `req.body.role` / `req.body.userId` | Privilege escalation, impersonation | Identity comes from `req.user` |
| Catching errors and responding `500` inline | Inconsistent error shapes | `next(error)` and one error handler |
| `res.json()` without `return` in a branch | Execution continues and tries a second response | `return res.status(...).json(...)` everywhere |
| Missing `Location` on `201` | Clients guess the new resource URL | `res.status(201).location(...)` |
| Using `200` for a delete | Inconsistent with the rest of the API | `204` (or document `200` + body) |
| Sending `{ error: … }` with a `200` | Client-side `response.ok` checks silently pass | Real status codes |
| Long `if/else` chains for statuses | Unreadable, easy to get wrong | A small mapping table per resource |
| Logging the whole `req` | Tokens, cookies and passwords in the logs | Log `req.id`, method, path, status |
| Formatting dates/numbers in the controller | Formatting logic spread across endpoints | Do it in the DTO/serialiser |
| One controller handling five resources | Another monolith | One controller per resource |

---

## Exercise 10.1 — Write the blog controllers

Implement controllers for the blog API from [09 — Routers](09-routers.md) with these contracts:

| Endpoint | Response |
| --- | --- |
| `GET /posts` | `200` + `{ data: PostDto[], meta: { page, limit, total, hasNext } }` |
| `GET /posts/:postId` | `200` + `{ data: PostDto }`, `404` when missing |
| `POST /posts` | `201` + `Location` + `{ data: PostDto }`; `409` when the slug exists |
| `PATCH /posts/:postId` | `200` + `{ data: PostDto }`; `403` when not the author and not an admin |
| `DELETE /posts/:postId` | `204`; `404` when missing |
| `GET /posts/:postId/comments` | `200` + `{ data: CommentDto[], meta: { count } }` |
| `POST /posts/:postId/comments` | `201` + `Location` + `{ data: CommentDto }` |

Include DTOs, never leak `internalStatus` or `authorEmail`, and unit-test every status branch.

<details>
<summary>Solution</summary>

```js
// File: src/dtos/postDto.js
export function toPostDto(post) {
  return {
    id: post.id,
    slug: post.slug,
    title: post.title,
    body: post.body,
    tags: post.tags ?? [],
    status: post.status,                         // 'draft' | 'published' | 'archived'
    author: { id: post.author.id, name: post.author.name },
    commentCount: post.commentCount ?? 0,
    publishedAt: post.publishedAt ?? null,
    createdAt: post.createdAt,
    updatedAt: post.updatedAt,
    // Omitted on purpose: authorEmail, internalStatus, moderationFlags, deletedAt
  };
}

export function toCommentDto(comment) {
  return {
    id: comment.id,
    postId: comment.postId,
    body: comment.body,
    author: { id: comment.author.id, name: comment.author.name },
    createdAt: comment.createdAt,
  };
}
```

```js
// File: src/controllers/postController.js
import { NotFoundError, ForbiddenError } from '../utils/AppError.js';
import { toPostDto } from '../dtos/postDto.js';

export function createPostController({ postService, logger }) {
  const isOwnerOrAdmin = (post, actor) =>
    Boolean(actor) && (post.authorId === actor.id || actor.role === 'ADMIN');

  return {
    async list(req, res, next) {
      try {
        const { items, total } = await postService.list(req.validated.query);
        const { page, limit } = req.validated.query;

        res.json({
          data: items.map(toPostDto),
          meta: { page, limit, total, hasNext: page * limit < total },
        });
      } catch (error) {
        next(error);
      }
    },

    async getOne(req, res, next) {
      try {
        const post = await postService.getById(req.params.postId);
        if (!post) throw new NotFoundError(`Post ${req.params.postId} not found`);
        res.json({ data: toPostDto(post) });
      } catch (error) {
        next(error);
      }
    },

    async create(req, res, next) {
      try {
        const post = await postService.create(req.validated.body, { actor: req.user });
        logger.info('post created', { postId: post.id, userId: req.user.id });
        res.status(201).location(`/api/v1/posts/${post.id}`).json({ data: toPostDto(post) });
      } catch (error) {
        next(error);
      }
    },

    async update(req, res, next) {
      try {
        const existing = await postService.getById(req.params.postId);
        if (!existing) throw new NotFoundError(`Post ${req.params.postId} not found`);

        // Authorisation that depends on the DATA lives here (or in the service).
        if (!isOwnerOrAdmin(existing, req.user)) {
          throw new ForbiddenError('You can only edit your own posts');
        }

        const updated = await postService.update(req.params.postId, req.validated.body, { actor: req.user });
        res.json({ data: toPostDto(updated) });
      } catch (error) {
        next(error);
      }
    },

    async remove(req, res, next) {
      try {
        const existing = await postService.getById(req.params.postId);
        if (!existing) throw new NotFoundError(`Post ${req.params.postId} not found`);
        if (!isOwnerOrAdmin(existing, req.user)) {
          throw new ForbiddenError('You can only delete your own posts');
        }

        await postService.remove(req.params.postId, { actor: req.user });
        res.status(204).end();
      } catch (error) {
        next(error);
      }
    },
  };
}
```

```js
// File: src/controllers/commentController.js
import { NotFoundError } from '../utils/AppError.js';
import { toCommentDto } from '../dtos/postDto.js';

export function createCommentController({ commentService }) {
  return {
    async list(req, res, next) {
      try {
        const comments = await commentService.listForPost(req.params.postId);
        res.json({ data: comments.map(toCommentDto), meta: { count: comments.length } });
      } catch (error) {
        next(error);
      }
    },

    async create(req, res, next) {
      try {
        const comment = await commentService.create(req.params.postId, req.validated.body, { actor: req.user });

        res
          .status(201)
          .location(`/api/v1/posts/${req.params.postId}/comments/${comment.id}`)
          .json({ data: toCommentDto(comment) });
      } catch (error) {
        next(error);
      }
    },
  };
}
```

```js
// File: src/services/postService.js
import { ConflictError, NotFoundError } from '../utils/AppError.js';

/** Domain logic: slug uniqueness, publication timestamps, DTO-free results. */
export function createPostService({ postRepository }) {
  return {
    async list({ page, limit, sort, q, status }) {
      return postRepository.list({ offset: (page - 1) * limit, limit, sort, q, status });
    },

    async getById(id) {
      return postRepository.findById(id);                 // the controller decides 404 vs 200
    },

    async create(input, { actor }) {
      const slug = input.slug ?? slugify(input.title);

      if (await postRepository.findBySlug(slug)) {
        throw new ConflictError('A post with that slug already exists', { field: 'slug' });
      }

      const now = new Date().toISOString();
      return postRepository.create({
        ...input,
        slug,
        authorId: actor.id,
        status: input.status ?? 'draft',
        publishedAt: input.status === 'published' ? now : null,
        createdAt: now,
        updatedAt: now,
      });
    },

    async update(id, patch, { actor }) {
      const current = await postRepository.findById(id);
      if (!current) throw new NotFoundError(`Post ${id} not found`);

      const next = { ...current, updatedAt: new Date().toISOString() };
      for (const key of ['title', 'body', 'tags', 'status']) {
        if (Object.hasOwn(patch, key)) next[key] = patch[key];
      }
      if (patch.status === 'published' && !current.publishedAt) {
        next.publishedAt = new Date().toISOString();
      }

      return postRepository.update(id, next);
    },

    async remove(id) {
      return postRepository.remove(id);
    },
  };
}

function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}
```

```js
// File: tests/postController.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createPostController } from '../src/controllers/postController.js';
import { NotFoundError, ForbiddenError, ConflictError } from '../src/utils/AppError.js';

function createContext({ params = {}, validated = {}, user } = {}) {
  const req = { params, validated, user, id: 'rid', get: () => undefined };
  const res = {
    statusCode: 200, headers: {}, body: undefined, finished: false,
    status(code) { this.statusCode = code; return this; },
    set(name, value) { this.headers[name] = value; return this; },
    location(value) { this.headers.Location = value; return this; },
    json(payload) { this.body = payload; this.finished = true; return this; },
    end() { this.finished = true; return this; },
  };
  let forwarded = null;
  const next = (error) => { forwarded = error ?? 'no-error'; };
  return { req, res, next, forwarded: () => forwarded };
}

const logger = { info() {}, error() {}, warn() {} };
const basePost = {
  id: 'p1', slug: 'hello', title: 'Hello', body: 'Body', tags: [], status: 'draft',
  authorId: 'u1', author: { id: 'u1', name: 'Ankit' }, authorEmail: 'private@example.com',
  internalStatus: 'flagged', createdAt: '2026-01-01T00:00:00.000Z', updatedAt: '2026-01-01T00:00:00.000Z',
};

function fakeService(overrides = {}) {
  return {
    list: async () => ({ items: [basePost], total: 1 }),
    getById: async () => basePost,
    create: async (input) => ({ ...basePost, ...input }),
    update: async () => ({ ...basePost, title: 'Updated' }),
    remove: async () => true,
    ...overrides,
  };
}

test('list maps posts through the DTO and never leaks internal fields', async () => {
  const controller = createPostController({ postService: fakeService(), logger });
  const ctx = createContext({ validated: { query: { page: 1, limit: 20 } } });

  await controller.list(ctx.req, ctx.res, ctx.next);

  const post = ctx.res.body.data[0];
  assert.equal(ctx.res.statusCode, 200);
  assert.deepEqual(Object.keys(post).sort(), [
    'author', 'body', 'commentCount', 'createdAt', 'id', 'publishedAt', 'slug', 'status', 'tags', 'title', 'updatedAt',
  ]);
  assert.equal(post.authorEmail, undefined);
  assert.equal(post.internalStatus, undefined);
  assert.equal(JSON.stringify(ctx.res.body).includes('private@example.com'), false);
});

test('getOne forwards a NotFoundError when the post does not exist', async () => {
  const controller = createPostController({ postService: fakeService({ getById: async () => null }), logger });
  const ctx = createContext({ params: { postId: 'missing' } });

  await controller.getOne(ctx.req, ctx.res, ctx.next);

  assert.ok(ctx.forwarded() instanceof NotFoundError);
  assert.equal(ctx.res.finished, false);
});

test('create returns 201 with Location and the DTO', async () => {
  const controller = createPostController({ postService: fakeService(), logger });
  const ctx = createContext({ validated: { body: { title: 'Hello' } }, user: { id: 'u1', role: 'USER' } });

  await controller.create(ctx.req, ctx.res, ctx.next);

  assert.equal(ctx.res.statusCode, 201);
  assert.equal(ctx.res.headers.Location, '/api/v1/posts/p1');
  assert.equal(ctx.res.body.data.title, 'Hello');
});

test('create propagates the service ConflictError unchanged', async () => {
  const conflict = new ConflictError('A post with that slug already exists', { field: 'slug' });
  const controller = createPostController({
    postService: fakeService({ create: async () => { throw conflict; } }),
    logger,
  });
  const ctx = createContext({ validated: { body: {} }, user: { id: 'u1' } });

  await controller.create(ctx.req, ctx.res, ctx.next);

  assert.equal(ctx.forwarded(), conflict);
});

test('update rejects a non-owner with 403', async () => {
  const controller = createPostController({ postService: fakeService(), logger });
  const ctx = createContext({
    params: { postId: 'p1' },
    validated: { body: { title: 'Hijack' } },
    user: { id: 'u2', role: 'USER' },
  });

  await controller.update(ctx.req, ctx.res, ctx.next);

  assert.ok(ctx.forwarded() instanceof ForbiddenError);
  assert.equal(ctx.res.finished, false);
});

test('update allows the author', async () => {
  const controller = createPostController({ postService: fakeService(), logger });
  const ctx = createContext({
    params: { postId: 'p1' },
    validated: { body: { title: 'Mine' } },
    user: { id: 'u1', role: 'USER' },
  });

  await controller.update(ctx.req, ctx.res, ctx.next);

  assert.equal(ctx.res.statusCode, 200);
  assert.equal(ctx.res.body.data.title, 'Updated');
});

test('update allows an admin', async () => {
  const controller = createPostController({ postService: fakeService(), logger });
  const ctx = createContext({
    params: { postId: 'p1' },
    validated: { body: { title: 'Moderated' } },
    user: { id: 'u9', role: 'ADMIN' },
  });

  await controller.update(ctx.req, ctx.res, ctx.next);

  assert.equal(ctx.res.statusCode, 200);
});

test('remove returns 204 for the author', async () => {
  const controller = createPostController({ postService: fakeService(), logger });
  const ctx = createContext({ params: { postId: 'p1' }, user: { id: 'u1', role: 'USER' } });

  await controller.remove(ctx.req, ctx.res, ctx.next);

  assert.equal(ctx.res.statusCode, 204);
  assert.equal(ctx.res.body, undefined);
});

test('remove rejects a non-owner', async () => {
  const controller = createPostController({ postService: fakeService(), logger });
  const ctx = createContext({ params: { postId: 'p1' }, user: { id: 'u2', role: 'USER' } });

  await controller.remove(ctx.req, ctx.res, ctx.next);

  assert.ok(ctx.forwarded() instanceof ForbiddenError);
});
```

```bash
node --test tests/postController.test.js
```

```text
✔ list maps posts through the DTO and never leaks internal fields
✔ getOne forwards a NotFoundError when the post does not exist
✔ create returns 201 with Location and the DTO
✔ create propagates the service ConflictError unchanged
✔ update rejects a non-owner with 403
✔ update allows the author
✔ update allows an admin
✔ remove returns 204 for the author
✔ remove rejects a non-owner
pass 9
fail 0
```

**Design notes**

| Decision | Reason |
| --- | --- |
| Every response goes through a DTO | The leak test asserts on the serialised body, not on hopes |
| `getById` returns `null` instead of throwing | The service stays HTTP-agnostic; the controller decides 404 |
| Ownership check in the controller | It needs the loaded post *and* the actor — a data-dependent authorisation decision |
| Slug uniqueness in the service | It is a rule, and it must also hold for imports and admin tools |
| `Location` on both 201s | Clients never need to guess a URL |
| Comment list returns `meta.count` | A count is metadata, not part of the collection |

</details>

---

## Exercise 10.2 — Refactor a fat controller

```js
// File: fatController.js
export async function createOrder(req, res) {
  const { items, couponCode, addressId } = req.body;
  if (!Array.isArray(items) || items.length === 0) return res.status(400).json({ message: 'items required' });
  if (items.length > 50) return res.status(400).json({ message: 'too many items' });

  const address = await Address.findById(addressId);
  if (!address || address.userId !== req.user.id) return res.status(403).json({ message: 'bad address' });

  let subtotal = 0;
  for (const line of items) {
    const product = await Product.findById(line.productId);
    if (!product) return res.status(404).json({ message: `no product ${line.productId}` });
    if (product.stock < line.quantity) return res.status(409).json({ message: 'out of stock' });
    subtotal += product.price * line.quantity;
  }

  let discount = 0;
  if (couponCode) {
    const coupon = await Coupon.findOne({ code: couponCode });
    if (!coupon || coupon.expiresAt < new Date()) return res.status(422).json({ message: 'invalid coupon' });
    discount = subtotal * (coupon.percent / 100);
  }

  const total = subtotal - discount;
  const order = await Order.create({ userId: req.user.id, items, addressId, total, status: 'pending' });

  for (const line of items) {
    await Product.updateOne({ _id: line.productId }, { $inc: { stock: -line.quantity } });
  }
  await mailer.send(req.user.email, 'Order placed', `Total: ${total}`);

  res.status(200).json(order);
}
```

Refactor it into validation schema + service + thin controller, and list what you fixed along the way.

<details>
<summary>Solution</summary>

```js
// File: src/validators/orderSchemas.js
import { z } from 'zod';

export const createOrderSchema = z.object({
  items: z
    .array(z.object({
      productId: z.string().regex(/^[0-9a-f]{24}$/i, 'must be a product id'),
      quantity: z.coerce.number().int().min(1).max(999),
    }).strict())
    .min(1, 'an order needs at least one item')
    .max(50, 'an order can contain at most 50 lines'),
  couponCode: z.string().trim().toUpperCase().max(40).optional(),
  addressId: z.string().regex(/^[0-9a-f]{24}$/i, 'must be an address id'),
}).strict();
```

```js
// File: src/services/orderService.js
import { AppError, BadRequestError, ConflictError, ForbiddenError, NotFoundError } from '../utils/AppError.js';

export function createOrderService({ addressRepository, productRepository, couponRepository, orderRepository, mailer, logger }) {
  /** Pure pricing: no I/O, so it can be unit-tested exhaustively. */
  function priceOrder(lines, coupon) {
    const subtotal = lines.reduce((sum, line) => sum + line.product.price * line.quantity, 0);
    const discount = coupon ? Math.round(subtotal * (coupon.percent / 100)) : 0;
    return { subtotal, discount, total: subtotal - discount };
  }

  return {
    async create(input, { actor }) {
      // 1. Ownership
      const address = await addressRepository.findById(input.addressId);
      if (!address) throw new NotFoundError('Address not found');
      if (address.userId !== actor.id) throw new ForbiddenError('That address belongs to another user');

      // 2. Load every product once, and fail with a precise error.
      const products = await productRepository.findByIds(input.items.map((line) => line.productId));
      const byId = new Map(products.map((product) => [product.id, product]));

      const lines = input.items.map((line) => {
        const product = byId.get(line.productId);
        if (!product) throw new NotFoundError(`Product ${line.productId} not found`);
        if (product.stock < line.quantity) {
          throw new ConflictError(`Not enough stock for ${product.name}`, {
            productId: product.id,
            requested: line.quantity,
            available: product.stock,
          });
        }
        return { ...line, product };
      });

      // 3. Coupon rules
      let coupon = null;
      if (input.couponCode) {
        coupon = await couponRepository.findByCode(input.couponCode);
        if (!coupon) throw new BadRequestError('Unknown coupon code', { field: 'couponCode' });
        if (coupon.expiresAt <= new Date()) throw new BadRequestError('Coupon has expired', { field: 'couponCode' });
      }

      // 4. Pricing
      const { subtotal, discount, total } = priceOrder(lines, coupon);

      // 5. Persist atomically — see 03-databases for transactions.
      const order = await orderRepository.createWithStockDecrement({
        userId: actor.id,
        addressId: address.id,
        lines: lines.map((line) => ({ productId: line.product.id, quantity: line.quantity, unitPrice: line.product.price })),
        subtotal,
        discount,
        total,
        status: 'pending',
      });

      // 6. Side effects after the commit, and never blocking the response on an email.
      void mailer
        .send(actor.email, 'Order placed', `Total: ${total}`)
        .catch((error) => logger.error('order confirmation email failed', { orderId: order.id, error: error.message }));

      logger.info('order created', { orderId: order.id, userId: actor.id, total });
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

        res
          .status(201)                                        // was 200: a resource was created
          .location(`/api/v1/orders/${order.id}`)
          .json({ data: toOrderDto(order) });                 // was: the raw document
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

### What the refactor fixed

| # | Original | Problem | Fixed by |
| --- | --- | --- | --- |
| 1 | Manual `if (!Array.isArray(items))` checks | Inconsistent 400s, no field names, no type coercion | Zod schema → 422 with `details` |
| 2 | `Product.findById` **inside a loop** | N+1 queries: 50 items = 50 round trips | `findByIds` → one query |
| 3 | `subtotal += product.price * line.quantity` with raw floats | Rounding drift in money | Integer cents / `Math.round` in one pure function |
| 4 | Stock check then decrement, separately | Race condition: two orders can over-sell | A single transactional `createWithStockDecrement` |
| 5 | `res.status(200).json(order)` | Wrong status; leaked the raw document | `201` + `Location` + DTO |
| 6 | `await mailer.send(...)` before responding | A slow mail server makes the API slow, and a failure loses the order | Fire-and-forget with a `.catch` log |
| 7 | Business rules (stock, coupon, pricing) in the controller | Unusable from a job or admin tool; untestable without HTTP | Moved into the service |
| 8 | Errors returned as `{ message }` | Different shape from the rest of the API | `throw new AppError(...)` → one contract |
| 9 | Distinct error codes conflated (`403` for a bad address, `404` for a product) | Wrong semantics | `NotFoundError` vs `ForbiddenError` used correctly |
| 10 | No logging or request id | Cannot correlate a failed order with the request | `logger.info` with `orderId`, plus `req.id` from middleware |
| 11 | `coupon.expiresAt < new Date()` only | Coupons had no usage limits, minimum totals or product restrictions | Rule space now lives in `couponRepository`/service and is testable |
| 12 | `req.user.email` used for mail | Identity taken from the token — correct here, but never from the body | Kept from `req.user`; explicitly noted |

```js
// File: tests/orderService.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createOrderService } from '../src/services/orderService.js';
import { ConflictError, ForbiddenError, NotFoundError, BadRequestError } from '../src/utils/AppError.js';

const actor = { id: 'u1', email: 'u1@example.com' };
const address = { id: 'a1', userId: 'u1' };
const products = [
  { id: 'p1', name: 'Keyboard', price: 5000, stock: 3 },
  { id: 'p2', name: 'Mouse', price: 2500, stock: 0 },
];

function buildDeps(overrides = {}) {
  return {
    addressRepository: { findById: async () => address },
    productRepository: { findByIds: async () => products },
    couponRepository: { findByCode: async () => null },
    orderRepository: { createWithStockDecrement: async (payload) => ({ id: 'o1', ...payload }) },
    mailer: { send: async () => {} },
    logger: { info() {}, error() {} },
    ...overrides,
  };
}

test('prices an order and creates it', async () => {
  const service = createOrderService(buildDeps());
  const order = await service.create(
    { addressId: 'a1', items: [{ productId: 'p1', quantity: 2 }] },
    { actor },
  );

  assert.equal(order.total, 10000);
  assert.equal(order.status, 'pending');
  assert.equal(order.userId, 'u1');
});

test('applies a percentage coupon and rounds to cents', async () => {
  const service = createOrderService(buildDeps({
    couponRepository: { findByCode: async () => ({ code: 'SAVE10', percent: 10, expiresAt: new Date(Date.now() + 86_400_000) }) },
  }));

  const order = await service.create(
    { addressId: 'a1', items: [{ productId: 'p1', quantity: 1 }], couponCode: 'SAVE10' },
    { actor },
  );

  assert.equal(order.discount, 500);
  assert.equal(order.total, 4500);
});

test('rejects an address owned by someone else', async () => {
  const service = createOrderService(buildDeps({
    addressRepository: { findById: async () => ({ id: 'a1', userId: 'u2' }) },
  }));

  await assert.rejects(
    () => service.create({ addressId: 'a1', items: [{ productId: 'p1', quantity: 1 }] }, { actor }),
    ForbiddenError,
  );
});

test('rejects an out-of-stock product with details', async () => {
  const service = createOrderService(buildDeps());

  await assert.rejects(
    () => service.create({ addressId: 'a1', items: [{ productId: 'p2', quantity: 1 }] }, { actor }),
    (error) => {
      assert.ok(error instanceof ConflictError);
      assert.deepEqual(error.details, { productId: 'p2', requested: 1, available: 0 });
      return true;
    },
  );
});

test('rejects a missing product', async () => {
  const service = createOrderService(buildDeps());

  await assert.rejects(
    () => service.create({ addressId: 'a1', items: [{ productId: 'nope', quantity: 1 }] }, { actor }),
    NotFoundError,
  );
});

test('rejects an expired coupon', async () => {
  const service = createOrderService(buildDeps({
    couponRepository: { findByCode: async () => ({ code: 'OLD', percent: 10, expiresAt: new Date(Date.now() - 1000) }) },
  }));

  await assert.rejects(
    () => service.create({ addressId: 'a1', items: [{ productId: 'p1', quantity: 1 }], couponCode: 'OLD' }, { actor }),
    BadRequestError,
  );
});
```

```bash
node --test tests/orderService.test.js
```

```text
✔ prices an order and creates it
✔ applies a percentage coupon and rounds to cents
✔ rejects an address owned by someone else
✔ rejects an out-of-stock product with details
✔ rejects a missing product
✔ rejects an expired coupon
pass 6
fail 0
```

**Note what these tests do not need:** an HTTP server, a request object, a response object, or a real
database. That is the payoff of a thin controller and a data-free service boundary — the same service
can be called from a cron job that re-prices abandoned carts.

</details>

---

## What's next

Controllers are now thin. Next: the layer they call — services — where business rules live, and how to
keep them free of HTTP so they can be reused and tested.

→ [11 — Services](11-services.md)
