# 06 — JSON and Data Formats

> **Where this fits:** You will spend your career moving data between JSON and the
> database. This chapter covers the format itself, the traps it sets for JavaScript
> developers, and the conventions that keep payloads sane. Everything here reappears in
> every Express controller you write.

---

## 1. What is JSON?

**JSON (JavaScript Object Notation)** is a text format for representing structured data.
It was derived from JavaScript object literal syntax — but it is *not* JavaScript.

| | JSON | JavaScript object |
| --- | --- | --- |
| Keys | Must be double-quoted strings | Identifiers or quoted |
| Strings | Double quotes only | Single, double or backtick |
| Trailing commas | **Illegal** | Allowed |
| Comments | **Illegal** | Allowed |
| Values | string, number, boolean, null, array, object | Also `undefined`, `function`, `Date`, `Map`, `Set`, `BigInt`, `Symbol`, `RegExp` |
| Numbers | Any precision, no NaN/Infinity | 64-bit float + `NaN`/`Infinity`/`BigInt` |

Two rules block most beginner bugs:

```json
// ❌ Invalid JSON — every one of these is a SyntaxError from JSON.parse
{
  name: "Ankit",          // key not quoted
  'email': "a@x.com",     // single quotes
  age: 30,                // trailing comma below
  role: undefined,        // undefined is not a JSON value
  joined: new Date(),     // not a literal, and Date is not a JSON type
  note: "line1\nline2",   // real newline inside a string must be escaped as \n
}
```

```json
// ✅ Valid JSON
{
  "name": "Ankit",
  "email": "a@x.com",
  "age": 30,
  "role": null,
  "joined": "2026-09-18T10:15:30.000Z",
  "note": "line1\nline2"
}
```

> **Practical takeaway:** JSON is a data *interchange* format. When you generate it, use
> `JSON.stringify` — never build strings by hand. When you consume it, use `JSON.parse`
> inside a `try/catch` — never `eval`.

### Why JSON instead of XML or CSV?

- **Human-readable** and reasonably compact.
- **Native to JavaScript** (`JSON.parse`/`JSON.stringify` are built in) — which matters
  enormously in a Node backend, where your internal objects and your wire format line up.
- **Universally supported** — every language has a JSON library.
- **Composable** — arbitrarily deep nesting without the namespace/attribute ceremony of
  XML.

Its weaknesses, for honesty:

- No date/time type (you send ISO strings — see §5).
- No comments (kills "config files in JSON"; use JSONC/YAML/TOML instead).
- No schema at the format level (`$schema` adding conventions exist, and JSON Schema is a
  separate specification).
- Numbers are doubles in JavaScript: integers above 2^53 lose precision.
- No binary support (you base64-encode or use multipart).

---

## 2. The grammar, precisely

```text
value      = object | array | string | number | "true" | "false" | "null"
object     = "{" [ member { "," member } ] "}"
member     = string ":" value
array      = "[" [ value { "," value } ] "]"
string     = '"' { any char except " and \ , or an escape } '"'
number     = [ "-" ] int [ frac ] [ exp ]
```

Escapes allowed in strings: `\"` `\\` `\/` `\b` `\f` `\n` `\r` `\t` `\uXXXX`.

```js
// File: json-basics.mjs
const payload = {
  id: 'u_42',
  name: 'Ankit Kumar',
  active: true,
  roles: ['user', 'editor'],
  address: { city: 'Pune', zip: '411001' },
  lastLoginAt: null,
};

const text = JSON.stringify(payload);
console.log(text);
// {"id":"u_42","name":"Ankit Kumar","active":true,"roles":["user","editor"],
//  "address":{"city":"Pune","zip":"411001"},"lastLoginAt":null}

console.log(typeof text);                       // string
const back = JSON.parse(text);
console.log(back.name);                         // Ankit Kumar
console.log(back.address.city);                 // Pune
console.log(String(back.roles.length));         // 2
```

Note the confusing-but-correct detail: `typeof text` is `"string"`. A JSON payload *is*
a string of text until you parse it.

### Parsing safely

```js
// File: safe-parse.mjs
function parseJsonSafe(text) {
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

console.log(parseJsonSafe('{"a":1}'));
// { ok: true, value: { a: 1 } }

console.log(parseJsonSafe('{"a":1,}'));
// { ok: false, error: "Expected double-quoted property name in JSON at position 7 …" }

console.log(parseJsonSafe(''));
// { ok: false, error: "Unexpected end of JSON input" }
```

