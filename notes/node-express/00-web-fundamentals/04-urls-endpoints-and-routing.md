# 04 — URLs, Endpoints and Routing

> **Where this fits:** HTTP defines the _shape_ of messages. This chapter is about the _address_ inside them: what each piece of a URL means, where parameters belong, and how a request URL turns into a specific function in your code. That last step — routing — is the heart of Express, and doing it well is 80% of API design.

***

## 1. Anatomy of a URL

```
 https://api.shop.example.com:443/v1/users/42/reviews?sort=-createdAt&page=2&limit=10#latest
 └─┬─┘   └────────┬─────────┘└┬┘└───────┬────────┘└─────────┬─────────┘ └────┬────┘
 scheme        host         port      path            query string      fragment

┌───────────────────────────────────────────┐
│ scheme  → https         how to communicate (http/https/ws/file)
│ userinfo→ (none)        user:password@ — do NOT use; credentials in URLs leak
│ host    → api.shop.example.com   which server (DNS name)
│ port    → 443           which program (omitted: 80 for http, 443 for https)
│ path    → /v1/users/42/reviews   which resource, hierarchical
│ query   → ?sort=-createdAt&page=2   how to filter/sort/paginate
│ fragment→ #latest       client-side only — NEVER sent to the server
└───────────────────────────────────────────┘
```

Two facts that surprise beginners:

1. **The fragment is never sent.** `#latest` is for the browser/app only. A backend can never see it. If your API needs that information, it must be a query parameter.
2. **The query string is a bag of strings.** `?page=2` gives your backend the _string_ `"2"`, not the number `2`. `?page=abc` also arrives happily. **Everything from a URL is untrusted text** and must be validated and converted ([02-express/12-validation.md](../02-express/12-validation.md)).

### Percent-encoding

URLs can only contain a limited set of characters. Others are escaped as `%XX`:

| Character | Encoded                         | When it happens                          |
| --------- | ------------------------------- | ---------------------------------------- |
| space     | `%20` (or `+` in query strings) | `?q=hello world`                         |
| `/`       | `%2F`                           | a search term containing a slash         |
| `?`       | `%3F`                           | a search term containing a question mark |
| `&`       | `%26`                           | a search term containing an ampersand    |
| `é`       | `%C3%A9`                        | non-ASCII text                           |

```js
// In Node.js, use the standard globals — do not hand-roll this.
const term = 'node & express/guides';
console.log(encodeURIComponent(term)); // node%20%26%20express%2Fguides
console.log(decodeURIComponent('node%20%26%20express%2Fguides')); // node & express/guides

// Express already decodes percent-encoding for you:
// GET /search?q=node%20express  →  req.query.q === 'node express'
```

Careful: `encodeURIComponent` escapes `/`, `?`, `&`, `=` — which is what you want for a _single value_. `encodeURI` leaves structural characters intact, which is what you want for a _complete URL_.

***

## 2. Path vs query vs body — where does data go?

This is the single most useful table in this chapter. Every API review comment about "where should this go?" reduces to it.

| Data                   | Put it in                    | Example                            | Why                                            |
| ---------------------- | ---------------------------- | ---------------------------------- | ---------------------------------------------- |
| Identity of a resource | **Path**                     | `GET /users/42`                    | It is part of _which_ thing you are addressing |
| A nested relationship  | **Path**                     | `GET /users/42/orders`             | Reads as a hierarchy                           |
| Filters / search       | **Query**                    | `?status=active&role=admin`        | Optional; narrows a collection                 |
| Sorting / pagination   | **Query**                    | `?sort=-createdAt&page=3&limit=20` | Optional; presentation of a collection         |
| Fields to include      | **Query**                    | `?fields=id,name,email`            | Optional; response shaping                     |
| Data to create/update  | **Body**                     | `POST /users` with `{...}`         | It is the payload, not the address             |
| Credentials            | **Header** (`Authorization`) | `Bearer eyJ…`                      | Headers are the protocol's metadata channel    |
| Client state (session) | **Cookie**                   | `session=…`                        | Automatically attached by the browser          |
| Cache version          | **Query**                    | `?v=2`                             | Cache busting for static assets                |

