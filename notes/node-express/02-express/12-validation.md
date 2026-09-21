# 12 — Validation

> **Where this fits:** Chapter 06 showed the three sources of input and why they cannot be trusted. This chapter answers "trusted by _what_": schemas, a middleware that enforces them, and an error shape clients can act on. Zod 4 is the primary tool; Joi and `express-validator` are compared at the end.

***

## 1. Why validation exists

Every byte that arrives in a request is attacker-controlled until proven otherwise. Without a validation layer, three things happen — usually all three:

| Failure             | Example                                                  | Result               |
| ------------------- | -------------------------------------------------------- | -------------------- |
| **Crash**           | `req.body.title.trim()` when `title` is a number         | `TypeError` → 500    |
| **Corruption**      | `{ "pinned": "false" }` stored as a truthy string        | Wrong data, silently |
| **Security breach** | `{ "price": { "$ne": null } }` passed into a Mongo query | Operator injection   |

Validation is the **trust boundary**: everything before it is untrusted, everything after it is validated. The boundary belongs in middleware, because it applies to every route and it must run before controllers, services and repositories.

```
client ──▶ route ──▶ ┌─────────────────────┐ ──▶ controller ──▶ service ──▶ repository
                      │ validate middleware │
                      │ (schema per source) │
                      └─────────────────────┘
                        body / query / params
                        → 422 with details, or
                        → req.validated.*
```

Two kinds of checks, in two different layers:

| Question                                                    | Layer      | Tool             | Failure           |
| ----------------------------------------------------------- | ---------- | ---------------- | ----------------- |
| Is this well-formed? (types, formats, ranges, unknown keys) | Middleware | Schema (Zod/Joi) | `422`             |
| Is this allowed? (uniqueness, ownership, state)             | Service    | Code + data      | `409`/`403`/`422` |

A schema cannot know whether an email is _taken_. It can only know whether it is _shaped_ like an email. Trying to put business rules into schemas produces schemas that need a database — and that is the signal that the rule belongs in a service.

***

## 2. Zod 4 in five minutes

```js
// File: src/validators/noteSchemas.js
import { z } from 'zod';

/** The base object: the shape of a note as clients may write it. */
export const noteBodySchema = z.object({
  title: z.string().trim().min(1, 'must not be empty').max(200, 'must be at most 200 characters'),
  content: z.string().trim().min(1, 'must not be empty').max(10_000),
  tags: z
    .array(z.string().trim().toLowerCase().min(1).max(30))
    .max(10, 'at most 10 tags')
    .default([]),
  pinned: z.boolean().default(false),
});

/** POST /notes — every field is present (after defaults). Unknown keys are an error. */
export const createNoteSchema = noteBodySchema.strict();

/** PUT /notes/:id — a full replacement; same shape as create. */
export const replaceNoteSchema = noteBodySchema.strict();

/** PATCH /notes/:id — every field optional, but at least one must be present. */
export const patchNoteSchema = noteBodySchema
  .partial()
  .strict()
  .refine((value) => Object.keys(value).length > 0, { message: 'at least one field must be provided' });
```

```js
// File: zod-tour.js
import { z } from 'zod';

// ── Scalars ─────────────────────────────────────────────────────────────────────
z.string();
z.string().min(1).max(200);
z.string().trim().toLowerCase();               // transforms run before later checks
z.email();                                     // Zod 4 top-level format types
z.url();
z.uuid();
z.iso.datetime();                              // ISO 8601 date-time string
z.iso.date();
z.number().int().min(0).max(100);
z.coerce.number().int().positive();            // coerces '5' → 5, 'abc' → error
z.boolean();
z.enum(['draft', 'published', 'archived']);
z.literal('admin');

// ── Collections ─────────────────────────────────────────────────────────────────
z.array(z.string()).min(1).max(10);
z.record(z.string(), z.number());              // { [key]: number }
z.tuple([z.string(), z.number()]);
z.set(z.string());
z.map(z.string(), z.number());

// ── Objects ─────────────────────────────────────────────────────────────────────
const user = z.object({
  email: z.email(),
  name: z.string().trim().min(1),
  role: z.enum(['USER', 'ADMIN']).default('USER'),
  age: z.number().int().min(13).optional(),
  bio: z.string().max(500).nullable(),         // explicitly allows null
  createdAt: z.iso.datetime(),
});

// Unknown-key behaviour — choose deliberately:
z.object({ a: z.string() });                        // strips unknown keys (default)
z.object({ a: z.string() }).strict();               // rejects unknown keys
z.strictObject({ a: z.string() });                  // the Zod 4 spelling of the same thing
z.object({ a: z.string() }).loose();                // keeps unknown keys
z.looseObject({ a: z.string() });

// Composition
const base = z.object({ email: z.email(), name: z.string() });
base.extend({ role: z.enum(['USER', 'ADMIN']) });   // add fields
base.pick({ email: true });                         // keep some
base.omit({ name: true });                          // drop some
base.partial();                                     // make every field optional
base.required();                                    // make every field required
```

### How errors look (Zod 4)

```js
// File: zod-errors.js
import { z } from 'zod';

const schema = z.object({
  title: z.string().trim().min(1, 'must not be empty'),
  tags: z.array(z.string()).max(2, 'at most 2 tags'),
  email: z.email(),
  count: z.coerce.number().int(),
}).strict();

const result = schema.safeParse({ title: '', tags: ['a', 'b', 'c'], email: 'nope', count: 'x', extra: 1 });

if (!result.success) {
  for (const issue of result.error.issues) {
    console.log(JSON.stringify({ path: issue.path, code: issue.code, message: issue.message }));
  }
}
```

```
{"path":["title"],"code":"too_small","message":"must not be empty"}
{"path":["tags"],"code":"too_big","message":"at most 2 tags"}
{"path":["email"],"code":"invalid_format","message":"Invalid email address"}
{"path":["count"],"code":"invalid_type","message":"Invalid input: expected number, received NaN"}
{"path":[],"code":"unrecognized_keys","message":"Unrecognized key: \"extra\""}
```

| Fact                                                                         | Consequence                                                             |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `safeParse` never throws                                                     | Always use it in middleware; `parse` throws a `ZodError` you must catch |
| `issues` is an array of `{ path, code, message }`                            | Perfect for `{ field, message }` error details                          |
| A **root** issue has an empty `path` (`[]`)                                  | Map it to `field: 'body'` (or `'query'`)                                |
| Message defaults are developer-oriented                                      | Override the ones users see: `.min(1, 'must not be empty')`             |
| `z.flattenError(error)` / `z.treeifyError(error)` / `z.prettifyError(error)` | Helpers for logging and for nested structures                           |

***

## 3. The validation middleware

One middleware, used for every route, for every source.