An unparseable body must become a **`400 Bad Request`**, not a `500`. This is exactly
what `express.json()` does for you, and why it must be registered before your routes
([02-express/07-middleware.md](../02-express/07-middleware.md)).

### Formatting for humans vs size

```js
// File: stringify-options.mjs
const user = { id: 1, name: 'Ankit', roles: ['admin', 'editor'] };

console.log(JSON.stringify(user));
// {"id":1,"name":"Ankit","roles":["admin","editor"]}          ← compact: what you send over the wire

console.log(JSON.stringify(user, null, 2));
// {
//   "id": 1,
//   "name": "Ankit",
//   "roles": [
//     "admin",
//     "editor"
//   ]
// }                                                            ← pretty: what you print for debugging

// The replacer acts as a field allowlist (second argument is either a function or an array).
console.log(JSON.stringify(user, ['id', 'name']));
// {"id":1,"name":"Ankit"}

// A function replacer can transform or drop values.
console.log(
  JSON.stringify({ user: 'ankit', password: 'hunter2', token: 'abc' }, (key, value) =>
    key === 'password' || key === 'token' ? undefined : value
  )
);
// {"user":"ankit"}
```

Never pretty-print API responses: it can double the payload size for zero benefit.

---

## 3. The JavaScript ↔ JSON mismatches (the important part)

### 3.1 `undefined`, functions and symbols vanish

```js
// File: json-mismatch.mjs
const obj = {
  a: 1,
  b: undefined,          // dropped entirely
  c: () => 'nope',       // dropped entirely
  d: Symbol('x'),        // dropped entirely
};

console.log(JSON.stringify(obj));   // {"a":1}

// But inside an array they become null instead (this inconsistency is real):
console.log(JSON.stringify([1, undefined, () => {}, Symbol('x')]));
// [1,null,null,null]
```

Why it matters: `res.json({ user: found })` where `found` is `undefined` sends `{}` — the
client gets no error and no data. Always handle "not found" explicitly with `404`.

### 3.2 Circular structures throw

```js
// File: json-circular.mjs
const a = { name: 'a' };
const b = { name: 'b', a };
a.b = b; // a → b → a

try {
  JSON.stringify(a);
} catch (error) {
  console.log(error.constructor.name); // TypeError
  console.log(error.message);          // Converting circular structure to JSON
}
```

This happens in real code when you serialise an ORM entity with its loaded relations
(`user.orders[0].user.orders[0]...`). The fix is to serialise a **DTO** — a plain object
with exactly the fields you intend to expose:

```js
// File: dto.example.mjs
function toUserDto(user) {
  return {
    id: String(user._id),
    name: user.name,
    email: user.email,
    createdAt: user.createdAt.toISOString(),
  };
}
export { toUserDto };
```

This one habit solves three problems at once: circular references, accidental leaking of
`passwordHash`, and coupling your API to your database schema.

### 3.3 Dates become strings

There is no `Date` in JSON. `JSON.stringify` calls `Date.prototype.toJSON()`, which
produces an ISO string in **UTC**:

```js
// File: json-dates.mjs
const now = new Date();

console.log(JSON.stringify({ createdAt: now }));
// {"createdAt":"2026-09-18T10:15:30.123Z"}     ← always UTC with a Z suffix

// Coming back in: it is a STRING, not a Date — this is the classic bug.
const parsed = JSON.parse(JSON.stringify({ createdAt: now }));
console.log(typeof parsed.createdAt);            // string
console.log(parsed.createdAt instanceof Date);   // false
console.log(parsed.createdAt.getFullYear);       // undefined  ← calling Date methods explodes

// Convert explicitly at the boundary:
const realDate = new Date(parsed.createdAt);
console.log(realDate instanceof Date);           // true
```

We will revisit this with "where should the conversion happen?" in
[02-express/05-request-response.md](../02-express/05-request-response.md) — the answer is
"in the controller/DTO layer, never by scattering `new Date()` through your services".

### 3.4 Big numbers lose precision

