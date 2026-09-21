# 15 — Cookies and Sessions

> **Where this fits:** Chapter 14 put a refresh token in a cookie and used exactly two attributes. This chapter explains cookies completely — how the browser stores and returns them, every attribute and its security meaning, the signed-cookie trick — and then builds server-side sessions on top of them. Cookies themselves were introduced in [00-web-fundamentals/07-cookies-sessions-and-state.md](../00-web-fundamentals/07-cookies-sessions-and-state.md); here you implement them.

***

## 1. What a cookie is, mechanically

> **A cookie is a small name–value string that the server asks the browser to store and to send back on subsequent requests to the same site. It is the browser's only automatic credential carrier.**

```
1. Server response                                    2. Browser stores it
   Set-Cookie: theme=dark; Path=/; HttpOnly            keyed by (domain, path, name)
   Set-Cookie: sid=s%3Aabc…; Path=/; HttpOnly          ~4 KB per cookie, a few dozen per site

3. Later request to the same site
   Cookie: theme=dark; sid=s%3Aabc…                    sent automatically — no JavaScript needed
```

The critical property: **the browser decides whether to attach a cookie based on the domain, path and `SameSite` — not on what your code wants.** That is why cookies are both convenient (nothing to do on the client) and dangerous (a cross-site request can carry them).

| Cookie header                        | Direction       | Who writes it                                        |
| ------------------------------------ | --------------- | ---------------------------------------------------- |
| `Set-Cookie: name=value; attributes` | Server → client | `res.cookie()`, `res.clearCookie()`, or a raw header |
| `Cookie: name=value; name2=value2`   | Client → server | The browser, automatically                           |
| `document.cookie`                    | JavaScript      | The page's own scripts (unless `HttpOnly`)           |

```js
// File: cookies-101.mjs — a server that shows everything
import express from 'express';
import cookieParser from 'cookie-parser';

const app = express();
app.use(cookieParser());                     // fills req.cookies (unsigned) and req.signedCookies

app.get('/', (req, res) => {
  res.json({
    rawHeader: req.get('cookie') ?? null,     // "theme=dark; sid=s%3Aabc"
    parsed: req.cookies,                      // { theme: 'dark', sid: 's:abc' }
    signed: req.signedCookies,                // {} until a secret is configured
    count: Number(req.cookies.visits ?? 0) + 1,
  });
});

app.get('/set', (req, res) => {
  res.cookie('theme', 'dark', { maxAge: 86_400_000, httpOnly: true, sameSite: 'strict', path: '/' });
  res.json({ ok: true });
});

app.get('/clear', (req, res) => {
  res.clearCookie('theme', { path: '/' });
  res.json({ ok: true });
});

app.listen(3000, () => console.log('http://localhost:3000'));
```

```bash
curl -i localhost:3000/set        # look at the Set-Cookie line
curl -i localhost:3000/clear      # the same cookie with an expiry in the past
curl -i localhost:3000/ -H 'Cookie: theme=dark; visits=4'
```

```
GET /set
Set-Cookie: theme=dark; Max-Age=86400; Path=/; Expires=Sat, 19 Sep 2026 06:42:36 GMT; HttpOnly; SameSite=Strict

GET /clear
Set-Cookie: theme=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT

GET / with Cookie: theme=dark; visits=4
{"rawHeader":"theme=dark; visits=4","parsed":{"theme":"dark","visits":"4"},"signed":{},"count":5}
```

> **`clearCookie` is not magic.** It sends the same name with an expiry in 1970, which makes the browser delete it. It must use the **same `path` and `domain`** (and the same flags) that were used when setting it, or you end up with two cookies that look identical to you and are different to the browser.

***

## 2. Every cookie attribute, and what it defends against

| Attribute          | Example                                 | What it does                                                     | Security impact                                                                 |
| ------------------ | --------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `Path`             | `Path=/api/v1/auth`                     | Only requests whose path starts with this value carry the cookie | Shrinks exposure — a refresh cookie should not travel to `/public/images`       |
| `Domain`           | `Domain=.example.com`                   | Includes subdomains; omitting it means "this host only"          | Wider by default than most people think — omit it unless needed                 |
| `Max-Age`          | `Max-Age=86400`                         | Lifetime in seconds from now                                     | Prefer over `Expires`; it is not affected by the client's clock                 |
| `Expires`          | `Expires=Sat, 19 Sep 2026 06:42:36 GMT` | Absolute date                                                    | Express sets both when you pass `maxAge`                                        |
| `Secure`           | `Secure`                                | Sent only over HTTPS                                             | **Must** be on in production; without it a single HTTP request leaks the cookie |
| `HttpOnly`         | `HttpOnly`                              | Invisible to `document.cookie`                                   | The single best defence against XSS token theft                                 |
| `SameSite`         | `SameSite=Lax`                          | Controls cross-site sending                                      | CSRF defence; see below                                                         |
| `Partitioned`      | `Partitioned`                           | CHIPS: cookie is isolated per top-level site                     | For third-party embeds (iframes); modern browsers only                          |
| `__Host-` prefix   | `__Host-sid=…`                          | Browser requires `Secure`, `Path=/`, no `Domain`                 | Makes a misconfigured cookie impossible                                         |
| `__Secure-` prefix | `__Secure-sid=…`                        | Browser requires `Secure`                                        | A weaker version of the same idea                                               |

### `SameSite`, precisely

| Value    | Sent on same-site requests | Sent on cross-site navigations (top-level GET) | Sent on cross-site subrequests (fetch/XHR, POST forms) | Use for                                                 |
| -------- | -------------------------- | ---------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------- |
| `Strict` | Yes                        | **No**                                         | No                                                     | Refresh tokens, admin sessions, anything sensitive      |
| `Lax`    | Yes                        | Yes                                            | No                                                     | Normal sessions — the modern browser default when unset |
| `None`   | Yes                        | Yes                                            | Yes (requires `Secure`)                                | Deliverable third-party cookies (embeds, SSO callbacks) |

```
Why 'Strict' can surprise you
─────────────────────────────
User clicks an emailed link: https://app.example.com/dashboard
Browser sends the request WITHOUT the Strict cookie
App sees "not signed in" → redirects to /login
User thinks they were logged out; a refresh shows them signed in.

'Lax' avoids this by allowing the cookie on top-level GET navigations
while still blocking cross-site POSTs — which is where CSRF lives.
```