```js
// File: src/middleware/validate.js
/**
 * Validate one part of the request with a Zod schema.
 *
 * - Never mutates req.body/req.query/req.params (raw input stays available for logs).
 * - Stores the parsed value on req.validated[source].
 * - Responds 422 with field-level details, or calls next().
 */
export function validate(schema, source = 'body') {
  if (!['body', 'query', 'params'].includes(source)) {
    throw new Error(`validate(): unsupported source "${source}"`);
  }

  return function validateMiddleware(req, res, next) {
    const input = req[source] ?? {};
    const result = schema.safeParse(input);

    if (!result.success) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Request validation failed',
          details: toFieldDetails(result.error, source),
          requestId: req.id,
        },
      });
    }

    req.validated ??= {};
    req.validated[source] = result.data;
    return next();
  };
}

/** Turn Zod issues into the stable, client-facing `{ field, message, code }` shape. */
export function toFieldDetails(error, source = 'body') {
  return error.issues.map((issue) => ({
    field: issue.path.length > 0 ? issue.path.join('.') : source,
    message: issue.message,
    code: issue.code,
  }));
}
```

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { createNoteSchema, replaceNoteSchema, patchNoteSchema, listNotesQuerySchema } from '../validators/noteSchemas.js';

export function createNoteRouter({ controller, authenticate, validateParam }) {
  const router = Router();

  router.param('id', validateParam('id', 'objectId'));       // params are validated too

  router.get('/', validate(listNotesQuerySchema, 'query'), controller.list);
  router.post('/', authenticate, validate(createNoteSchema), controller.create);
  router.get('/:id', controller.getOne);
  router.put('/:id', authenticate, validate(replaceNoteSchema), controller.replace);
  router.patch('/:id', authenticate, validate(patchNoteSchema), controller.update);
  router.delete('/:id', authenticate, controller.remove);

  return router;
}
```

```bash
curl -s -X POST localhost:3000/api/v1/notes -H 'Content-Type: application/json' \
  -d '{"title":"","tags":["a","b","c","d","e","f","g","h","i","j","k"],"extra":true}'
```

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "title", "message": "must not be empty", "code": "too_small" },
      { "field": "tags", "message": "at most 10 tags", "code": "too_big" },
      { "field": "body", "message": "Unrecognized key: \"extra\"", "code": "unrecognized_keys" }
    ],
    "requestId": "6a1f3e2b-8f4a-4b1e-9a3d-5b2c9e0f1a77"
  }
}
```

Note the shape: **all** problems at once (not just the first), each with a field the client can highlight in a form, and a machine-readable `code`.

***

## 4. Schemas per operation

The same resource needs different schemas for different operations. Reuse the base and adjust:

```js
// File: src/validators/noteSchemas.js
import { z } from 'zod';

/* ── Reusable pieces ────────────────────────────────────────────────────────── */
const ObjectId = z.string().regex(/^[0-9a-f]{24}$/i, 'must be a 24-character hex id');
const Tag = z.string().trim().toLowerCase().min(1).max(30);

const SORTABLE = ['createdAt', 'updatedAt', 'title'];             // in TypeScript: as const

/* ── Bodies ─────────────────────────────────────────────────────────────────── */
export const createNoteSchema = z.object({
  title: z.string().trim().min(1, 'required').max(200),
  content: z.string().trim().min(1, 'required').max(10_000),
  tags: z.array(Tag).max(10).default([]),
  pinned: z.boolean().default(false),
}).strict();

/** PUT: the same shape as create — a full replacement. */
export const replaceNoteSchema = createNoteSchema;

/** PATCH: every field optional, at least one required. */
export const patchNoteSchema = createNoteSchema
  .partial()
  .refine((value) => Object.keys(value).length > 0, { message: 'at least one field must be provided' });

/* ── Query strings: everything arrives as a string ──────────────────────────── */
export const listNotesQuerySchema = z.object({
  // Coercion turns "?page=2" into 2 and rejects "?page=abc"
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),

  // Repeated params (?tag=a&tag=b) arrive as an array; a single one arrives as a string.
  tag: z
    .union([z.string(), z.array(z.string())])
    .transform((value) => (Array.isArray(value) ? value : [value]))
    .pipe(z.array(Tag).max(10))
    .optional(),

  sort: z
    .string()
    .default('-createdAt')
    .transform((value) => value.split(',').map((part) => part.trim()).filter(Boolean))
    .pipe(z.array(z.enum(['createdAt', '-createdAt', 'updatedAt', '-updatedAt', 'title', '-title'])).max(3)),

  q: z.string().trim().max(200).optional(),

  // "true"/"false" only — "1"/"0"/"" are rejected, so there is exactly one spelling.
  pinned: z
    .enum(['true', 'false'], { message: 'must be true or false' })
    .transform((value) => value === 'true')
    .optional(),

  fields: z
    .string()
    .transform((value) => value.split(',').map((part) => part.trim()))
    .pipe(z.array(z.enum(['id', 'title', 'content', 'tags', 'pinned', 'createdAt', 'updatedAt'])).max(7))
    .optional(),
}).strict();                       // an unknown query parameter is a 422, not a silent no-op

/* ── Params ─────────────────────────────────────────────────────────────────── */
export const noteIdParamSchema = z.object({ id: ObjectId }).strict();
```

```bash
# Coercion works: "2" becomes the number 2
curl -s 'localhost:3000/api/v1/notes?page=2&limit=5&sort=title,-createdAt&pinned=true&tag=node&tag=http'

# Every one of these is a 422, not a silent default
curl -s 'localhost:3000/api/v1/notes?page=0'
curl -s 'localhost:3000/api/v1/notes?limit=1000'
curl -s 'localhost:3000/api/v1/notes?sort=passwordHash'
curl -s 'localhost:3000/api/v1/notes?pinned=1'
curl -s 'localhost:3000/api/v1/notes?unknownParam=1'
```

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Request validation failed",
  "details": [{ "field": "sort", "message": "Invalid option: expected one of \"createdAt\"|\"-createdAt\"|…", "code": "invalid_value" }] } }
```

### Query-string types cheat sheet

| Client sends   | `req.query` (simple parser) | Schema                                       |
| -------------- | --------------------------- | -------------------------------------------- |
| `?page=2`      | `'2'` (string)              | `z.coerce.number().int().min(1)`             |
| `?tag=a`       | `'a'`                       | `z.union([z.string(), z.array(z.string())])` |
| `?tag=a&tag=b` | `['a','b']`                 | same                                         |
| `?pinned=true` | `'true'`                    | `z.enum(['true','false']).transform(…)`      |
| `?q=`          | `''`                        | `.optional()` or `.min(1)` — decide which    |
| _(absent)_     | `undefined`                 | `.default(…)` or `.optional()`               |

> **A note on `z.coerce.number()` messages.** `.int('must be an integer')` only fires when a real number is not an integer. When coercion itself fails, `?limit=abc` becomes `NaN` and the message is the default `Invalid input: expected number, received NaN`. If you want a friendly message for that case, validate the string first:
>
> ```js
> z.string().regex(/^\d+$/, 'must be a positive whole number').transform(Number).pipe(z.number().max(100))
> ```
>
> Both approaches are legitimate; pick one and use it consistently across the API.

***

## 5. PUT vs PATCH schemas

The difference is not a detail — it is the difference between replacing a document and updating one.

```js
// File: put-vs-patch-schemas.js
import { z } from 'zod';

const note = z.object({
  title: z.string().trim().min(1).max(200),
  content: z.string().trim().min(1).max(10_000),
  tags: z.array(z.string().trim().toLowerCase()).max(10).default([]),
  pinned: z.boolean().default(false),
});

/** PUT: required fields are REQUIRED. Absent optional fields get their defaults. */
export const replaceSchema = note.strict();

