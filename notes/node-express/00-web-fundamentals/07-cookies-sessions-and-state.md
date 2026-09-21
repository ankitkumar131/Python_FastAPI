# 07 — Cookies, Sessions and State

> **Where this fits:** HTTP is stateless — the server forgets you between requests. But "log in once, stay logged in" requires memory. This chapter explains the three ways backends create the illusion of a continuous session (cookies, server-side sessions, and tokens), why browsers have their own rules about cookies, and how CORS fits in. This is the conceptual foundation for 04-authentication _(not available in this published source revision)_.

***

## 1. The problem, stated precisely

```
Request 1:  POST /api/v1/login      { email, password }
Response 1: 200 OK                  "you are Ankit"

Request 2:  GET /api/v1/orders      ← who is asking? The server has no idea.
```

HTTP itself gives the server no memory. Every request is a stranger. A **session mechanism** is any technique that lets request 2 prove it is the same client as request 1.

There are exactly three general strategies:

| Strategy                | Where the state lives                          | Client holds                  | Revocable?                   |
| ----------------------- | ---------------------------------------------- | ----------------------------- | ---------------------------- |
| **Server-side session** | Your database/Redis                            | An opaque session id (cookie) | ✅ Instantly                  |
| **Token (JWT)**         | Nowhere (stateless) — the token _is_ the state | A signed token                | ⚠️ Only with extra machinery |
| **Hybrid**              | Short-lived JWT + server-side refresh token    | Both                          | ✅ (via the refresh token)    |

All three answer the same question — _"who is this?"_ — with different trade-offs. Real systems often combine them (that combination is the "hybrid" row, and it is what we implement in 04-authentication/04-access-refresh-tokens.md _(not available in this published source revision)_).

***

## 2. Cookies

A **cookie** is a small piece of text (max \~4 KB) that the **browser stores** and **automatically re-sends** with every matching request. That automation is the whole point: it is what makes "stay logged in" possible without the frontend JavaScript doing anything.

### The flow

```
1. Client  →  POST /login { email, password }

2. Server  →  200 OK
              Set-Cookie: sessionId=abc123; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=86400

3. Browser stores it against the domain api.example.com

4. Client  →  GET /orders
              Cookie: sessionId=abc123          ← added automatically, no JS involved

5. Server looks up session "abc123", finds the user, authorises the request.
```

### Cookie attributes, and why each one matters

| Attribute                     | Meaning                                                    | Backend security impact                                                    |
| ----------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------- |
| `HttpOnly`                    | JavaScript (`document.cookie`) cannot read it              | **Blocks XSS token theft** — one of the most important lines of defence    |
| `Secure`                      | Only sent over HTTPS                                       | Without it, the cookie leaks on any plain-HTTP request                     |
| `SameSite=Strict`             | Not sent on any cross-site request                         | Strongest CSRF protection; may break external links into your app          |
| `SameSite=Lax`                | Sent on top-level GET navigations, not on cross-site POSTs | Good default for most apps                                                 |
| `SameSite=None`               | Always sent cross-site                                     | **Requires `Secure`**; needed for third-party embeds and cross-domain SPAs |
| `Path=/`                      | Which paths receive the cookie                             | Limit to `/api` to reduce exposure                                         |
| `Domain=example.com`          | Also sent to subdomains                                    | Prefer omitting it (host-only cookie)                                      |
| `Max-Age=86400` / `Expires=…` | Lifetime in seconds / absolute date                        | Session cookies (neither set) die with the browser                         |
| `__Host-` prefix              | Name prefix that enforces `Secure`, no `Domain`, `Path=/`  | Strong guarantee against subdomain cookie injection                        |

```js
// File: set-cookie.example.js — what the values mean in code (Express)
// SESSION COOKIE: readable only by the server, sent on same-site requests.
res.cookie('sessionId', sessionId, {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production', // HTTPS only in production
  sameSite: 'lax',
  maxAge: 1000 * 60 * 60 * 24,                   // 24 hours in ms
  path: '/',
});

// CSRF DOUBLE-SUBMIT COOKIE: deliberately readable by JS so the SPA can echo it.
res.cookie('csrfToken', csrfToken, {
  httpOnly: false,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax',
  path: '/',
});
```

### Cookies and CSRF