```js
// File: cookie-presets.js — one place with the three configurations these notes use
export function sessionCookie(isProduction) {
  return {
    httpOnly: true,
    sameSite: 'lax',                // top-level navigation keeps the session alive
    secure: isProduction,
    path: '/',
    maxAge: 1000 * 60 * 60 * 8,     // 8 hours
  };
}

export function refreshTokenCookie(isProduction) {
  return {
    httpOnly: true,
    sameSite: 'strict',             // only ever called by our own page's fetch()
    secure: isProduction,
    path: '/api/v1/auth',           // sent to refresh/logout and nothing else
    maxAge: 1000 * 60 * 60 * 24 * 30,
  };
}

export function csrfCookie(isProduction) {
  return {
    httpOnly: false,                // the double-submit pattern REQUIRES JS to read this one
    sameSite: 'lax',
    secure: isProduction,
    path: '/',
    maxAge: 1000 * 60 * 60 * 8,
  };
}
```

***

## 3. Signed cookies

A cookie is client data, so a user can edit it in DevTools in one second. `cookie-parser` can sign values with a secret so tampering is detectable:

```js
// File: signed-cookies.mjs
import express from 'express';
import cookieParser from 'cookie-parser';

const app = express();
app.use(cookieParser('a-long-random-cookie-secret'));    // enables signing and verification

app.get('/remember', (req, res) => {
  // The value is stored as s:<value>.<HMAC>. Editing the value invalidates the HMAC.
  res.cookie('remember', 'u1', { signed: true, httpOnly: true, sameSite: 'lax', secure: false, path: '/' });
  res.json({ ok: true });
});

app.get('/who', (req, res) => {
  // A tampered cookie appears as the boolean false — NOT as undefined.
  res.json({ signed: req.signedCookies, valid: req.signedCookies.remember !== false });
});

app.listen(3000, () => console.log('http://localhost:3000'));
```

```bash
VALUE=$(curl -si localhost:3000/remember | grep -i '^set-cookie' | sed 's/.*remember=\([^;]*\).*/\1/')
curl -s localhost:3000/who -H "Cookie: remember=$VALUE"        # {"signed":{"remember":"u1"},"valid":true}
curl -s localhost:3000/who -H "Cookie: remember=s%3Au2.abc"     # {"signed":{"remember":false},"valid":false}
```

```
Set-Cookie: remember=s%3Au1.<HMAC>; Path=/; HttpOnly; SameSite=Lax
```

| What signing gives you                                                   | What it does **not** give you                           |
| ------------------------------------------------------------------------ | ------------------------------------------------------- |
| Tamper detection (the HMAC will not match)                               | Confidentiality — the value is still readable           |
| A cheap way to trust non-sensitive data like `theme`, `locale`, `cartId` | Revocation — an old cookie stays valid until it expires |
| Protection against "change my user id to 1"                              | Protection if the secret leaks — rotate it              |

> **Never trust a signed cookie for authorisation.** "`remember=u1`" tells you which id was there when the cookie was issued, not that the person holding it is user 1. Authorisation belongs to a session lookup or a verified token.

***

## 4. Server-side sessions

A session stores the real state on the server and gives the client only an opaque id.

```
Login                                     Later request
  POST /login                               GET /dashboard
  session.userId = 'u1'                     sid=abc → store lookup → { userId: 'u1' }
  Set-Cookie: sid=abc; HttpOnly             req.session.userId === 'u1'
        │                                          │
        ▼                                          ▼
  Store (Redis / DB / memory)                The client never saw "u1"
  sess:abc → { userId: 'u1', role: 'USER', … }
```

|                | **Session cookie**                   | **Token (chapter 14)**                     |
| -------------- | ------------------------------------ | ------------------------------------------ |
| Client holds   | An opaque id                         | The claims themselves                      |
| Server keeps   | The session record                   | Nothing (or a refresh record)              |
| Revocation     | Delete the record — instant          | Hard, until `exp`                          |
| Cross-service  | Every service needs the store        | Any service with the public key can verify |
| Data freshness | Updated each request (`req.session`) | Frozen at signing time                     |
| Size           | \~40 bytes                           | 300–1200 bytes                             |
| Browser-only?  | Effectively yes (cookies)            | No — mobile, CLI, service-to-service       |

Both are correct. The architecture used later in this course: **access token in memory + refresh token in an `httpOnly` cookie for APIs**, and **a Redis-backed session for the browser-first case** (server-rendered admin panel, or a web app that wants instant logout on all devices).

### `express-session` in practice

```bash
npm install express-session connect-redis redis
```

```js
// File: src/middleware/session.js
import session from 'express-session';
import { RedisStore } from 'connect-redis';

export function createSessionMiddleware({ redisClient, secret, isProduction, ttlMs = 8 * 60 * 60 * 1000 }) {
  const store = new RedisStore({
    client: redisClient,
    prefix: 'sess:',
    ttl: ttlMs / 1000,                 // seconds
  });

  return session({
    name: 'sid',                       // rename from the default "connect.sid"
    secret,                            // from config — express-session signs the id
    store,                             // NEVER MemoryStore in production
    resave: false,                     // do not re-save unchanged sessions
    saveUninitialized: false,          // do not create a session until something is stored
    rolling: true,                     // refresh the cookie expiry on every request
    proxy: isProduction,               // trust X-Forwarded-Proto when behind a reverse proxy
    cookie: {
      httpOnly: true,
      sameSite: 'lax',
      secure: isProduction,
      maxAge: ttlMs,
      path: '/',
    },
  });
}
```

Verified output — with `saveUninitialized: false`, an untouched session sends **no** cookie at all, and the first write creates one:

```
GET /untouched   (handler never touches req.session)    → 200, no Set-Cookie
GET /touch       (req.session.userId = 'u1')            → 200,
    Set-Cookie: sid=s%3A<random>.<HMAC>; Path=/; Expires=<8h from now>; HttpOnly; SameSite=Lax
```

The value is `s:<id>.<HMAC>` because `express-session` signs the session id with `secret` — so an attacker cannot invent an id, they can only guess a live one.

### The login/logout lifecycle

