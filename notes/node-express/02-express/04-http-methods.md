# 04 — HTTP Methods

> **Where this fits:** Routing decides _which function runs_. The HTTP method decides _what that function is allowed to assume_. Choosing the wrong verb is not a style issue — it breaks retries, caching, proxies, and every client library that trusts HTTP semantics. This chapter covers all the methods an Express API needs, and the one comparison that matters most: **PUT vs PATCH**.

***

## 1. The method is a contract

Every HTTP request carries a method that tells _everyone in the chain_ — your framework, the proxies, the caches, the client library — what the request does:

```http
GET /api/v1/notes/42 HTTP/1.1
Host: api.example.com
```

`GET` says: "retrieve this; do not change anything." That sentence is what lets a cache store the response, a proxy retry it after a network blip, and a browser prefetch it safely.

Two properties describe that contract:

| Property       | Meaning                                                    | Why it matters                                                              |
| -------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------- |
| **Safe**       | Read-only: no intended change to server state              | Caches, crawlers, prefetchers and proxies may make the request on their own |
| **Idempotent** | Repeating the request has the same effect as doing it once | Retries after timeouts are safe — and clients _will_ retry                  |

**The full table:**

| Method             | Safe | Idempotent | Has a body by convention | Typical status codes                     | Used for                                                     |
| ------------------ | ---- | ---------- | ------------------------ | ---------------------------------------- | ------------------------------------------------------------ |
| `GET`              | ✅    | ✅          | No                       | `200`, `206`, `304`, `400`, `404`        | Read a resource or collection                                |
| `POST`             | ❌    | ❌          | **Yes**                  | `201`, `202`, `200`, `400`, `409`, `422` | Create, or run a non-idempotent action                       |
| `PUT`              | ❌    | ✅          | **Yes**                  | `200`, `201`, `204`, `409`               | Create-or-**replace** the resource at a known URL            |
| `PATCH`            | ❌    | Usually ❌  | **Yes**                  | `200`, `204`, `422`                      | Apply a **partial** modification                             |
| `DELETE`           | ❌    | ✅          | Normally no              | `200`, `202`, `204`, `404`               | Remove a resource                                            |
| `HEAD`             | ✅    | ✅          | No                       | Same as `GET`, no body                   | Metadata: existence, size, `ETag`, freshness                 |
| `OPTIONS`          | ✅    | ✅          | No                       | `204`, `200`                             | Discover allowed methods; CORS preflight                     |
| `TRACE`, `CONNECT` | —    | —          | —                        | —                                        | Do not implement them — security risk, no use case in an API |

> **`PATCH` is "usually not idempotent"** because _this_ patch is idempotent: `{"counter": 5}` (set to 5) but _this_ one is not: `{"counter": {"$inc": 1}}` (increment). The method does not guarantee idempotency; the _patch document_ decides. Write patches that set absolute values where you can.

***

## 2. `GET` — read

```js
// File: src/routes/noteRoutes.js (excerpt)
import { Router } from 'express';

export function createNoteRouter({ controller }) {
  const router = Router();

  router.get('/', controller.list);        // GET /api/v1/notes
  router.get('/:id', controller.getOne);   // GET /api/v1/notes/42

  return router;
}
```

```js
// File: src/controllers/noteController.js (excerpt)
export const noteController = {
  list: async (req, res) => {
    // Filtering, sorting, pagination all live in the query string — never in the path.
    const { tag, q, sort = '-createdAt', page = 1, limit = 20 } = req.query;
    const result = await req.services.noteService.list({ tag, q, sort, page, limit });

    res.status(200).json({
      data: result.items,
      meta: { page: result.page, limit: result.limit, total: result.total },
    });
  },

  getOne: async (req, res) => {
    const note = await req.services.noteService.getById(req.params.id);
    if (!note) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: `Note ${req.params.id} not found` } });
    }
    return res.status(200).json({ data: note });
  },
};
```

```bash
curl -i http://localhost:3000/api/v1/notes/42
```

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
ETag: W/"5f-8pJ0lZcM6Dk"
Content-Length: 132

{"data":{"id":"42","title":"Learn Node","tags":["node"]}}
```

Rules for `GET`:

| Rule                                                       | Reason                                                                                                            |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Never change state** — no `GET /notes/42/delete`         | Proxies and crawlers may issue `GET` on their own; a state change is a security hole (this is _CSRF_, see ch. 18) |
| Put all inputs in the query string                         | The URL stays shareable, bookmarkable and cacheable                                                               |
| Return `404` for a missing resource, not `200` with `null` | Clients branch on status codes; `null` bodies hide errors                                                         |
| Send `ETag`/`Last-Modified` when the resource is cacheable | Saves bandwidth with `304` responses                                                                              |
| Make it safe to call millions of times                     | Monitoring, health checks and prefetchers all rely on it                                                          |

***

## 3. `POST` — create (and non-idempotent actions)

```js
// File: src/controllers/noteController.js (excerpt)
export const noteController = {
  create: async (req, res, next) => {
    try {
      const note = await req.services.noteService.create(req.body);

      // 201 + Location: the client now knows the URL of the new resource.
      res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: note });
    } catch (error) {
      next(error);
    }
  },
};
```

```bash
curl -i -X POST http://localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' \
  -d '{"title":"Learn Node","content":"Chapter 04","tags":["node"]}'
```

```http
HTTP/1.1 201 Created
Location: /api/v1/notes/9f1c2f6a-7a3f-4c9e-9c3b-2f4b1e6c8a11
Content-Type: application/json; charset=utf-8