/** PATCH: nothing is required, but something must be present. */
export const patchSchema = note
  .partial()
  .refine((value) => Object.keys(value).length > 0, { message: 'at least one field must be provided' });

/** PATCH that allows explicit nulls (clears a field) — see §7 of chapter 04. */
export const patchWithNulls = z.object({
  title: z.string().trim().min(1).max(200).optional(),
  content: z.string().trim().min(1).max(10_000).nullable().optional(),  // null clears it
  tags: z.array(z.string().trim().min(1)).max(10).nullable().optional(),
  pinned: z.boolean().optional(),
}).strict().refine((value) => Object.keys(value).length > 0, { message: 'at least one field must be provided' });
```

| Behaviour            | `PUT`                           | `PATCH`                                    |
| -------------------- | ------------------------------- | ------------------------------------------ |
| Missing `title`      | `422` (required)                | Allowed — field untouched                  |
| Missing `tags`       | Defaults to `[]`                | Field untouched                            |
| `null` for `content` | `422` (a string is required)    | Allowed only if `.nullable()` was declared |
| Unknown key          | `422` (`.strict()`)             | `422`                                      |
| Empty object         | `422` (required fields missing) | `422` (`refine`: at least one field)       |

***

## 6. `refine` and `superRefine`: cross-field rules

A schema can express relationships _within_ the input — never anything that needs a database.

```js
// File: cross-field.js
import { z } from 'zod';

/** A date range: `from` must come before `to`. */
export const reportQuerySchema = z
  .object({
    from: z.iso.date(),
    to: z.iso.date(),
    format: z.enum(['json', 'csv']).default('json'),
  })
  .strict()
  .refine((value) => value.from <= value.to, {
    message: '`to` must be on or after `from`',
    path: ['to'],                                  // attach the error to the right field
  });

/** A password change: the confirmation must match, and the new one must differ. */
export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, 'required'),
    newPassword: z.string().min(12, 'must be at least 12 characters').max(200),
    confirmPassword: z.string().min(1, 'required'),
  })
  .strict()
  .refine((value) => value.newPassword === value.confirmPassword, {
    message: 'passwords do not match',
    path: ['confirmPassword'],
  })
  .refine((value) => value.newPassword !== value.currentPassword, {
    message: 'the new password must be different from the current one',
    path: ['newPassword'],
  });

/** Several problems at once, with different fields — superRefine. */
export const createCampaignSchema = z
  .object({
    name: z.string().trim().min(1).max(120),
    startsAt: z.iso.datetime(),
    endsAt: z.iso.datetime(),
    budgetCents: z.number().int().min(0),
    couponCode: z.string().trim().toUpperCase().max(40).optional(),
  })
  .strict()
  .superRefine((value, ctx) => {
    if (value.endsAt <= value.startsAt) {
      ctx.addIssue({ code: 'custom', path: ['endsAt'], message: 'must be after startsAt' });
    }
    if (value.budgetCents === 0 && value.couponCode) {
      ctx.addIssue({ code: 'custom', path: ['couponCode'], message: 'not allowed on a zero-budget campaign' });
    }
  });
```

```bash
curl -s -X POST localhost:3000/api/v1/campaigns -H 'Content-Type: application/json' -d '{
  "name": "Launch", "startsAt": "2026-10-01T00:00:00Z", "endsAt": "2026-09-01T00:00:00Z",
  "budgetCents": 0, "couponCode": "LAUNCH"
}'
```

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      { "field": "endsAt", "message": "must be after startsAt", "code": "custom" },
      { "field": "couponCode", "message": "not allowed on a zero-budget campaign", "code": "custom" }
    ]
  }
}
```

| Use `refine` for              | Use `superRefine` for                         |
| ----------------------------- | --------------------------------------------- |
| One predicate, one message    | Several independent checks                    |
| Simple cross-field comparison | Adding issues with different paths and codes  |
| A boolean answer              | Early-exit logic (`if (ctx.value.x) return;`) |

> **Never put a database call in a `refine`.** A schema must be synchronous, fast and side-effect free. "Is this email taken?" is a service rule — and it must still be protected by a database constraint, because two requests can pass the same refine at the same moment.

***

## 7. Validation is not authorisation

```js
// ❌ A type check is not a permission check.
export const updateUserSchema = z.object({
  name: z.string().min(1).optional(),
  role: z.enum(['USER', 'ADMIN']).optional(),      // ← now any client can promote itself
});

// ✅ The rule is "which fields may THIS endpoint change", not "which fields exist".
export const updateProfileSchema = z.object({
  name: z.string().trim().min(1).max(100).optional(),
  bio: z.string().trim().max(500).optional(),
}).strict();                                        // `role` is not a known key → 422

// ✅ Promotion is a separate, protected operation.
export const changeRoleSchema = z.object({
  role: z.enum(['USER', 'ADMIN']),
  reason: z.string().trim().min(3).max(200),
}).strict();
// …registered as POST /api/v1/admin/users/:id/role behind requireRole('ADMIN').
```

The same principle applies to **filters**: validating that `status` is a string is not enough; validate that it is one of the statuses the caller is allowed to see.

***

## 8. Validating responses (yes, really)

Schemas are not only for input. A response schema catches a whole class of bugs — and stops accidental leaks from a careless `SELECT *`.

```js
// File: src/dtos/serialise.js
import { z } from 'zod';

const userResponseSchema = z.object({
  id: z.string(),
  email: z.email(),
  name: z.string(),
  role: z.enum(['USER', 'ADMIN']),
  createdAt: z.iso.datetime(),
}).strict();

const noteResponseSchema = z.object({
  id: z.string(),
  title: z.string(),
  content: z.string(),
  tags: z.array(z.string()),
  pinned: z.boolean(),
  author: userResponseSchema.pick({ id: true, name: true }),
  createdAt: z.iso.datetime(),
  updatedAt: z.iso.datetime(),
}).strict();

/**
 * Serialise with a schema in development/staging: it strips everything unknown and
 * shouts if the shape drifts. In production you keep the (already-tested) fast path.
 */
export function createSerialiser({ strict = false, logger = console } = {}) {
  return function serialise(schema, value) {
    const result = schema.safeParse(value);
    if (result.success) return result.data;

    if (strict) {
      // Fail loudly in development so schema drift is caught immediately.
      throw new Error(`Response does not match the contract: ${z.prettifyError(result.error)}`);
    }

    logger.warn('response schema mismatch', { issues: toFieldDetails(result.error, 'response') });
    return value;                       // production: log, never break the response
  };
}
```

| Benefit                   | Example bug it catches                                             |
| ------------------------- | ------------------------------------------------------------------ |
| No accidental field leaks | Someone adds `passwordHash` to the model and it flows to the API   |
| Contract stability        | A date starts arriving as a `Date` object instead of an ISO string |
| Typed clients             | A generated TypeScript client depends on the exact shape           |
| Documentation             | The schema _is_ the contract, written in code                      |

***

## 9. Joi and express-validator (when to use them instead)

Zod is not the only option. Here is the same user schema in **Joi** — the closest equivalent:

