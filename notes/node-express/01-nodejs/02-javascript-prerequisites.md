# 02 — JavaScript Prerequisites

> **Where this fits:** You know JavaScript. This chapter is not a language course — it is
> the **specific subset** that backend code uses constantly, with the traps that cause real
> bugs. If you can read every snippet here without pausing, skip to
> [03 — Node.js Basics](03-nodejs-basics.md). If some are unfamiliar, this is the highest-
> value hour you will spend before writing a server.

How to use this chapter: run every snippet with `node file.js`. Reading JavaScript teaches
you much less than watching values print.

---

## 1. `let`, `const`, and scope

```js
// File: scope.js
const MAX_RETRIES = 3;         // cannot be reassigned
let attempts = 0;              // can be reassigned

attempts += 1;

// Block scope: braces create a new scope for let/const.
for (let i = 0; i < 3; i += 1) {
  const label = `attempt-${i}`;
  console.log(label);
}

// console.log(label);  // ReferenceError: label is not defined
```

Rules to live by in backend code:

| Rule | Why |
| --- | --- |
| Default to `const` | It communicates "this binding never changes"; use `let` only when reassigning |
| Never use `var` | Function-scoped, hoisted, and leaks out of blocks; it is a legacy footgun |
| `const` objects are not immutable | `const config = {}; config.port = 3000;` is legal — the *binding* is constant, not the contents |

```js
// File: const-not-immutable.js
const config = { port: 3000 };
config.port = 4000;          // ✅ allowed — mutating the object
// config = {};              // ❌ TypeError: Assignment to constant variable

// To really freeze (shallow):
const frozen = Object.freeze({ port: 3000 });
frozen.port = 5000;          // silently ignored (throws in strict mode)
console.log(frozen.port);    // 3000
```

---

## 2. Functions: declarations, expressions, arrows

```js
// File: functions.js
// 1. Declaration — hoisted, so it can be called before its definition.
function add(a, b) {
  return a + b;
}

// 2. Function expression assigned to a const — NOT hoisted.
const subtract = function (a, b) {
  return a - b;
};

// 3. Arrow function — the backend workhorse.
const multiply = (a, b) => a * b;

// Arrow with a block body (needed when you have multiple statements).
const divide = (a, b) => {
  if (b === 0) throw new Error('Division by zero');
  return a / b;
};

console.log([add(2, 3), subtract(5, 2), multiply(3, 4), divide(10, 2)]); // [5,3,12,5]
```

### The one difference that bites: `this`

```js
// File: this-difference.js
const counter = {
  count: 0,
  incrementArrow: () => {
    // `this` inside an arrow is the ENCLOSING scope's `this` — here, undefined/module scope
    return typeof this;
  },
  incrementMethod() {
    // `this` is the object the method was called on
    this.count += 1;
    return this.count;
  },
};

console.log(counter.incrementArrow()); // 'undefined'  (module scope has no this)
console.log(counter.incrementMethod()); // 1
console.log(counter.incrementMethod()); // 2
```

Rules:

- **Arrow functions do not have their own `this`.** Use them for callbacks and standalone
  functions.
- **Object methods and Express handlers** should be regular `function`s or method shorthand
  when they need `this` — otherwise the arrow form is fine.
- Arrow functions also have no `arguments` object and cannot be constructors (`new`).

### Default parameters and rest/spread

```js
// File: params.js
function createUser({ name, role = 'user', tags = [] } = {}) {
  return { name, role, tags };
}

console.log(createUser({ name: 'Ankit' }));                    // { name: 'Ankit', role: 'user', tags: [] }
console.log(createUser({ name: 'Priya', role: 'admin' }));     // { name: 'Priya', role: 'admin', tags: [] }
console.log(createUser());                                     // { name: undefined, role: 'user', tags: [] }

// Rest: collect the remaining arguments into a real array.
function sum(...numbers) {
  return numbers.reduce((total, n) => total + n, 0);
}
console.log(sum(1, 2, 3, 4)); // 10

// Spread: expand an array or object.
const base = { role: 'user', active: true };
const admin = { ...base, role: 'admin' };
console.log(admin);                                   // { role: 'admin', active: true }
console.log(Math.max(...[3, 9, 4]));                  // 9
```

The `{ name, role = 'user', tags = [] } = {}` pattern is *exactly* how options objects are
handled in Express middleware and service functions — learn it well.

---

## 3. Destructuring