```js
// File: json-bigint.mjs
const huge = 9007199254740993n; // 2^53 + 1, a BigInt

console.log(Number(huge));                     // 9007199254740992 ← wrong!
try {
  console.log(JSON.stringify({ id: huge }));   // BigInt cannot be serialised
} catch (error) {
  console.log(error.message);                  // Do not know how to serialize a BigInt
}
```

This is why **database ids are serialised as strings** in almost every serious API: a
MongoDB ObjectId, a Snowflake id, or a MySQL `BIGINT` can all exceed the safe range.

### 3.5 Duplicate keys and other silent surprises

```js
// File: json-duplicates.mjs
// Last value wins — no error is raised.
console.log(JSON.parse('{"role":"user","role":"admin"}'));
// { role: 'admin' }
```

That looks harmless until you realise that **"last key wins" is how some
prototype-pollution and parameter-smuggling attacks work**: a proxy, a WAF and your
application can disagree about which `role` is authoritative. Reject duplicate keys
during validation when the value is security-relevant.

### 3.6 A worked example: `__proto__`

```js
// File: json-proto.mjs
const parsed = JSON.parse('{"__proto__": {"isAdmin": true}}');
console.log(parsed.isAdmin);          // undefined  ← JSON.parse is safe here
console.log({}.isAdmin);              // undefined

// The dangerous version is a hand-written merge/assign, e.g. Object.assign({}, parsed)
// or a naive deep-merge that walks attacker-controlled keys.
function unsafeMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (source[key] && typeof source[key] === 'object') {
      target[key] = unsafeMerge(target[key] ?? {}, source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

const evil = JSON.parse('{"__proto__": {"polluted": true}}');
unsafeMerge({}, evil);
console.log(String({}.polluted));     // true ← prototype polluted for the whole process

// Safe version: skip dangerous keys and create null-prototype objects.
function safeMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') continue;
    target[key] = source[key];
  }
  return target;
}

const safe = safeMerge(Object.create(null), evil);
console.log(String(safe.polluted));   // undefined
console.log(String({}.polluted));     // undefined
```

Lesson: `JSON.parse` itself is safe; **your own merging, `Object.assign`, and recursive
utilities are not.** This is why `npm audit` regularly shows prototype-pollution CVEs in
innocent-looking helper libraries.

---

## 4. JSON vs the alternatives (when to use what)

| Format | Size | Human-readable | Schema | Best for |
| --- | --- | --- | --- | --- |
| **JSON** | Medium | ✅ | Optional (JSON Schema) | REST APIs — the default |
| **YAML** | Larger | ✅✅ | Optional | Config files (Docker Compose, CI) — but indentation-sensitive |
| **JSONC/JSON5** | Medium | ✅ | Optional | Config with comments (tsconfig, VS Code) |
| **TOML** | Medium | ✅ | ✅ | Config (Rust tooling, `pyproject.toml`) |
| **Protocol Buffers** | Small | ❌ | Required (`.proto`) | gRPC, internal high-throughput services |
| **MessagePack/CBOR** | Smaller than JSON | ❌ | No | Binary transports, IoT |
| **CSV** | Small | ✅ | No | Spreadsheet exports, bulk imports (loses nesting and types) |
| **XML** | Large | ✅ | ✅ (XSD) | Legacy/SOAP, documents, office formats |

Rule of thumb for a backend developer: **JSON for APIs, YAML/TOML for configuration,
protobuf for internal service traffic, CSV for exports.**

### Content negotiation

The client can *ask* for a format, and you can honour it:

```http
GET /api/v1/reports/2026-08
Accept: text/csv
```

```js
// File: negotiation.example.js — this is how you would branch on it
function sendReport(req, res, rows) {
  const accept = req.get('Accept') ?? 'application/json';

  if (accept.includes('text/csv')) {
    res.type('text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename="report.csv"');
    return res.send(toCsv(rows));
  }

  return res.json({ data: rows });
}

function toCsv(rows) {
  if (rows.length === 0) return '';
  const headers = Object.keys(rows[0]);
  const lines = rows.map((row) => headers.map((h) => JSON.stringify(row[h] ?? '')).join(','));
  return [headers.join(','), ...lines].join('\n');
}

export { sendReport, toCsv };
```

---

## 5. Practical conventions for API payloads