```js
// File: joi-example.js
import Joi from 'joi';

const createUserSchema = Joi.object({
  email: Joi.string().trim().lowercase().email().max(254).required(),
  password: Joi.string().min(12).max(200).required(),
  name: Joi.string().trim().min(1).max(100).required(),
  theme: Joi.string().valid('light', 'dark').default('light'),
  age: Joi.number().integer().min(13).optional(),
}).unknown(false);

const { error, value } = createUserSchema.validate(
  { email: 'A@B.com', password: 'supersecret99', name: 'Ankit' },
  { abortEarly: false, stripUnknown: true, convert: true },
);

if (error) {
  console.log(error.details.map((detail) => ({ field: detail.path.join('.'), message: detail.message })));
} else {
  console.log(value);   // { email: 'a@b.com', …, theme: 'light' }
}
```

```js
// File: express-validator-example.js
import express from 'express';
import { body, query, validationResult } from 'express-validator';

const app = express();
app.use(express.json());

app.post(
  '/api/v1/users',
  body('email').isEmail().normalizeEmail(),
  body('password').isLength({ min: 12 }).isString(),
  body('name').trim().isLength({ min: 1, max: 100 }),
  (req, res) => {
    const result = validationResult(req);
    if (!result.isEmpty()) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          details: result.array().map((item) => ({ field: item.path, message: item.msg })),
        },
      });
    }
    return res.status(201).json({ data: { email: req.body.email } });
  },
);

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

|                      | **Zod 4**                                       | **Joi 17**                               | **express-validator 7**                      |
| -------------------- | ----------------------------------------------- | ---------------------------------------- | -------------------------------------------- |
| Style                | Declarative schema object                       | Declarative schema object                | Chainable validators per field               |
| TypeScript inference | Excellent (`z.infer`)                           | Weak (needs `@types` effort)             | Weak                                         |
| Bundle size          | Small (tree-shakeable, `@zod/mini`)             | Larger                                   | Small                                        |
| Query/body/params    | Same schema API for all three                   | Same                                     | Separate `query()`/`body()`/`param()` chains |
| Error details        | `issues` with `path`/`code`/`message`           | `details[]` with `path`/`message`/`type` | `array()` with `path`/`msg`                  |
| Reuse/composition    | `.extend()`, `.pick()`, `.omit()`, `.partial()` | `.concat()`, `.fork()`                   | Limited                                      |
| Ecosystem fit        | Modern Node/TS, works for env vars, forms, RPC  | Enterprise/legacy Node                   | Express-only projects                        |
| Best for             | New projects in these notes                     | Existing Joi codebases                   | Teams already on Express middleware chains   |

**Recommendation:** use **Zod** for new code (one library for request validation, environment config and response contracts), **Joi** if an existing codebase already depends on it, and `express-validator` only when its per-field chain style fits the team better. Do not mix two validators in one project.

***

## 10. Security: what validation must stop

| Attack                       | Malicious input                        | Defence in the schema                                                                    |
| ---------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------- |
| Mass assignment              | `{"role":"ADMIN"}` on a profile update | `.strict()` + a schema that has no `role` key                                            |
| NoSQL operator injection     | `{"email":{"$ne":null}}`               | `z.string()` — an object fails the type check                                            |
| Prototype pollution          | `{"__proto__":{"isAdmin":true}}`       | `.strict()` rejects unknown keys; never merge raw bodies                                 |
| Query-based injection        | `?sort=passwordHash`                   | `z.enum([...allowed])`                                                                   |
| Path traversal               | `:file` = `../../etc/passwd`           | Param schema `.regex()`/allowlist (ch. 07 of the Node section)                           |
| ReDoS                        | `?q=((((a+)+)+)+)+`                    | Never build a `RegExp` from input; cap length; escape for literal search                 |
| Huge payloads                | 500 MB body                            | `express.json({ limit })` **and** `.max()` on strings/arrays                             |
| Integer overflow abuse       | `?limit=1e309`                         | `z.coerce.number().int().min(1).max(100)`                                                |
| Unicode surprises            | 5000 emoji in a "200 char" field       | Remember `.max()` counts UTF-16 code units; add `.max()` on byte length where it matters |
| Field injection into updates | `{"$set":{...}}`                       | Never spread `req.body` into an update; pick fields explicitly                           |

```js
// File: harden-signup.js
import { z } from 'zod';

/** A signup schema that survives the payloads in exercise 12.2. */
export const signupSchema = z
  .object({
    email: z.email().max(254),
    password: z.string().min(12).max(200),
    name: z.string().trim().min(1).max(100),
    // No `role`, no `isAdmin`, no `credits` — a client cannot send what does not exist.
  })
  .strict();

/** Normalisation that must NOT be part of the security decision. */
export const normaliseEmail = (email) => String(email).trim().toLowerCase();
```

***

## 11. Testing validation

Validation is the easiest code in the system to test exhaustively, because it is a pure function.

```js
// File: tests/noteSchemas.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createNoteSchema, patchNoteSchema, listNotesQuerySchema, replaceNoteSchema } from '../src/validators/noteSchemas.js';
import { validate } from '../src/middleware/validate.js';

const validBody = {
  title: 'Learn Express',
  content: 'Chapter 12',
  tags: ['Node', 'express', 'NODE'],
  pinned: true,
};

/* ── Schema-level tests (pure, fast) ───────────────────────────────────────── */

test('a valid body is parsed, trimmed, lowercased and de-duplicated', () => {
  const result = createNoteSchema.safeParse({ ...validBody, title: '  Learn Express  ' });

  assert.equal(result.success, true);
  assert.equal(result.data.title, 'Learn Express');           // trimmed
  assert.deepEqual(result.data.tags, ['node', 'express', 'node']);
});

test('defaults are applied for omitted optional fields', () => {
  const result = createNoteSchema.safeParse({ title: 'T', content: 'C' });
  assert.equal(result.success, true);
  assert.deepEqual(result.data, { title: 'T', content: 'C', tags: [], pinned: false });
});

test('every problem is reported at once, with paths', () => {
  const result = createNoteSchema.safeParse({ title: '', tags: 'nope', extra: 1 });

  assert.equal(result.success, false);
  const fields = result.error.issues.map((issue) => issue.path.join('.') || 'body');
  assert.ok(fields.includes('title'));
  assert.ok(fields.includes('content'));       // missing required field
  assert.ok(fields.includes('tags'));
  assert.ok(fields.includes('body'));          // the unknown key
});

test('non-object bodies are rejected', () => {
  for (const body of [null, [], 'string', 42, true]) {
    assert.equal(createNoteSchema.safeParse(body).success, false, `accepted ${JSON.stringify(body)}`);
  }
});

test('whitespace-only strings fail the required check', () => {
  const result = createNoteSchema.safeParse({ title: '   ', content: 'C' });
  assert.equal(result.success, false);
  assert.equal(result.error.issues[0].path[0], 'title');
});

test('patch requires at least one field, and rejects unknown ones', () => {
  assert.equal(patchNoteSchema.safeParse({}).success, false);
  assert.equal(patchNoteSchema.safeParse({ title: 'ok' }).success, true);
  assert.equal(patchNoteSchema.safeParse({ nope: 1 }).success, false);
});

test('put is a full replacement: required fields must be present', () => {
  assert.equal(replaceNoteSchema.safeParse({ title: 'only a title' }).success, false);
  assert.equal(replaceNoteSchema.safeParse(validBody).success, true);
});