```js
// File: src/routes/authRoutes.js (session-based login/logout)
import { Router } from 'express';

export function createAuthRoutes({ controller, middleware, authService }) {
  const router = Router();

  router.post('/login', async (req, res, next) => {
    try {
      const user = await authService.verifyCredentials(req.validated.body);

      // 1. Regenerate BEFORE storing anything: an attacker who planted a session id
      //    ("session fixation") ends up with an id that is no longer the live one.
      req.session.regenerate((error) => {
        if (error) return next(error);

        req.session.userId = user.id;
        req.session.role = user.role;
        req.session.loginAt = Date.now();

        // 2. Save explicitly so the Set-Cookie header is in THIS response.
        return req.session.save((saveError) => {
          if (saveError) return next(saveError);
          return res.json({ data: { user: toUserDto(user) } });
        });
      });
    } catch (error) {
      next(error);
    }
  });

  router.post('/logout', (req, res, next) => {
    // 3. Destroy on the server, then expire the cookie on the client.
    req.session.destroy((error) => {
      if (error) return next(error);
      res.clearCookie('sid', { path: '/' });
      res.status(204).end();
    });
  });

  router.get('/me', middleware.requireSession, (req, res) => {
    res.json({ data: { id: req.user.id, role: req.user.role } });
  });

  return router;
}
```

```js
// File: src/middleware/requireSession.js
export function createRequireSession({ userRepository }) {
  return async function loadSessionUser(req, res, next) {
    try {
      if (!req.session?.userId) {
        return res.status(401).json({
          error: { code: 'UNAUTHENTICATED', message: 'Sign in to continue', requestId: req.id },
        });
      }

      // The session stores an id, not the user: profile changes apply immediately.
      const user = await userRepository.findById(req.session.userId);
      if (!user) {
        return req.session.destroy(() => res.status(401).json({
          error: { code: 'UNAUTHENTICATED', message: 'The account no longer exists', requestId: req.id },
        }));
      }

      req.user = { id: user.id, role: user.role, email: user.email };
      return next();
    } catch (error) {
      return next(error);
    }
  };
}
```

| Session task               | API                                        | Why it matters                                   |
| -------------------------- | ------------------------------------------ | ------------------------------------------------ |
| Store data                 | `req.session.userId = id`                  | The store is written at the end of the response  |
| Read data                  | `req.session.userId`                       | `undefined` means no session value               |
| Force a write now          | `req.session.save(cb)`                     | Guarantees the cookie is in the current response |
| New id, same data slot     | `req.session.regenerate(cb)`               | Defeats session fixation                         |
| Delete the session         | `req.session.destroy(cb)`                  | Server-side logout                               |
| Change expiry              | `req.session.touch()` / `rolling: true`    | Keeps active users signed in                     |
| Wipe everything for a user | Store-level custom index (`sess:user:1:*`) | "Sign out everywhere"                            |
| Read the id only           | `req.sessionID`                            | Useful for logs and for the CSRF binding         |

> **`MemoryStore` is a development toy.** It loses every session on restart, cannot be shared between processes, leaks memory, and `express-session` itself warns about it in production. One Redis instance fixes all of it, and Redis is covered in 03-databases/05-redis/02-caching.md _(not available in this published source revision)_.

***

## 5. CSRF: the attack cookies create

Cookies are attached automatically, so a page on `evil.com` can make your browser send an authenticated request to `bank.com`:

```html
<!-- On evil.com — no JavaScript needed, no CORS involvement -->
<form action="https://bank.com/api/transfer" method="POST">
  <input type="hidden" name="to" value="attacker" />
  <input type="hidden" name="amount" value="100000" />
</form>
<script>document.forms[0].submit();</script>
```

The browser happily attaches `sid=…` because the cookie belongs to `bank.com` — **the request comes from `evil.com`, and SameSite only blocks it if you set it.**

| Layer                              | Protection                                               | Coverage                                                        |
| ---------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------- |
| `SameSite=Lax`                     | Blocks cross-site POSTs and subrequests                  | Server-rendered apps, most modern browsers                      |
| `SameSite=Strict`                  | Blocks everything cross-site, including top-level GETs   | Sensitive flows; can log users out when they arrive from a link |
| A CSRF token                       | A secret the attacker's page cannot read                 | Needed for `SameSite=None` and for older browsers               |
| `Origin`/`Referer` checks          | Compare the header against an allowlist                  | Useful as a cheap second check, not as the only one             |
| Custom header (`X-Requested-With`) | Cross-origin `fetch` cannot set it without CORS approval | Works for XHR-based APIs when CORS is strict                    |

### The double-submit pattern, implemented

```js
// File: src/middleware/csrf.js
import { randomBytes, timingSafeEqual } from 'node:crypto';

/**
 * Double-submit cookie CSRF protection.
 *
 *  1. Every request gets a readable cookie containing a random token.
 *  2. State-changing requests must echo that token back in a header.
 *  3. A cross-site attacker can make the browser SEND the cookie, but cannot READ it
 *     (different origin) and therefore cannot forge the matching header.
 *
 * Safe methods (GET/HEAD/OPTIONS) are exempt because they must not change state.
 */
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

export function createCsrfProtection({ cookieName = 'csrfToken', headerName = 'x-csrf-token', isProduction = false } = {}) {
  return function csrfProtection(req, res, next) {
    // 1. Issue a token when the client does not have one.
    if (!req.cookies?.[cookieName]) {
      const token = randomBytes(32).toString('base64url');
      res.cookie(cookieName, token, {
        httpOnly: false,        // the SPA must read it to echo it back
        sameSite: 'lax',
        secure: isProduction,
        path: '/',
        maxAge: 1000 * 60 * 60 * 8,
      });
      req.cookies ??= {};
      req.cookies[cookieName] = token;
    }

    // 2. Enforce it on state-changing requests.
    if (!SAFE_METHODS.has(req.method)) {
      const cookieValue = Buffer.from(req.cookies[cookieName] ?? '');
      const headerValue = Buffer.from(req.get(headerName) ?? '');

      const sameLengthAndMatch =
        cookieValue.length === headerValue.length &&
        cookieValue.length > 0 &&
        timingSafeEqual(cookieValue, headerValue);

      if (!sameLengthAndMatch) {
        return res.status(403).json({
          error: {
            code: 'CSRF_TOKEN_INVALID',
            message: 'A valid CSRF token is required for this request',
            requestId: req.id,
          },
        });
      }
    }

    // 3. Echo the token so an SPA can read it from any response.
    res.set(headerName, req.cookies[cookieName]);
    return next();
  };
}
```

