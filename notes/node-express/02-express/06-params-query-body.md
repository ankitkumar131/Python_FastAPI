# 06 — Params, Query and Body

> **Where this fits:** Chapter 05 covered the request object as a whole. This chapter covers the three
> places user input arrives — `req.params`, `req.query` and `req.body` — including what types they
> actually hold, how to parse them safely, and the injection risks that come from trusting them.

---

## 1. Three sources of input, three different jobs

| Source | Example | Holds | Correct use | Wrong use |
| --- | --- | --- | --- | --- |
| **Path params** | `/notes/42` → `req.params.id = '42'` | Identity: *which* resource | Addressing a specific resource in a hierarchy | Passing filters, options, or large data |
| **Query string** | `/notes?tag=node&page=2` → `req.query` | Options: filter, sort, paginate, search | Anything optional that does not change *which* endpoint is called | Putting identity here (`/notes?id=42`) |
| **Request body** | `{"title":"x"}` → `req.body` | Payload: the data itself | Create/update data, credentials, complex filters | Sending data in a `GET` body |

```text
POST /api/v1/notes/42/comments?notify=true&expand=author
                    ▲         ▲          ▲
                    │         │          └── query: options for this call
                    │         └───────────── path param: which resource
                    └─────────────────────── body: the comment being created
```

A quick test of judgement:

| Requirement | Correct place | Why |
| --- | --- | --- |
| "Get note 42" | `/notes/42` | Identity |
| "Get notes tagged `node`, newest first, page 2" | `/notes?tag=node&sort=-createdAt&page=2` | Options; the resource is the collection |
| "Create a note titled X" | Body of `POST /notes` | Payload |
| "Delete note 42" | `DELETE /notes/42` | Identity + method |
| "Get comments of note 42" | `/notes/42/comments` | Hierarchy |
| "Which user's notes?" | `/users/7/notes` (or `?authorId=7`) | Identity of a *different* resource — nesting is clearer |
| "Format as CSV" | `Accept: text/csv` (content negotiation) — or `?format=csv` as a fallback | It is representation, not data |

> **Never put identity in the query string and never put filters in the path.** `/notes?id=42` cannot be
> cached per resource, breaks every link-sharing cache, and forces your router to be a query parser.

---

## 2. `req.params` — path parameters

```js
// File: params-basics.js
import express from 'express';

const app = express();

app.get('/users/:userId/notes/:noteId', (req, res) => {
  res.json({
    params: req.params,     // { userId: '7', noteId: '42' }
    types: Object.values(req.params).map((value) => typeof value),   // ['string', 'string']
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

| Fact | Consequence |
| --- | --- |
| Params are **always strings** | `req.params.page + 1` is `'21'`, not `22` — coerce explicitly |
| Params are **URL-decoded** | `%2F` becomes `/`, so a "segment" can contain a slash — never use a param as a file path |
| Wildcard params are **arrays** | `/files/*splat` → `req.params.splat = ['a', 'b.txt']` |
| Optional params are **missing, not empty** | `/opt{/:id}` → `req.params.id` is `undefined` when absent |
| Params come from several routers | A mounted router merges its own params with the parent's |

### Validating params is not optional

A param is attacker-controlled input. Two examples of what happens when you skip validation:

```text
GET /notes/../../etc/passwd        → path traversal if the param is used as a filename
GET /notes/%7B%22$ne%22:null%7D     → { "$ne": null } if the param is passed into a Mongo query
GET /users/99999999999999999999999 → ObjectId cast error → 500 instead of 422
```

```js
// File: src/validators/params.js
/**
 * Small, dependency-free param validators.
 * Each returns { ok: true, value } or { ok: false, message } — never throws.
 */
import { z } from 'zod';

const UuidSchema = z.string().uuid();
const ObjectIdSchema = z.string().regex(/^[0-9a-f]{24}$/i, 'must be a 24-character hex id');
const SlugSchema = z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'must be a lowercase slug');

const schemas = {
  uuid: UuidSchema,
  objectId: ObjectIdSchema,
  slug: SlugSchema,
  int: z.coerce.number().int().positive(),
};

/** Use as router.param('id', ...) so every route gets the same, validated value. */
export function validateParam(name, kind) {
  const schema = schemas[kind];

  return function paramValidator(req, res, next, value) {
    const parsed = schema.safeParse(value);
    if (!parsed.success) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          details: [{ field: name, message: parsed.error.issues[0].message }],
        },
      });
    }

    // Replace the raw string with the parsed value (never mutate req.params in place).
    req.validated ??= {};
    req.validated[name] = parsed.data;
    return next();
  };
}
```

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { validateParam } from '../validators/params.js';

export function createNoteRouter({ controller }) {
  const router = Router({ mergeParams: true });

  // Runs for every route below that declares :id — once per request.
  router.param('id', validateParam('id', 'uuid'));

  router.get('/:id', controller.getOne);        // controller reads req.validated.id
  router.patch('/:id', controller.update);
  router.delete('/:id', controller.remove);

  return router;
}
```

```bash
curl -s 'localhost:3000/api/v1/notes/not-a-uuid'
# 422 {"error":{"code":"VALIDATION_ERROR","details":[{"field":"id","message":"Invalid uuid"}]}}

curl -s 'localhost:3000/api/v1/notes/3f2b1a90-8c7d-4e5f-a6b1-2c3d4e5f6a7b'
# 200 (the controller never had to think about formats)
```

| Rule | Why |
| --- | --- |
| Validate the **format** (`uuid`, `objectId`, `slug`, positive int) | Turns a 500 into a clean 422 |
| Validate the **existence** in the service, not the router | The router should not know about repositories |
| Keep the raw and parsed values apart | `req.params.id` stays the string the client sent — audit logs and error messages need it |
| Never use a param as a path | `../../` traversal — see [01-nodejs/07-path.md](../01-nodejs/07-path.md) |
| Never put a param straight into a query | `?id=1 OR 1=1` and `$ne` injections — see §8 |

---

## 3. `req.query` — the query string