{"data":{"id":"9f1c2f6a-…","title":"Learn Node","createdAt":"2026-09-18T10:15:30.001Z"}}
```

| Situation                             | Status                        | Body                   |
| ------------------------------------- | ----------------------------- | ---------------------- |
| Created synchronously                 | `201` + `Location`            | The created resource   |
| Accepted for later processing (queue) | `202` + `Location` of the job | `{ data: { jobId } }`  |
| Validation failed                     | `422`                         | Field-level details    |
| Duplicate (unique constraint)         | `409`                         | Which field conflicted |
| Rate limited                          | `429` + `Retry-After`         | Retry hint             |

**Why `POST` is not idempotent matters in practice:** if the client times out after your server created the note, an automatic retry creates a **second note**. Two standard fixes:

1. **`POST` with a client-generated id** (`PUT /notes/{clientUuid}` instead) — inherently idempotent.
2. **`Idempotency-Key`** header, stored for a while and replayed — see §11.

**`POST` is also the correct verb for anything that is not CRUD:** `POST /auth/login`, `POST /notes/:id/publish`, `POST /payments/charge`. If an operation does not fit "get, replace, patch, delete", `POST` is the honest answer.

***

## 4. `PUT` — replace the resource at a known URL

`PUT` means: _"make the resource at this URL look exactly like this body."_ It is a **full replacement**, and it is **idempotent**.

```js
// File: src/controllers/noteController.js (excerpt)
export const noteController = {
  replace: async (req, res, next) => {
    try {
      // PUT semantics: all required fields must be present; omitted optional fields are reset.
      const replacement = {
        title: req.body.title,
        content: req.body.content,
        tags: req.body.tags ?? [],
        pinned: req.body.pinned ?? false,
      };

      const result = await req.services.noteService.replace(req.params.id, replacement);

      if (result.created) {
        return res.status(201).location(`/api/v1/notes/${result.note.id}`).json({ data: result.note });
      }
      return res.status(200).json({ data: result.note });
    } catch (error) {
      return next(error);
    }
  },
};
```

```bash
# 1. Full replacement — every field is supplied. 'pinned' is reset even though it was true before.
curl -i -X PUT http://localhost:3000/api/v1/notes/42 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Learn Node deeply","content":"Rewritten","tags":["node","backend"]}'
```

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{"data":{"id":"42","title":"Learn Node deeply","content":"Rewritten","tags":["node","backend"],"pinned":false}}
```

```bash
# 2. PUT to a URL that does not exist yet — the client chooses the id.
curl -i -X PUT http://localhost:3000/api/v1/notes/client-chosen-id \
  -H 'Content-Type: application/json' -d '{"title":"Upserted","content":"by PUT"}'
```

```http
HTTP/1.1 201 Created
Location: /api/v1/notes/client-chosen-id
```

```bash
# 3. Idempotency in action: run the same PUT five times and compare.
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -w '%{http_code} ' -X PUT http://localhost:3000/api/v1/notes/client-chosen-id \
    -H 'Content-Type: application/json' -d '{"title":"Upserted","content":"by PUT"}'
done; echo
# 201 200 200 200 200   ← same end state every time; the first created it
```

| `PUT` rule                                               | Consequence if ignored                                                    |
| -------------------------------------------------------- | ------------------------------------------------------------------------- |
| The body is the **complete** representation              | Clients "lose" fields they did not send — the classic PUT bug             |
| Missing required fields → `422`                          | Silent partial updates masquerade as replacements                         |
| Missing optional fields are **defaulted, not preserved** | That is the semantics; be explicit about it in your API docs              |
| Idempotent                                               | Retries are safe — this is why `PUT` is preferred for sync/mobile clients |
| Can create at a client-chosen URL                        | Powers offline-first clients that generate ids locally                    |

> **`PUT` with a partial body is a bug, not a shortcut.** If callers send only changed fields, they are describing a `PATCH`. Accepting a partial body for `PUT` means a client that omitted `tags` silently wipes the tags — and nobody discovers it until production data is gone.

***

## 5. `PATCH` — partially modify

`PATCH` means: _"apply this modification to the resource."_ Only the supplied fields change.

```js
// File: src/controllers/noteController.js (excerpt)
export const noteController = {
  update: async (req, res, next) => {
    try {
      const patch = req.body ?? {};
      if (Object.keys(patch).length === 0) {
        return res.status(422).json({
          error: { code: 'VALIDATION_ERROR', details: [{ field: 'body', message: 'at least one field is required' }] },
        });
      }

      const note = await req.services.noteService.update(req.params.id, patch);
      return res.status(200).json({ data: note });
    } catch (error) {
      return next(error);
    }
  },
};
```

```bash
# Only the title changes. content, tags and pinned keep their current values.
curl -i -X PATCH http://localhost:3000/api/v1/notes/42 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Learn Node — revised"}'
```

```http
HTTP/1.1 200 OK

{"data":{"id":"42","title":"Learn Node — revised","content":"Rewritten","tags":["node","backend"],"pinned":false}}
```

### The null-versus-absent problem

JSON has no way to express "do not touch this field", because `{"tags": null}` and `{}` are different _only_ if you define them to be. Decide and document:

| Client intent                       | Body               | Server behaviour                                     |
| ----------------------------------- | ------------------ | ---------------------------------------------------- |
| Leave `tags` alone                  | omit the key       | keep the current value                               |
| Clear the array                     | `{"tags": []}`     | replace with an empty array                          |
| Set an optional field to "no value" | `{"pinned": null}` | either reject (`422`) or store `null` — **pick one** |