**Anti-patterns to avoid:**

```
❌ POST /users?name=Ankit&email=a@x.com     → data belongs in the body
❌ GET  /users/42/delete                    → verb in URL; use DELETE /users/42
❌ GET  /users?id=42                        → id is identity; belongs in the path
❌ GET  /users/42?password=secret           → credentials in a URL get logged everywhere
❌ GET  /getAllUsersPage2SortedByName       → the endpoint is doing five jobs
```

A URL ends up in browser history, server access logs, proxy logs, and `Referer` headers. **Anything in a query string should be considered public forever.**

***

## 3. What is an "endpoint"?

An **endpoint** is a **method + path** pair that your API accepts:

```
GET    /api/v1/users          ← one endpoint
POST   /api/v1/users          ← a different endpoint (same path!)
GET    /api/v1/users/:id      ← another
```

Two things follow from that definition:

1. **Same path, different method = different endpoints.** `POST /users` and `GET /users` are unrelated pieces of code.
2. **An endpoint is a contract.** Once clients depend on it, changing its path, its response shape, or its status codes is a breaking change.

### An endpoint's full contract should specify

| Aspect              | Example                                                                |
| ------------------- | ---------------------------------------------------------------------- |
| Method + path       | `POST /api/v1/users`                                                   |
| Auth required?      | No (public registration)                                               |
| Request body schema | `{ name: string, email: string, password: string }`                    |
| Validation rules    | email format, password ≥ 8 chars, name ≤ 100 chars                     |
| Success response    | `201` + `{ id, name, email, createdAt }` — **never the password hash** |
| Error responses     | `422` validation, `409` duplicate email                                |
| Rate limit          | 5 requests/hour/IP                                                     |
| Idempotency         | not idempotent                                                         |

Writing that table _before_ coding is what separates API design from "typing code until it works". In larger teams this document becomes an OpenAPI spec ([02-express/21-complete-express-project.md](../02-express/21-complete-express-project.md)).

***

## 4. Routing: from a URL to a function

**Routing** is the process of matching an incoming `(method, path)` pair to a handler function.

```
Incoming:  GET /api/v1/users/42/orders?status=paid

Step 1 — match method + path pattern:
   Registered routes on the app:
     GET  /api/v1/users            → listUsers
     GET  /api/v1/users/:id        → getUser
     GET  /api/v1/users/:id/orders → getUserOrders     ← MATCH
     POST /api/v1/users            → createUser

Step 2 — extract path parameters:
   :id = "42"

Step 3 — parse the query string:
   req.query = { status: "paid" }

Step 4 — call the handler:
   getUserOrders(req, res)

Step 5 — the handler does the work and ends the response.
```

### Static vs dynamic segments

```
/api/v1/users/42        → dynamic segment (:id matches "42", "abc", anything)
/api/v1/users/me        → static segment — always wins over :id if both are registered
```

**Order matters.** In Express, routes are evaluated in the order they are declared, so `/users/me` must be registered _before_ `/users/:id`, otherwise `me` is captured as an id. This trips up nearly everyone once.

```js
// File: src/routes/userRoutes.js
router.get('/me', requireAuth, getMyProfile);   // must come first
router.get('/:id', getUserById);                // otherwise "me" is treated as an id
```

### Route parameters vs query parameters (side by side)

```
GET /api/v1/users/42/orders?status=paid&sort=-total&page=2

req.params → { id: "42" }                     ← required, structural
req.query  → { status: "paid", sort: "-total", page: "2" }   ← optional, filters
req.body   → {} (undefined for GET)           ← payload
```

|           | Path parameters                            | Query parameters                                   |
| --------- | ------------------------------------------ | -------------------------------------------------- |
| Purpose   | Identify a resource                        | Filter/sort/paginate                               |
| Required? | Yes — the route will not match without it  | No                                                 |
| Caching   | Part of the cache key                      | Part of the cache key                              |
| Logs      | Visible in access logs and metrics by path | Must be logged explicitly                          |
| Type      | Always a string                            | Always a string (or array/object with `qs` syntax) |
| Example   | `/orders/42`                               | `/orders?userId=42`                                |