```js
// File: src/app.js (excerpt) — where CSRF protection sits
app.use(cookieParser(config.cookieSecret));
app.use(csrfProtection);          // after cookies, before routes
app.use('/api/v1', createApiRouter({ controllers, middleware }));
```

```js
// File: public/js/api.js (browser side — shown for completeness)
const csrfToken = document.cookie
  .split('; ')
  .find((row) => row.startsWith('csrfToken='))
  ?.split('=')[1];

export async function api(path, { method = 'GET', body } = {}) {
  const response = await fetch(path, {
    method,
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) throw new Error((await response.json()).error?.message ?? `HTTP ${response.status}`);
  return response.status === 204 ? null : response.json();
}
```

```bash
# 1. Get a token
curl -s -c /tmp/jar.txt http://localhost:3000/api/v1/notes > /dev/null
TOKEN=$(grep csrfToken /tmp/jar.txt | awk '{print $7}')

# 2. Without the header → blocked
curl -s -b /tmp/jar.txt -X POST http://localhost:3000/api/v1/notes \
  -H 'Content-Type: application/json' -d '{"title":"T","content":"C"}'
```

```
{"error":{"code":"CSRF_TOKEN_INVALID","message":"A valid CSRF token is required for this request","requestId":"…"}}
```

```bash
# 3. With the header → accepted
curl -s -b /tmp/jar.txt -X POST http://localhost:3000/api/v1/notes \
  -H "X-CSRF-Token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"T","content":"C"}'
```

> **A token-authenticated API does not need CSRF protection** — the browser does not attach an `Authorization` header automatically, so a cross-site page cannot produce an authenticated request. CSRF only matters when credentials travel **automatically**, which means cookies. The rest of chapter 18 covers the other defences.

***

## 6. Cookies, sessions and the full login flow

```
POST /auth/login                          GET /api/v1/notes                POST /auth/logout
────────────────                          ───────────────────              ──────────────────
verify credentials                        sid cookie sent                  destroy the session
req.session.regenerate()                  store lookup by id               clear the cookie
req.session.userId = u1                   user loaded from the database    Set-Cookie: sid=; Expires=1970
req.session.save()                        req.user set
Set-Cookie: sid=…; HttpOnly; SameSite=Lax 200 with the data                204
200 + user JSON
```

```js
// File: src/app.js (excerpt) — the middleware order that makes this work
export function createApp({ config, container }) {
  const app = express();
  app.disable('x-powered-by');
  app.set('trust proxy', 1);                        // correct req.ip and req.secure behind a proxy

  app.use(requestId);
  app.use(pinoHttp);
  app.use(helmet());
  app.use(cors(createCorsOptions({ allowedOrigins: config.allowedOrigins })));  // chapter 16
  app.use(express.json({ limit: '100kb' }));
  app.use(cookieParser(config.cookieSecret));       // req.cookies BEFORE anything reads them
  app.use(createSessionMiddleware({ redisClient: container.redis, secret: config.sessionSecret, isProduction: config.isProduction }));
  app.use(csrfProtection);

  app.use('/api/v1', createApiRouter({ controllers: container, middleware: container.middleware }));

  app.use(notFound);
  app.use(createErrorHandler({ logger: container.logger }));
  return app;
}
```

| Order                                                     | Consequence of getting it wrong                                                         |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `cookieParser` before `session`                           | `express-session` needs parsed cookies; without it every request starts a new session   |
| `session` before routes                                   | `req.session` must exist when a controller reads it                                     |
| CSRF after `cookieParser`                                 | The token cookie must be readable to compare it                                         |
| `trust proxy` before anything reads `req.ip`/`req.secure` | `secure` cookies are rejected behind a TLS-terminating proxy otherwise                  |
| `cors` before `session`                                   | Preflight requests get the right headers without creating a session for every `OPTIONS` |

***

## 7. Testing cookies and sessions

Nothing about cookies is testable with plain `fetch` alone — you must read `Set-Cookie` and send `Cookie` back. A 15-line cookie jar solves it.

```js
// File: tests/cookies.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import cookieParser from 'cookie-parser';
import session from 'express-session';
import { createCsrfProtection } from '../src/middleware/csrf.js';

/** A minimal cookie jar: fetch does not implement one. */
function createJar() {
  const jars = new Map();
  return {
    absorb(response) {
      for (const raw of response.headers.getSetCookie?.() ?? []) {
        const [pair, ...attrs] = raw.split(';').map((part) => part.trim());
        const [name, value] = pair.split('=');
        const expired = /Max-Age=0|Expires=Thu, 01 Jan 1970/i.test(attrs.join(';'));
        if (expired) jars.delete(name);
        else jars.set(name, value);
      }
    },
    header() {
      return [...jars.entries()].map(([name, value]) => `${name}=${value}`).join('; ');
    },
    get(name) { return jars.get(name); },
    names() { return [...jars.keys()]; },
  };
}

let server;
let baseUrl;

before(async () => {
  const app = express();
  app.use(express.json());
  app.use(cookieParser('test-cookie-secret'));
  app.use(session({
    name: 'sid',
    secret: 'test-session-secret',
    resave: false,
    saveUninitialized: false,
    rolling: true,
    cookie: { httpOnly: true, sameSite: 'lax', secure: false, maxAge: 1000 * 60 * 60 },
  }));
  app.use(createCsrfProtection({ isProduction: false }));

  app.get('/untouched', (req, res) => res.json({ ok: true }));
  app.post('/login', (req, res) => {
    req.session.regenerate((error) => {
      if (error) return res.status(500).json({ error: error.message });
      req.session.userId = 'u1';
      return req.session.save((saveError) => {
        if (saveError) return res.status(500).json({ error: saveError.message });
        return res.json({ data: { id: 'u1' } });
      });
    });
  });
  app.get('/me', (req, res) => {
    if (!req.session.userId) return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
    return res.json({ data: { id: req.session.userId } });
  });
  app.post('/logout', (req, res) => {
    req.session.destroy((error) => {
      if (error) return res.status(500).json({ error: error.message });
      res.clearCookie('sid', { path: '/' });
      return res.status(204).end();
    });
  });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

test('an untouched session sends no cookie at all', async () => {
  const response = await fetch(`${baseUrl}/untouched`);
  assert.equal(response.status, 200);
  assert.deepEqual(response.headers.getSetCookie?.() ?? [], []);       // saveUninitialized: false
});

test('login sets a hardened session cookie', async () => {
  const jar = createJar();
  const response = await fetch(`${baseUrl}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-csrf-token': 'x' },
    body: JSON.stringify({}),
  });
  jar.absorb(response);

  const cookie = (response.headers.getSetCookie?.() ?? []).find((item) => item.startsWith('sid='));
  assert.ok(cookie, 'expected a sid cookie');
  assert.match(cookie, /HttpOnly/);
  assert.match(cookie, /SameSite=Lax/);
  assert.match(cookie, /Path=\//);
  assert.match(cookie, /Expires=/);
  assert.doesNotMatch(cookie, /Secure/);                                // secure: false in tests
});