```js
// File: query-basics.js
import express from 'express';

const app = express();

app.get('/search', (req, res) => {
  // Everything is a string, an array of strings, or (with the extended parser) an object.
  res.json({
    query: req.query,                                       // { tag: ['a','b'], page: '2', q: 'node' }
    pageType: typeof req.query.page,                        // 'string'
    tagIsArray: Array.isArray(req.query.tag),               // true for ?tag=a&tag=b
    raw: req.originalUrl.split('?')[1] ?? '',               // 'tag=a&tag=b&page=2&q=node'
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

### Which parser is used? (This changed in Express 5)

| Setting | Implementation | `?tag=a&tag=b` | `?a[b]=1` |
| --- | --- | --- | --- |
| **`'simple'` — the Express 5 default** | `node:querystring` | `['a','b']` | `{ 'a[b]': '1' }` (key kept literally) |
| `'extended'` | the `qs` library | `['a','b']` | `{ a: { b: '1' } }` (nested objects) |
| `false` | disabled | `req.query` is `{}` (you parse `req.url` yourself) | — |
| a function | custom | whatever you return | — |

```js
// File: query-parser.js
import express from 'express';
import qs from 'qs';

const app = express();

// 1. The default: flat, predictable, no nested objects — the safe choice for APIs.
app.set('query parser', 'simple');

// 2. Nested/array syntax when you want it (?filter[status]=active&tags[]=a).
// app.set('query parser', 'extended');

// 3. Fully custom parsing (e.g. commas as separators):
// app.set('query parser', (str) => qs.parse(str, { comma: true, depth: 2 }));

app.get('/q', (req, res) => res.json({ query: req.query }));

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

Verified behaviour of the two parsers:

```text
query parser = 'simple'   (default)
  ?tag=a&tag=b        → { tag: ['a','b'] }
  ?a[b]=1             → { 'a[b]': '1' }          ← no nesting; the key is literal
  ?x=                 → { x: '' }
  ?plus=a+b           → { plus: 'a b' }          ← '+' means space
  ?encoded=%2F        → { encoded: '/' }

query parser = 'extended'
  ?a[b]=1&a[c]=2      → { a: { b: '1', c: '2' } }
  ?list[]=x&list[]=y  → { list: ['x','y'] }
```

> **Recommendation for an API: keep `'simple'`.** Nested query objects make validation harder, and
> `?filter[status]=active` is a DSL you then have to document. Flat, explicit parameters
> (`?status=active`) validate cleanly with a schema and are unambiguous.

### The five query patterns every API needs

```http
// The five query patterns, expressed as raw requests (not code yet)

// 1. Filtering        — equality, sets, ranges
GET /api/v1/notes?status=published
GET /api/v1/notes?tag=node&tag=backend          // repeated = OR
GET /api/v1/notes?createdAfter=2026-01-01&createdBefore=2026-06-30

// 2. Sorting          — a leading '-' means descending; never accept arbitrary field names
GET /api/v1/notes?sort=-createdAt
GET /api/v1/notes?sort=title,-createdAt          // multiple keys, applied in order

// 3. Pagination       — offset/limit is simplest; cursor is correct for large data
GET /api/v1/notes?page=2&limit=20
GET /api/v1/notes?cursor=eyJpZCI6IjQyIn0&limit=20

// 4. Searching        — one parameter, one meaning
GET /api/v1/notes?q=express%20middleware

// 5. Shaping          — what to include in the response
GET /api/v1/notes?fields=id,title
GET /api/v1/notes?include=author,comments
```

### Parsing query input safely

The naive version — `const limit = req.query.limit` — produces strings, `NaN`s and injection
opportunities. Here is a complete, dependency-free parser for a list endpoint:

```js
// File: src/validators/listQuery.js
/**
 * Parse and validate list-endpoint query parameters.
 * Returns { value } on success or { errors } — the handler decides the response.
 */

const SORTABLE_FIELDS = new Set(['createdAt', 'updatedAt', 'title']);
const MAX_LIMIT = 100;
const DEFAULT_LIMIT = 20;
const MAX_SEARCH_LENGTH = 200;

function asArray(value) {
  if (value === undefined) return undefined;
  return Array.isArray(value) ? value : [value];
}

function parsePositiveInt(raw, errors, field, { fallback, min = 1, max } = {}) {
  if (raw === undefined || raw === '') return fallback;

  const value = Number(raw);
  if (!Number.isInteger(value) || value < min) {
    errors.push({ field, message: `must be an integer >= ${min}` });
    return fallback;
  }
  if (max !== undefined && value > max) {
    errors.push({ field, message: `must be an integer <= ${max}` });
    return fallback;
  }
  return value;
}

function parseBoolean(raw, errors, field, fallback = undefined) {
  if (raw === undefined) return fallback;
  if (raw === 'true' || raw === '1') return true;
  if (raw === 'false' || raw === '0') return false;
  errors.push({ field, message: 'must be true or false' });
  return fallback;
}

function parseSort(raw, errors, field = 'sort') {
  if (raw === undefined || raw === '') return ['-createdAt'];

  const parts = String(raw).split(',').map((part) => part.trim()).filter(Boolean);
  if (parts.length === 0) {
    errors.push({ field, message: 'must contain at least one field' });
    return ['-createdAt'];
  }
  if (parts.length > 3) {
    errors.push({ field, message: 'supports at most 3 sort fields' });
    return ['-createdAt'];
  }

  const keys = [];
  for (const part of parts) {
    const descending = part.startsWith('-');
    const name = descending ? part.slice(1) : part;

    // ALLOWLIST: never pass an unvalidated field name to a query builder.
    if (!SORTABLE_FIELDS.has(name)) {
      errors.push({ field, message: `cannot sort by "${name}"` });
      continue;
    }
    keys.push({ field: name, direction: descending ? 'desc' : 'asc' });
  }

  return keys.length > 0 ? keys : [{ field: 'createdAt', direction: 'desc' }];
}

function parseFields(raw, errors, field = 'fields') {
  if (raw === undefined || raw === '') return undefined;

  const allowlist = new Set(['id', 'title', 'content', 'tags', 'pinned', 'createdAt', 'updatedAt']);
  const requested = String(raw).split(',').map((part) => part.trim()).filter(Boolean);

  const unknown = requested.filter((name) => !allowlist.has(name));
  if (unknown.length > 0) {
    errors.push({ field, message: `unknown fields: ${unknown.join(', ')}` });
    return undefined;
  }
  return requested;
}

export function parseListQuery(query) {
  const errors = [];

  const limit = parsePositiveInt(query.limit, errors, 'limit', { fallback: DEFAULT_LIMIT, max: MAX_LIMIT });
  const page = parsePositiveInt(query.page, errors, 'page', { fallback: 1 });
  const pinned = parseBoolean(query.pinned, errors, 'pinned');
  const sort = parseSort(query.sort, errors, 'sort');
  const fields = parseFields(query.fields, errors, 'fields');

  const tags = asArray(query.tag)
    ?.map((tag) => String(tag).trim().toLowerCase())
    .filter(Boolean)
    .slice(0, 10);

  const q = query.q === undefined ? undefined : String(query.q).trim().slice(0, MAX_SEARCH_LENGTH);

  // Reject unknown parameters so typos surface as errors, not as ignored filters.
  const known = new Set(['limit', 'page', 'pinned', 'sort', 'fields', 'tag', 'q']);
  for (const key of Object.keys(query)) {
    if (!known.has(key)) errors.push({ field: key, message: 'is not a supported query parameter' });
  }

  return {
    errors,
    value: { limit, page, offset: (page - 1) * limit, sort, fields, tags, q, pinned },
  };
}
```