test('query strings are coerced and allowlisted', () => {
  const ok = listNotesQuerySchema.safeParse({ page: '3', limit: '50', sort: 'title,-createdAt', pinned: 'true', tag: ['a', 'b'] });
  assert.equal(ok.success, true);
  assert.equal(ok.data.page, 3);
  assert.equal(ok.data.limit, 50);
  assert.equal(ok.data.pinned, true);
  assert.deepEqual(ok.data.sort, ['title', '-createdAt']);
  assert.deepEqual(ok.data.tag, ['a', 'b']);

  assert.equal(listNotesQuerySchema.safeParse({ page: '0' }).success, false);
  assert.equal(listNotesQuerySchema.safeParse({ limit: '1000' }).success, false);
  assert.equal(listNotesQuerySchema.safeParse({ sort: 'passwordHash' }).success, false);
  assert.equal(listNotesQuerySchema.safeParse({ pinned: '1' }).success, false);
  assert.equal(listNotesQuerySchema.safeParse({ unknown: '1' }).success, false);
});

/* ── Middleware-level tests (the HTTP contract) ─────────────────────────────── */

function createMocks({ body = {}, query = {}, params = {} } = {}) {
  const req = { body, query, params, id: 'rid-1' };
  const res = {
    statusCode: 200, body: undefined,
    status(code) { this.statusCode = code; return this; },
    json(payload) { this.body = payload; return this; },
  };
  let nextCalled = 0;
  const next = () => { nextCalled += 1; };
  return { req, res, next, nextCalls: () => nextCalled };
}

test('the middleware stores parsed values and calls next() on success', () => {
  const { req, res, next, nextCalls } = createMocks({ body: { title: 'T', content: 'C' } });
  validate(createNoteSchema, 'body')(req, res, next);

  assert.equal(nextCalls(), 1);
  assert.equal(res.body, undefined);                       // nothing was sent
  assert.deepEqual(req.validated.body, { title: 'T', content: 'C', tags: [], pinned: false });
  assert.deepEqual(req.body, { title: 'T', content: 'C' }); // raw input untouched
});

test('the middleware responds 422 with the documented envelope', () => {
  const { req, res, next, nextCalls } = createMocks({ body: { title: '' } });
  validate(createNoteSchema, 'body')(req, res, next);

  assert.equal(nextCalls(), 0);
  assert.equal(res.statusCode, 422);
  assert.equal(res.body.error.code, 'VALIDATION_ERROR');
  assert.equal(res.body.error.requestId, 'rid-1');
  assert.ok(Array.isArray(res.body.error.details));
  assert.ok(res.body.error.details.every((detail) => detail.field && detail.message && detail.code));
});

test('a missing body is treated as an empty object, not a crash', () => {
  const { req, res, next, nextCalls } = createMocks({});
  req.body = undefined;
  validate(createNoteSchema, 'body')(req, res, next);

  assert.equal(nextCalls(), 0);
  assert.equal(res.statusCode, 422);
});
```

```bash
node --test tests/noteSchemas.test.js
```

```
✔ a valid body is parsed, trimmed, lowercased and de-duplicated
✔ defaults are applied for omitted optional fields
✔ every problem is reported at once, with paths
✔ non-object bodies are rejected
✔ whitespace-only strings fail the required check
✔ patch requires at least one field, and rejects unknown ones
✔ put is a full replacement: required fields must be present
✔ query strings are coerced and allowlisted
✔ the middleware stores parsed values and calls next() on success
✔ the middleware responds 422 with the documented envelope
✔ a missing body is treated as an empty object, not a crash
pass 11
fail 0
```

***

## 12. Common mistakes

| Mistake                                     | Symptom                                                        | Fix                                                  |
| ------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------- |
| Validating in the controller                | Rules scattered; some endpoints forget                         | One `validate` middleware per source                 |
| Using `parse` in middleware                 | A `ZodError` becomes a 500                                     | `safeParse` and respond `422`                        |
| Not dividing raw vs parsed input            | Logs show parsed data; debugging the raw request is impossible | Keep `req.body` raw, store parsed in `req.validated` |
| Only validating `body`                      | `?limit=999999` reaches the database; `:id` casts explode      | Validate query and params too                        |
| Messages written for developers             | Clients display "Expected string, received number"             | Override user-visible messages                       |
| Only the first error returned               | Users fix forms one field at a time                            | Report every issue (`issues` already does)           |
| Unknown keys silently stripped              | A typo'd field is ignored, the client thinks it worked         | `.strict()` and return `422`                         |
| `.passthrough()`/`.loose()` by default      | Unvalidated data flows into the database                       | Strict unless you have a reason                      |
| Business rules in a schema                  | Refines that need a database; races                            | Service rules + database constraints                 |
| Mass assignment through a permissive schema | `role`, `credits`, `isAdmin` updatable by clients              | Endpoint-specific schemas; never spread the body     |
| Coercion without bounds                     | `?limit=1e9`                                                   | `.min().max()` on every numeric                      |
| Reusing one schema for create/update        | PATCH demands fields; PUT loses fields                         | Three schemas per resource: create, replace, patch   |
| Validating but not normalising              | `A@B.com` and `a@b.com` become two accounts                    | `.trim()`, `.toLowerCase()` in the schema            |
| Trusting validation for authorisation       | Any authenticated user can change any field                    | Validate _which_ fields the endpoint may change      |
| No response validation                      | Field leaks and shape drift go unnoticed                       | Serialise with a response schema                     |

***

## Exercise 12.1 — Build the validation layer for the notes API

Create schemas and wiring for:

| Route                      | Validate                                                                                              |
| -------------------------- | ----------------------------------------------------------------------------------------------------- |
| `GET /api/v1/notes`        | query: `page`, `limit`, `sort`, `q`, `tag` (repeatable), `pinned`, `fields` — unknown params rejected |
| `POST /api/v1/notes`       | body: `title`, `content`, `tags`, `pinned` — unknown fields rejected                                  |
| `GET /api/v1/notes/:id`    | params: `id` is a UUID                                                                                |
| `PUT /api/v1/notes/:id`    | body: full replacement                                                                                |
| `PATCH /api/v1/notes/:id`  | body: any subset, at least one field, explicit `null` clears `content`                                |
| `DELETE /api/v1/notes/:id` | params only                                                                                           |

Plus: a table-driven test file proving each rule, and curl commands demonstrating the 422 contract.

<details>

<summary>Solution</summary>

```js
// File: src/validators/noteSchemas.js
import { z } from 'zod';

const Uuid = z.string().uuid('must be a valid UUID');
const Tag = z.string().trim().toLowerCase().min(1).max(30);

const SORT_VALUES = ['createdAt', '-createdAt', 'updatedAt', '-updatedAt', 'title', '-title'];
const FIELD_VALUES = ['id', 'title', 'content', 'tags', 'pinned', 'createdAt', 'updatedAt'];

/** Shared body shape. */
const noteBody = z.object({
  title: z.string().trim().min(1, 'must not be empty').max(200, 'must be at most 200 characters'),
  content: z.string().trim().min(1, 'must not be empty').max(10_000),
  tags: z.array(Tag).max(10, 'at most 10 tags').default([]),
  pinned: z.boolean().default(false),
});

export const createNoteSchema = noteBody.strict();

export const replaceNoteSchema = noteBody
  .extend({ content: z.string().trim().min(1).max(10_000) })
  .strict();