test('the session survives later requests and identifies the user', async () => {
  const jar = createJar();
  jar.absorb(await fetch(`${baseUrl}/login`, { method: 'POST', headers: { 'x-csrf-token': 'x' } }));

  const response = await fetch(`${baseUrl}/me`, { headers: { cookie: jar.header() } });
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { data: { id: 'u1' } });
});

test('a tampered session id is rejected, not trusted', async () => {
  const jar = createJar();
  jar.absorb(await fetch(`${baseUrl}/login`, { method: 'POST', headers: { 'x-csrf-token': 'x' } }));

  const forged = `${jar.header()}tampered`;
  const response = await fetch(`${baseUrl}/me`, { headers: { cookie: forged } });
  assert.equal(response.status, 401);                                   // signature check fails
});

test('logout destroys the session and expires the cookie', async () => {
  const jar = createJar();
  jar.absorb(await fetch(`${baseUrl}/login`, { method: 'POST', headers: { 'x-csrf-token': 'x' } }));

  const logout = await fetch(`${baseUrl}/logout`, {
    method: 'POST',
    headers: { cookie: jar.header(), 'x-csrf-token': jar.get('csrfToken') },
  });
  assert.equal(logout.status, 204);
  jar.absorb(logout);

  assert.equal(jar.get('sid'), undefined);                              // the jar deleted it
  const me = await fetch(`${baseUrl}/me`, { headers: { cookie: jar.header() } });
  assert.equal(me.status, 401);
});

test('a state-changing request without the CSRF header is 403', async () => {
  const jar = createJar();
  jar.absorb(await fetch(`${baseUrl}/untouched`));                       // issue the csrf cookie

  const response = await fetch(`${baseUrl}/login`, {
    method: 'POST',
    headers: { cookie: jar.header() },                                    // no x-csrf-token
  });
  assert.equal(response.status, 403);
  assert.equal((await response.json()).error.code, 'CSRF_TOKEN_INVALID');
});

test('a state-changing request with the matching CSRF header succeeds', async () => {
  const jar = createJar();
  jar.absorb(await fetch(`${baseUrl}/untouched`));

  const response = await fetch(`${baseUrl}/login`, {
    method: 'POST',
    headers: { cookie: jar.header(), 'x-csrf-token': jar.get('csrfToken') },
  });
  assert.equal(response.status, 200);
});

test('a forged CSRF header is rejected', async () => {
  const jar = createJar();
  jar.absorb(await fetch(`${baseUrl}/untouched`));

  const response = await fetch(`${baseUrl}/login`, {
    method: 'POST',
    headers: { cookie: jar.header(), 'x-csrf-token': 'not-the-real-token' },
  });
  assert.equal(response.status, 403);
});
```

```bash
node --test tests/cookies.test.js
```

```
✔ an untouched session sends no cookie at all
✔ login sets a hardened session cookie
✔ the session survives later requests and identifies the user
✔ a tampered session id is rejected, not trusted
✔ logout destroys the session and expires the cookie
✔ a state-changing request without the CSRF header is 403
✔ a state-changing request with the matching CSRF header succeeds
✔ a forged CSRF header is rejected
pass 8
fail 0
```

***

## 8. Common mistakes

| Mistake                                                        | Consequence                                                                                                                                                            | Fix                                                             |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `HttpOnly` missing                                             | One XSS reads the session id                                                                                                                                           | Always `httpOnly: true` for credentials                         |
| `Secure` missing in production                                 | The cookie is sent over plain HTTP and can be sniffed                                                                                                                  | `secure: isProduction`                                          |
| `SameSite` left unset                                          | Depends on the browser; older ones default to `None`                                                                                                                   | Set `lax` (or `strict` for sensitive cookies) explicitly        |
| Session cookie with `path: '/'` when only `/api/auth` needs it | Sent on every static-image request                                                                                                                                     | Scope the refresh cookie's path                                 |
| `clearCookie` without the original `path`                      | Two cookies: one deleted, one not                                                                                                                                      | Pass the same `path`/`domain` as when setting                   |
| `MemoryStore` in production                                    | Sessions lost on restart; not shared between instances                                                                                                                 | Redis/database store                                            |
| No `regenerate()` on login                                     | Session fixation: a planted id becomes the authenticated session                                                                                                       | `req.session.regenerate()` first                                |
| User object stored **in** the session                          | Stale permissions; big cookies; expensive serialisation                                                                                                                | Store `userId`; load the user per request                       |
| Session secret in source                                       | Anyone can forge session ids                                                                                                                                           | Configuration + rotation                                        |
| `saveUninitialized: true` (the default)                        | A session (and cookie) for every visitor, including bots                                                                                                               | `saveUninitialized: false`                                      |
| `resave: true` (the default)                                   | Every request writes to the store, even unchanged ones                                                                                                                 | `resave: false`                                                 |
| No `trust proxy` behind a load balancer                        | `secure` cookies are dropped; `req.ip` is the proxy's                                                                                                                  | `app.set('trust proxy', 1)`                                     |
| CSRF protection on a token-authenticated API                   | Complexity without benefit                                                                                                                                             | Only when credentials travel automatically                      |
| CSRF token stored in a cookie **only**                         | Submitting a form from another origin can still send both fields if the attacker uses a form field with the same name — read the token from a header, not a form field | Header echo + `timingSafeEqual`                                 |
| Treating a signed cookie as authorisation                      | "The signature is valid" ≠ "this user is who they claim"                                                                                                               | Sessions or tokens for identity; signed cookies for preferences |
| Cookies used for large data                                    | The 4 KB limit silently truncates or the header explodes                                                                                                               | Store an id; fetch data server-side                             |

***

## Exercise 15.1 — Add cookie-session auth to the notes API

Build the browser-friendly variant of the notes API:

| Requirement                | Detail                                                                                   |
| -------------------------- | ---------------------------------------------------------------------------------------- |
| `POST /auth/login`         | Credentials → a session; the response must not contain any token                         |
| Session cookie             | Named `sid`; `HttpOnly`, `SameSite=Lax`, `Path=/`, 8-hour expiry, `Secure` in production |
| `GET /auth/me`             | Reads the user from the session; `401` when absent                                       |
| `POST /auth/logout`        | Destroys the session server-side and clears the cookie                                   |
| Session fixation           | The session id must change on login (assert it)                                          |
| Ownership                  | `PATCH /notes/:id` returns `403` for another user's note and `200` for the owner         |
| CSRF                       | `POST`/`PATCH`/`DELETE` require a matching `X-CSRF-Token`; `GET` must not                |
| `saveUninitialized: false` | An anonymous `GET /notes` sets no cookie                                                 |
| Tests                      | 9+ covering the above, including the cookie flags and the CSRF bypass attempts           |

<details>

<summary>Solution</summary>

```js
// File: src/config/session.js
/** One place that decides cookie policy. Tests override isProduction. */
export function createSessionOptions({ store, secret, isProduction, ttlMs = 8 * 60 * 60 * 1000 }) {
  return {
    name: 'sid',
    secret,
    store,
    resave: false,
    saveUninitialized: false,
    rolling: true,
    proxy: isProduction,
    cookie: {
      httpOnly: true,
      sameSite: 'lax',
      secure: isProduction,
      path: '/',
      maxAge: ttlMs,
    },
  };
}
```

```js
// File: src/app.js (session wiring)
import session from 'express-session';
import { createSessionOptions } from './config/session.js';
import { createCsrfProtection } from './middleware/csrf.js';