```js
// File: destructuring.js
// Objects
const user = { id: 42, name: 'Ankit', email: 'a@x.com', role: 'admin' };
const { name, role } = user;
const { name: fullName, city = 'Pune' } = user;       // rename + default

console.log(name, role);        // Ankit admin
console.log(fullName, city);    // Ankit Pune

// Nested
const order = { id: 7, customer: { id: 3, name: 'Priya' }, items: ['a', 'b'] };
const {
  customer: { name: customerName },
  items: [firstItem],
} = order;
console.log(customerName, firstItem);  // Priya a

// Arrays
const [first, second, ...rest] = [10, 20, 30, 40];
console.log(first, second, rest);      // 10 20 [30, 40]

// Function parameters — the standard backend signature style
function logRequest({ method, url, headers }) {
  console.log(`${method} ${url} ua=${headers?.['user-agent'] ?? 'unknown'}`);
}

logRequest({ method: 'GET', url: '/users', headers: { 'user-agent': 'curl/8.7' } });
// GET /users ua=curl/8.7
```

### Swapping and skipping

```js
// File: swap.js
let a = 1;
let b = 2;
[a, b] = [b, a];
console.log(a, b);              // 2 1

const [, , third] = ['x', 'y', 'z'];
console.log(third);             // z
```

Express's `req` object is destructured like this in every real controller you will write:

```js
const { params, query, body, user, headers } = req; // snippet: partial
```

---

## 4. Truthiness, equality and the operators that matter

```js
// File: truthiness.js
const falsy = [false, 0, -0, 0n, '', null, undefined, NaN];
console.log(falsy.filter((v) => !v).length); // 8 — everything else is truthy
console.log(Boolean([]));      // true  ← an empty array is TRUTHY (classic bug)
console.log(Boolean({}));      // true  ← an empty object is TRUTHY
console.log(Boolean('0'));     // true  ← the string "0" is truthy
console.log(Boolean('false')); // true  ← the string "false" is truthy
```

Those last two are the reason query parameters mislead beginners: `req.query.flag` is `"false"`,
which is **truthy**. Convert explicitly: `String(req.query.flag) === 'true'`.

```js
// File: equality.js
// == performs type coercion; === does not. Always prefer ===.
console.log(0 == '');        // true   (both coerced to 0)
console.log(0 === '');       // false
console.log(null == undefined);  // true  ← the ONE useful == case
console.log(null === undefined); // false
console.log('1' == 1);       // true
console.log('1' === 1);      // false
```

Because API data arrives as strings and numbers mixed, `===` prevents an entire category of
bug. The single defensible use of `==` is `x == null`, which is true for both `null` and
`undefined`.

### Nullish coalescing vs logical OR

```js
// File: nullish-vs-or.js
const config = { port: 0, retries: 3, timeout: undefined, limit: null };

console.log(config.port || 3000);      // 3000  ❌ WRONG — 0 is falsy, so the default wins
console.log(config.port ?? 3000);      // 0     ✅ correct — only null/undefined trigger the default

console.log(config.retries || 5);      // 3
console.log(config.timeout ?? 10);     // 10
console.log(config.limit ?? 10);       // 10
```

**Rule: use `??` for defaults, `||` for boolean logic.** `0`, `''` and `false` are legitimate
values (a port, an empty string, a disabled flag) and `||` will silently destroy them.

### Optional chaining and assignment

```js
// File: optional-chaining.js
const res = { status: 200, data: { users: [{ name: 'Ankit' }] } };

console.log(res.data?.users?.[0]?.name);   // Ankit
console.log(res.error?.message);           // undefined — no TypeError
console.log(res.error.message);            // TypeError: Cannot read properties of undefined

// Optional method call
const logger = { info: (msg) => console.log('INFO', msg) };
logger.debug?.('not called');              // no error, simply skipped

// Nullish assignment — only assigns when the left side is null/undefined
const settings = { theme: 'dark' };
settings.theme ??= 'light';                // stays 'dark'
settings.locale ??= 'en-IN';               // assigned
console.log(settings);                     // { theme: 'dark', locale: 'en-IN' }
```

Optional chaining (`?.`) is everywhere in backend code because data from databases,
external APIs and request bodies is routinely missing.

---

## 5. Arrays — the methods you will actually use