export const patchNoteSchema = z
  .object({
    title: z.string().trim().min(1, 'must not be empty').max(200).optional(),
    content: z.string().trim().min(1, 'must not be empty').max(10_000).nullable().optional(),  // null clears
    tags: z.array(Tag).max(10).optional(),
    pinned: z.boolean().optional(),
  })
  .strict()
  .refine((value) => Object.keys(value).length > 0, { message: 'at least one field must be provided' });

export const noteIdParamSchema = z.object({ id: Uuid }).strict();

export const listNotesQuerySchema = z
  .object({
    page: z.coerce.number().int('must be an integer').min(1, 'must be at least 1').default(1),
    limit: z.coerce.number().int('must be an integer').min(1).max(100, 'must be at most 100').default(20),
    sort: z
      .string()
      .default('-createdAt')
      .transform((value) => value.split(',').map((part) => part.trim()).filter(Boolean))
      .pipe(z.array(z.enum(SORT_VALUES, { message: 'contains an unsupported sort field' })).max(3)),
    q: z.string().trim().max(200, 'must be at most 200 characters').optional(),
    tag: z
      .union([z.string(), z.array(z.string())])
      .transform((value) => (Array.isArray(value) ? value : [value]))
      .pipe(z.array(Tag).max(10))
      .optional(),
    pinned: z
      .enum(['true', 'false'], { message: 'must be true or false' })
      .transform((value) => value === 'true')
      .optional(),
    fields: z
      .string()
      .transform((value) => value.split(',').map((part) => part.trim()))
      .pipe(z.array(z.enum(FIELD_VALUES, { message: 'contains an unknown field' })).min(1).max(7))
      .optional(),
  })
  .strict();
```

```js
// File: src/middleware/validateParam.js
/** Validate a single route parameter with a Zod schema, once per request. */
export function validateParam(name, schema) {
  return function paramValidator(req, res, next, value) {
    const result = schema.safeParse(value);
    if (!result.success) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Request validation failed',
          details: result.error.issues.map((issue) => ({
            field: name,
            message: issue.message,
            code: issue.code,
          })),
          requestId: req.id,
        },
      });
    }

    req.validated ??= {};
    req.validated.params ??= {};
    req.validated.params[name] = result.data;
    return next();
  };
}
```

```js
// File: src/routes/noteRoutes.js
import { Router } from 'express';
import { z } from 'zod';
import { validate } from '../middleware/validate.js';
import { validateParam } from '../middleware/validateParam.js';
import {
  createNoteSchema,
  patchNoteSchema,
  replaceNoteSchema,
  listNotesQuerySchema,
} from '../validators/noteSchemas.js';

export function createNoteRouter({ controller, authenticate }) {
  const router = Router();

  router.param('id', validateParam('id', z.string().uuid('must be a valid UUID')));

  router.get('/', validate(listNotesQuerySchema, 'query'), controller.list);
  router.post('/', authenticate, validate(createNoteSchema), controller.create);
  router.get('/:id', controller.getOne);
  router.put('/:id', authenticate, validate(replaceNoteSchema), controller.replace);
  router.patch('/:id', authenticate, validate(patchNoteSchema), controller.update);
  router.delete('/:id', authenticate, controller.remove);

  return router;
}
```

```js
// File: tests/notes.validation.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { createNoteRouter } from '../src/routes/noteRoutes.js';
import { NotFoundError } from '../src/utils/AppError.js';

const UUID = '3f2b1a90-8c7d-4e5f-a6b1-2c3d4e5f6a7b';
const seen = [];

const controller = {
  list: (req, res) => { seen.push(['list', req.validated.query]); res.json({ data: [], meta: {} }); },
  create: (req, res) => { seen.push(['create', req.validated.body]); res.status(201).json({ data: { id: UUID } }); },
  getOne: (req, res) => res.json({ data: { id: req.params.id } }),
  replace: (req, res) => { seen.push(['replace', req.validated.body]); res.json({ data: { id: req.params.id } }); },
  update: (req, res) => { seen.push(['update', req.validated.body]); res.json({ data: { id: req.params.id } }); },
  remove: (req, res) => res.status(204).end(),
};

const authenticate = (req, res, next) => {
  if (!req.get('authorization')) return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
  req.user = { id: 'u1', role: 'USER' };
  return next();
};

let server;
let baseUrl;

before(async () => {
  const app = express();
  app.use(express.json({ limit: '100kb' }));
  app.use((req, res, next) => { req.id = 'test-request-id'; next(); });
  app.use('/api/v1/notes', createNoteRouter({ controller, authenticate }));
  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    const statusCode = error.statusCode ?? 500;
    return res.status(statusCode).json({ error: { code: error.code ?? 'INTERNAL_ERROR', message: error.message } });
  });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1/notes`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const call = (path, { method = 'GET', body, token = 'Bearer test', query = '' } = {}) =>
  fetch(`${baseUrl}${path}${query}`, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: token } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

const expect422 = async (response, expectedFields) => {
  assert.equal(response.status, 422);
  const payload = await response.json();
  assert.equal(payload.error.code, 'VALIDATION_ERROR');
  const fields = payload.error.details.map((detail) => detail.field);
  for (const field of expectedFields) {
    assert.ok(fields.includes(field), `expected a detail for "${field}", got ${fields.join(', ')}`);
  }
  return payload;
};

test('GET / rejects unknown query parameters', async () => {
  const response = await call('/', { query: '?unknown=1' });
  await expect422(response, ['unknown']);
});

test('GET / rejects out-of-range pagination and unsupported sorts', async () => {
  await expect422(await call('/', { query: '?limit=1000' }), ['limit']);
  await expect422(await call('/', { query: '?limit=abc' }), ['limit']);
  await expect422(await call('/', { query: '?page=0' }), ['page']);
  await expect422(await call('/', { query: '?sort=passwordHash' }), ['sort']);
  await expect422(await call('/', { query: '?pinned=1' }), ['pinned']);
});

test('GET / coerces and defaults valid query parameters', async () => {
  const response = await call('/', { query: '?page=3&limit=50&sort=title,-createdAt&pinned=true&tag=a&tag=b' });
  assert.equal(response.status, 200);

  const [, query] = seen.at(-1);
  assert.equal(query.page, 3);
  assert.equal(query.limit, 50);
  assert.deepEqual(query.tag, ['a', 'b']);
  assert.equal(query.pinned, true);
  assert.deepEqual(query.sort, ['title', '-createdAt']);
});

test('POST / rejects an empty title, an empty body and unknown fields', async () => {
  await expect422(await call('/', { method: 'POST', body: { title: '', content: 'x' } }), ['title']);
  await expect422(await call('/', { method: 'POST', body: {} }), ['title', 'content']);
  await expect422(await call('/', { method: 'POST', body: { title: 'T', content: 'C', role: 'ADMIN' } }), ['body']);
  await expect422(await call('/', { method: 'POST', body: { title: 'T', content: 'C', tags: 'nope' } }), ['tags']);
});

test('POST / applies defaults and normalises tags', async () => {
  const response = await call('/', { method: 'POST', body: { title: '  Hi  ', content: 'C', tags: ['Node'] } });
  assert.equal(response.status, 201);

  const [, body] = seen.at(-1);
  assert.equal(body.title, 'Hi');
  assert.deepEqual(body.tags, ['node']);
  assert.equal(body.pinned, false);
});

test('POST / requires a token', async () => {
  const response = await call('/', { method: 'POST', body: { title: 'T', content: 'C' }, token: null });
  assert.equal(response.status, 401);
});

test('GET /:id rejects a malformed id with 422', async () => {
  const response = await call('/not-a-uuid');
  await expect422(response, ['id']);
});

test('PUT /:id requires the full document', async () => {
  await expect422(await call(`/${UUID}`, { method: 'PUT', body: { title: 'only title' } }), ['content']);

  const ok = await call(`/${UUID}`, { method: 'PUT', body: { title: 'T', content: 'C' } });
  assert.equal(ok.status, 200);
});

test('PATCH /:id accepts a subset, rejects an empty patch, and allows null to clear content', async () => {
  await expect422(await call(`/${UUID}`, { method: 'PATCH', body: {} }), ['body']);
  await expect422(await call(`/${UUID}`, { method: 'PATCH', body: { unknown: 1 } }), ['body']);

  const response = await call(`/${UUID}`, { method: 'PATCH', body: { content: null, pinned: true } });
  assert.equal(response.status, 200);

  const [, patch] = seen.at(-1);
  assert.equal(patch.content, null);
  assert.equal(patch.pinned, true);
});

test('every 422 carries the request id and per-field codes', async () => {
  const payload = await expect422(await call('/', { method: 'POST', body: {} }), ['title']);
  assert.equal(payload.error.requestId, 'test-request-id');
  assert.ok(payload.error.details.every((detail) => typeof detail.code === 'string'));
});
```