Recommended: **`undefined`/absent = leave alone; `null` = clear; reject truly unknown fields.** That keeps `PATCH` predictable and makes `PUT` a special case of "send everything".

```js
// File: src/services/noteService.js (excerpt) — distinguishing "absent" from "null"
export function createNoteService({ repository }) {
  return {
    async update(id, patch) {
      const current = await repository.findById(id);
      if (!current) return null;

      const next = { ...current };

      // Object.hasOwn is the correct "was this key present?" check.
      if (Object.hasOwn(patch, 'title')) next.title = patch.title;

      // Explicit null clears the field; absence keeps it.
      if (Object.hasOwn(patch, 'content')) next.content = patch.content;
      if (Object.hasOwn(patch, 'tags')) next.tags = patch.tags ?? [];
      if (Object.hasOwn(patch, 'pinned')) next.pinned = patch.pinned ?? false;

      next.updatedAt = new Date().toISOString();
      return repository.update(id, next);
    },
  };
}
```

***

## 6. `DELETE` — remove

```js
// File: src/controllers/noteController.js (excerpt)
export const noteController = {
  remove: async (req, res, next) => {
    try {
      const deleted = await req.services.noteService.remove(req.params.id);
      if (!deleted) {
        return res.status(404).json({ error: { code: 'NOT_FOUND', message: `Note ${req.params.id} not found` } });
      }
      return res.status(204).end();          // success, nothing to say
    } catch (error) {
      return next(error);
    }
  },
};
```

```bash
curl -i -X DELETE http://localhost:3000/api/v1/notes/42
```

```http
HTTP/1.1 204 No Content
```

```bash
# Idempotent by design: the SECOND delete is a 404, but the state is unchanged.
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE http://localhost:3000/api/v1/notes/42   # 404
```

| Decision            | Options                                          | Recommendation                                                                |
| ------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------- |
| Second delete       | `404` (not found now) or `204` (goal achieved)   | `404` — it is more informative; both are defensible, pick one and document it |
| Success status      | `204` (no body) or `200` with `{ data: { id } }` | `204` when the client needs nothing back                                      |
| Soft vs hard delete | `deletedAt` column vs removing the row           | Soft delete for recoverable data; hard delete when the data must go (privacy) |
| Async deletion      | `202` + a job id                                 | For large cascades                                                            |
| Delete a collection | `DELETE /notes?tag=old`                          | Legal but dangerous — require an explicit confirmation parameter              |

***

## 7. `HEAD` and `OPTIONS`

```js
// File: src/app.js (excerpt)
// You do NOT register HEAD: Express answers it automatically for every GET route,
// running the handler and discarding the body.
```

```bash
curl -I http://localhost:3000/api/v1/notes/42      # -I sends HEAD
```

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
ETag: W/"5f-8pJ0lZcM6Dk"
Content-Length: 132
```

`HEAD` is used by clients to check existence, size and freshness without downloading the body (a mobile client syncing thousands of items saves a lot of bytes). Express handles it, but note that the **handler still runs** — so a `GET` handler with expensive side effects would still pay for them.

`OPTIONS` is what browsers use for the CORS preflight request (ch. 16). Express provides an automatic answer **when no catch-all middleware intercepts the request**:

```bash
curl -i -X OPTIONS http://localhost:3000/api/v1/notes/42
```

```http
HTTP/1.1 200 OK
Allow: GET, HEAD
Content-Length: 9

GET, HEAD
```

Two things to know about that auto-answer:

1. It only happens if the path matches a registered route **and** nothing else (like your own 404 middleware) consumed the request first.
2. It lists only the methods of that exact path — so if you want a full, correct `Allow` header, use the `methodNotAllowed` helper from [03 — Routing](03-routing.md), which answers `OPTIONS` with `204` plus a complete `Allow`.

```js
// File: src/routes/noteRoutes.js (excerpt)
// An explicit OPTIONS handler when you need custom behaviour (e.g. CORS headers).
router.options('/:id', (req, res) => {
  res.set('Allow', 'GET, PATCH, DELETE, HEAD, OPTIONS').status(204).end();
});
```

***

## 8. `app.all`, and method overriding for HTML forms

```js
// File: app-all.js
import express from 'express';

const app = express();

// Runs for every method — useful for middleware-style guards, not for CRUD.
app.all('/api/v1/notes/*splat', (req, res, next) => {
  res.set('X-Api-Version', 'v1');
  next();
});