```js
// File: arrays.js
const employees = [
  { id: 1, name: 'Ankit', dept: 'Engineering', salary: 90000, active: true },
  { id: 2, name: 'Priya', dept: 'Engineering', salary: 110000, active: true },
  { id: 3, name: 'Ravi', dept: 'Sales', salary: 70000, active: false },
  { id: 4, name: 'Meera', dept: 'Sales', salary: 85000, active: true },
];

// map — transform every element (1:1). Returns a NEW array.
const names = employees.map((e) => e.name);
console.log(names); // [ 'Ankit', 'Priya', 'Ravi', 'Meera' ]

// filter — keep elements matching a predicate
const activeEngineers = employees.filter((e) => e.active && e.dept === 'Engineering');
console.log(activeEngineers.map((e) => e.name)); // [ 'Ankit', 'Priya' ]

// find — first match, or undefined
const priya = employees.find((e) => e.name === 'Priya');
console.log(priya?.id); // 2

// findIndex / indexOf
console.log(employees.findIndex((e) => e.id === 3)); // 2

// some — does ANY element match?  every — do ALL match?
console.log(employees.some((e) => e.salary > 100000));  // true
console.log(employees.every((e) => e.active));          // false

// reduce — fold the array into one value
const payroll = employees
  .filter((e) => e.active)
  .reduce((total, e) => total + e.salary, 0);
console.log(payroll); // 285000

// sort — MUTATES the array, and compares as STRINGS by default!
const nums = [10, 9, 100];
console.log([...nums].sort());                      // [ 10, 100, 9 ]  ← lexicographic
console.log([...nums].sort((a, b) => a - b));       // [ 9, 10, 100 ]  ← numeric
console.log(employees.map((e) => e.salary).sort((a, b) => b - a)); // descending

// flat / flatMap
console.log([[1, 2], [3, [4]]].flat());        // [ 1, 2, 3, [ 4 ] ]
console.log([[1, 2], [3, 4]].flat(2));         // [ 1, 2, 3, 4 ]
console.log(['a b', 'c d'].flatMap((s) => s.split(' '))); // [ 'a', 'b', 'c', 'd' ]

// forEach — side effects only; returns undefined (so: never use it to build an array)
employees.forEach((e) => console.log(e.id));
```

### The `map` + `filter` chain is the backbone of API responses

```js
// File: shape-response.js
const rows = [
  { id: 1, first_name: 'Ankit', password_hash: '$2b$12$…', created_at: new Date('2026-01-01') },
  { id: 2, first_name: 'Priya', password_hash: '$2b$12$…', created_at: new Date('2026-02-01') },
];

// Map database rows → API DTOs. Note how the chain filters, transforms and drops secrets.
const response = rows
  .filter((row) => row.deleted_at == null)
  .map((row) => ({
    id: String(row.id),
    name: row.first_name,
    createdAt: row.created_at.toISOString(),
  }));

console.log(response);
// [ { id: '1', name: 'Ankit', createdAt: '2026-01-01T00:00:00.000Z' },
//   { id: '2', name: 'Priya', createdAt: '2026-02-01T00:00:00.000Z' } ]
```

### `sort` is mutating — the bug you will hit

```js
// File: sort-mutation.js
const original = [3, 1, 2];
const sorted = original.sort((a, b) => a - b);  // ❌ mutates `original` too!

console.log(original);          // [ 1, 2, 3 ]  ← surprising
console.log(sorted === original); // true      ← SAME array reference

// Safe: copy first (spread, slice, or toSorted where available)
const safeOriginal = [3, 1, 2];
const safeSorted = [...safeOriginal].sort((a, b) => a - b);
console.log(safeOriginal);      // [ 3, 1, 2 ]
console.log(safeSorted);        // [ 1, 2, 3 ]
```

Mutating methods to know: `sort`, `reverse`, `push`, `pop`, `shift`, `unshift`, `splice`,
`fill`, `copyWithin`. Non-mutating (safe) methods: `map`, `filter`, `slice`, `concat`,
`flat`, `reduce`, `find`, `some`, `every`, `includes`.

---

## 6. Objects