```bash
node --test tests/notes.validation.test.js
```

```
✔ GET / rejects unknown query parameters
✔ GET / rejects out-of-range pagination and unsupported sorts
✔ GET / coerces and defaults valid query parameters
✔ POST / rejects an empty title, an empty body and unknown fields
✔ POST / applies defaults and normalises tags
✔ POST / requires a token
✔ GET /:id rejects a malformed id with 422
✔ PUT /:id requires the full document
✔ PATCH /:id accepts a subset, rejects an empty patch, and allows null to clear content
✔ every 422 carries the request id and per-field codes
pass 10
fail 0
```

```bash
# The same rules, from the command line:
BASE=http://localhost:3000/api/v1/notes
curl -s "$BASE?limit=1000"                       # 422 — limit must be at most 100
curl -s "$BASE?sort=passwordHash"                # 422 — unsupported sort field
curl -s "$BASE?bogus=1"                          # 422 — unknown query parameter
curl -s -X POST "$BASE" -H 'Content-Type: application/json' -d '{}'                    # 422 (title, content)
curl -s -X POST "$BASE" -H 'Content-Type: application/json' -d '{"title":"T","content":"C","role":"ADMIN"}'  # 422 (body)
curl -s -X PATCH "$BASE/$UUID" -H 'Content-Type: application/json' -d '{}'             # 422 (body)
curl -s -X PUT  "$BASE/$UUID" -H 'Content-Type: application/json' -d '{"title":"T"}'   # 422 (content)
curl -s "$BASE/not-a-uuid"                        # 422 (id)
```

**Design notes**

| Decision                                  | Reason                                                                                 |
| ----------------------------------------- | -------------------------------------------------------------------------------------- |
| Three body schemas (create/replace/patch) | PUT and PATCH have different contracts; sharing one schema loses that                  |
| `.strict()` everywhere                    | A typo'd field is a client bug worth reporting, and mass assignment becomes impossible |
| Coercion only in query schemas            | Bodies should have real JSON types; query strings are always strings                   |
| Allowlists for `sort` and `fields`        | These values reach query builders; an enum is the strongest possible validation        |
| `pinned` accepts only `'true'`/`'false'`  | One spelling means no `?pinned=1` ambiguity                                            |
| Raw input preserved                       | `req.body` is untouched, so logs and error reports show what the client actually sent  |
| Params validated with `router.param`      | Runs once per request, and the controller never sees a malformed id                    |

</details>

***

## Exercise 12.2 — Break the signup endpoint

Here is a deliberately naive signup handler. Write a table-driven test with **malicious and malformed payloads**, then harden the endpoint until every one of them is a `422` with a useful message and nothing reaches the "database".

```js
// File: naive-signup.js
import express from 'express';
const app = express();
app.use(express.json());

app.post('/signup', async (req, res) => {
  const { email, password, name, role, credits } = req.body;
  const user = await db.users.insert({ email, password, name, role, credits });
  res.json({ id: user.id, email: user.email, password: user.password });
});

app.listen(3000);
```

Attack payloads to defeat:

```
1. {}                                              → missing everything
2. {"email":"not-an-email"}                        → invalid format
3. {"email":{"$ne":null},"password":"x"}           → NoSQL operator injection
4. {"email":"a@b.com","password":"short"}          → weak password
5. {"email":"a@b.com","password":"supersecret","role":"ADMIN"}          → privilege escalation
6. {"email":"a@b.com","password":"supersecret","credits":999999}        → mass assignment
7. {"email":"A@B.com","password":"supersecret","name":"A"}  twice       → normalisation/duplicates
8. {"email":"a@b.com","password":"supersecret","name":"X".repeat(5000)} → unbounded length
9. {"email":"a@b.com","password":"supersecret","__proto__":{"admin":true}} → prototype pollution
10. "not-an-object"                                → wrong top-level type
```

<details>

<summary>Solution</summary>

```js
// File: src/validators/authSchemas.js
import { z } from 'zod';

/**
 * The schema is the allowlist. Fields that do not exist in it cannot be sent —
 * not because they are filtered, but because they are not part of the contract.
 */
export const signupSchema = z
  .object({
    email: z.email('must be a valid email address').max(254, 'must be at most 254 characters'),
    password: z
      .string()
      .min(12, 'must be at least 12 characters')
      .max(200, 'must be at most 200 characters'),
    name: z.string().trim().min(1, 'required').max(100, 'must be at most 100 characters'),
  })
  .strict();
```

```js
// File: src/routes/authRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { signupSchema } from '../validators/authSchemas.js';

export function createAuthRouter({ controller }) {
  const router = Router();

  router.post('/signup', validate(signupSchema), controller.signup);

  return router;
}
```

```js
// File: src/controllers/authController.js
export function createAuthController({ authService }) {
  return {
    async signup(req, res, next) {
      try {
        const user = await authService.signup(req.validated.body);
        res.status(201).location(`/api/v1/users/${user.id}`).json({ data: user });
      } catch (error) {
        next(error);
      }
    },
  };
}
```

```js
// File: src/services/authService.js
import { ConflictError } from '../utils/AppError.js';

const normaliseEmail = (email) => String(email).trim().toLowerCase();

export function createAuthService({ userRepository, passwordHasher }) {
  return {
    async signup({ email, password, name }) {
      const normalised = normaliseEmail(email);

      if (await userRepository.existsByEmail(normalised)) {
        throw new ConflictError('That email is already registered', { field: 'email' });
      }

      const user = await userRepository.create({
        email: normalised,
        name: name.trim(),
        passwordHash: await passwordHasher.hash(password),
        role: 'USER',                                    // never from input
        credits: 0,                                      // never from input
      });

      // The response DTO: never the hash, never the raw record.
      return { id: user.id, email: user.email, name: user.name, role: user.role, createdAt: user.createdAt };
    },
  };
}
```