Because the browser attaches cookies automatically, a page on `evil.com` can make the user's browser send a request to `bank.com` **with the user's cookies attached** — the user's browser cannot tell that the request was not intentional. That is **CSRF (Cross-Site Request Forgery)**.

The defences, in order of preference:

1. **`SameSite=Lax` or `Strict`** on session cookies — cheapest and effective for most apps.
2. **A CSRF token** for state-changing requests (double-submit cookie, or a token tied to the session) — needed when you must use `SameSite=None`.
3. **Check `Origin`/`Referer`** headers on unsafe methods.
4. **Never use `GET` for state changes** — a `<img src="…/delete-account">` cannot send a POST body, but it can trigger a GET.

Note that **Bearer-token APIs are largely immune to CSRF**, because the token is not attached automatically — an attacker's page cannot read it from local storage. That is one genuine advantage of tokens, and it comes with the XSS exposure of localStorage as a counterweight.

### Reading and writing cookies without a library

```js
// File: cookie-raw.mjs
// Cookies arrive as one header: "a=1; b=2; sessionId=abc123"
function parseCookieHeader(header = '') {
  return header.split(';').reduce((cookies, pair) => {
    const index = pair.indexOf('=');
    if (index === -1) return cookies;
    const key = pair.slice(0, index).trim();
    const value = pair.slice(index + 1).trim();
    if (key) cookies[key] = decodeURIComponent(value);
    return cookies;
  }, {});
}

console.log(parseCookieHeader('a=1; b=2; sessionId=abc123'));
// { a: '1', b: '2', sessionId: 'abc123' }
```

(Express ships `cookie-parser` — but note that for _reading_ cookies Express 5 is enough once `cookie-parser` is installed; for _writing_ you need no library at all, `res.cookie()` is built in.)

***

## 3. Server-side sessions

With sessions, the cookie holds only an opaque **session id**. The real data (user id, roles, cart, flash messages) lives on the server.

```
Browser                        Server                     Store (Redis/MySQL)
   │  POST /login {…}  ──────────▶ verify password
   │                              create session { userId, roles, expiresAt }
   │                              sessionId = crypto.randomUUID()  ─────▶ SET session:abc123 …
   │  ◀── Set-Cookie: sessionId=abc123; HttpOnly … ───
   │
   │  GET /orders  ──────────────▶ read cookie, look up session  ─────▶ GET session:abc123 → hit
   │  ◀── 200 OK orders ──────────
```

**Pros**

* **Instant revocation**: delete the session record and the user is logged out _now_ — this is the one thing JWTs cannot do without extra infrastructure.
* **Small cookies**: the client holds an id, not a payload.
* **Secrets stay server-side**: roles, permissions and cart contents never leave your servers, so they cannot be tampered with.
* **Simple mental model**: it is just a database lookup.

**Cons**

* **Stateful**: every request needs a lookup, so you need a fast store (Redis is the standard choice).
* **Scaling**: with multiple servers, sessions must be shared (Redis) or sticky (load balancer affinity). Sticky sessions are a smell — use a shared store.
* **Not great for mobile/third-party clients**: cookies are a browser mechanism; a mobile app has to implement its own cookie jar.
* **Needs CSRF protection** (because the cookie is sent automatically).

### A minimal session implementation using Redis

```js
// File: redis-session.example.js — conceptual sketch (run this after the Redis chapter)
import { randomUUID } from 'node:crypto';

const SESSION_TTL_SECONDS = 60 * 60 * 24; // 24h

export function createSessionStore(redis) {
  return {
    async create(userId, roles) {
      const sessionId = randomUUID();
      await redis.set(`session:${sessionId}`, JSON.stringify({ userId, roles }), {
        EX: SESSION_TTL_SECONDS,
      });
      return sessionId;
    },

    async read(sessionId) {
      const raw = await redis.get(`session:${sessionId}`);
      return raw ? JSON.parse(raw) : null;
    },

    async destroy(sessionId) {
      await redis.del(`session:${sessionId}`);
    },

    // "Sliding" sessions: refresh the TTL on activity so active users stay logged in.
    async touch(sessionId) {
      await redis.expire(`session:${sessionId}`, SESSION_TTL_SECONDS);
    },
  };
}

export function sessionMiddleware(store) {
  return async function attachSession(req, res, next) {
    const sessionId = req.cookies?.sessionId;
    req.session = sessionId ? await store.read(sessionId) : null;
    if (sessionId) await store.touch(sessionId);
    next();
  };
}
```