```js
// File: objects.js
const user = { id: 1, name: 'Ankit' };

// Read: dot vs computed
console.log(user.name);          // Ankit
const key = 'name';
console.log(user[key]);          // Ankit — needed when the key is dynamic

// Safe read of a possibly-missing key
console.log(user.email ?? 'not set');   // not set

// Write / add / delete
user.email = 'a@x.com';
delete user.email;

// Keys, values, entries
const settings = { theme: 'dark', fontSize: 14, notifications: true };
console.log(Object.keys(settings));       // [ 'theme', 'fontSize', 'notifications' ]
console.log(Object.values(settings));     // [ 'dark', 14, true ]
console.log(Object.entries(settings));    // [ [ 'theme', 'dark' ], … ]

// Loop over an object
for (const [k, v] of Object.entries(settings)) {
  console.log(`${k} = ${v}`);
}

// Merging (spread does a SHALLOW merge; nested objects are shared by reference)
const defaults = { port: 3000, host: 'localhost', db: { name: 'app' } };
const config = { ...defaults, port: 4000 };
console.log(config.port, config.db.name);  // 4000 app
console.log(config.db === defaults.db);    // true ← nested objects are NOT copied

// Existence checks — the safe way
console.log(Object.hasOwn(config, 'port'));       // true
console.log(Object.hasOwn(config, 'toString'));   // false (inherited, not own)

// Freeze / seal
Object.freeze(config);                            // no adds, no writes, no deletes
```

### Shallow vs deep copy (matters for request handling)

```js
// File: copy-depth.js
const original = { user: { name: 'Ankit', roles: ['user'] } };

const shallow = { ...original };
shallow.user.name = 'Changed';
console.log(original.user.name);        // 'Changed' ← the nested object was shared!

const deep = structuredClone(original); // real deep copy (built into Node 17+)
deep.user.name = 'Deeply changed';
console.log(original.user.name);        // 'Changed' ← unaffected
console.log(deep.user.roles);           // [ 'user' ] — independent copy
```

`structuredClone` handles Dates, Maps, Sets, Arrays and circular references. It does *not*
clone functions, class prototypes' methods, or DOM nodes.

> **Warning:** never deep-clone a request body with a hand-written recursive merge — that is
> the prototype-pollution vector from [00-web-fundamentals/06](../00-web-fundamentals/06-json-and-data-formats.md).

---

## 7. Classes and OOP (used sparingly but you must read it)

```js
// File: classes.js
class ValidationError extends Error {
  constructor(message, details = []) {
    super(message);
    this.name = 'ValidationError';
    this.details = details;
    this.statusCode = 422;       // our own convention, used by the error middleware
    Error.captureStackTrace(this, this.constructor);  // clean stack in Node
  }
}

class HttpClient {
  #baseUrl;                      // private field — truly inaccessible from outside
  #timeoutMs;

  constructor({ baseUrl, timeoutMs = 5000 }) {
    this.#baseUrl = baseUrl;
    this.#timeoutMs = timeoutMs;
  }

  async get(path) {             // a normal method; `this` works as expected
    const response = await fetch(`${this.#baseUrl}${path}`, {
      signal: AbortSignal.timeout(this.#timeoutMs),
    });
    if (!response.ok) {
      throw new ValidationError(`GET ${path} failed`, [{ status: response.status }]);
    }
    return response.json();
  }

  static version() {
    return '1.0';                // static: called on the class, not an instance
  }
}

const error = new ValidationError('Bad input', [{ field: 'email' }]);
console.log(error instanceof Error, error.statusCode, error.details);
// true 422 [ { field: 'email' } ]

console.log(HttpClient.version());   // 1.0
```

Where classes genuinely earn their place in backend code: **custom error types**, SDK
clients, connection pools, small domain objects with invariants. Where they are usually
overkill: controllers, services, and anything you would otherwise write as three functions.
Modern Node/Express code is mostly functions plus modules — do not force Java-style layering
onto it.

`extends Error` is the single most valuable class in this chapter: every custom error in
your app should look like `ValidationError`.

---

## 8. Closures and higher-order functions

```js
// File: closures.js
// A closure = a function that remembers the scope it was created in.
function createCounter(start = 0) {
  let count = start;                 // captured, and private
  return {
    increment: () => ++count,
    current: () => count,
  };
}

const counter = createCounter(10);
counter.increment();
counter.increment();
console.log(counter.current());      // 12
console.log(counter.count);          // undefined — genuinely private

// Higher-order function: takes/returns a function.
const withRetry = (fn, retries = 3, delayMs = 100) => async (...args) => {
  let lastError;
  for (let attempt = 1; attempt <= retries; attempt += 1) {
    try {
      return await fn(...args);
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, delayMs * attempt));
    }
  }
  throw lastError;
};

// A flaky function, for demonstration.
let calls = 0;
const flaky = async () => {
  calls += 1;
  if (calls < 3) throw new Error('temporary failure');
  return 'succeeded';
};

const resilient = withRetry(flaky);
resilient()
  .then((result) => console.log(result, `after ${calls} calls`)) // succeeded after 3 calls
  .catch((error) => console.error(error.message));