```js
// File: src/controllers/noteController.js (excerpt)
import { parseListQuery } from '../validators/listQuery.js';

export const noteController = {
  list: async (req, res, next) => {
    try {
      const { value: query, errors } = parseListQuery(req.query);

      if (errors.length > 0) {
        return res.status(422).json({ error: { code: 'VALIDATION_ERROR', details: errors } });
      }

      const { items, total } = await req.services.noteService.list(query);

      return res.json({
        data: items,
        meta: {
          page: query.page,
          limit: query.limit,
          total,
          totalPages: Math.ceil(total / query.limit),
          hasNext: query.page * query.limit < total,
          sort: query.sort,
        },
      });
    } catch (error) {
      return next(error);
    }
  },
};
```

```bash
curl -s 'localhost:3000/api/v1/notes?limit=2&sort=-createdAt&tag=node&tag=backend'
```

```json
{
  "data": [
    { "id": "…", "title": "Learn Node", "tags": ["node", "backend"], "createdAt": "2026-09-18T10:15:30.001Z" }
  ],
  "meta": { "page": 1, "limit": 2, "total": 7, "totalPages": 4, "hasNext": true,
            "sort": [{ "field": "createdAt", "direction": "desc" }] }
}
```

```bash
# Errors you now get for free:
curl -s 'localhost:3000/api/v1/notes?limit=999'      # 422 "must be an integer <= 100"
curl -s 'localhost:3000/api/v1/notes?sort=password'  # 422 'cannot sort by "password"'
curl -s 'localhost:3000/api/v1/notes?page=abc'       # 422 "must be an integer >= 1"
curl -s 'localhost:3000/api/v1/notes?pinned=maybe'   # 422 "must be true or false"
curl -s 'localhost:3000/api/v1/notes?limitt=5'       # 422 "is not a supported query parameter"
```

| Rule | Reason |
| --- | --- |
| **Cap `limit`** | `?limit=10000000` is a denial-of-service vector |
| **Allowlist sortable fields** | `sort` becomes an SQL `ORDER BY` / Mongo `sort()` — unvalidated it is an injection point |
| **Reject unknown parameters** | A typo'd filter silently returning everything is worse than an error |
| **Parse booleans explicitly** | `?pinned=false` is truthy in a naive `if (req.query.pinned)` check |
| **Never trust `page` arithmetic** | Negative pages produce negative SQL offsets |
| **Cap search length** | Long `q` values turn into expensive scans |

---

## 4. `req.body` — parsed request payloads

`req.body` is filled in by middleware. Without a body parser it is `undefined` — and that is the single
most common Express bug.

```js
// File: body-parsers.js
import express from 'express';

const app = express();

// 1. JSON — for APIs. `limit` protects the process; `strict` rejects primitives.
app.use(express.json({
  limit: '100kb',        // '100kb' | '1mb' | bytes as a number
  strict: true,          // only objects and arrays are accepted at the top level
  type: ['application/json', 'application/*+json'],   // what Content-Type values are parsed
}));

// 2. Form bodies — for HTML forms and legacy clients.
app.use(express.urlencoded({ extended: false, limit: '100kb' }));

app.post('/json', (req, res) => {
  res.json({ body: req.body ?? null, receivedType: req.get('content-type') });
});

app.post('/form', (req, res) => {
  res.json({ body: req.body ?? null });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

### What actually happens, verified

| Request | `req.body` | Status |
| --- | --- | --- |
| `POST` JSON `{"title":"x"}` (content-type json) | `{ title: 'x' }` | `200` |
| `POST` JSON `''` (empty body, content-type json) | `{}` | `200` |
| `POST` JSON `'{bad'` | — | **`400`**, `type: 'entity.parse.failed'` |
| `POST` JSON `'null'` | — | **`400`** (strict mode rejects primitives) |
| `POST` body larger than `limit` | — | **`413`**, `type: 'entity.too.large'` |
| `POST` `text/plain` body (no parser matches) | `undefined` | `200` — *your handler must cope* |
| `POST` with **no** `Content-Type` from a naive client | `undefined` | `200` — the parser skips it |
| `{"__proto__":{"admin":true}}` | `{ ['__proto__']: { admin: true } }` as an **own key** | `200` — see §8 |

```bash
# The three failure modes, seen from the client:
curl -s -i -X POST localhost:3000/json -H 'Content-Type: application/json' -d '{bad' | head -1
# HTTP/1.1 400 Bad Request

curl -s -X POST localhost:3000/json -H 'Content-Type: application/json' -d 'null'
# 400 {"error":…}   ← strict mode