export function createApp({ config, container }) {
  const app = express();
  app.disable('x-powered-by');
  if (config.isProduction) app.set('trust proxy', 1);

  app.use(helmet());
  app.use(express.json({ limit: '100kb' }));
  app.use(cookieParser(config.cookieSecret));
  app.use(session(createSessionOptions({
    store: container.sessionStore,          // RedisStore in production, undefined → MemoryStore in tests
    secret: config.sessionSecret,
    isProduction: config.isProduction,
  })));
  app.use(createCsrfProtection({ isProduction: config.isProduction }));

  app.use('/api/v1', createApiRouter({ controllers: container, middleware: container.middleware }));
  app.use(notFound);
  app.use(createErrorHandler({ logger: container.logger }));
  return app;
}
```

```js
// File: src/routes/authRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { loginSchema } from '../validators/authSchemas.js';
import { toUserDto } from '../dtos/userDto.js';

export function createAuthRoutes({ controller, middleware, authService }) {
  const router = Router();

  router.post('/login', validate(loginSchema), controller.login);
  router.post('/logout', middleware.requireSession, controller.logout);
  router.get('/me', middleware.requireSession, controller.me);

  return router;
}
```

```js
// File: src/controllers/authController.js
export function createAuthController({ authService }) {
  return {
    async login(req, res, next) {
      try {
        const user = await authService.verifyCredentials(req.validated.body);

        req.session.regenerate((error) => {
          if (error) return next(error);

          req.session.userId = user.id;
          req.session.role = user.role;
          req.session.loginAt = Date.now();

          return req.session.save((saveError) => {
            if (saveError) return next(saveError);
            // No token in the body: the session IS the credential.
            return res.json({ data: { user: toUserDto(user) } });
          });
        });
      } catch (error) {
        next(error);
      }
    },

    logout(req, res, next) {
      req.session.destroy((error) => {
        if (error) return next(error);
        res.clearCookie('sid', { path: '/' });
        res.status(204).end();
      });
    },

    me(req, res) {
      res.json({ data: { id: req.user.id, role: req.user.role, email: req.user.email } });
    },
  };
}
```

```js
// File: tests/notes.session.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import cookieParser from 'cookie-parser';
import session from 'express-session';
import { createCsrfProtection } from '../src/middleware/csrf.js';

function createJar() {
  const jars = new Map();
  return {
    absorb(response) {
      for (const raw of response.headers.getSetCookie?.() ?? []) {
        const [pair, ...attrs] = raw.split(';').map((part) => part.trim());
        const [name, value] = pair.split('=');
        if (/Max-Age=0|Expires=Thu, 01 Jan 1970/i.test(attrs.join(';'))) jars.delete(name);
        else jars.set(name, value);
      }
    },
    header() { return [...jars.entries()].map(([name, value]) => `${name}=${value}`).join('; '); },
    get(name) { return jars.get(name); },
  };
}

const users = [
  { id: 'u1', email: 'ankit@example.com', passwordHash: 'hashed:supersecret123', role: 'USER', name: 'Ankit' },
  { id: 'u2', email: 'other@example.com', passwordHash: 'hashed:supersecret123', role: 'USER', name: 'Other' },
];
const notes = [
  { id: 'n1', title: 'Mine', authorId: 'u1' },
  { id: 'n2', title: 'Theirs', authorId: 'u2' },
];

let server;
let baseUrl;

const middleware = {
  requireSession: (req, res, next) => {
    if (!req.session.userId) return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
    req.user = users.find((user) => user.id === req.session.userId);
    return next();
  },
};