```

**This is exactly how Express middleware factories work:**

```js
// File: middleware-factory.js
const requireRole = (role) => (req, res, next) => {
  // `role` is captured from the outer call — a closure over configuration
  if (req.user?.role !== role) {
    return res.status(403).json({ error: { code: 'FORBIDDEN' } });
  }
  return next();
};

// Used as: router.delete('/users/:id', requireRole('admin'), deleteUser)
```

Understanding closures is what turns `requireRole('admin')` from "magic" into "obviously, the
returned function remembers `role`".

### The classic loop-variable closure trap

```js
// File: closure-trap.js
// ❌ var: all callbacks share ONE binding
for (var i = 0; i < 3; i += 1) {
  setTimeout(() => console.log('var', i), 0);   // var 3, var 3, var 3
}

// ✅ let: each iteration gets its own binding
for (let j = 0; j < 3; j += 1) {
  setTimeout(() => console.log('let', j), 0);   // let 0, let 1, let 2
}
```

---

## 9. `this`, and why backend code mostly avoids it

```js
// File: this-binding.js
const obj = {
  name: 'obj',
  regular() {
    return this.name;
  },
  arrow: () => (globalThis?.name ?? 'no this binding'),
};

const fn = obj.regular;
console.log(obj.regular());   // 'obj' — called as a method
console.log(fn());            // undefined — called standalone, `this` is undefined
console.log(obj.arrow());     // 'no this binding'

// Abusing this is the source of the classic Express bug:
// const router = { handle: function () { this.doStuff(); } };
// setTimeout(router.handle, 100); // `this` is lost → TypeError
```

Because callbacks lose `this`, modern Node code favours **plain functions and modules**. When
you *do* need a method as a callback, bind it once: `this.handle = this.handle.bind(this)`.

---

## 10. Errors: throwing, catching, and propagating

```js
// File: errors.js
// Built-in error types you will meet
const builtins = [
  new Error('generic'),
  new TypeError("Cannot read properties of undefined (reading 'x')"),
  new RangeError('Invalid array length'),
  new SyntaxError('Unexpected token } in JSON'),
  new ReferenceError('x is not defined'),
];
console.log(builtins.map((e) => e.name).join(', '));
// Error, TypeError, RangeError, SyntaxError, ReferenceError

// Always throw Error objects, never strings.
// ❌ throw 'not found'      → no stack trace, no name, cannot be distinguished
// ✅ throw new NotFoundError('…')

// try/catch/finally
function parsePositiveInt(value) {
  try {
    const n = Number(value);
    if (!Number.isInteger(n) || n <= 0) {
      throw new RangeError(`Expected a positive integer, received "${value}"`);
    }
    return n;
  } catch (error) {
    // Re-throw enriched — the standard backend pattern
    throw new Error(`parsePositiveInt failed for "${value}": ${error.message}`, { cause: error });
  } finally {
    // Runs whether or not an error was thrown. Use for cleanup, NOT for returning.
  }
}

try {
  parsePositiveInt('abc');
} catch (error) {
  console.log(error.message);        // parsePositiveInt failed for "abc": Expected a positive integer…
  console.log(error.cause?.name);    // RangeError
}
```

### Custom errors + `cause` = a debuggable backend

```js
// File: custom-errors.js
class AppError extends Error {
  constructor(message, { statusCode = 500, code = 'INTERNAL_ERROR', details, cause } = {}) {
    super(message, { cause });
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.isOperational = true;   // expected error (4xx) vs programmer error (5xx)
    Error.captureStackTrace(this, new.target);
  }
}

class NotFoundError extends AppError {
  constructor(resource, id) {
    super(`${resource} ${id} not found`, { statusCode: 404, code: 'NOT_FOUND' });
  }
}

class ConflictError extends AppError {
  constructor(message, details) {
    super(message, { statusCode: 409, code: 'CONFLICT', details });
  }
}

const error = new NotFoundError('User', 42);
console.log(error.name, error.statusCode, error.code, error.message);
// NotFoundError 404 NOT_FOUND User 42 not found
console.log(error instanceof AppError, error instanceof Error); // true true
```

This hierarchy is the foundation of the error handling we build in
[16 — Error Handling](16-error-handling.md) and
[02-express/08-error-handling.md](../02-express/08-error-handling.md). It is worth learning
properly here.

---

## 11. Iteration: `for...of`, `for...in`, and async loops

```js
// File: iteration.js
const roles = ['user', 'editor', 'admin'];