// A guard registered for all methods, used as a 405 fallback (see chapter 03).
app.all('/api/v1/notes/:id', (req, res) => {
  res.set('Allow', 'GET, PATCH, DELETE, HEAD, OPTIONS');
  res.status(405).json({ error: { code: 'METHOD_NOT_ALLOWED', method: req.method } });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

HTML forms can only send `GET` and `POST`. If an old client must perform a `PUT`/`PATCH`/`DELETE`, the `method-override` package turns `POST` + a parameter into the real method:

```js
// File: method-override.js (only if you genuinely need HTML-form clients)
import express from 'express';
import methodOverride from 'method-override';

const app = express();

// Reads ?_method=DELETE or the X-HTTP-Method-Override header and rewrites req.method.
app.use(methodOverride('_method'));
app.use(methodOverride('X-HTTP-Method-Override'));

app.post('/api/v1/notes/:id', (req, res) => {
  // With ?_method=DELETE, req.method is now 'DELETE' by the time we get here.
  res.json({ actualMethod: req.method, id: req.params.id });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
npm install method-override
curl -s -X POST 'http://localhost:3000/api/v1/notes/42?_method=DELETE'
# {"actualMethod":"DELETE","id":"42"}
```

> **Treat method overriding as a compatibility shim.** It exists for legacy HTML forms and for corporate proxies that block `PATCH`. Do not use it as a design tool — it confuses caches (a `POST` that behaves like a `DELETE` is cached like a `POST`, i.e. not at all) and it surprises tooling.

***

## 9. PUT vs PATCH — the full comparison

This is the comparison everyone gets wrong in interviews and in code, so it deserves its own section.

| Aspect                         | `PUT`                                                    | `PATCH`                                                            |
| ------------------------------ | -------------------------------------------------------- | ------------------------------------------------------------------ |
| Intent                         | Replace the whole resource                               | Modify part of the resource                                        |
| Body contains                  | The complete representation                              | Only the changes                                                   |
| Missing fields                 | **Reset to defaults** (or rejected)                      | **Left untouched**                                                 |
| Creates the resource if absent | Yes, at the request URL                                  | Not specified by the standard; normally `404`                      |
| Idempotent                     | ✅ Always                                                 | Only if the patch document is (absolute sets: yes; increments: no) |
| Typical status codes           | `200` / `201` (created) / `204`                          | `200` / `204`                                                      |
| Bandwidth                      | Large (sends everything)                                 | Small (sends the delta)                                            |
| Race conditions                | Last write wins — a stale client overwrites _everything_ | Safe to merge concurrently, but can still clobber single fields    |
| Conflict detection             | Natural with `If-Match`/`ETag`                           | Also possible with `If-Match`                                      |
| Right for                      | Full-document editors, offline sync, idempotent upserts  | Setting a flag, changing one field, admin UIs, mobile clients      |

### The same change, expressed both ways

Suppose the note is:

```json
{ "id": "42", "title": "Learn Node", "content": "Chapter 4", "tags": ["node", "http"], "pinned": false }
```

**Goal: pin the note.**

```jsonc
// PUT — the client must know and resend the entire resource
PUT /api/v1/notes/42
{ "title": "Learn Node", "content": "Chapter 4", "tags": ["node", "http"], "pinned": true }

// PATCH — the client sends only what changes
PATCH /api/v1/notes/42
{ "pinned": true }
```

**What happens when two clients edit concurrently?**

```
Client A: PATCH {"title": "Learn Node — revised"}     → title changes
Client B: PATCH {"pinned": true}                      → pinned changes
Result:   both changes survive                        ✔ (different fields)

Client A: PUT   {title, content, tags, pinned: false} → full document, taken from a stale read
Client B: PUT   {title, content, tags, pinned: true}  → full document, taken from a stale read
Result:   A's write is entirely lost                  ✘ (last write wins)
```

That is the honest summary: **`PATCH` merges changes, `PUT` asserts a complete state.** Both are correct; they express different intents. Pick based on what the client actually knows.

### Combining both, correctly

Many APIs expose both verbs on the same resource, with the same underlying service but different validation:

```js
// File: src/routes/noteRoutes.js (excerpt)
import { Router } from 'express';
import { validateReplaceNote, validatePatchNote } from '../validators/noteSchemas.js';

export function createNoteRouter({ controller, validate }) {
  const router = Router();

  // PUT requires the full document — validation of the "replace" shape.
  router.put('/:id', validate(validateReplaceNote), controller.replace);

  // PATCH requires at least one known field — a different schema.
  router.patch('/:id', validate(validatePatchNote), controller.update);

  return router;
}
```

```js
// File: src/validators/noteSchemas.js (excerpt, Zod 4 — details in chapter 12)
import { z } from 'zod';

/** PUT: the complete representation. */
export const validateReplaceNote = z.object({
  title: z.string().trim().min(1).max(200),
  content: z.string().trim().min(1).max(10_000),
  tags: z.array(z.string().trim().min(1).toLowerCase()).max(10).default([]),
  pinned: z.boolean().default(false),
}).strict();

/** PATCH: any subset, but at least one key. */
export const validatePatchNote = z.object({
  title: z.string().trim().min(1).max(200).optional(),
  content: z.string().trim().min(1).max(10_000).optional(),
  tags: z.array(z.string().trim().min(1).toLowerCase()).max(10).optional(),
  pinned: z.boolean().optional(),
}).strict().refine((value) => Object.keys(value).length > 0, {
  message: 'at least one field must be provided',
});
```

> **Do not "support both" by making `PUT` accept partial bodies.** If your `PUT` handler merges instead of replacing, clients cannot tell the two verbs apart, and a tool that does a correct `PUT` (sending everything) still behaves identically while a client doing a partial `PUT` silently corrupts data. Two verbs, two semantics, two schemas.

***

## 10. Idempotency in practice: retries and the `Idempotency-Key`

Networks fail _after_ the server did the work. Without idempotency handling, "retry" means "do it twice".

| Situation                         | Safe to retry automatically?                            |
| --------------------------------- | ------------------------------------------------------- |
| `GET` timed out                   | ✅ Always                                                |
| `PUT` timed out                   | ✅ Always (same final state)                             |
| `DELETE` timed out                | ✅ Always (the resource is gone either way)              |
| `PATCH` that sets absolute values | ✅ Usually                                               |
| `PATCH` that increments / appends | ❌ Never                                                 |
| `POST` that creates               | ❌ Unless the client sends an idempotency key            |
| `POST /payments/charge`           | ❌ Unless the payment provider supports idempotency keys |

```js
// File: src/middleware/idempotency.js
import { randomUUID } from 'node:crypto';

/**
 * A small, honest idempotency layer:
 *   - Client sends `Idempotency-Key: <uuid>` on POST.
 *   - The first request runs; its response is stored under that key for `ttlMs`.
 *   - A retry with the same key replays the stored response instead of creating again.
 *
 * For production, store the records in Redis or a database — this in-memory version
 * is single-process only (which is all a tutorial should pretend to be).
 */
export function createIdempotency({ ttlMs = 24 * 60 * 60 * 1000, logger = console } = {}) {
  const store = new Map();     // key → { status, body, createdAt }

  // Sweep expired entries so the map cannot grow forever.
  const sweep = setInterval(() => {
    const cutoff = Date.now() - ttlMs;
    for (const [key, record] of store) {
      if (record.createdAt < cutoff) store.delete(key);
    }
  }, Math.min(ttlMs, 60_000));
  sweep.unref();

  return function idempotency(req, res, next) {
    // Only requests that create state need this.
    if (req.method !== 'POST') return next();

    const key = req.get('idempotency-key');
    if (!key) return next();                       // opt-in: behave normally without a key

    const existing = store.get(key);
    if (existing) {
      logger.info('idempotent replay', { key, path: req.originalUrl });
      res.set('Idempotency-Replayed', 'true');
      return res.status(existing.status).json(existing.body);
    }

    // Capture the response the first time so it can be replayed.
    const originalJson = res.json.bind(res);
    res.json = (body) => {
      store.set(key, { status: res.statusCode, body, createdAt: Date.now() });
      return originalJson(body);
    };

    req.idempotencyKey = key;
    return next();
  };
}
```

```bash
# First call creates; note the id in the response.
KEY=$(node -e "console.log(crypto.randomUUID())")
curl -s -i -X POST localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' -H "Idempotency-Key: $KEY" \
  -d '{"title":"Charge once","content":"exactly once"}' | head -6
```

```http
HTTP/1.1 201 Created
Location: /api/v1/notes/8c1d…-2f19
```

```bash
# Retry with the SAME key: same response, no second note.
curl -s -i -X POST localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' -H "Idempotency-Key: $KEY" \
  -d '{"title":"Charge once","content":"exactly once"}' | grep -i 'idempotency\|HTTP/'
```

```http
HTTP/1.1 201 Created
Idempotency-Replayed: true
```

```bash
# Confirm only one note exists:
curl -s 'localhost:3000/api/v1/notes?q=Charge%20once' | node -e "
  let raw=''; process.stdin.on('data', (c) => (raw += c)).on('end', () => {
    console.log('matches:', JSON.parse(raw).meta.total);   // matches: 1
  });"
```

| Design point                                  | Why                                                                                          |
| --------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Key is **client-generated**                   | Only the client knows a retry is the same logical operation                                  |
| Replay the **exact stored response**          | The client's retry must be indistinguishable from the original                               |
| `Idempotency-Replayed: true` header           | Makes the behaviour observable in logs and tests                                             |
| TTL (24h)                                     | Keys must not accumulate forever; 24h covers realistic retry windows                         |
| Store outside the process in production       | Two server instances must share the key space                                                |
| Reject a key reused with a **different body** | Otherwise a client bug becomes data corruption — compare a hash of the body and return `422` |

***

## 11. Methods and caching

```http
GET /api/v1/notes/42 HTTP/1.1
If-None-Match: W/"5f-8pJ0lZcM6Dk"
```

```http
HTTP/1.1 304 Not Modified
ETag: W/"5f-8pJ0lZcM6Dk"
```

| Rule                                                                  | Consequence                                                         |
| --------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `GET` and `HEAD` are cacheable by default                             | Add `Cache-Control` and `ETag` to control _how_                     |
| `POST`/`PUT`/`PATCH`/`DELETE` responses are **not** cacheable         | A cache must not serve "the result of the delete" to another client |
| `Cache-Control: no-store` on anything sensitive                       | Tokens, personal data, `Set-Cookie` responses                       |
| `Vary: Authorization` on per-user responses                           | Otherwise a shared cache leaks one user's data to another           |
| A `304` has no body                                                   | Clients must reuse their stored copy                                |
| `POST` responses can be _stored_ only with explicit freshness headers | Rare, and easy to get wrong — prefer not to                         |

```js
// File: src/middleware/cacheControl.js
/** Apply conservative cache headers to all GET responses by default. */
export function cacheControl({ maxAgeSeconds = 0 } = {}) {
  return function cacheControlMiddleware(req, res, next) {
    if (req.method === 'GET' || req.method === 'HEAD') {
      res.set('Cache-Control', maxAgeSeconds > 0 ? `private, max-age=${maxAgeSeconds}` : 'private, no-cache');
      res.set('Vary', 'Authorization, Accept-Encoding');
    } else {
      res.set('Cache-Control', 'no-store');
    }
    next();
  };
}
```

***

## 12. Methods and status codes together

| Action    | Method + path             | Success            | Validation failure | Not found                | Conflict                  | Other                    |
| --------- | ------------------------- | ------------------ | ------------------ | ------------------------ | ------------------------- | ------------------------ |
| List      | `GET /notes`              | `200`              | `422` (bad query)  | —                        | —                         | `304` if unchanged       |
| Read      | `GET /notes/:id`          | `200`              | `422` (bad id)     | `404`                    | —                         | `304` with `ETag`        |
| Create    | `POST /notes`             | `201` + `Location` | `422`              | —                        | `409`                     | `429`                    |
| Replace   | `PUT /notes/:id`          | `200` / `201`      | `422`              | `404` (if not upserting) | `409`                     | `412` with `If-Match`    |
| Modify    | `PATCH /notes/:id`        | `200` / `204`      | `422`              | `404`                    | `409`                     | `412`                    |
| Delete    | `DELETE /notes/:id`       | `204`              | `422`              | `404`                    | —                         | `409` (still referenced) |
| Action    | `POST /notes/:id/publish` | `200` / `202`      | `422`              | `404`                    | `409` (already published) | `429`                    |
| Preflight | `OPTIONS /notes/:id`      | `204` + `Allow`    | —                  | `404`                    | —                         | `405` for a wrong path   |

***

## 13. Real-world example: a method-correct notes resource

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { methodNotAllowed } from '../middleware/methodNotAllowed.js';
import { validate } from '../middleware/validate.js';
import { createNoteSchema, replaceNoteSchema, patchNoteSchema, listQuerySchema } from '../validators/noteSchemas.js';

export function createNoteRouter({ controller }) {
  const router = Router();

  // Collection
  router.get('/', validate(listQuerySchema, 'query'), controller.list);
  router.post('/', validate(createNoteSchema), controller.create);

  // Item
  router.get('/:id', controller.getOne);
  router.put('/:id', validate(replaceNoteSchema), controller.replace);   // full replacement
  router.patch('/:id', validate(patchNoteSchema), controller.update);    // partial update
  router.delete('/:id', controller.remove);

  // Actions that are not CRUD are POSTs on sub-resources.
  router.post('/:id/publish', controller.publish);
  router.post('/:id/archive', controller.archive);

  // 405 guards, after the real handlers (chapter 03).
  router.all('/', methodNotAllowed(['GET', 'POST']));
  router.all('/:id', methodNotAllowed(['GET', 'PUT', 'PATCH', 'DELETE']));
  router.all('/:id/publish', methodNotAllowed(['POST']));
  router.all('/:id/archive', methodNotAllowed(['POST']));

  return router;
}
```

```bash
BASE=http://localhost:3000/api/v1/notes

# Create
NOTE=$(curl -s -X POST $BASE -H 'Content-Type: application/json' \
  -d '{"title":"Draft","content":"first version","tags":["drafts"]}')
ID=$(printf '%s' "$NOTE" | node -e "let r='';process.stdin.on('data',c=>r+=c).on('end',()=>console.log(JSON.parse(r).data.id));")

# PATCH: one field changes, everything else is preserved
curl -s -X PATCH $BASE/$ID -H 'Content-Type: application/json' -d '{"pinned":true}'

# PUT: the whole document is replaced — 'tags' missing means tags become []
curl -s -X PUT $BASE/$ID -H 'Content-Type: application/json' \
  -d '{"title":"Final","content":"rewritten completely"}'

# PUT is idempotent: run it again, compare
curl -s -X PUT $BASE/$ID -H 'Content-Type: application/json' \
  -d '{"title":"Final","content":"rewritten completely"}'

# Wrong method on an existing path → 405 with Allow
curl -s -i -X POST $BASE/$ID | head -3

# PATCH with an empty body → 422
curl -s -X PATCH $BASE/$ID -H 'Content-Type: application/json' -d '{}'

# DELETE, then DELETE again → 404
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE $BASE/$ID
```

Expected:

```
PATCH  {"data":{"id":"…","title":"Draft","content":"first version","tags":["drafts"],"pinned":true}}
PUT    {"data":{"id":"…","title":"Final","content":"rewritten completely","tags":[],"pinned":false}}
PUT    {"data":{"id":"…","title":"Final","content":"rewritten completely","tags":[],"pinned":false}}
405    Allow: GET, PUT, PATCH, DELETE, HEAD, OPTIONS
422    {"error":{"code":"VALIDATION_ERROR","details":[{"field":"body","message":"at least one field is required"}]}}
204
404
```

Note the third line: a second identical `PUT` returns the same state — that is what idempotency means in a test you can actually run.

***

## 14. Common mistakes

| Mistake                                                 | Symptom                                                                                         | Fix                                                       |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `GET /notes/:id/delete`                                 | State changes on a "safe" method — crawlers, prefetchers and prefetching caches can delete data | Use `DELETE`                                              |
| `PUT` accepting partial bodies                          | Fields silently reset to defaults; data loss                                                    | `PUT` = full document; `PATCH` = partial                  |
| `PATCH` requiring the full document                     | Mobile clients must download-and-resend everything                                              | Validate only present keys                                |
| `POST` for updates                                      | Retries duplicate work; caches behave oddly                                                     | `PATCH`/`PUT` for updates                                 |
| `POST` create with no retry story                       | Network blips create duplicates                                                                 | Client-chosen ids or `Idempotency-Key`                    |
| `DELETE` returning `200` with no body                   | Inconsistent with `204` usage across the API                                                    | Pick one convention                                       |
| `405` missing entirely                                  | Clients get `404` for a wrong method and chase phantom bugs                                     | Add `Allow`-aware guards (ch. 03)                         |
| `Allow` missing on `OPTIONS`                            | CORS preflight fails in browsers                                                                | Return `Allow` (ch. 16)                                   |
| Assuming `HEAD` is free                                 | The `GET` handler still runs                                                                    | Keep `GET` handlers cheap                                 |
| Using `GET` with a request body                         | Ignored by many proxies and clients; undefined behaviour                                        | Put inputs in the query string                            |
| Sending `Content-Type` on `GET`/`DELETE` without a body | Some proxies reject it                                                                          | Omit the header when there is no body                     |
| Making `PATCH` mean "replace one field, guess the rest" | Lost updates under concurrency                                                                  | Send explicit deltas; use `ETag`/`If-Match` for conflicts |

***

## Exercise 4.1 — Implement `PUT` correctly

Take the notes API from [03 — Routing](03-routing.md) and add `PUT /api/v1/notes/:id` with **true replacement semantics**, plus tests that prove `PUT` and `PATCH` differ.

<details>

<summary>Solution</summary>

```js
// File: src/services/noteService.js
import { randomUUID } from 'node:crypto';

export function createNoteService({ repository, logger }) {
  return {
    /** POST /notes — the server chooses the id. */
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
      logger.info('note created', { id: created.id });
      return created;
    },

    /**
     * PUT /notes/:id — the FULL document.
     * Fields absent from the body are reset to their defaults, because the body
     * describes the resource's complete desired state.
     */
    async replace(id, input) {
      const existing = await repository.findById(id);
      const now = new Date().toISOString();

      const note = {
        id,                                       // the URL owns the id
        title: input.title,
        content: input.content,
        tags: input.tags ?? [],                   // absent → default, NOT "keep old"
        pinned: input.pinned ?? false,            // absent → default, NOT "keep old"
        createdAt: existing?.createdAt ?? now,    // creation time survives a replace
        updatedAt: now,
      };

      if (!existing) {
        const created = await repository.create(note);
        return { created: true, note: created };
      }

      const updated = await repository.update(id, note);
      return { created: false, note: updated };
    },

    /**
     * PATCH /notes/:id — a delta.
     * Fields absent from the body are left exactly as they are.
     */
    async update(id, patch) {
      const current = await repository.findById(id);
      if (!current) return null;

      const next = { ...current };
      if (Object.hasOwn(patch, 'title')) next.title = patch.title;
      if (Object.hasOwn(patch, 'content')) next.content = patch.content;
      if (Object.hasOwn(patch, 'tags')) next.tags = patch.tags ?? [];
      if (Object.hasOwn(patch, 'pinned')) next.pinned = patch.pinned ?? false;
      next.updatedAt = new Date().toISOString();

      return repository.update(id, next);
    },
  };
}
```

```js
// File: tests/put-vs-patch.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';
import { createInMemoryRepository } from '../src/repositories/noteRepository.js';

let server;
let baseUrl;

before(async () => {
  const app = createApp({
    config: { bodyLimit: '100kb', nodeEnv: 'test' },
    // A fake repository keeps this test about HTTP semantics, not disk I/O.
    repository: createInMemoryRepository(),
    logger: { info() {}, error() {}, warn() {}, debug() {} },
  });
  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1/notes`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const json = (path, options = {}) =>
  fetch(`${baseUrl}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
  });

async function createNote(overrides = {}) {
  const response = await json('', {
    method: 'POST',
    body: JSON.stringify({ title: 'Original', content: 'Body', tags: ['a', 'b'], pinned: true, ...overrides }),
  });
  assert.equal(response.status, 201);
  return (await response.json()).data;
}

test('PATCH changes only the supplied field', async () => {
  const note = await createNote();

  const response = await json(`/${note.id}`, { method: 'PATCH', body: JSON.stringify({ title: 'Patched' }) });
  assert.equal(response.status, 200);

  const patched = (await response.json()).data;
  assert.equal(patched.title, 'Patched');
  assert.equal(patched.content, 'Body');            // preserved
  assert.deepEqual(patched.tags, ['a', 'b']);       // preserved
  assert.equal(patched.pinned, true);               // preserved
});

test('PUT replaces the whole document and resets absent optional fields', async () => {
  const note = await createNote();

  const response = await json(`/${note.id}`, {
    method: 'PUT',
    body: JSON.stringify({ title: 'Replaced', content: 'New body' }),   // tags/pinned omitted
  });
  assert.equal(response.status, 200);

  const replaced = (await response.json()).data;
  assert.equal(replaced.title, 'Replaced');
  assert.equal(replaced.content, 'New body');
  assert.deepEqual(replaced.tags, []);              // ← reset, not preserved
  assert.equal(replaced.pinned, false);             // ← reset, not preserved
  assert.equal(replaced.createdAt, note.createdAt); // creation time is stable
});

test('PUT is idempotent: two identical calls produce the same state', async () => {
  const note = await createNote();
  const body = JSON.stringify({ title: 'Same', content: 'Same' });

  const first = (await (await json(`/${note.id}`, { method: 'PUT', body })).json()).data;
  const second = (await (await json(`/${note.id}`, { method: 'PUT', body })).json()).data;

  assert.equal(second.updatedAt >= first.updatedAt, true);   // may re-write the timestamp
  assert.deepEqual(
    { title: second.title, content: second.content, tags: second.tags, pinned: second.pinned },
    { title: first.title, content: first.content, tags: first.tags, pinned: first.pinned },
  );
});

test('PUT to an unknown id creates the resource at that URL', async () => {
  const response = await json('/client-chosen-id', {
    method: 'PUT',
    body: JSON.stringify({ title: 'Upserted', content: 'by PUT' }),
  });
  assert.equal(response.status, 201);
  assert.equal(response.headers.get('location'), '/api/v1/notes/client-chosen-id');
  assert.equal((await response.json()).data.id, 'client-chosen-id');
});

test('PATCH with an empty body is rejected', async () => {
  const note = await createNote();
  const response = await json(`/${note.id}`, { method: 'PATCH', body: '{}' });
  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.code, 'VALIDATION_ERROR');
});
```

```bash
node --test tests/put-vs-patch.test.js
```

```
✔ PATCH changes only the supplied field
✔ PUT replaces the whole document and resets absent optional fields
✔ PUT is idempotent: two identical calls produce the same state
✔ PUT to an unknown id creates the resource at that URL
✔ PATCH with an empty body is rejected
pass 5
fail 0
```

**The lesson:** the two verbs need _different service methods_, not different branches in one method. `replace()` starts from defaults; `update()` starts from the current document. Mixing them is how APIs lose data.

</details>

***

## Exercise 4.2 — Make `POST` retry-safe

Add the `Idempotency-Key` middleware from §10 to the notes API, and write a test proving that two identical `POST`s with the same key create exactly one note.

<details>

<summary>Solution</summary>

```js
// File: src/app.js (excerpt)
import express from 'express';
import { Router } from 'express';
import { createIdempotency } from './middleware/idempotency.js';