A useful rule: _if removing the parameter changes which resource you are talking about, it is a path parameter; if it changes which parts of a collection you see, it is a query parameter._

***

## 5. Designing a readable, consistent API surface

Pick these conventions once, write them in a `CONTRIBUTING.md`/`README.md`, and never argue about them again:

| Decision                 | Recommendation                                       | Rationale                                                                                       |
| ------------------------ | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Case                     | `kebab-case` for multi-word paths (`/user-profiles`) | Consistent with domain names; avoids case-sensitivity bugs                                      |
| Plural nouns             | `/users`, not `/user`                                | Collections read consistently: `/users/42`                                                      |
| No verbs                 | `POST /orders` not `/createOrder`                    | The method is the verb                                                                          |
| No file extensions       | `/users` not `/users.json`                           | Use `Accept` for format negotiation                                                             |
| Nesting depth ≤ 2        | `/users/42/orders` ✅, `/users/42/orders/7/items/3` ❌ | Deep paths get ambiguous and brittle — use a flat route for the deep resource: `/order-items/3` |
| Trailing slash           | Treat as identical                                   | Avoids duplicate-content and confusing 404s                                                     |
| Version prefix           | `/api/v1/...`                                        | See §6                                                                                          |
| Consistent pluralisation | Never mix `/users` and `/product`                    | Predictability is the whole game                                                                |
| Query param naming       | `camelCase` (`?pageSize=10`)                         | Matches JSON bodies                                                                             |

### Nesting: when to nest and when to flatten

```
Nested  — when the child cannot exist without the parent, and you always
          ask for it in the context of the parent:

   GET  /users/42/orders            "orders belonging to user 42"
   POST /users/42/orders            "create an order for user 42"

Flatten — when the child has its own identity and is looked up directly:

   GET  /orders/987                 "fetch this order, whoever owns it"
   PATCH /orders/987
```

Both are usually correct _together_: create via the nested route, operate on the resource via the flat route. This is standard practice (GitHub, Stripe, and most large APIs do it).

### Actions that are not CRUD

Not everything is a resource. For genuinely non-CRUD operations, a controlled verb is acceptable — the alternatives are worse:

```
POST /orders/987/cancel        ✅ action on a resource, scoped and readable
POST /users/42/password-reset  ✅
PUT  /orders/987/cancel        ❌ reads like "replace with cancelled"
POST /cancelOrder              ❌ ambiguous scope, no resource
```

The signal: if you _must_ express a state transition or a command, hang it off the resource it affects and use `POST`.

***

## 6. API versioning

You will have to change something breaking eventually: rename a field, remove an endpoint, change a type. Versioning is how existing clients survive that.

| Strategy           | Example                                | Pros                                     | Cons                                                              |
| ------------------ | -------------------------------------- | ---------------------------------------- | ----------------------------------------------------------------- |
| **URI versioning** | `/api/v1/users`                        | Obvious, cache-friendly, easy in Express | "Impure" REST (the URL should identify a resource, not a version) |
| Header versioning  | `Accept: application/vnd.shop.v2+json` | Clean URLs                               | Hard to test in a browser, easy to forget                         |
| Custom header      | `X-API-Version: 2`                     | Simple                                   | Non-standard                                                      |
| Query param        | `?version=2`                           | Trivial                                  | Pollutes every cache key and URL                                  |
| No versioning      | change in place                        | Simplest                                 | Breaks every client                                               |

**Recommendation: URI versioning (`/api/v1/…`)** for public APIs. It is the least surprising, works in `curl` and browsers, and is trivial to implement with Express routers. Header versioning is defensible for internal APIs where clients are under your control.

### Breaking vs non-breaking changes