// for...of — VALUES, and works with `break`/`continue`/`await`
for (const role of roles) {
  if (role === 'editor') continue;
  console.log('role:', role);            // user, admin
}

// for...in — KEYS of an object (and inherited ones! do not use on arrays)
const user = { id: 1, name: 'Ankit' };
for (const key in user) {
  if (Object.hasOwn(user, key)) console.log('key:', key);  // id, name
}

// entries() gives index + value
for (const [index, role] of roles.entries()) {
  console.log(index, role);              // 0 user / 1 editor / 2 admin
}
```

### Sequential vs parallel async loops (a real performance decision)

```js
// File: async-loops.js
const ids = [1, 2, 3, 4, 5];

// A fake async operation that takes 100ms.
const fetchUser = (id) => new Promise((resolve) => setTimeout(() => resolve({ id }), 100));

// ❌ SEQUENTIAL: total ≈ 500ms. Fine when each step depends on the previous one.
async function sequential() {
  const results = [];
  for (const id of ids) {
    results.push(await fetchUser(id));
  }
  return results;
}

// ✅ PARALLEL: total ≈ 100ms. Use when the operations are independent.
async function parallel() {
  return Promise.all(ids.map((id) => fetchUser(id)));
}

// Parallel with partial failure tolerance: never rejects; each result is inspected.
async function parallelSettled() {
  const outcomes = await Promise.allSettled(ids.map((id) => fetchUser(id)));
  return outcomes.map((o) => (o.status === 'fulfilled' ? o.value : { error: o.reason.message }));
}

async function main() {
  console.log('sequential…');
  await sequential();
  console.log('parallel…');
  await parallel();
  console.log('settled…', (await parallelSettled()).length);
}

main();
```

Rule of thumb: **default to parallel; use sequential only when there is a dependency or a
deliberate rate limit.** The classic backend version of this mistake is fetching a user, then
their orders, then each order's items — a hundred sequential round trips ("N+1"), each 20ms.

Important: `array.forEach(async () => {…})` does **not** await. It fires all callbacks and
returns immediately. Use `for...of` with `await`, or `Promise.all(arr.map(...))`.

---

## 12. Getters, setters, and computed keys (nice-to-have but common)

```js
// File: object-extras.js
const configKey = 'databaseUrl';
const env = {
  [`${configKey}`]: 'postgres://localhost/app',   // computed key
  get port() {
    return Number(process.env.PORT ?? 3000);
  },
  set port(value) {
    if (value < 1024 || value > 65535) throw new RangeError('Invalid port');
    process.env.PORT = String(value);
  },
};

console.log(env.databaseUrl);   // postgres://localhost/app
console.log(env.port);          // 3000
env.port = 4000;
console.log(env.port);          // 4000

// Symbol.iterator: make your own object iterable
const range = {
  from: 1,
  to: 4,
  [Symbol.iterator]() {
    let current = this.from;
    const last = this.to;
    return {
      next: () => (current <= last ? { value: current++, done: false } : { value: undefined, done: true }),
    };
  },
};