export function createApp({ config, repository, logger = console }) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: config.bodyLimit ?? '100kb' }));

  const api = Router();

  // Idempotency runs before any route that can create state.
  api.use(createIdempotency({ logger }));

  api.post('/notes', createNoteHandler({ repository, logger }));
  api.get('/notes', listNotesHandler({ repository }));

  app.use('/api/v1', api);

  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    const statusCode = error.statusCode ?? 500;
    return res.status(statusCode).json({ error: { code: error.code ?? 'INTERNAL_ERROR', message: error.message } });
  });

  return app;
}
```

```js
// File: src/handlers/notes.js
import { randomUUID } from 'node:crypto';

export function createNoteHandler({ repository, logger }) {
  return async function createNote(req, res, next) {
    try {
      const body = req.body ?? {};
      if (typeof body.title !== 'string' || body.title.trim() === '') {
        return res.status(422).json({
          error: { code: 'VALIDATION_ERROR', details: [{ field: 'title', message: 'required' }] },
        });
      }

      const now = new Date().toISOString();
      const note = {
        id: randomUUID(),
        title: body.title.trim(),
        content: typeof body.content === 'string' ? body.content : '',
        createdAt: now,
        updatedAt: now,
      };

      await repository.create(note);
      logger.info('note created', { id: note.id, idempotencyKey: req.idempotencyKey });

      // sendJson via res.json so the idempotency middleware can capture the body.
      return res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: note });
    } catch (error) {
      return next(error);
    }
  };
}