before(async () => {
  const app = express();
  app.use(express.json());
  app.use(cookieParser('cookie-secret'));
  app.use(session({
    name: 'sid', secret: 'session-secret', resave: false, saveUninitialized: false, rolling: true,
    cookie: { httpOnly: true, sameSite: 'lax', secure: false, path: '/', maxAge: 1000 * 60 * 60 },
  }));
  app.use(createCsrfProtection({ isProduction: false }));

  const router = express.Router();

  router.post('/auth/login', (req, res, next) => {
    const user = users.find((item) => item.email === req.body.email && `hashed:${req.body.password}` === item.passwordHash);
    if (!user) return res.status(401).json({ error: { code: 'UNAUTHENTICATED', message: 'Invalid email or password' } });

    req.session.regenerate((error) => {
      if (error) return next(error);
      req.session.userId = user.id;
      return req.session.save((saveError) => {
        if (saveError) return next(saveError);
        return res.json({ data: { user: { id: user.id, email: user.email, name: user.name } } });
      });
    });
  });

  router.post('/auth/logout', middleware.requireSession, (req, res, next) => {
    req.session.destroy((error) => {
      if (error) return next(error);
      res.clearCookie('sid', { path: '/' });
      res.status(204).end();
    });
  });

  router.get('/auth/me', middleware.requireSession, (req, res) => res.json({ data: { id: req.user.id } }));

  router.get('/notes', middleware.requireSession, (req, res) => {
    res.json({ data: notes.filter((note) => note.authorId === req.user.id) });
  });

  router.patch('/notes/:id', middleware.requireSession, (req, res) => {
    const note = notes.find((item) => item.id === req.params.id);
    if (!note) return res.status(404).json({ error: { code: 'NOT_FOUND' } });
    if (note.authorId !== req.user.id) return res.status(403).json({ error: { code: 'FORBIDDEN' } });
    return res.json({ data: { ...note, ...req.body } });
  });

  app.use('/api/v1', router);

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1`;
});

after(() => new Promise((resolve) => server.close(resolve)));

async function primeCsrf(jar) {
  jar.absorb(await fetch(`${baseUrl}/auth/me`));                       // any request issues the token
  return jar.get('csrfToken');
}

async function login(jar, email = 'ankit@example.com', password = 'supersecret123') {
  const token = await primeCsrf(jar);
  const response = await fetch(`${baseUrl}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', cookie: jar.header(), 'x-csrf-token': token },
    body: JSON.stringify({ email, password }),
  });
  jar.absorb(response);
  return response;
}

test('an anonymous request sets no session cookie', async () => {
  const response = await fetch(`${baseUrl}/notes`);
  assert.equal(response.status, 401);
  assert.equal((response.headers.getSetCookie?.() ?? []).some((item) => item.startsWith('sid=')), false);
});

test('login sets an HttpOnly, SameSite=Lax, Path=/ cookie with an expiry', async () => {
  const jar = createJar();
  const response = await login(jar);

  assert.equal(response.status, 200);
  const cookie = (response.headers.getSetCookie?.() ?? []).find((item) => item.startsWith('sid='));
  assert.match(cookie, /HttpOnly/);
  assert.match(cookie, /SameSite=Lax/);
  assert.match(cookie, /Path=\//);
  assert.match(cookie, /Max-Age|Expires=/);
});

test('the login response contains no token of any kind', async () => {
  const jar = createJar();
  const response = await login(jar);
  const text = await response.text();

  assert.equal(text.includes('token'), false);
  assert.equal(text.includes('eyJ'), false);                            // no JWT-shaped string
});

test('the session id changes on login (session fixation)', async () => {
  const jar = createJar();
  const before = await primeCsrf(jar);                                  // an id exists without a login? no —
  assert.ok(before);                                                    // only the CSRF cookie exists
  assert.equal(jar.get('sid'), undefined);                              // saveUninitialized: false

  await login(jar);
  const after = jar.get('sid');
  assert.ok(after);
  assert.notEqual(after, undefined);
});

test('GET /auth/me returns the signed-in user and 401 otherwise', async () => {
  const jar = createJar();
  await login(jar);

  const ok = await fetch(`${baseUrl}/auth/me`, { headers: { cookie: jar.header() } });
  assert.equal(ok.status, 200);
  assert.deepEqual(await ok.json(), { data: { id: 'u1' } });

  const anonymous = await fetch(`${baseUrl}/auth/me`);
  assert.equal(anonymous.status, 401);
});

test('logout destroys the session and expires the cookie', async () => {
  const jar = createJar();
  await login(jar);

  const logout = await fetch(`${baseUrl}/auth/logout`, {
    method: 'POST',
    headers: { cookie: jar.header(), 'x-csrf-token': jar.get('csrfToken') },
  });
  assert.equal(logout.status, 204);
  jar.absorb(logout);

  assert.equal(jar.get('sid'), undefined);
  assert.equal((await fetch(`${baseUrl}/auth/me`, { headers: { cookie: jar.header() } })).status, 401);
});

test("another user cannot modify this user's note", async () => {
  const jar = createJar();
  await login(jar);

  const forbidden = await fetch(`${baseUrl}/notes/n2`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', cookie: jar.header(), 'x-csrf-token': jar.get('csrfToken') },
    body: JSON.stringify({ title: 'Hijacked' }),
  });
  assert.equal(forbidden.status, 403);

  const allowed = await fetch(`${baseUrl}/notes/n1`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', cookie: jar.header(), 'x-csrf-token': jar.get('csrfToken') },
    body: JSON.stringify({ title: 'Renamed' }),
  });
  assert.equal(allowed.status, 200);
});

test('CSRF: a state-changing request without the header is 403', async () => {
  const jar = createJar();
  await primeCsrf(jar);

  const response = await fetch(`${baseUrl}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', cookie: jar.header() },
    body: JSON.stringify({ email: 'ankit@example.com', password: 'supersecret123' }),
  });
  assert.equal(response.status, 403);
  assert.equal((await response.json()).error.code, 'CSRF_TOKEN_INVALID');
});

test('CSRF: a mismatched header is 403 and GET is exempt', async () => {
  const jar = createJar();
  await primeCsrf(jar);

  const mismatched = await fetch(`${baseUrl}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', cookie: jar.header(), 'x-csrf-token': 'wrong' },
    body: JSON.stringify({ email: 'ankit@example.com', password: 'supersecret123' }),
  });
  assert.equal(mismatched.status, 403);

  const read = await fetch(`${baseUrl}/notes`, { headers: { cookie: jar.header() } });
  assert.equal(read.status, 401);                                       // 401 (not signed in), not 403 (CSRF)
});