console.log([...range]);        // [ 1, 2, 3, 4 ]
```

---

## 13. Common mistakes

| Mistake | Example | Fix |
| --- | --- | --- |
| Using `||` for defaults with valid falsy values | `port = process.env.PORT \|\| 3000` breaks on `"0"` | Use `??` |
| Trusting a truthiness check on strings | `if (req.query.active)` is true for `"false"` | Compare explicitly: `=== 'true'` |
| Assuming `==` is fine "because it works" | `'1' == 1` is `true` | Always `===` (except `== null`) |
| Mutating arrays/objects that others share | `arr.sort()` in a helper | Copy first: `[...arr].sort()` |
| Using `map` for side effects | `arr.map(x => console.log(x))` | `forEach` for side effects, `map` for transformation |
| `forEach` with an async callback | `arr.forEach(async x => await save(x))` | `for...of` with `await`, or `Promise.all(arr.map(...))` |
| Deep-merging untrusted input | Prototype pollution | Allowlist keys, use vetted libraries |
| `catch (e) { console.log(e) }` and continue | Swallowing errors hides bugs | Log *and* re-throw, or handle meaningfully |
| Throwing strings | `throw 'error'` | Throw `Error` instances |
| Losing the original error | `throw new Error('failed')` | Pass `{ cause: error }` |
| Rebuilding objects instead of spreading | Verbose and error-prone | `{ ...base, override }` |
| Using `this` in callbacks | `this` is undefined | Arrow functions or `.bind()` |

---

## Exercise 2.1 — Shaping an API response

Given this database result, produce the exact JSON you would send, then compute a summary.

```js
const rows = [
  { id: 1, first_name: 'Ankit', dept: 'Engineering', salary_cents: 9000000, active: 1, joined: new Date('2022-04-01'), password_hash: 'x' },
  { id: 2, first_name: 'Priya', dept: 'Engineering', salary_cents: 11000000, active: 1, joined: new Date('2021-09-15'), password_hash: 'x' },
  { id: 3, first_name: 'Ravi', dept: 'Sales', salary_cents: 7000000, active: 0, joined: new Date('2023-01-10'), password_hash: 'x' },
  { id: 4, first_name: 'Meera', dept: 'Sales', salary_cents: 8500000, active: 1, joined: new Date('2020-06-30'), password_hash: 'x' },
];
```

Requirements: exclude `password_hash`; convert `active` (0/1) to a boolean; convert
`joined` to an ISO string; convert `salary_cents` to `salary` in major units (a number with
two decimals); return only active employees, sorted by most recently joined first; include a
`meta` object with `count`, `totalPayroll`, and the average salary rounded to two decimals.

<details>
<summary>Solution</summary>

```js
// File: exercise-2-1.js
const rows = [
  { id: 1, first_name: 'Ankit', dept: 'Engineering', salary_cents: 9000000, active: 1, joined: new Date('2022-04-01'), password_hash: 'x' },
  { id: 2, first_name: 'Priya', dept: 'Engineering', salary_cents: 11000000, active: 1, joined: new Date('2021-09-15'), password_hash: 'x' },
  { id: 3, first_name: 'Ravi', dept: 'Sales', salary_cents: 7000000, active: 0, joined: new Date('2023-01-10'), password_hash: 'x' },
  { id: 4, first_name: 'Meera', dept: 'Sales', salary_cents: 8500000, active: 1, joined: new Date('2020-06-30'), password_hash: 'x' },
];

const toEmployeeDto = (row) => ({
  id: String(row.id),                                  // ids as strings: future-proof
  name: row.first_name,
  department: row.dept,
  salary: Number((row.salary_cents / 100).toFixed(2)),  // cents → major units
  active: Boolean(row.active),                          // 0/1 → boolean
  joinedAt: row.joined.toISOString(),                   // Date → ISO 8601 UTC string
  // password_hash is deliberately absent: allowlist, not blocklist
});

const round2 = (n) => Number(n.toFixed(2));

const activeEmployees = rows
  .filter((row) => row.active === 1)
  .sort((a, b) => b.joined - a.joined)   // most recent first — sort(a,b) returns a number
  .map(toEmployeeDto);

const totalSalary = activeEmployees.reduce((sum, e) => sum + e.salary, 0);

const payload = {
  data: activeEmployees,
  meta: {
    count: activeEmployees.length,
    totalPayroll: round2(totalSalary),
    averageSalary: round2(totalSalary / activeEmployees.length),
  },
};

console.log(JSON.stringify(payload, null, 2));
```

Output:

```json
{
  "data": [
    { "id": "1", "name": "Ankit", "department": "Engineering", "salary": 90000, "active": true, "joinedAt": "2022-04-01T00:00:00.000Z" },
    { "id": "2", "name": "Priya", "department": "Engineering", "salary": 110000, "active": true, "joinedAt": "2021-09-15T00:00:00.000Z" },
    { "id": "4", "name": "Meera", "department": "Sales", "salary": 85000, "active": true, "joinedAt": "2020-06-30T00:00:00.000Z" }
  ],
  "meta": { "count": 3, "totalPayroll": 285000, "averageSalary": 95000 }
}
```

Ravi is correctly absent (`active: 0`), and the order is most-recently-joined first.

### Why `b.joined - a.joined` works here — and when it does not

Subtracting two `Date` objects is legal JavaScript: the `-` operator coerces each operand to
a number (milliseconds since the epoch), so you get a plain number back and the comparator
behaves:

```js
new Date('2022-04-01') - new Date('2020-06-30'); // 56505600000 — a positive number
```

That works, but it is easy to misread and it **silently breaks the moment the value is a
string**, which is exactly what you get after `JSON.parse` or when reading from a database
driver that returns text:

```js
'2022-04-01' - '2020-06-30'; // NaN → the comparator returns NaN → the sort is a no-op
```

An array sorted with a comparator that returns `NaN` is left in an arbitrary order and **no
error is raised**. That is the real trap: a wrong comparator fails silently.

Write the intention-revealing version instead:

```js
// Both values are Dates:
const byJoinDate = [...employees].sort(
  (a, b) => b.joined.getTime() - a.joined.getTime()
);