export function listNotesHandler({ repository }) {
  return async function listNotes(req, res, next) {
    try {
      const notes = await repository.list();
      return res.json({ data: notes, meta: { total: notes.length } });
    } catch (error) {
      return next(error);
    }
  };
}
```

```js
// File: tests/idempotency.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { createApp } from '../src/app.js';
import { createInMemoryRepository } from '../src/repositories/noteRepository.js';

let server;
let baseUrl;
let repository;

before(async () => {
  repository = createInMemoryRepository();
  const app = createApp({ config: { nodeEnv: 'test' }, repository, logger: { info() {}, error() {}, warn() {} } });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1/notes`;
});

after(() => new Promise((resolve) => server.close(resolve)));

function post(body, headers = {}) {
  return fetch(baseUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });
}

test('two POSTs with the same Idempotency-Key create one note', async () => {
  const key = randomUUID();
  const payload = { title: 'Exactly once', content: 'retry me' };

  const first = await post(payload, { 'Idempotency-Key': key });
  assert.equal(first.status, 201);
  const firstBody = await first.json();

  const second = await post(payload, { 'Idempotency-Key': key });
  assert.equal(second.status, 201);
  assert.equal(second.headers.get('idempotency-replayed'), 'true');

  const secondBody = await second.json();
  assert.deepEqual(secondBody, firstBody);           // byte-identical replay

  const list = await (await fetch(baseUrl)).json();
  const matching = list.data.filter((note) => note.title === 'Exactly once');
  assert.equal(matching.length, 1);                  // ← the whole point
});

test('without a key, each POST creates a new note', async () => {
  const before = (await (await fetch(baseUrl)).json()).meta.total;

  await post({ title: 'No key A', content: '' });
  await post({ title: 'No key A', content: '' });

  const after = (await (await fetch(baseUrl)).json()).meta.total;
  assert.equal(after, before + 2);
});

test('different keys create different notes', async () => {
  const before = (await (await fetch(baseUrl)).json()).meta.total;

  await post({ title: 'Distinct', content: '' }, { 'Idempotency-Key': randomUUID() });
  await post({ title: 'Distinct', content: '' }, { 'Idempotency-Key': randomUUID() });

  const after = (await (await fetch(baseUrl)).json()).meta.total;
  assert.equal(after, before + 2);
});
```

```bash
node --test tests/idempotency.test.js
```

```
✔ two POSTs with the same Idempotency-Key create one note
✔ without a key, each POST creates a new note
✔ different keys create different notes
pass 3
fail 0
```

**Production hardening (and why this solution is honest about its limits):**

| Limitation                                        | Production fix                                                                   |
| ------------------------------------------------- | -------------------------------------------------------------------------------- |
| In-memory map                                     | Redis (`SET key value NX EX 86400`) or a database table                          |
| Two instances have separate maps                  | Shared store, keyed by `<key>:<route>`                                           |
| Nothing stops the same key with a different body  | Store a hash of the request body; `422` on mismatch                              |
| A crashed request may leave a half-written record | Store a "pending" marker first, then the response (the payment-provider pattern) |
| A key can be replayed forever                     | TTL + a `createdAt` column you can audit                                         |

</details>

***

## What's next

Methods describe intent. Next: the two objects that carry it — every property and method of `req` and `res` that you will actually use, with the mistakes each one invites.

→ [05 — Request and Response](05-request-response.md)