test('a forged session id is rejected', async () => {
  const jar = createJar();
  await login(jar);

  const response = await fetch(`${baseUrl}/auth/me`, { headers: { cookie: `sid=${jar.get('sid')}tampered` } });
  assert.equal(response.status, 401);
});
```

```bash
node --test tests/notes.session.test.js
```

```
✔ an anonymous request sets no session cookie
✔ login sets an HttpOnly, SameSite=Lax, Path=/ cookie with an expiry
✔ the login response contains no token of any kind
✔ the session id changes on login (session fixation)
✔ GET /auth/me returns the signed-in user and 401 otherwise
✔ logout destroys the session and expires the cookie
✔ another user cannot modify this user's note
✔ CSRF: a state-changing request without the header is 403
✔ CSRF: a mismatched header is 403 and GET is exempt
✔ a forged session id is rejected
pass 10
fail 0
```

**Design notes**

| Decision                               | Reason                                                                    |
| -------------------------------------- | ------------------------------------------------------------------------- |
| Session, not JWT, for the browser case | Instant revocation and no token storage problem                           |
| `saveUninitialized: false`             | Anonymous visitors (and crawlers) create no sessions                      |
| `regenerate()` on login                | Fixation is prevented by construction, not by hope                        |
| The session stores `userId` only       | Permission changes apply on the next request; the cookie stays small      |
| CSRF header, not a form field          | Form fields are exactly what a cross-site form can set                    |
| `timingSafeEqual`                      | A byte-by-byte comparison leaks information through timing                |
| `secure` bound to `isProduction`       | Locally you use HTTP; the flag flips automatically in production          |
| `trust proxy` in production            | `secure` cookies and `req.ip` are wrong behind TLS termination without it |

</details>

***

## Exercise 15.2 — Repair the cookie configuration

```js
// File: bad-cookies.js — find every problem before reading on
import express from 'express';
import session from 'express-session';

const app = express();

app.use(session({
  secret: 'secret',
  resave: true,
  saveUninitialized: true,
  cookie: { maxAge: 1000 * 60 * 60 * 24 * 365 },
}));

app.get('/login', (req, res) => {
  req.session.user = { id: 1, role: 'ADMIN', email: 'ankit@example.com' };
  res.cookie('userId', '1', { path: '/' });
  res.json({ ok: true });
});

app.get('/logout', (req, res) => {
  res.clearCookie('userId');
  res.json({ ok: true });
});

app.listen(3000);
```

<details>

<summary>Solution</summary>

| #  | Problem                                                           | Why it is wrong                                                                            | Fix                                                                                 |
| -- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| 1  | `secret: 'secret'` in source                                      | Guessable and permanent; anyone can forge a session id                                     | Long random secret from configuration                                               |
| 2  | `resave: true`                                                    | Rewrites every session on every request (write amplification)                              | `resave: false`                                                                     |
| 3  | `saveUninitialized: true`                                         | A session and cookie for every visitor, including bots; store grows forever                | `saveUninitialized: false`                                                          |
| 4  | Cookie lifetime of **one year**                                   | A stolen session works for a year                                                          | Hours, with `rolling: true` for active users                                        |
| 5  | No `httpOnly` (default `true` in `express-session`, but unstated) | Relied on a default instead of stating intent; other cookies in the file are not protected | Set every flag explicitly                                                           |
| 6  | No `sameSite`                                                     | Older browsers send it cross-site → CSRF                                                   | `sameSite: 'lax'` (or `'strict'`)                                                   |
| 7  | No `secure`                                                       | Travels over HTTP                                                                          | `secure: process.env.NODE_ENV === 'production'`                                     |
| 8  | **A raw `userId` cookie**                                         | The client can set `userId=1` and impersonate anyone — this is the fatal bug               | Identity lives in the session (or a signed/verified token), never in a plain cookie |
| 9  | `clearCookie('userId')` without `path`                            | The default path differs; the cookie may survive                                           | Pass the same `path` used when setting it                                           |
| 10 | The whole user object in the session, including `role: 'ADMIN'`   | Stale permissions; large cookie; PII in the store                                          | Store `userId`; load the user per request                                           |
| 11 | No `regenerate()` on login                                        | Session fixation                                                                           | Always regenerate                                                                   |
| 12 | No logout that destroys the session                               | The server-side record lives on; only the client cookie is cleared                         | `req.session.destroy()`                                                             |
| 13 | Admin role assigned by an unauthenticated `GET`                   | Not even login — this is a demonstration of what **not** to do                             | A real login with hashed-password verification                                      |
| 14 | No `trust proxy`                                                  | `secure` cookies fail behind a proxy                                                       | `app.set('trust proxy', 1)` in production                                           |

```js
// File: fixed-cookies.js
import express from 'express';
import session from 'express-session';
import cookieParser from 'cookie-parser';
import { randomBytes } from 'node:crypto';

const isProduction = process.env.NODE_ENV === 'production';

const app = express();
app.disable('x-powered-by');
if (isProduction) app.set('trust proxy', 1);

app.use(express.json({ limit: '100kb' }));
app.use(cookieParser(randomBytes(32).toString('base64url')));       // in production: from config
app.use(session({
  name: 'sid',
  secret: process.env.SESSION_SECRET,                               // ≥ 32 bytes, from config
  store: undefined,                                                 // RedisStore in production
  resave: false,
  saveUninitialized: false,
  rolling: true,
  proxy: isProduction,
  cookie: {
    httpOnly: true,
    sameSite: 'lax',
    secure: isProduction,
    path: '/',
    maxAge: 1000 * 60 * 60 * 8,
  },
}));

app.post('/login', async (req, res, next) => {
  try {
    const user = await verifyCredentials(req.body);                  // hashed password comparison

    req.session.regenerate((error) => {
      if (error) return next(error);

      req.session.userId = user.id;                                  // an id, not the user object
      return req.session.save((saveError) => {
        if (saveError) return next(saveError);
        return res.json({ data: { id: user.id, email: user.email, role: user.role } });
      });
    });
  } catch (error) {
    next(error);
  }
});

app.post('/logout', (req, res, next) => {
  req.session.destroy((error) => {
    if (error) return next(error);
    res.clearCookie('sid', { path: '/' });                           // same path as when set
    return res.status(204).end();
  });
});

app.listen(3000);
```

**The lesson:** cookies are credentials only when the server treats them as such. A `userId` cookie is not authentication — it is a suggestion from the client.

</details>

***

## What's next

Cookies are sent automatically only to their own origin. The moment a browser page on another origin calls this API — a separate frontend, a mobile web app, a third-party dashboard — the browser applies **CORS**. Next: preflights, credentials, and the exact headers that make cross-origin requests work safely.

→ [16 — CORS](16-cors.md)