curl -s -i -X POST localhost:3000/json -H 'Content-Type: application/json' \
  -d "$(node -e 'process.stdout.write(JSON.stringify({a:"x".repeat(200000)}))')" | head -1
# HTTP/1.1 413 Payload Too Large

curl -s -X POST localhost:3000/json -H 'Content-Type: text/plain' -d 'hello'
# {"body":null,"receivedType":"text/plain"}   ← no parser matched
```

**Express 5's automatic error handler for these failures** produces an error object with useful fields:

```json
{
  "name": "SyntaxError",
  "status": 400,
  "type": "entity.parse.failed",
  "message": "Expected property name or '}' in JSON at position 1 (line 1 column 2)"
}
```

That is why the error middleware in [08 — Error Handling](08-error-handling.md) must read
`error.status`/`error.statusCode` — otherwise a malformed JSON body becomes a 500.

### Body parser options worth knowing

| Option | Default | Why you would change it |
| --- | --- | --- |
| `limit` | `'100kb'` | Raise for uploads, lower for untrusted endpoints |
| `strict` | `true` | `false` accepts `"string"`/`123`/`null` at the top level — usually a mistake |
| `type` | `application/json` | Add `application/*+json` for `application/vnd.api+json`, `application/merge-patch+json` |
| `inflate` | `true` | Set `false` to refuse compressed request bodies (a small DoS mitigation) |
| `verify` | — | Capture the raw bytes for signature verification (webhooks) |

```js
// File: webhook-verify.js
import express from 'express';
import { createHmac, timingSafeEqual } from 'node:crypto';

const app = express();

/** Webhook signatures are computed over the RAW body, so keep the bytes. */
app.post(
  '/webhooks/payments',
  express.json({
    limit: '1mb',
    verify: (req, res, buf) => {
      req.rawBody = buf;                     // a Buffer of the exact bytes received
    },
  }),
  (req, res) => {
    const signature = req.get('x-signature') ?? '';
    const expected = createHmac('sha256', process.env.WEBHOOK_SECRET ?? '')
      .update(req.rawBody)
      .digest('hex');

    const a = Buffer.from(signature, 'utf8');
    const b = Buffer.from(expected, 'utf8');

    // Constant-time comparison — length must match before timingSafeEqual is called.
    if (a.length !== b.length || !timingSafeEqual(a, b)) {
      return res.status(401).json({ error: { code: 'INVALID_SIGNATURE' } });
    }

    // Safe: nothing in this body was trusted before the signature was verified.
    return res.status(202).json({ received: true });
  },
);

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

### Which parser for which content type

| `Content-Type` | Parser | Result |
| --- | --- | --- |
| `application/json` | `express.json()` | Object/array |
| `application/x-www-form-urlencoded` | `express.urlencoded()` | Object (values are strings) |
| `multipart/form-data` | **not built in** — use `multer` (ch. 17) | `req.file` / `req.files` |
| `text/plain`, `application/xml`, `text/csv` | `express.text()` / `express.raw()` | String / `Buffer` |
| Anything else | no parser matches | `req.body` stays `undefined` |

```js
// File: text-and-raw.js
import express from 'express';

const app = express();

// Plain text: useful for simple webhooks and text-based protocols.
app.post('/text', express.text({ type: 'text/plain', limit: '10kb' }), (req, res) => {
  res.json({ body: req.body, length: req.body?.length ?? 0 });     // body is a STRING
});

// Raw bytes: signature verification, binary protocols, protobuf, images.
app.post('/raw', express.raw({ type: 'application/octet-stream', limit: '5mb' }), (req, res) => {
  res.json({
    isBuffer: Buffer.isBuffer(req.body),
    bytes: req.body?.length ?? 0,
    firstBytes: req.body?.subarray(0, 4).toString('hex'),
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

---

## 5. Where validation belongs

```text
client ──▶ route ──▶ validate (shape, types, ranges) ──▶ controller ──▶ service (business rules) ──▶ repository
                     ▲                                    ▲
                     │                                    └── "is this allowed?" — needs data, not just shapes
                     └── "is this well-formed?" — needs nothing but the request
```

| Layer | Validates | Example |
| --- | --- | --- |
| Route/middleware | Shape and format | `id` is a UUID; `title` is a non-empty string ≤ 200 chars; `limit` ≤ 100 |
| Service | Business rules | "A note cannot be pinned in an archived workspace"; "email must be unique" |
| Repository | Nothing — it executes queries | — |
| Database | Constraints of last resort | `CHECK`, `UNIQUE`, `NOT NULL` — the final safety net |

The practical rule: **the route layer rejects malformed input (422); the service layer rejects
disallowed input (409/403/404)**. Chapter 12 shows the same split implemented with Zod instead of
hand-written parsers.

---

## 6. A complete worked example

```js
// File: src/app.js (excerpt) — the middleware order that makes all of this work
import express from 'express';

export function createApp({ config }) {
  const app = express();

  // 1. Body parsers BEFORE routes.
  app.use(express.json({ limit: config.bodyLimit, strict: true, type: ['application/json', 'application/*+json'] }));
  app.use(express.urlencoded({ extended: false, limit: config.bodyLimit }));

  // 2. Query parser choice is an app-level decision.
  app.set('query parser', 'simple');

  // 3. Routes.
  app.use('/api/v1', createApiRouter({ /* … */ }));

  return app;
}
```

```bash
# Happy path
curl -s -X POST localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' \
  -d '{"title":"Query strings","content":"chapter 06","tags":["express","http"]}'

# Filtering + pagination + shaping
curl -s 'localhost:3000/api/v1/notes?tag=express&sort=-createdAt&limit=10&fields=id,title,tags'

# Bad input — every failure is a documented 4xx, never a 500
curl -s 'localhost:3000/api/v1/notes?limit=abc'                     # 422
curl -s 'localhost:3000/api/v1/notes?sort=../../etc/passwd'         # 422 (not allowed to sort by that)
curl -s -X POST localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' -d '{"title":""}'             # 422 (field-level details)
curl -s -X POST localhost:3000/api/v1/notes \
  -H 'Content-Type: text/plain' -d 'title=x'                        # 415 from a content-type guard