| Change                                         | Breaking?                                   |
| ---------------------------------------------- | ------------------------------------------- |
| Add a new optional field to a response         | ❌ No (clients should ignore unknown fields) |
| Add a new optional query parameter             | ❌ No                                        |
| Add a new endpoint                             | ❌ No                                        |
| Add a new **required** field to a request body | ✅ Yes                                       |
| Rename or remove a response field              | ✅ Yes                                       |
| Change a field's type (`"42"` → `42`)          | ✅ Yes                                       |
| Change validation to be stricter               | ✅ Yes for previously-valid clients          |
| Change a status code (`200` → `201`)           | ✅ Usually yes — clients branch on codes     |

> **Practical tip:** additive changes plus a "clients must ignore unknown fields" rule let many teams evolve an API for years without ever cutting a v2.

***

## 7. Routing in Express (a taste)

You will do this in depth in [02-express/03-routing.md](../02-express/03-routing.md), but here is the shape so the rest of this chapter is concrete:

```js
// File: src/routes/users.js
import { Router } from 'express';
import {
  listUsers,
  getUserById,
  createUser,
  updateUser,
  deleteUser,
} from '../controllers/userController.js';

const router = Router();

router.get('/', listUsers);        // GET    /api/v1/users
router.post('/', createUser);      // POST   /api/v1/users
router.get('/:id', getUserById);   // GET    /api/v1/users/:id
router.patch('/:id', updateUser);  // PATCH  /api/v1/users/:id
router.delete('/:id', deleteUser); // DELETE /api/v1/users/:id

export default router;
```

and it is mounted with a version prefix:

```js
// File: src/app.js (fragment)
app.use('/api/v1/users', userRoutes);
app.use('/api/v1/orders', orderRoutes);
```

So `GET /api/v1/users/42` travels: `app` → `/api/v1/users` prefix matches → `userRoutes` → `/:id` matches → `getUserById`.

### Wildcards, patterns and 404s

```js
// Catch-all 404 — registered LAST. Any request that matched nothing ends here.
app.use((req, res) => {
  res.status(404).json({ error: { message: `Route ${req.method} ${req.originalUrl} not found` } });
});
```

In Express 5, wildcard strings must be named — `app.use('*', handler)` (the Express 4 idiom) **throws**; use `app.use((req, res) => …)` with no path, or a named wildcard like `'/*splat'`. This is one of the most common Express 4 → 5 migration errors.

***

## 8. Common mistakes

| Mistake                                       | Consequence                                                   | Fix                                                          |
| --------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------ |
| `/users/:id` registered before `/users/me`    | `/users/me` hits the id handler and 404s                      | Declare static routes first                                  |
| Reading `req.query.page` without parsing      | `"2" + 1 === "21"`                                            | `const page = Number(req.query.page) \|\| 1` (and validate!) |
| Trusting `req.params.id` as an ObjectId       | `CastError: Cast to ObjectId failed` → 500                    | Validate the id format, return `400`                         |
| Deep nesting (`/a/1/b/2/c/3/d`)               | Unreadable, hard to authorise, easy to break                  | Flatten beyond two levels                                    |
| Verbs in URLs                                 | Two conventions in the same API                               | Nouns + HTTP methods                                         |
| No global 404 handler                         | Express returns HTML "Cannot GET /x" to JSON clients          | Add a JSON 404 at the end                                    |
| Versioning by hand in every route (`if (v2)`) | Spaghetti                                                     | Mount separate routers per version                           |
| Putting secrets in query strings              | They end up in logs, history and `Referer`                    | Headers or body only                                         |
| Case-inconsistent paths (`/Users/42`)         | Two cache entries, confusing errors                           | Lowercase everything                                         |
| Returning arrays wrapped in nothing           | Cannot add pagination metadata later without breaking clients | Always return an object: `{ data, meta }`                    |

That last point deserves emphasis — decide _now_ that a list endpoint returns:

```json
{
  "data": [ { "id": "42", "name": "Ankit" } ],
  "meta": { "page": 1, "limit": 20, "total": 137, "totalPages": 7 }
}
```