| Concern | Convention | Example |
| --- | --- | --- |
| Field names | `camelCase` in JSON (or `snake_case`, but pick one) | `"createdAt"` |
| Dates | ISO 8601 UTC string | `"2026-09-18T10:15:30.000Z"` |
| Date only | `YYYY-MM-DD` | `"1995-04-02"` |
| Money | Integer minor units + currency code | `{ "amount": 1499, "currency": "INR" }` |
| Booleans | Real booleans, not `"true"`/`0`/`1` | `"isActive": true` |
| Absent vs null | Absent = "not provided"; `null` = "explicitly empty" | PATCH semantics depend on this |
| IDs | Strings | `"id": "64f1a2b3…"` |
| Collections | `{ data: [...], meta: {...} }` | see [05](05-rest-and-api-design.md) |
| Enums | Lowercase strings, not magic numbers | `"status": "pending"` |
| Empty collections | `[]`, never `null` | Clients loop over it directly |
| Unicode | JSON is UTF-8; `Content-Type: application/json; charset=utf-8` | Emojis, names like "Ankit Kumár" |

### The PATCH null-vs-absent problem

```json
// PATCH /users/42
{ "name": "New Name" }          // email not mentioned → leave it alone
{ "email": null }               // email explicitly cleared → set to NULL
```

If your code uses `if (req.body.email)` you cannot tell the difference between
"not sent" and "sent as null". Use an explicit check:

```js
// File: patch-null.example.js
function applyPatch(current, patch) {
  const next = { ...current };
  for (const [key, value] of Object.entries(patch)) {
    if (Object.prototype.hasOwnProperty.call(patch, key)) {
      next[key] = value; // present, even when value is null
    }
  }
  return next;
}

export { applyPatch };
```

Schema libraries make this explicit too: in Zod, `.optional()` means "may be absent" and
`.nullable()` means "may be null" — and `.nullish()` means both. Using the right one is
the difference between "clear the field" and "ignore the field".

---

## 6. Size, performance and safety

```js
// Server-side: always bound the payload you are willing to parse.
app.use(express.json({ limit: '100kb' })); // snippet: partial
```

| Concern | Guidance |
| --- | --- |
| Payload size | Keep request bodies under ~100 KB; files go through multipart upload, not JSON |
| Compression | Enable gzip/brotli for responses over ~1 KB (JSON compresses ~80%) |
| Nesting depth | Avoid > 5 levels; deep nesting means clients over-fetch and queries get slow |
| Repeated keys | Large arrays of identical keys compress well but cost CPU to parse; consider a `{columns, rows}` shape for bulk data |
| Compression attack risk | Brotli/`Content-Encoding` request bodies can be an amplification vector — do not accept compressed *requests* unless you need them |
| PII in payloads | Never log raw bodies containing passwords, tokens or card data |

---

## 7. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| Building JSON with string concatenation | Broken payloads, injection | `JSON.stringify` |
| `JSON.parse` without try/catch | `500` on malformed input | Catch → `400` |
| Assuming a parsed date is a `Date` | `parsed.createdAt.getFullYear is not a function` | `new Date(str)` explicitly |
| Sending `undefined` fields | Keys silently missing | Send `null`, or omit deliberately |
| Sending the whole ORM entity | Leaks `passwordHash`, circular error | DTO/serialiser |
| Using `res.send(obj)` believing it is JSON | Express 5 *does* JSON-encode, but the type may surprise you | Use `res.json()` for intent and headers |
| Parsing large JSON in a loop unnecessarily | CPU spikes | Parse once, reuse |
| Storing JSON in a `TEXT` column and querying it | Full table scans | Use the DB's JSON type (MySQL `JSON`, Postgres `jsonb`, Mongo native) |
| Trailing commas / comments in config | `SyntaxError` at startup | Use JSONC/YAML for config, or accept the strictness |

---

## Exercise 6.1 — Find the bugs

```json
{
  "user": 'ankit',
  "age": 30,
  "signupDate": new Date(),
  "bio": "He said "hello" loudly",
  "tags": ["a", "b",],
  "score": NaN,
}
```

List every reason this is invalid JSON, then produce a corrected version and the
JavaScript object it parses to.

<details>
<summary>Solution</summary>

**Invalid:**

1. `'ankit'` — JSON strings must use double quotes.
2. `new Date()` — not a JSON literal; JSON has no Date type.
3. `"He said "hello" loudly"` — unescaped inner double quotes (needs `\"`).
4. `["a", "b",]` — trailing comma in an array.
5. `NaN` — not a valid JSON number.
6. Trailing comma after `"score": NaN,` — also illegal.