```

---

## 7. Choosing the right source

| Situation | Params | Query | Body |
| --- | --- | --- | --- |
| Which resource | ✅ | ❌ | ❌ |
| Hierarchy (`/users/7/notes`) | ✅ | ❌ | ❌ |
| Filtering | ❌ | ✅ | ⚠️ only for complex, repeatable filters (`POST /notes/search`) |
| Sorting, pagination | ❌ | ✅ | ❌ |
| Search term | ❌ | ✅ (`?q=`) | ❌ |
| Content of the resource | ❌ | ❌ | ✅ |
| Credentials | ❌ | ❌ | ✅ (over HTTPS, in the body) |
| A filter with 30 possible parameters | ❌ | ⚠️ unwieldy — consider a search body | ✅ |
| CSV export options | ❌ | ✅ | ❌ |
| A file | ❌ | ❌ | ✅ (`multipart/form-data`) |

```js
// File: search-body.js
import express from 'express';

const app = express();
app.use(express.json());

/**
 * When filters are complex and repeatable, a POST body with a documented schema is
 * clearer than 20 query parameters — and the payload limit protects the server.
 * Note: POST means "not cacheable by default", so use GET+query whenever it fits.
 */
app.post('/api/v1/notes/search', (req, res) => {
  const { filters = [], sort = [{ field: 'createdAt', direction: 'desc' }], limit = 20 } = req.body ?? {};

  if (!Array.isArray(filters) || filters.length > 10) {
    return res.status(422).json({
      error: { code: 'VALIDATION_ERROR', details: [{ field: 'filters', message: 'must be an array of at most 10 filters' }] },
    });
  }

  return res.json({ data: [], meta: { applied: { filters, sort, limit } } });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
curl -s -X POST localhost:3000/api/v1/notes/search -H 'Content-Type: application/json' -d '{
  "filters": [
    {"field":"tags","operator":"contains","value":"node"},
    {"field":"createdAt","operator":"gte","value":"2026-01-01"}
  ],
  "sort": [{"field":"title","direction":"asc"}],
  "limit": 10
}'
```

---

## 8. Security: the input-handling attack surface

Everything in this section has the same fix: **validate the exact shape you expect and reject
everything else.**

### 8.1 NoSQL operator injection

```js
// ❌ VULNERABLE — the body is passed straight into a Mongo query.
app.post('/login', async (req, res) => {
  // Attacker sends: {"email": "victim@example.com", "password": {"$ne": null}}
  // The query becomes { email, password: { $ne: null } } → the password check always passes.
  const user = await users.findOne({ email: req.body.email, password: req.body.password });
  res.json({ user });
});

// ✅ SAFE — validate the type first, then compare properly.
```

```js
// File: safe-login.js
import express from 'express';
import { z } from 'zod';
import { compare } from 'bcryptjs';

const app = express();
app.use(express.json());

const LoginSchema = z.object({
  email: z.string().email().max(254),
  password: z.string().min(8).max(200),          // ← a string, not an object
}).strict();

app.post('/login', async (req, res) => {
  const parsed = LoginSchema.safeParse(req.body ?? {});
  if (!parsed.success) {
    // Same message for unknown email and bad password: do not leak which failed.
    return res.status(401).json({ error: { code: 'INVALID_CREDENTIALS' } });
  }

  const user = await users.findOne({ email: parsed.data.email });        // only the validated string
  const ok = user ? await compare(parsed.data.password, user.passwordHash) : false;

  if (!ok) return res.status(401).json({ error: { code: 'INVALID_CREDENTIALS' } });
  return res.json({ data: { id: user.id } });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

The same rule protects SQL: **parameterised queries take values, never code.**
`db.query('SELECT * FROM users WHERE email = $1', [email])` is safe;
`db.query(\`SELECT * FROM users WHERE email = '${email}'\`)` is not.

### 8.2 Prototype pollution

```json
{ "__proto__": { "isAdmin": true } }
```

- `JSON.parse` creates an **own** key literally named `__proto__` — it does not modify the prototype
  by itself, so a simple `req.body.title` read is safe.
- The danger is *merging* untrusted objects into other objects:

```js
// ❌ VULNERABLE to prototype pollution and mass assignment in one line.
const user = { ...defaults, ...req.body };            // attacker-supplied keys win
Object.assign(existingUser, req.body);                // attacker can set role, isAdmin, id

// A deep-merge or an update that forwards the body to the model is worse:
await User.findByIdAndUpdate(id, req.body);           // now { __proto__: … } / { role: 'admin' } is applied
```

```js
// File: safe-update.js
/** ✅ SAFE: pick fields explicitly. The schema is the allowlist. */
export function pickProfileFields(body) {
  return {
    name: typeof body.name === 'string' ? body.name.trim() : undefined,
    bio: typeof body.bio === 'string' ? body.bio.trim() : undefined,
  };
}

// Or let a strict schema reject unknown keys outright (Zod `.strict()`), so a
// `role` or `isAdmin` field is a 422, not a privilege escalation.
```

### 8.3 Mass assignment

```text
PATCH /api/v1/users/me
{"name":"Ankit","role":"admin"}      ← the client decided its own role
```

Fix: never spread a request body into a model. Validate with a schema that *only* contains the fields
the endpoint allows, and write the update explicitly.

### 8.4 Other input traps

| Attack | Input | Defence |
| --- | --- | --- |
| Parameter pollution | `?id=1&id=2` → an array where a string is expected | Validate the type; treat arrays as an error for scalar params |
| ReDoS | `?q=(a+)+$` used as a regular expression | Never build a regex from user input; escape it, or cap its length |
| Path traversal | `:file` = `../../etc/passwd` | Allowlist + `path.basename` + containment checks (ch. 07 of the Node section) |
| Body bomb | 500 MB JSON | `limit` on every parser |
| Slowloris-style streams | A body that never ends | `requestTimeout`/`headersTimeout` on the server (ch. 20) |
| Deep nesting DoS | `{"a":{"a":{"a":…}}}` with the extended query parser | Keep `'simple'`; cap `depth` if using `qs` |
| Header injection | `X-Filename: a\r\nSet-Cookie: …` | Never reflect input into headers unsanitised |
| Type juggling | `?limit[]=1` → an array to `Number()` | Validate types, not just values |

---

## 9. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| No body parser registered | `req.body` is `undefined` → `TypeError` | `app.use(express.json())` before routes |
| Parser registered **after** routes | Same, for most requests | Order is registration order |
| Assuming `req.body` always exists | `Cannot read properties of undefined` | `req.body ?? {}` **and** a schema |
| Arithmetic on strings | `'2' + 1 === '21'`, `'abc' * 2 === NaN` | Coerce then validate |
| `if (req.query.pinned)` | `'false'` is truthy → every filter matches | Parse booleans explicitly |
| `Number(req.query.limit)` without bounds | `limit=100000000` scans the whole collection | Cap with a max |
| Sorting by an unvalidated field name | Injection into `ORDER BY` / `sort()`; internal fields leak | Allowlist sortable fields |
| Passing `req.params.id` straight to the DB | Cast errors (`500`) for bad ids; operator injection for objects | Validate the format first |
| Trusting `req.query` shape | `?tag[]=x` becomes a nested object with the extended parser | Keep `'simple'`, validate the shape |
| Spreading the body into the model | Mass assignment / privilege escalation | Pick fields explicitly |
| No `limit` on the parser | Memory exhaustion from big bodies | `express.json({ limit: '100kb' })` |
| Returning the raw validation error from the parser | Leaks internal details; the client cannot map fields | Normalise into `{ field, message }` details |
| `GET` with a body | Silently ignored by proxies and many clients | Use query parameters |
| Sending `Content-Type: application/json` on a body-less request | Some parsers produce `{}` and confuse validation | Omit the header, or accept both |
| Not handling `415` | Clients get confusing 400s | Guard the content type explicitly (ch. 08) |

---

## Exercise 6.1 — Implement list filtering properly

Add these capabilities to `GET /api/v1/notes`:

| Parameter | Meaning | Rules |
| --- | --- | --- |
| `tag` | Filter by tag (repeatable = OR) | Lowercase, at most 10 values |
| `q` | Search in title and content | Trimmed, max 200 characters |
| `pinned` | Filter by pinned state | `true`/`false` only |
| `sort` | Comma-separated, `-` for descending | Only `createdAt`, `updatedAt`, `title`; max 3 |
| `fields` | Sparse fieldset | Subset of `id,title,content,tags,pinned,createdAt,updatedAt` |
| `limit` / `page` | Pagination | `1 ≤ limit ≤ 100` (default 20), `page ≥ 1` |
| anything else | — | `422` |

Return `{ data, meta: { page, limit, total, totalPages, hasNext, sort, appliedFilters } }`, and write
tests that prove each rule.

<details>
<summary>Solution</summary>

Reuse `parseListQuery` from §3 (it already implements the rules) and add the repository, service and
controller wiring plus tests.

```js
// File: src/repositories/noteRepository.js (in-memory version for tests and demos)
export function createInMemoryRepository(seed = []) {
  let notes = seed.map((note) => ({ ...note }));
  let sequence = notes.length;

  const matches = (note, { tags, q, pinned }) => {
    if (tags?.length && !tags.some((tag) => note.tags.includes(tag))) return false;
    if (typeof pinned === 'boolean' && note.pinned !== pinned) return false;
    if (q) {
      const needle = q.toLowerCase();
      if (!note.title.toLowerCase().includes(needle) && !note.content.toLowerCase().includes(needle)) return false;
    }
    return true;
  };

  const compare = (a, b, { field, direction }) => {
    const left = a[field] ?? '';
    const right = b[field] ?? '';
    const result = String(left).localeCompare(String(right));
    return direction === 'desc' ? -result : result;
  };

  return {
    async list({ tags, q, pinned, sort, offset, limit, fields }) {
      const filtered = notes.filter((note) => matches(note, { tags, q, pinned }));
      const sorted = [...filtered].sort((a, b) => {
        for (const key of sort) {
          const result = compare(a, b, key);
          if (result !== 0) return result;
        }
        return 0;
      });

      const pageItems = sorted.slice(offset, offset + limit);
      const projected = fields
        ? pageItems.map((note) => Object.fromEntries(fields.map((field) => [field, note[field]])))
        : pageItems;

      return { items: projected, total: filtered.length };
    },

    async create(note) {
      sequence += 1;
      const created = { ...note, id: note.id ?? `note-${sequence}` };
      notes.push(created);
      return created;
    },

    async findById(id) {
      return notes.find((note) => note.id === id) ?? null;
    },

    async update(id, patch) {
      const index = notes.findIndex((note) => note.id === id);
      if (index === -1) return null;
      notes[index] = { ...notes[index], ...patch, id };
      return notes[index];
    },

    async remove(id) {
      const before = notes.length;
      notes = notes.filter((note) => note.id !== id);
      return notes.length < before;
    },
  };
}
```

```js
// File: src/services/noteService.js (list part)
export function createNoteService({ repository }) {
  return {
    async list(query) {
      const { items, total } = await repository.list(query);
      return {
        items,
        total,
        meta: {
          page: query.page,
          limit: query.limit,
          totalPages: Math.ceil(total / query.limit),
          hasNext: query.page * query.limit < total,
          sort: query.sort,
          appliedFilters: {
            tags: query.tags ?? [],
            q: query.q ?? null,
            pinned: query.pinned ?? null,
            fields: query.fields ?? null,
          },
        },
      };
    },
  };
}
```

```js
// File: src/controllers/noteController.js (list part)
import { parseListQuery } from '../validators/listQuery.js';

export function createNoteController({ noteService }) {
  return {
    list: async (req, res, next) => {
      try {
        const { value: query, errors } = parseListQuery(req.query);
        if (errors.length > 0) {
          return res.status(422).json({ error: { code: 'VALIDATION_ERROR', details: errors } });
        }

        const { items, meta } = await noteService.list(query);
        return res.json({ data: items, meta });
      } catch (error) {
        return next(error);
      }
    },
  };
}
```

```js
// File: tests/list-query.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { createInMemoryRepository } from '../src/repositories/noteRepository.js';
import { createNoteService } from '../src/services/noteService.js';
import { createNoteController } from '../src/controllers/noteController.js';
import { createNoteRouter } from '../src/routes/noteRoutes.js';

let server;
let baseUrl;

before(async () => {
  const seed = [
    { id: '1', title: 'Alpha', content: 'about node', tags: ['node', 'backend'], pinned: false, createdAt: '2026-01-01T00:00:00.000Z', updatedAt: '2026-01-01T00:00:00.000Z' },
    { id: '2', title: 'Beta', content: 'about express', tags: ['express'], pinned: true, createdAt: '2026-02-01T00:00:00.000Z', updatedAt: '2026-02-01T00:00:00.000Z' },
    { id: '3', title: 'Gamma', content: 'about node and express', tags: ['node', 'express'], pinned: true, createdAt: '2026-03-01T00:00:00.000Z', updatedAt: '2026-03-01T00:00:00.000Z' },
  ];

  const repository = createInMemoryRepository(seed);
  const noteService = createNoteService({ repository });
  const controller = createNoteController({ noteService });

  const app = express();
  app.use(express.json());
  app.use('/api/v1/notes', createNoteRouter({ controller }));
  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: error.message } });
  });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1/notes`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const get = async (qs) => (await fetch(`${baseUrl}?${qs}`)).json();

test('filters by a single tag', async () => {
  const body = await get('tag=express');
  assert.equal(body.meta.total, 2);                       // Beta and Gamma
  assert.deepEqual(body.data.map((n) => n.id).sort(), ['2', '3']);
});

test('repeated tags behave as OR', async () => {
  const body = await get('tag=backend&tag=express');
  assert.equal(body.meta.total, 3);
});

test('searches title and content', async () => {
  const body = await get('q=node');
  assert.equal(body.meta.total, 2);                       // Alpha and Gamma
});

test('filters by pinned', async () => {
  assert.equal((await get('pinned=true')).meta.total, 2);
  assert.equal((await get('pinned=false')).meta.total, 1);
});

test('sorts descending with a leading dash', async () => {
  const body = await get('sort=-createdAt');
  assert.deepEqual(body.data.map((n) => n.title), ['Gamma', 'Beta', 'Alpha']);
  assert.equal(body.meta.sort[0].direction, 'desc');
});

test('sorts by multiple keys', async () => {
  const body = await get('sort=pinned,-title');
  assert.deepEqual(body.data.map((n) => n.title), ['Alpha', 'Gamma', 'Beta']);
});

test('paginates and reports meta', async () => {
  const body = await get('limit=2&page=2&sort=title');
  assert.equal(body.data.length, 1);                      // 3 items, page 2 of size 2
  assert.deepEqual(body.meta, {
    page: 2, limit: 2, total: 3, totalPages: 2, hasNext: false,
    sort: [{ field: 'title', direction: 'asc' }],
    appliedFilters: { tags: [], q: null, pinned: null, fields: null },
  });
});

test('projects a sparse fieldset', async () => {
  const body = await get('fields=id,title');
  assert.deepEqual(Object.keys(body.data[0]).sort(), ['id', 'title']);
});

test('rejects invalid parameters with field-level details', async () => {
  assert.equal((await get('limit=1000')).error.code, 'VALIDATION_ERROR');
  assert.equal((await get('limit=abc')).error.details[0].field, 'limit');
  assert.equal((await get('sort=password')).error.details[0].field, 'sort');
  assert.equal((await get('pinned=maybe')).error.details[0].field, 'pinned');
  assert.equal((await get('fields=secret')).error.details[0].field, 'fields');
  assert.equal((await get('limitt=5')).error.details[0].field, 'limitt');
});
```

```bash
node --test tests/list-query.test.js
```

```text
✔ filters by a single tag
✔ repeated tags behave as OR
✔ searches title and content
✔ filters by pinned
✔ sorts descending with a leading dash
✔ sorts by multiple keys
✔ paginates and reports meta
✔ projects a sparse fieldset
✔ rejects invalid parameters with field-level details
pass 9
fail 0
```

**Design notes**

| Decision | Reason |
| --- | --- |
| Reject unknown parameters instead of ignoring them | A typo'd filter that silently returns everything is a production incident |
| Allowed sort fields are a hard-coded set | `sort=passwordHash` must be impossible, not merely unlikely |
| `appliedFilters` echoed in `meta` | Clients (and support engineers) can confirm what the server understood |
| Sparse fieldsets applied in the repository | Never send columns you did not query — this is a data-exposure control, not just bandwidth |
| Array-safe parsing (`asArray`) | `?tag=a&tag=b` and `?tag=a` must not behave differently |

</details>

---

## Exercise 6.2 — Audit an endpoint

```js
// File: src/routes/broken.js
import express from 'express';
const app = express();

app.post('/api/v1/users', (req, res) => {
  const { email, password, role, profile } = req.body;

  if (!email.includes('@')) {
    return res.status(400).send('bad email');
  }

  const user = {
    email,
    password,
    role: role || 'user',
    profile: { ...profile, theme: profile.theme || 'light' },
  };

  db.insert('users', user);
  res.status(200).send(JSON.stringify({ user }));
});

app.get('/api/v1/users', (req, res) => {
  const users = db.find('users', { role: req.query.role, limit: Number(req.query.limit) });
  res.send(users);
});

app.listen(3000);
```

Find every input-handling problem.

<details>
<summary>Solution</summary>

| # | Problem | Risk |
| --- | --- | --- |
| 1 | No `express.json()` | `req.body` is `undefined` → destructuring throws → 500 on every request |
| 2 | No schema validation | Any shape is accepted: `email` can be an object, `profile` can be a string |
| 3 | `role` comes from the client | **Privilege escalation** — anyone can create an admin |
| 4 | `profile.theme` read without checking `profile` | `Cannot read properties of undefined` when `profile` is omitted |
| 5 | `{ ...profile }` spreads attacker-controlled keys | Prototype pollution / unexpected fields persisted |
| 6 | Password stored as-is | Massive legal and security failure — hash it (04-authentication/02-password-hashing.md *(not available in this published source revision)*) |
| 7 | `email.includes('@')` as validation | `"@@"`, `"a@b"`, `"a@b\nX-Injected: 1"` all pass; no length limit; no normalisation |
| 8 | `400` for a validation failure | `422` is the correct status for well-formed-but-invalid input |
| 9 | Error response is a bare string | Contract mismatch — clients expect `{ error: { code, message, details } }` |
| 10 | `res.status(200)` for a creation | Should be `201` + `Location` |
| 11 | The returned `user` includes the password | Sensitive-data disclosure; use an explicit DTO |
| 12 | `res.send(JSON.stringify(...))` | `Content-Type` becomes `text/html` → clients parse it as HTML |
| 13 | Casting `Number(req.query.limit)` blindly | `NaN` when absent or invalid; no cap → full-table scan |
| 14 | `req.query.role` passed straight into the query | A query filter built from untrusted input (operator injection, information disclosure) |
| 15 | No pagination defaults or maximum | One request can return every user |
| 16 | No error handling | A thrown error returns Express's default HTML page with a stack in development |
| 17 | No `limit` on the body parser (none registered at all) | Memory exhaustion |
| 18 | No `PORT` from the environment | Hard-coded `3000` |
| 19 | No authentication or authorisation | Anyone can create and list users |

```js
// File: src/routes/fixed.js
import express from 'express';
import { z } from 'zod';
import { hash } from 'bcryptjs';
import { randomUUID } from 'node:crypto';

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '100kb', strict: true }));