(For production, use a battle-tested implementation such as `express-session` with a Redis store rather than rolling your own — the sketch above exists to show the mechanics, not to ship.)

***

## 4. Tokens and statelessness

Instead of storing a session, the server issues a **signed token** containing the claims. The client sends it back on every request (usually in the `Authorization` header), and the server **verifies the signature** — no database lookup needed.

```
Browser                                  Server
   │  POST /login {…}  ──────────────────▶ verify password
   │                                      sign JWT { sub: userId, role, exp }
   │  ◀── { accessToken: "eyJhbGci…" } ───
   │     (stored in memory / localStorage / a cookie)
   │
   │  GET /orders
   │  Authorization: Bearer eyJhbGci…
   │  ────────────────────────────────────▶ verify signature & exp → user id known
   │  ◀── 200 OK orders ────────────────────
```

**Pros**

* **Truly stateless**: any server can validate the token with just the secret/public key. Horizontal scaling is trivial.
* **Works for all clients**: browsers, mobile, CLIs, service-to-service.
* **Not CSRF-prone** when sent in a header (nothing attaches it automatically).
* **Cross-service**: one auth service can issue tokens that five services accept.

**Cons**

* **Hard to revoke** before expiry. Mitigations: short access-token lifetimes (5–15 min), a server-side refresh token, and a deny-list (which reintroduces state).
* **Stale claims**: if you put `role` in the token, a role change does not take effect until the token expires.
* **Payload is readable**: a JWT is signed, _not encrypted_. Never put secrets in it.
* **Easy to get wrong**: `alg: none`, weak secrets, missing `exp` checks, storing tokens in `localStorage` (XSS-readable).

We cover the mechanics in depth in 04-authentication/03-jwt.md _(not available in this published source revision)_.

***

## 5. Where should the browser keep a token?

This is one of the most-debated questions in frontend/backend security. The honest answer:

| Storage                                                              | XSS risk                                 | CSRF risk                                      | Notes                                                            |
| -------------------------------------------------------------------- | ---------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------- |
| **`localStorage` / `sessionStorage`**                                | ❌ High — any injected script can read it | ✅ Immune (not auto-attached)                   | Convenient; common in SPAs; a single XSS = full account takeover |
| **Non-`HttpOnly` cookie**                                            | ❌ High — JS can read it                  | ❌ High — sent automatically                    | Worst of both                                                    |
| **`HttpOnly` + `Secure` + `SameSite` cookie**                        | ✅ Good — JS cannot read it               | ❌ Needs CSRF defence (mitigated by `SameSite`) | **Recommended for browser apps**                                 |
| **In-memory variable**                                               | ✅ Good (lost on refresh)                 | ✅ Immune                                       | Best for short-lived access tokens + silent refresh              |
| **`HttpOnly` cookie for the refresh token + in-memory access token** | ✅✅ Best balance                          | ✅ Refresh call needs CSRF token                | The pattern used by mature SPAs                                  |

**Recommendation for a browser app:** put the refresh token in an `HttpOnly`, `Secure`, `SameSite=Lax/Strict` cookie scoped to your refresh endpoint only, keep the short-lived access token in memory, and protect state-changing endpoints against CSRF. Never keep credentials in `localStorage` if you can avoid it, and never at all in a non-`HttpOnly` cookie.

For a **mobile app**, there are no cookies to speak of — store the refresh token in the platform keychain/keystore and send the access token as a Bearer header.

***

## 6. CORS, in the one place it belongs

The browser enforces a security rule called the **Same-Origin Policy**: JavaScript on `https://app.example.com` may not read the response of a request to `https://api.other.com` unless that server explicitly allows it.

**Origin** = scheme + host + port, all three:

```
https://app.example.com   vs  https://app.example.com   ✅ same origin
https://app.example.com   vs  http://app.example.com    ❌ different scheme
https://app.example.com   vs  https://api.example.com   ❌ different host
https://app.example.com   vs  https://app.example.com:3000 ❌ different port
```

**CORS (Cross-Origin Resource Sharing)** is how the _server_ says "this other origin may read my responses". It is a browser mechanism — `curl`, Postman and server-to-server calls ignore it entirely.