// The value might be a string (after JSON.parse, or from a TEXT column):
const byJoinedString = [...rowsFromJson].sort(
  (a, b) => new Date(b.joined).getTime() - new Date(a.joined).getTime()
);

console.log(byJoinDate[0]?.name, byJoinedString[0]?.first_name);
```

Rule: after any sort that matters — especially one backing a paginated API — print the first
few results and confirm the order. Silent mis-sorting produces duplicates and missing rows
across pages, which is a genuinely hard bug to diagnose later.

</details>

## Exercise 2.2 — Fix the async loop

This function is supposed to send a welcome email to each new user and report how many
succeeded. Find every bug.

```js
async function notifyUsers(userIds) {
  let sent = 0;
  userIds.forEach(async (id) => {
    const user = await getUser(id);
    await sendEmail(user.email);
    sent += 1;
  });
  return sent;
}
```

<details>
<summary>Solution</summary>

**Bugs:**

1. **`forEach` does not await.** `notifyUsers` returns `sent` immediately — almost always
   `0` — while the emails are still being sent. The returned value is meaningless.
2. **Unhandled rejections.** If `getUser` or `sendEmail` throws, the error escapes into an
   unhandled promise rejection (which crashes modern Node in some configurations) and is not
   attributed to `notifyUsers`.
3. **`sent` is a shared mutable counter** being incremented from several concurrent async
   callbacks. It happens to work for a simple `+= 1` on one thread, but it is an unnecessary
   shared-state pattern.
4. **No concurrency limit and no error isolation.** A single failing user aborts nothing
   (because nothing is awaited), yet also produces no report of who failed.
5. **Silent partial failure.** The caller cannot tell *which* emails failed, so it cannot
   retry them.

**Fixed version:**

```js
// File: exercise-2-2.js
async function getUser(id) {
  if (id === 3) throw new Error(`user ${id} not found`);
  return { id, email: `user${id}@example.com` };
}

async function sendEmail(email) {
  await new Promise((resolve) => setTimeout(resolve, 10));
  return { delivered: true, email };
}

async function notifyUsers(userIds, { concurrency = 5 } = {}) {
  const results = [];

  // Process in small batches: parallel enough to be fast, bounded enough to be safe.
  for (let index = 0; index < userIds.length; index += concurrency) {
    const batch = userIds.slice(index, index + concurrency);

    const batchResults = await Promise.allSettled(
      batch.map(async (id) => {
        const user = await getUser(id);
        await sendEmail(user.email);
        return { id, status: 'sent' };
      })
    );

    batchResults.forEach((outcome, offset) => {
      const id = batch[offset];
      results.push(
        outcome.status === 'fulfilled'
          ? outcome.value
          : { id, status: 'failed', reason: outcome.reason.message }
      );
    });
  }

  return {
    sent: results.filter((r) => r.status === 'sent').length,
    failed: results.filter((r) => r.status === 'failed'),
    results,
  };
}

notifyUsers([1, 2, 3, 4, 5, 6, 7])
  .then((report) => console.log(JSON.stringify(report, null, 2)))
  .catch((error) => console.error('Unexpected failure:', error.message));
```

Expected output shape:

```json
{
  "sent": 6,
  "failed": [ { "id": 3, "status": "failed", "reason": "user 3 not found" } ],
  "results": [ … ]
}
```

**Why each fix matters:**

- `Promise.allSettled` gives **partial-failure tolerance** — one bad user does not lose the
  other six emails.
- Batching bounds concurrency, so 10,000 users do not open 10,000 SMTP connections at once
  (real providers rate-limit and block you for that).
- Returning a structured report lets the caller retry only the failures.
- `await` in the outer loop means the function's promise resolves when the work is truly done.

The general lesson: **`forEach` + `async` is always a bug. Use `for...of` with `await` for
sequential work, `Promise.all`/`allSettled` for parallel work.**

</details>

---

## What's next

You have the language. Now the runtime's own tools: the global objects, the module systems,
and the process lifecycle that every Node program lives inside.

→ [03 — Node.js Basics](03-nodejs-basics.md)