// ---- schemas: the allowlist ------------------------------------------------
const CreateUserSchema = z.object({
  email: z.string().trim().toLowerCase().email().max(254),
  password: z.string().min(8).max(200),
  profile: z.object({
    name: z.string().trim().min(1).max(100),
    theme: z.enum(['light', 'dark']).default('light'),
  }).strict().default({ name: 'Anonymous', theme: 'light' }),
  // `role` is deliberately ABSENT: clients cannot choose their own role.
}).strict();

const ListUsersSchema = z.object({
  role: z.enum(['user', 'admin']).optional(),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  page: z.coerce.number().int().min(1).default(1),
}).strict();

const toUserDto = (user) => ({
  id: user.id,
  email: user.email,
  role: user.role,
  profile: user.profile,
  createdAt: user.createdAt,
});   // ← no passwordHash, ever

// ---- routes ---------------------------------------------------------------
app.post('/api/v1/users', async (req, res, next) => {
  try {
    const parsed = CreateUserSchema.safeParse(req.body ?? {});
    if (!parsed.success) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          details: parsed.error.issues.map((issue) => ({
            field: issue.path.join('.') || 'body',
            message: issue.message,
          })),
        },
      });
    }

    const { email, password, profile } = parsed.data;

    if (await db.findUserByEmail(email)) {
      return res.status(409).json({ error: { code: 'EMAIL_TAKEN', message: 'That email is already registered' } });
    }

    const user = {
      id: randomUUID(),
      email,
      passwordHash: await hash(password, 12),
      role: 'user',                       // server-decided, never client-supplied
      profile,
      createdAt: new Date().toISOString(),
    };

    await db.insertUser(user);
    return res.status(201).location(`/api/v1/users/${user.id}`).json({ data: toUserDto(user) });
  } catch (error) {
    return next(error);
  }
});