```http
# Preflight: the browser asks permission before the real request.
OPTIONS /api/v1/users HTTP/1.1
Origin: https://app.example.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type,authorization

# Server answers:
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET,POST,PATCH,DELETE
Access-Control-Allow-Headers: content-type,authorization
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 600
```

Key rules that cause 90% of CORS confusion:

1. **A preflight happens only for "non-simple" requests** — those with a custom header (like `Authorization`), a non-simple `Content-Type` (`application/json` is non-simple!), or methods other than GET/POST/HEAD.
2. **`Access-Control-Allow-Origin` must be an exact origin or `*` — never a list.** With multiple frontends, echo back the request's origin after checking it against an allowlist.
3. **`*` and `credentials: 'include'` are mutually exclusive.** If cookies must travel, you must name the origin exactly.
4. **CORS is not a server-side security control.** Your API is still wide open to `curl`. CORS only protects _other people's browsers_ from being used against your API. Real authorisation is your auth middleware.

```js
// File: cors.example.js — the shape of a correct answer
const ALLOWED_ORIGINS = new Set([
  'https://app.example.com',
  'http://localhost:5173', // local dev frontend
]);

app.use((req, res, next) => {
  const origin = req.get('Origin');
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin'); // critical for caches to not mix origins
    res.setHeader('Access-Control-Allow-Credentials', 'true');
  }
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PATCH,PUT,DELETE');
    res.setHeader(
      'Access-Control-Allow-Headers',
      req.get('Access-Control-Request-Headers') ?? 'content-type,authorization'
    );
    return res.sendStatus(204);
  }
  return next();
});
```

In practice you use the `cors` package: [02-express/16-cors.md](../02-express/16-cors.md).

***

## 7. A comparison table worth memorising

|                  | Cookies (session)                                    | JWT (stateless)                                 |
| ---------------- | ---------------------------------------------------- | ----------------------------------------------- |
| State location   | Server                                               | Client (token payload)                          |
| Revocation       | Instant (delete the record)                          | Hard (needs deny-list/rotation)                 |
| Scale-out        | Needs a shared store                                 | Trivial                                         |
| Cross-domain     | Painful (CORS + `SameSite=None` + `Secure`)          | Easy (headers)                                  |
| Mobile clients   | Awkward                                              | Natural                                         |
| CSRF             | Vulnerable → needs `SameSite`/token                  | Not vulnerable when header-based                |
| XSS              | Protected by `HttpOnly`                              | Exposed if in `localStorage`                    |
| Size per request | Tiny (an id)                                         | Larger (payload grows with claims)              |
| Best for         | Server-rendered apps, same-domain SPAs, admin panels | APIs, mobile, microservices, third-party access |
| Typical lifetime | Days to weeks                                        | Minutes (access) + days (refresh)               |

***

## 8. Common mistakes

| Mistake                                                       | Consequence                                                  | Fix                                                    |
| ------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------ |
| Storing sessions in server memory (`new Map()` in the module) | Works on one process; breaks on restart and with >1 instance | Redis/DB-backed store                                  |
| Session cookie without `HttpOnly`                             | XSS steals the session                                       | Always `httpOnly: true` for session cookies            |
| `SameSite=None` without `Secure`                              | Browsers reject the cookie entirely                          | Add `Secure` (and therefore HTTPS)                     |
| Long-lived JWTs (30 days) with no refresh mechanism           | Stolen token is valid for a month                            | 5–15 min access token + refresh rotation               |
| Putting secrets (`passwordHash`, `apiKey`) in the JWT         | The payload is only base64 — readable by anyone              | Keep only non-sensitive claims (`sub`, `role`, `exp`)  |
| Trusting the `alg` field from the token                       | `alg: none` / algorithm-confusion attacks                    | Pin the algorithm when verifying                       |
| `Access-Control-Allow-Origin: *` with credentials             | Browsers refuse; if it worked, it would be a security hole   | Exact origin + `Vary: Origin`                          |
| Assuming CORS protects the API                                | `curl` ignores CORS completely                               | Real auth + rate limiting                              |
| Logging cookies/tokens                                        | Credentials in log files forever                             | Redact them in the logger                              |
| Sessions that never expire                                    | A stolen id is valid forever                                 | TTL, idle timeout, absolute timeout, rotation on login |