**Corrected:**

```json
{
  "user": "ankit",
  "age": 30,
  "signupDate": "2026-09-18T10:15:30.000Z",
  "bio": "He said \"hello\" loudly",
  "tags": ["a", "b"],
  "score": null
}
```

**Parses to (JavaScript):**

```js
// File: exercise-6-1.mjs
const parsed = JSON.parse(
  '{"user":"ankit","age":30,"signupDate":"2026-09-18T10:15:30.000Z",' +
    '"bio":"He said \\"hello\\" loudly","tags":["a","b"],"score":null}'
);

console.log(parsed.user);                              // ankit
console.log(typeof parsed.signupDate);                 // string   ← not a Date
console.log(new Date(parsed.signupDate).getUTCFullYear()); // 2026
console.log(parsed.tags.join(','));                    // a,b
console.log(parsed.score);                             // null
```

Note how `score: null` communicates "no score" explicitly, whereas `undefined` would have
removed the key (or become `null` inside an array — see §3.1).

</details>

## Exercise 6.2 — Design a safe response DTO

A Mongoose document looks like this. Write a function that produces the JSON you would
send to the owner of the account, and a second version for a public profile view.

```js
const rawUser = {
  _id: '64f1a2b3c4d5e6f7a8b9c0d1',
  name: 'Ankit Kumar',
  email: 'ankit@example.com',
  passwordHash: '$2b$12$abcdefghijklmnopqrstuv',
  role: 'admin',
  apiKey: 'sk_live_9f8e7d6c5b4a',
  resetToken: 'a1b2c3',
  createdAt: new Date('2026-01-05T08:00:00Z'),
  __v: 0,
  updatePassword: function () {}, // a Mongoose method
};
```

<details>
<summary>Solution</summary>

```js
// File: dto-solution.mjs
const rawUser = {
  _id: '64f1a2b3c4d5e6f7a8b9c0d1',
  name: 'Ankit Kumar',
  email: 'ankit@example.com',
  passwordHash: '$2b$12$abcdefghijklmnopqrstuv',
  role: 'admin',
  apiKey: 'sk_live_9f8e7d6c5b4a',
  resetToken: 'a1b2c3',
  createdAt: new Date('2026-01-05T08:00:00Z'),
  __v: 0,
  updatePassword: function () {},
};

// FULL: for the account owner. Includes email, never credentials.
function toSelfDto(user) {
  return {
    id: String(user._id),                 // string: ids can exceed JS safe integers
    name: user.name,
    email: user.email,
    role: user.role,
    createdAt: user.createdAt.toISOString(), // explicit conversion, UTC
  };
}

// PUBLIC: for anyone. No email, no internal fields, no role.
function toPublicDto(user) {
  return {
    id: String(user._id),
    name: user.name,
    memberSince: user.createdAt.getUTCFullYear(),
  };
}

console.log(JSON.stringify(toSelfDto(rawUser), null, 2));
console.log(JSON.stringify(toPublicDto(rawUser), null, 2));

// Proof that the dangerous fields never reach the wire:
console.log(JSON.stringify(toSelfDto(rawUser)).includes('passwordHash')); // false
console.log(JSON.stringify(toSelfDto(rawUser)).includes('apiKey'));       // false
console.log(JSON.stringify(toPublicDto(rawUser)).includes('ankit@'));     // false
```

**Design notes**

- **Allowlist, not blocklist.** Listing the fields you *do* expose is safe forever; a
  `delete user.passwordHash` blocklist breaks the day someone adds a new secret field.
- `__v` and methods would be dropped by `JSON.stringify` for other reasons, but relying on
  that is fragile — the DTO makes the intent explicit.
- **Two DTOs, one source.** The public view is not "self minus email"; it is a separate
  contract that can evolve independently.
- `createdAt` → `memberSince` is an example of the API *not* mirroring the database
  schema, which is exactly what lets you rename columns later without breaking clients.

</details>

---

## What's next

Data is flowing over HTTP in JSON. Now the part everyone underestimates: HTTP is
**stateless**, so how do we know who is logged in across requests? Cookies, sessions and
tokens.

→ [07 — Cookies, Sessions and State](07-cookies-sessions-and-state.md)