app.get('/api/v1/users', async (req, res, next) => {
  try {
    const parsed = ListUsersSchema.safeParse(req.query);
    if (!parsed.success) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          details: parsed.error.issues.map((issue) => ({ field: issue.path.join('.') || 'query', message: issue.message })),
        },
      });
    }

    const { role, limit, page } = parsed.data;
    const { items, total } = await db.listUsers({ role, limit, offset: (page - 1) * limit });

    return res.json({
      data: items.map(toUserDto),
      meta: { page, limit, total, hasNext: page * limit < total },
    });
  } catch (error) {
    return next(error);
  }
});

app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

app.use((error, req, res, next) => {
  if (res.headersSent) return next(error);
  const statusCode = error.statusCode ?? error.status ?? 500;
  return res.status(statusCode).json({
    error: {
      code: error.code ?? 'INTERNAL_ERROR',
      message: statusCode >= 500 && process.env.NODE_ENV === 'production' ? 'Something went wrong' : error.message,
    },
  });
});

const port = Number(process.env.PORT ?? 3000);
app.listen(port, '0.0.0.0', () => console.log(`listening on http://localhost:${port}`));
```

**Note the remaining gaps** — this exercise is about input handling, so authentication and
authorisation for `GET /users` are deliberately left for
[13 — Authentication](13-authentication.md) and [18 — Security](18-security.md), and the database layer
is a stand-in.

```bash
# Validation, allowlisting and privilege protection, demonstrated:
curl -s -X POST localhost:3000/api/v1/users -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"supersecret","role":"admin"}'
# 422 — "role" is not a supported field, so privilege escalation is impossible

curl -s -X POST localhost:3000/api/v1/users -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"short"}'
# 422 — password too short

curl -s -X POST localhost:3000/api/v1/users -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"longenough","profile":{"name":"Ankit"}}'
# 201 with data (and no password field in the response)

curl -s 'localhost:3000/api/v1/users?limit=100000'
# 422 — limit capped

curl -s 'localhost:3000/api/v1/users?role=superadmin'
# 422 — role is an enum
```

**The audit in one sentence:** the original endpoint treated three untrusted inputs as trusted *and
persisted them*, which is how one `PATCH` request becomes a privilege escalation.

</details>

---

## What's next

You can read input correctly now. Next: the mechanism that ties every chapter together — middleware,
the onion model, `next()`, and the order-dependent bugs it creates.

→ [07 — Middleware](07-middleware.md)