***

## Exercise 7.1 — Choose the mechanism

For each scenario, pick cookies+sessions, JWT, or hybrid, and justify it in one or two sentences.

1. An admin dashboard served by Express with server-rendered EJS pages, one domain.
2. A public REST API consumed by third-party developers, mobile apps and an SPA on a different domain.
3. A large SaaS with an SPA frontend, a mobile app, five backend microservices, and a requirement that support staff can force a user to log out immediately.
4. An internal service-to-service API (service A calls service B) with no human users.

<details>

<summary>Solution</summary>

1. **Cookies + server-side sessions.** Same origin, browser-only, server renders pages. Cookies are automatic and `HttpOnly` protects the session id from any XSS in the views. CSRF is handled with `SameSite=Lax` plus a token on forms.
2. **JWT (with refresh tokens).** Cross-domain, multiple client types, no shared cookie domain. Bearer tokens work identically from a mobile app, an SPA and `curl`. Keep access tokens short-lived because third-party API tokens can leak.
3. **Hybrid.** Short-lived JWT access tokens (5–15 min) validated by every microservice without a shared session store, plus server-side **refresh tokens** so that "force logout" is possible by revoking the refresh token — and a deny-list/short TTL to cover the remaining few minutes. This is the realistic answer for a large multi-client, multi-service system.
4. **JWT (or mTLS + a service token).** There is no browser, no cookie, and no CSRF concern. Issue short-lived tokens per service or use mutual TLS; the important part is that service B can verify the caller without calling service A.

The pattern in the answers: **the mechanism follows the client and the revocation requirement**, not fashion.

</details>

## Exercise 7.2 — Diagnose the cookie

The frontend at `https://app.example.com` calls the API at `https://api.example.com`. Login succeeds (`200`, and the browser shows a `Set-Cookie` in the Network tab), but the next request to `/api/v1/me` returns `401`.

```http
Set-Cookie: sessionId=abc123; HttpOnly; Max-Age=86400; Path=/
```

Name every likely cause and the fix for each.

<details>

<summary>Solution</summary>

1. **`SameSite` defaults to `Lax`**, and `app.example.com` → `api.example.com` is a cross-site request, so the cookie is not sent on the follow-up `fetch`. **Fix:** set `SameSite=None; Secure` (requires HTTPS) — or, better, serve the API under the same site (`api.example.com` is cross-_origin_ but same-_site_: `SameSite=Lax` does allow same-site subdomains, so the real issue here is more likely #2 — the cookie is host-only for `api.example.com` and the request must actually go to that host).
2. **The cookie is host-only for `api.example.com`.** If the frontend is instead calling `https://example.com/api/...` through a different host, the cookie does not match. **Fix:** use one consistent API host, or set `Domain=example.com` (with caution — that exposes the cookie to every subdomain).
3. **Credentials are not being sent by the client.** A cross-origin `fetch` or `axios` call sends no cookies unless you opt in. **Fix:** `fetch(url, { credentials: 'include' })` or `axios.defaults.withCredentials = true`, and the server must answer with `Access-Control-Allow-Credentials: true` **and** an exact `Access-Control-Allow-Origin` (never `*`).
4. **`Secure` is missing in production.** Browsers increasingly reject/ignore non-`Secure` cookies on HTTPS-only sites, and `SameSite=None` cookies are rejected outright without `Secure`. **Fix:** `secure: true` in production.
5. **The CORS preflight fails** (for a `fetch` with `Authorization` or `Content-Type: application/json`), so the browser never even sends the request. **Fix:** handle `OPTIONS` and return the right `Access-Control-Allow-*` headers.
6. **The cookie was set with `Path=/api/login`** in some earlier version, so it is not sent to `/api/v1/me`. **Fix:** `Path=/`.

Diagnostic habit: the browser's **Network tab → the failing request → Cookies panel** tells you immediately whether the browser _has_ a cookie for that host and whether it was sent. That single panel resolves most "the cookie isn't working" reports in seconds.

</details>

***

## What's next

You now have every ingredient: the transport, the protocol, the addressing, the style, the payloads and the state. The final chapter of this section puts them together into one narrative you can hold in your head — the complete life of a request.

→ [08 — The Full Request Lifecycle](08-full-request-lifecycle.md)