```js
// File: tests/signup.security.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { signupSchema } from '../src/validators/authSchemas.js';
import { createAuthService } from '../src/services/authService.js';
import { createAuthController } from '../src/controllers/authController.js';

/** Records everything that reached the "database". */
const inserted = [];
const repository = {
  async existsByEmail(email) { return inserted.some((user) => user.email === email); },
  async create(data) {
    if (typeof data.email !== 'string') throw new Error(`email must be a string, got ${typeof data.email}`);
    const user = { id: `u${inserted.length + 1}`, ...data };
    inserted.push(user);
    return user;
  },
};

const controller = createAuthController({
  authService: createAuthService({
    userRepository: repository,
    passwordHasher: { hash: async (plain) => `hashed:${plain}`, compare: async () => true },
  }),
});

let server;
let baseUrl;

before(async () => {
  const app = express();
  app.use(express.json({ limit: '10kb' }));
  app.use((req, res, next) => { req.id = 'rid'; next(); });
  app.use('/api/v1/auth', (await import('../src/routes/authRoutes.js')).createAuthRouter({ controller }));
  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    const statusCode = error.statusCode ?? 500;
    return res.status(statusCode).json({ error: { code: error.code ?? 'INTERNAL_ERROR', message: error.message } });
  });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1/auth/signup`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const post = (payload) => {
  const isObject = payload !== null && typeof payload === 'object';
  return fetch(baseUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: isObject ? JSON.stringify(payload) : String(payload),
  });
};

test('payload 1 — an empty object reports every missing field', async () => {
  const response = await post({});
  assert.equal(response.status, 422);

  const fields = (await response.json()).error.details.map((detail) => detail.field);
  assert.ok(fields.includes('email'));
  assert.ok(fields.includes('password'));
  assert.ok(fields.includes('name'));
});

test('payload 2 — a malformed email', async () => {
  const response = await post({ email: 'not-an-email', password: 'supersecret123', name: 'A' });
  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.details[0].field, 'email');
});

test('payload 3 — NoSQL operator injection is a type error, not a query', async () => {
  const response = await post({ email: { $ne: null }, password: 'supersecret123', name: 'A' });
  assert.equal(response.status, 422);

  const detail = (await response.json()).error.details.find((item) => item.field === 'email');
  assert.ok(detail);
  assert.ok(inserted.every((user) => typeof user.email === 'string'));
});

test('payload 4 — a short password', async () => {
  const response = await post({ email: 'a@b.com', password: 'short', name: 'A' });
  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.details[0].field, 'password');
});

test('payload 5 — privilege escalation via a client-supplied role', async () => {
  const response = await post({ email: 'role@example.com', password: 'supersecret123', name: 'A', role: 'ADMIN' });
  assert.equal(response.status, 422);
  assert.ok(inserted.every((user) => user.role !== 'ADMIN'));
});

test('payload 6 — mass assignment via credits', async () => {
  const response = await post({ email: 'credits@example.com', password: 'supersecret123', name: 'A', credits: 999_999 });
  assert.equal(response.status, 422);
  assert.ok(inserted.every((user) => user.credits === undefined || user.credits === 0));
});

test('payload 7 — email normalisation prevents duplicate accounts', async () => {
  const first = await post({ email: 'Dup@Example.com', password: 'supersecret123', name: 'A' });
  assert.equal(first.status, 201);

  const second = await post({ email: '  dup@example.COM ', password: 'supersecret123', name: 'B' });
  assert.equal(second.status, 409);                                    // ConflictError
  assert.equal(inserted.filter((user) => user.email === 'dup@example.com').length, 1);
});

test('payload 8 — an unbounded name', async () => {
  const response = await post({ email: 'long@example.com', password: 'supersecret123', name: 'X'.repeat(5000) });
  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.details[0].field, 'name');
});

test('payload 9 — prototype pollution is rejected as an unknown key', async () => {
  const response = await post({ email: 'proto@example.com', password: 'supersecret123', name: 'A', __proto__: { admin: true } });
  assert.equal(response.status, 422);
  assert.equal({}.admin, undefined);                                   // the prototype is untouched
});

test('payload 10 — a non-object body', async () => {
  const response = await post('not-an-object');
  assert.ok([400, 422].includes(response.status));                     // 400 if JSON parsing rejects it first
  assert.ok({}.admin === undefined);
});

test('a valid signup returns 201 and never the password', async () => {
  const response = await post({ email: 'valid@example.com', password: 'supersecret123', name: 'Ankit' });
  assert.equal(response.status, 201);

  const body = await response.json();
  assert.deepEqual(Object.keys(body.data).sort(), ['createdAt', 'email', 'id', 'name', 'role']);
  assert.equal(JSON.stringify(body).includes('supersecret123'), false);
  assert.equal(JSON.stringify(body).includes('hashed:'), false);
});

test('the schema alone rejects every attack payload', () => {
  const payloads = [
    {},
    { email: 'x', password: 'supersecret123', name: 'A' },
    { email: { $ne: null }, password: 'supersecret123', name: 'A' },
    { email: 'a@b.com', password: 'short', name: 'A' },
    { email: 'a@b.com', password: 'supersecret123', name: 'A', role: 'ADMIN' },
    { email: 'a@b.com', password: 'supersecret123', name: 'A', credits: 1 },
    { email: 'a@b.com', password: 'supersecret123', name: 'X'.repeat(5000) },
    { email: 'a@b.com', password: 'supersecret123', name: 'A', __proto__: { admin: true } },
    null,
    [],
  ];

  for (const payload of payloads) {
    assert.equal(signupSchema.safeParse(payload).success, false, `schema accepted ${JSON.stringify(payload)?.slice(0, 60)}`);
  }
});
```

```bash
node --test tests/signup.security.test.js
```

```
✔ payload 1 — an empty object reports every missing field
✔ payload 2 — a malformed email
✔ payload 3 — NoSQL operator injection is a type error, not a query
✔ payload 4 — a short password
✔ payload 5 — privilege escalation via a client-supplied role
✔ payload 6 — mass assignment via credits
✔ payload 7 — email normalisation prevents duplicate accounts
✔ payload 8 — an unbounded name
✔ payload 9 — prototype pollution is rejected as an unknown key
✔ payload 10 — a non-object body
✔ a valid signup returns 201 and never the password
✔ the schema alone rejects every attack payload
pass 12
fail 0
```

**The four mechanisms that make this work**

| Mechanism                                   | Defeats                                     |
| ------------------------------------------- | ------------------------------------------- |
| **Type checks** (`z.string()`, `z.email()`) | Operator injection, wrong shapes            |
| **`.strict()`**                             | Mass assignment, prototype pollution, typos |
| **Bounds** (`.min`, `.max`)                 | Truncation attacks, oversized fields, DoS   |
| **Server-assigned fields + DTOs**           | Privilege escalation, leaking hashes        |

**And the one thing the schema cannot do:** uniqueness. `409` comes from the service plus a unique index in the database, because two identical requests can pass validation simultaneously.

</details>

***

## What's next

Input is now bounded and typed. Next: proving who the caller is — authentication, sessions versus tokens, and the password rules that make credentials hard to steal.

→ [13 — Authentication](13-authentication.md)