Adding `meta` later to a bare array is a breaking change; including it from day one is free.

***

## Exercise 4.1 — Design the routes

A library system needs an API for **books**, **members**, and **loans** (a member borrowing a book). Design the full endpoint list for v1, including methods, paths, status codes, and where each piece of data goes. Cover: list with search/filter/paging, read one, create, update, delete, borrow a book, return a book, and "list a member's active loans".

<details>

<summary>Solution</summary>

```
BOOKS
GET    /api/v1/books                      200  ?q=&author=&available=&sort=-title&page=1&limit=20
GET    /api/v1/books/42                   200  → 404 if missing
POST   /api/v1/books                      201  body: {title, author, isbn, copies}  Location: /api/v1/books/42
PATCH  /api/v1/books/42                   200  body: partial fields
DELETE /api/v1/books/42                   204  → 409 if active loans exist

MEMBERS
GET    /api/v1/members                    200  ?q=&status=active&page=1&limit=20
GET    /api/v1/members/7                  200
POST   /api/v1/members                    201  body: {name, email, phone}
PATCH  /api/v1/members/7                  200
DELETE /api/v1/members/7                  204  → 409 if active loans

LOANS
GET    /api/v1/loans                      200  ?memberId=&bookId=&status=active&dueBefore=
GET    /api/v1/loans/123                  200
POST   /api/v1/loans                      201  body: {bookId, memberId}          ← borrow
PATCH  /api/v1/loans/123                  200  body: {status: "returned"}        ← return
GET    /api/v1/members/7/loans            200  ?status=active                    ← nested read

NON-CRUD ACTIONS (deliberately verbs, scoped to a resource)
POST   /api/v1/loans/123/renew            200  extends dueDate
POST   /api/v1/members/7/suspend          200  body: {reason}
```

**Reasoning for the interesting decisions:**

* **Borrow is `POST /loans`, not `POST /books/42/borrow`.** Borrowing _creates a loan resource_ — a real noun with its own id, due date and history. Modelling the action as a resource creation means you get `GET /loans`, audit trails and cancellation for free.
* **Return is `PATCH /loans/123` with `{"status":"returned"}`,** not `DELETE /loans/123`. The loan did happen; history must survive. Only genuinely destructive operations use `DELETE`.
* **`GET /members/7/loans` is nested** because loans are always viewed in the context of a member; the flat `/loans?memberId=7` also exists for admin views. Offering both is normal.
* **`409 Conflict` on delete** because a book with active loans cannot be removed — the state conflicts with the request.
* **`POST /loans/123/renew`** is a state transition, so a controlled verb hangs off the resource. `PUT /loans/123/renew` would be wrong: it implies replacing the loan with the string "renew".
* Every list endpoint returns `{ data, meta }` so pagination metadata can be added without breaking clients.

</details>

## Exercise 4.2 — Find the routing bug

```js
router.get('/:id', getUserById);
router.get('/search', searchUsers);
router.get('/me', getMe);
```

A request to `GET /users/search?q=ankit` returns `400 Invalid user id`. Why, and how do you fix it?

<details>

<summary>Solution</summary>

Express evaluates routes **in declaration order** and `/:id` is declared first, so `/search` matches `/:id` with `req.params.id === "search"`. The id validation then rejects it as a malformed ObjectId and returns `400`.

**Fix — most specific first:**

```js
router.get('/search', searchUsers); // static
router.get('/me', getMe);           // static
router.get('/:id', getUserById);    // dynamic param last
```

The general rule: **static segments before dynamic segments.** The same trap exists for `/users/export.csv`, `/users/count`, and anything else that is not an id.

A defensive companion habit: validate the id shape _inside_ the handler and return `400` with a clear message, so a mistake like this shows up as "not a valid id" instead of a `CastError` 500.

</details>

***

## What's next

You can address resources and route requests. The remaining piece of the API picture is the _style_ — how to structure resources, responses, errors and pagination so the whole API feels like one product instead of forty random endpoints.

→ [05 — REST and API Design](05-rest-and-api-design.md)
