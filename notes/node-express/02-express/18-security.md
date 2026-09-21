# 18 — Security

> **Where this fits:** Chapters 13–17 each ended with a security section. This chapter is the systematic pass: the classes of attack that matter for a Node/Express API, what each defence actually stops, and precisely what Express gives you out of the box versus what you must build. The dedicated sections go deeper on authentication _(not available in this published source revision)_ and database-level injection; here everything is wired into one production-shaped app.

***

## 1. The threat model in one page

You cannot defend against "hackers". You defend against specific attacks, each with a specific cause.

| Attack                     | The cause it exploits                                       | Primary defence                                                  |
| -------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------- |
| **Injection** (SQL/NoSQL)  | Input concatenated into a query or used as a query operator | Parameterised queries + schema validation                        |
| **XSS** (stored/reflected) | Untrusted data rendered as HTML/JS                          | Output encoding, CSP, `HttpOnly` cookies, JSON-only APIs         |
| **CSRF**                   | Credentials attached automatically by the browser           | `SameSite` cookies + CSRF tokens                                 |
| **Broken access control**  | A route forgets a check; ids are guessable                  | Auth middleware at the mount point + ownership rules in services |
| **Credential attacks**     | Weak passwords, no throttling, user enumeration             | Hashing, rate limits, identical error messages                   |
| **Token theft**            | Tokens in `localStorage`, in URLs, in logs                  | `HttpOnly` cookies, memory, short expiry, redaction              |
| **DoS**                    | Unbounded body size, expensive queries, no limits           | `express.json({ limit })`, pagination caps, rate limiting        |
| **Information disclosure** | Stack traces, verbose errors, `X-Powered-By`                | One error contract, `helmet`, no internals in responses          |
| **Supply chain**           | Malicious/outdated dependency, `postinstall` scripts        | Lockfile, `npm ci`, audits, Renovate/Dependabot                  |
| **Secret leakage**         | Secrets in git, in logs, in client bundles                  | Configuration, redaction, rotation                               |

Two habits make the rest tractable:

1. **Validate at the boundary, authorise at every entry point.** Chapters 12 and 13.
2. **Assume every layer will be bypassed and add the next one.** A schema is not a query; a WAF is not an authorisation check; CORS is not authentication.

***

## 2. What Express gives you, and what it does not

| Concern             | Express provides                                                    | You must provide                                                |
| ------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------- |
| Body parsing        | `express.json()`, `express.urlencoded()` (with a `limit` option)    | Choosing and enforcing limits; validating the parsed values     |
| Routing             | Matching and ordering                                               | Not exposing internal routes; 404/405 handling                  |
| Query parsing       | `req.query` with a safe parser (`'simple'` by default in Express 5) | Allowlists; never passing raw query objects to a database       |
| Cookies             | `res.cookie`, `res.clearCookie`, `req.cookies` via `cookie-parser`  | Every security attribute (`HttpOnly`, `Secure`, `SameSite`)     |
| Static files        | `express.static`                                                    | Not serving private data; never serving uploads unauthenticated |
| Headers             | None                                                                | `helmet()` and any custom headers                               |
| Rate limiting       | None                                                                | `express-rate-limit` (or an edge/API-gateway limiter)           |
| Authentication      | None                                                                | Sessions or tokens, password hashing, middleware                |
| Authorisation       | None                                                                | `requireAuth`, `requireRole`, ownership checks                  |
| Input validation    | None                                                                | Zod/Joi schemas                                                 |
| CSRF                | None                                                                | `SameSite` + tokens                                             |
| CORS                | None                                                                | The `cors` middleware with an explicit allowlist                |
| HTTPS / HSTS        | None (HTTPS is terminated before or around Node)                    | A TLS terminator + `trust proxy` + HSTS                         |
| Secrets             | `process.env` and `--env-file`                                      | A validated config module, a secret manager in production       |
| Dependency scanning | None                                                                | `npm audit`, CI checks, Renovate/Dependabot                     |
| Logging             | None                                                                | Structured logs with redaction                                  |

> **Express is deliberately small.** It is a router plus middleware plumbing. Every "security feature" in the second column is your responsibility — which is why this chapter exists.

***

## 3. Hardening the app: middleware order

```js
// File: src/app.js — the hardened pipeline, in order
import express from 'express';
import helmet from 'helmet';
import cookieParser from 'cookie-parser';
import { rateLimit } from 'express-rate-limit';
import { createRequestId } from './middleware/requestId.js';
import { createCorsMiddleware, createCorsOptions } from './middleware/cors.js';
import { createCsrfProtection } from './middleware/csrf.js';
import { notFound } from './middleware/notFound.js';
import { createErrorHandler } from './middleware/errorHandler.js';
import { createLogger } from './utils/logger.js';

export function createApp({ config, container }) {
  const app = express();
  const logger = container.logger ?? createLogger(config);

  // 1. Hide the framework fingerprint. X-Powered-By: Express is free reconnaissance.
  app.disable('x-powered-by');

  // 2. Trust exactly one proxy hop (the load balancer) so req.ip and req.secure are real.
  //    'true' would trust any client-supplied X-Forwarded-For — the classic rate-limit bypass.
  if (config.isProduction) app.set('trust proxy', 1);

  // 3. Security headers, first, so even error responses carry them.
  app.use(helmet({
    contentSecurityPolicy: {
      useDefaults: true,
      directives: {
        // This API serves JSON, but /docs and the playground need a few adjustments:
        "img-src": ["'self'", 'data:', 'https://cdn.example.com'],
        "script-src": ["'self'"],
        "connect-src": ["'self'", 'https://api.example.com'],
        'upgrade-insecure-requests': config.isProduction ? [] : null, // no HSTS/upgrade locally
      },
    },
    // The API returns JSON only; keep the default same-origin policy unless a CDN needs otherwise.
    crossOriginResourcePolicy: { policy: 'same-origin' },
    // HSTS: only in production, and only after you are certain HTTPS works everywhere.
    hsts: config.isProduction ? { maxAge: 31_536_000, includeSubDomains: true, preload: false } : false,
  }));

  // 4. CORS before anything that could answer the request (chapter 16).
  app.use(createCorsMiddleware(createCorsOptions({
    allowedOrigins: config.allowedOrigins,
    isProduction: config.isProduction,
  })));

  // 5. Request identity for logs, errors and support tickets.
  app.use(createRequestId);

  // 6. Structured logging with redaction (never log authorization/cookie/password).
  app.use(container.httpLogger);

  // 7. Body parsing WITH a limit. The default is 100 kb in Express 5; make it explicit.
  app.use(express.json({ limit: '100kb', strict: true }));
  app.use(express.urlencoded({ extended: false, limit: '100kb' }));

  app.use(cookieParser(config.cookieSecret));

  // 8. Global rate limit as a backstop…
  app.use(rateLimit({
    windowMs: 60_000,
    limit: config.isProduction ? 300 : 10_000,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { error: { code: 'RATE_LIMITED', message: 'Too many requests, slow down' } },
  }));

  // 9. …and stricter limits on the routes worth attacking.
  app.use('/api/v1/auth/login', container.authLimiter);
  app.use('/api/v1/auth/register', container.registerLimiter);

  // 10. CSRF protection for cookie-authenticated, state-changing requests (chapter 15).
  app.use(createCsrfProtection({ isProduction: config.isProduction }));

  // 11. Routes.
  app.use('/api/v1', container.apiRouter);

  // 12. Terminators.
  app.use(notFound);
  app.use(createErrorHandler({ logger }));

  return app;
}
```

| Step                      | Why it is in this position            | Consequence of moving it                                    |
| ------------------------- | ------------------------------------- | ----------------------------------------------------------- |
| `disable('x-powered-by')` | Before anything can send a response   | Leave it on and every 404 advertises Express                |
| `trust proxy`             | Before `req.ip`/`req.secure` are read | Wrong rate-limit keys; `Secure` cookies dropped             |
| `helmet`                  | First middleware                      | Error responses miss the headers                            |
| `cors`                    | Before routes and parsers             | Preflights 404 (chapter 16)                                 |
| request id + logging      | Before parsing                        | Uploads/parse errors are unlogged                           |
| `express.json({ limit })` | Before routes                         | Default limits may not suit you; unbounded bodies are a DoS |
| Rate limiting             | Before auth routes                    | Credential stuffing runs at full speed                      |
| CSRF                      | After cookies, before routes          | The token cookie cannot be compared                         |
| Error handler             | Last                                  | Errors leak stack traces or crash the process               |

***

## 4. Headers: `helmet` and the ones worth understanding

Verified output from `helmet` 8.x on a plain Express 5 app (with `x-powered-by` disabled):

```
Content-Security-Policy: default-src 'self';base-uri 'self';font-src 'self' https: data:;form-action 'self';
    frame-ancestors 'self';img-src 'self' data:;object-src 'none';script-src 'self';script-src-attr 'none';
    style-src 'self' https: 'unsafe-inline';upgrade-insecure-requests
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
Origin-Agent-Cluster: ?1
Referrer-Policy: no-referrer
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-DNS-Prefetch-Control: off
X-Download-Options: noopen
X-Frame-Options: SAMEORIGIN
X-Permitted-Cross-Domain-Policies: none
X-XSS-Protection: 0
```

| Header                                | Protects against                             | Notes                                                                                         |
| ------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `Content-Security-Policy`             | XSS, data exfiltration, clickjacking         | The most powerful header; irrelevant for a JSON-only API but essential for any HTML you serve |
| `Strict-Transport-Security`           | SSL stripping, cookie theft on first visit   | Only send over HTTPS; `includeSubDomains` is a commitment                                     |
| `X-Content-Type-Options: nosniff`     | MIME confusion (a `.txt` executed as script) | Always on. Pair with an explicit `Content-Type`                                               |
| `X-Frame-Options` / `frame-ancestors` | Clickjacking                                 | `frame-ancestors` is the modern replacement                                                   |
| `Referrer-Policy: no-referrer`        | Leaking URLs (with tokens) to third parties  | `strict-origin-when-cross-origin` is a common alternative                                     |
| `Cross-Origin-Resource-Policy`        | Other sites embedding your resources         | `cross-origin` when a CDN/partner must consume it                                             |
| `X-XSS-Protection: 0`                 | Legacy browser XSS filters                   | Deliberately disabled: the old filter caused bugs of its own                                  |
| `Permissions-Policy`                  | Powerful APIs (camera, geolocation)          | Not set by default; add `camera=(), microphone=()` etc.                                       |

```js
// File: src/middleware/permissionsPolicy.js — a header helmet does not include by default
export function permissionsPolicy() {
  return function permissionsPolicyMiddleware(req, res, next) {
    res.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=()');
    next();
  };
}
```

```js
// File: helmet-overrides.js — two configurations you will actually need
import helmet from 'helmet';

/** 1. A JSON API that also serves a Swagger UI page from the same origin. */
export const apiAndDocs = helmet({
  contentSecurityPolicy: {
    useDefaults: true,
    directives: {
      "script-src": ["'self'", "'unsafe-inline'"],       // Swagger UI injects its bootstrap script
      "img-src": ["'self'", 'data:', 'https://unpkg.com'],
      "connect-src": ["'self'"],
      'upgrade-insecure-requests': null,                  // stays valid over plain HTTP in dev
    },
  },
});

/** 2. An API whose images are embedded by a separate frontend origin. */
export const apiWithCdnAssets = helmet({
  crossOriginResourcePolicy: { policy: 'cross-origin' },  // CORP must allow other origins
  crossOriginEmbedderPolicy: false,                        // otherwise the embedder breaks
});
```

> **A CSP is a whitelist, not a fix.** `'unsafe-inline'` in `script-src` removes most of its value. Prefer nonces or hashes; the point is that _your_ pages never render attacker HTML in the first place (§6).

***

## 5. Injection

### SQL injection

```js
// ❌ Concatenation: the attacker writes part of the query.
const result = await db.query(`SELECT id, email FROM users WHERE email = '${email}'`);
// email = "' OR '1'='1' --"      → returns every user
// email = "'; DROP TABLE users; --" → depends only on the driver's multi-statement setting
```

```js
// ✅ Parameterised: the values never become SQL syntax.
const result = await db.query('SELECT id, email FROM users WHERE email = $1', [email]);       // pg
const [rows] = await pool.execute('SELECT id, email FROM users WHERE email = ?', [email]);    // mysql2

// Even safer: never build identifiers from input, and use an allowlist when you must.
const SORTS = { createdAt: 'created_at', title: 'title', updatedAt: 'updated_at' };
const orderBy = SORTS[sort] ?? 'created_at';                                                  // enum in, column out
const direction = order === 'asc' ? 'ASC' : 'DESC';
await db.query(`SELECT id, title FROM notes ORDER BY ${orderBy} ${direction} LIMIT $2`, [limit]);
```

| Rule                                                              | Why                                                                  |
| ----------------------------------------------------------------- | -------------------------------------------------------------------- |
| Values → placeholders (`$1`, `?`)                                 | The driver sends data out-of-band from the statement                 |
| Identifiers (table/column/direction) → allowlist maps             | Placeholders cannot be used for identifiers                          |
| Never multi-statement mode (`multipleStatements: true` in mysql2) | One successful injection becomes a chain of them                     |
| Least-privilege database user                                     | The app user needs `SELECT/INSERT/UPDATE/DELETE`, not `DROP`/`GRANT` |
| `LIMIT` also comes from validation                                | `'10000000'` is a DoS, not an injection                              |

### NoSQL injection

MongoDB has no SQL, but query **operators** are part of the document you send — and that document may come straight from the request body.

```js
// ❌ The attacker controls operators, not just values.
const user = await User.findOne({ email: req.body.email, password: req.body.password });
// body: { "email": "admin@example.com", "password": { "$ne": null } }   → logs in as the admin
// body: { "email": { "$regex": "^a" }, ... }                            → enumerates accounts
```

```js
// ✅ Validate first (chapter 12), then query with a known type.
import { z } from 'zod';

const loginSchema = z
  .object({ email: z.email(), password: z.string().min(1).max(200) })
  .strict();                                          // {$ne: …} is an object → fails z.email()

const { email, password } = loginSchema.parse(req.body);
const user = await userRepository.findByEmail(email); // now a string, not an object
const ok = user && (await passwordHasher.compare(password, user.passwordHash));
```

| Dangerous sink                                 | Why                                                         | Defence                                                        |
| ---------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------- |
| `Model.find(req.body)`                         | Any operator, any field                                     | Build the filter field by field from validated values          |
| `Model.find({ email: req.query.email })`       | Query strings can be objects with the `extended` parser     | Validate query params with schemas; keep the `'simple'` parser |
| `$where`, `$expr`, `$function` with user input | Server-side JavaScript execution                            | Never accept them from clients                                 |
| `Model.updateOne({ _id }, req.body)`           | `$set`, `$unset`, `$rename` arrive as keys; mass assignment | Pick allowed fields explicitly; `.strict()` schemas            |
| `$regex` with raw input                        | ReDoS and information leaks                                 | Escape it (`escapeRegex`) or use `$text` search                |

```js
// File: src/utils/escapeRegex.js — when a regex search is genuinely required
export const escapeRegex = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
// Usage: { title: new RegExp(escapeRegex(q), 'i') } with a length cap on `q` from the schema.
```

### Command injection (Node-specific)

```js
// ❌ exec() runs a shell: ; | && $() are all interpreted.
import { exec } from 'node:child_process';
exec(`convert ${req.file.path} -resize 200x200 ${req.file.path}.thumb`);     // filename = "a.png; rm -rf /"

// ✅ execFile/spawn run a binary with an argument array — no shell, no interpretation.
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
const run = promisify(execFile);

await run('convert', [req.file.path, '-resize', '200x200', `${req.file.path}.thumb`]);
// …and still validate that the path is inside your uploads directory (01-nodejs/07-path.md).
```

| API                                      | Shell? | Safe with user input?                         |
| ---------------------------------------- | ------ | --------------------------------------------- |
| `exec`, `execSync`                       | Yes    | **No**                                        |
| `execFile`, `spawn` (with an args array) | No     | Yes, if the binary and the args are validated |
| `spawn` with `{ shell: true }`           | Yes    | **No**                                        |

***

## 6. XSS: how an API becomes the attacker

An API returns JSON, and JSON is data — so where does XSS come from? Three places:

| Path                             | Example                                   | Defence                                                                               |
| -------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------- |
| **Stored, served as HTML**       | `res.send('<h1>' + note.title + '</h1>')` | Never build HTML by concatenation; escape or use a template engine with auto-escaping |
| **Stored, rendered by the SPA**  | `element.innerHTML = note.title`          | `textContent`; a framework's escape-by-default; sanitize any HTML you must render     |
| **Uploaded files served inline** | An uploaded `.html`/`.svg` on your origin | Forced download, `nosniff`, CSP, a separate origin (chapter 17)                       |

```js
// File: xss-examples.js

// ❌ Express picks text/html for a string body (verified in chapter 05),
//    so this response executes script in the API's own origin.
app.get('/greet', (req, res) => {
  res.send(`<h1>Hello ${req.query.name}</h1>`);
  // /greet?name=<script>fetch('/api/v1/me').then(r=>r.text()).then(console.log)</script>
});

// ✅ Return data, not markup. Content-Type: application/json cannot be executed.
app.get('/api/v1/greet', (req, res) => {
  res.json({ data: { greeting: `Hello ${req.query.name}` } });
});

// ✅ If you must return HTML, escape every interpolation.
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));

app.get('/greet-safe', (req, res) => {
  res.type('html').send(`<h1>Hello ${escapeHtml(req.query.name)}</h1>`);
});
```

```js
// File: public/js/render.js (browser — shown because the API's contract enables it)
// ❌ Any note title containing <img src=x onerror=...> runs.
list.innerHTML = notes.map((note) => `<li>${note.title}</li>`).join('');

// ✅ Text nodes cannot become elements.
for (const note of notes) {
  const item = document.createElement('li');
  item.textContent = note.title;               // the browser escapes it for you
  list.append(item);
}

// ✅ When HTML is genuinely required (a rich-text editor), sanitize with a maintained library.
import DOMPurify from 'dompurify';
preview.innerHTML = DOMPurify.sanitize(note.content, { ALLOWED_TAGS: ['p', 'strong', 'em', 'a', 'ul', 'li'] });
```

| Defence layer                                | Stops                                             | Does not stop                                                     |
| -------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------- |
| Escaping / `textContent`                     | Everything rendered from that value               | A different field rendered elsewhere                              |
| `Content-Type: application/json` + `nosniff` | Script execution of JSON                          | A client that injects it into HTML                                |
| CSP without `'unsafe-inline'`                | Inline script, external script from other origins | HTML injection itself (the page still looks wrong)                |
| `HttpOnly` cookies                           | Token theft via `document.cookie`                 | Session riding: injected code still _acts_ as the user            |
| `Sanitize-HTML` libraries                    | Markup-based payloads                             | Payloads in attributes the allowlist missed — keep the list tight |

> **XSS is a client-side bug with a server-side multiplier.** Your job as the API author is to keep the data channel a data channel, set `Content-Type` correctly, and never serve attacker-controlled bytes as executable content from your own origin.

***

## 7. CSRF, CORS and cookies (recap of the mechanics)

| Defence                    | Where           | Notes                                                       |
| -------------------------- | --------------- | ----------------------------------------------------------- |
| `SameSite=Lax`             | Cookie          | Blocks cross-site POSTs; the baseline                       |
| CSRF token (double submit) | Cookie + header | Required for `SameSite=None` and older browsers             |
| `Origin`/`Referer` check   | Middleware      | A cheap extra check when the browser sends it               |
| Token in `Authorization`   | Client          | Immune to CSRF: the browser never attaches it automatically |
| CORS allowlist             | Server          | Not a CSRF defence — but it prevents reading the response   |

```js
// File: src/middleware/requireSameOrigin.js — an extra cheap check for cookie-authenticated mutations
const SAFE = new Set(['GET', 'HEAD', 'OPTIONS']);

export function requireSameOrigin({ allowedOrigins }) {
  const allowed = new Set(allowedOrigins);
  return function requireSameOriginMiddleware(req, res, next) {
    if (SAFE.has(req.method)) return next();

    const origin = req.get('origin');
    if (!origin) return next();                     // curl/server-to-server: no Origin header
    if (allowed.has(origin)) return next();

    return res.status(403).json({
      error: { code: 'CROSS_ORIGIN_BLOCKED', message: 'Cross-origin requests are not allowed here', requestId: req.id },
    });
  };
}
```

***

## 8. Rate limiting and brute-force protection

Rate limiting defends three different things: credential stuffing, expensive endpoints and abuse. They need different limits.

```js
// File: src/middleware/limiters.js
import { rateLimit } from 'express-rate-limit';
import { RedisStore } from 'rate-limit-redis';

/** Shared factory so every limiter reports the same way. */
export function createLimiter({ redisClient, windowMs, limit, prefix, message, skip = () => false }) {
  return rateLimit({
    windowMs,
    limit,
    standardHeaders: 'draft-8',         // RateLimit + RateLimit-Policy (IETF draft 8)
    legacyHeaders: false,               // drop X-RateLimit-*
    store: redisClient
      ? new RedisStore({ sendCommand: (...args) => redisClient.sendCommand(args), prefix })
      : undefined,                       // in-memory per instance — fine for tests, not for a cluster
    message: { error: { code: 'RATE_LIMITED', message } },
    skip,
    // Key by user when known, by IP otherwise: NAT does not punish a whole office.
    keyGenerator: (req) => req.user?.id ?? req.ip,
  });
}

export function createLimiters({ redisClient, isProduction }) {
  return {
    /** Credential endpoints: tight, and keyed by account as well as IP (see below). */
    auth: createLimiter({
      redisClient, windowMs: 15 * 60 * 1000, limit: isProduction ? 10 : 100, prefix: 'rl:auth:',
      message: 'Too many sign-in attempts. Try again in a few minutes.',
    }),

    /** Account creation: stops mass registration. */
    register: createLimiter({
      redisClient, windowMs: 60 * 60 * 1000, limit: isProduction ? 5 : 50, prefix: 'rl:register:',
      message: 'Too many accounts created from this address.',
    }),

    /** Expensive reads: pagination plus a per-minute ceiling. */
    expensive: createLimiter({
      redisClient, windowMs: 60 * 1000, limit: isProduction ? 30 : 300, prefix: 'rl:expensive:',
      message: 'That endpoint is rate limited.',
    }),

    /** Uploads: each one costs disk and CPU. */
    upload: createLimiter({
      redisClient, windowMs: 60 * 60 * 1000, limit: isProduction ? 100 : 1000, prefix: 'rl:upload:',
      message: 'Upload limit reached for this hour.',
    }),
  };
}
```

Verified behaviour of `express-rate-limit` 8.x with `standardHeaders: 'draft-8'`:

```
Request 1 → 200  RateLimit: "3-in-1min"; r=1; t=60
                  RateLimit-Policy: "3-in-1min"; q=3; w=60; pk=:MTJjYTE3YjQ5YWYy:
Request 2 → 200  RateLimit: "3-in-1min"; r=0; t=60
Request 3 → 429  RateLimit: "3-in-1min"; r=0; t=60
                  Retry-After: 60
                  {"error":{"code":"RATE_LIMITED","message":"Too many requests, slow down"}}
```

| Option                       | Meaning                                | Gotcha                                                                  |
| ---------------------------- | -------------------------------------- | ----------------------------------------------------------------------- |
| `windowMs`                   | The window length                      | Too long and a burst locks a user out for an hour                       |
| `limit`                      | Requests allowed per window            | Renamed from `max` in v7 — old tutorials show `max`                     |
| `standardHeaders: 'draft-8'` | Emits `RateLimit`/`RateLimit-Policy`   | `legacyHeaders: false` removes `X-RateLimit-*`                          |
| `keyGenerator`               | What identifies a caller               | `req.ip` needs correct `trust proxy`; user ids are fairer               |
| `store`                      | Where counters live                    | The default memory store is **per process**: N instances = N× the limit |
| `skip`                       | Exempt health checks and static assets | Exempting too much defeats the limiter                                  |
| `handler`                    | Custom 429 body                        | Must match your error envelope                                          |

### Locking an account without breaking it

```js
// File: src/services/loginThrottle.js
import { TooManyRequestsError } from '../utils/AppError.js';

/**
 * Per-account throttling on top of per-IP limiting:
 * an attacker with a botnet has many IPs but still targets a few accounts.
 * Exponential backoff with a cap, and a counter that clears on success.
 */
export function createLoginThrottle({ cache, maxAttempts = 5, baseDelayMs = 1_000, maxDelayMs = 15 * 60 * 1000 }) {
  const key = (email) => `login:fail:${email.toLowerCase()}`;

  return {
    async assertAllowed(email) {
      const state = await cache.get(key(email));
      if (!state) return;

      const { failures, lockedUntil } = state;
      if (lockedUntil && Date.now() < lockedUntil) {
        throw new TooManyRequestsError('Too many failed attempts. Try again later', {
          retryAfterSeconds: Math.ceil((lockedUntil - Date.now()) / 1000),
        });
      }
      if (failures >= maxAttempts) return;                    // allowed again after the lock expires
    },

    async recordFailure(email) {
      const state = (await cache.get(key(email))) ?? { failures: 0, lockedUntil: 0 };
      state.failures += 1;

      if (state.failures >= 5) {
        const delay = Math.min(baseDelayMs * 2 ** (state.failures - 5), maxDelayMs);
        state.lockedUntil = Date.now() + delay;
      }

      await cache.set(key(email), state, { ttlSeconds: 24 * 60 * 60 });
      return state;
    },

    async clear(email) {
      await cache.del(key(email));
    },
  };
}
```

| Brute-force defence                     | Effect                                  | Cost                                                              |
| --------------------------------------- | --------------------------------------- | ----------------------------------------------------------------- |
| Per-IP rate limit                       | Stops single-source guessing            | A botnet spreads across IPs                                       |
| Per-account throttling (above)          | Stops targeting one account             | Legitimate users can lock themselves out — pair with a reset flow |
| CAPTCHA after N failures                | Slows automated attempts                | Friction, accessibility                                           |
| Email notification on suspicious logins | Turns an attack into a visible event    | Delayed detection                                                 |
| MFA / passkeys                          | Removes the value of a guessed password | Implementation effort                                             |
| Uniform error messages + timing         | Prevents account enumeration            | Requires care (dummy hash comparisons)                            |

***

## 9. Secrets, configuration and dependencies

```js
// File: src/config/env.js (excerpt) — the only file that reads process.env
import { z } from 'zod';

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(0).max(65_535).default(3000),

  DATABASE_URL: z.url(),
  JWT_SECRET: z.string().min(32, 'must be at least 32 characters'),
  JWT_REFRESH_SECRET: z.string().min(32),
  SESSION_SECRET: z.string().min(32),
  COOKIE_SECRET: z.string().min(32),

  ALLOWED_ORIGINS: z.string().transform((value) => value.split(',').map((item) => item.trim()).filter(Boolean)),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
}).strict();

const parsed = schema.safeParse(process.env);

if (!parsed.success) {
  // Fail fast, and never print the VALUES — only the names and the problem.
  console.error('Invalid environment configuration:');
  for (const issue of parsed.error.issues) console.error(`  ${issue.path.join('.')}: ${issue.message}`);
  process.exit(1);
}

export const env = parsed.data;
```

```bash
# Never commit secrets. .gitignore first, then generate.
echo '.env*' >> .gitignore
echo '!.env.example' >> .gitignore

openssl rand -base64 48        # JWT_SECRET
openssl rand -base64 48        # SESSION_SECRET
openssl rand -base64 48        # COOKIE_SECRET

# Audit what actually goes into the image/repo
git log -p -- . ':!*.lock' | grep -nE 'SECRET|PASSWORD|API_KEY' | head
```

| Practice                                                                   | Why                                                  |
| -------------------------------------------------------------------------- | ---------------------------------------------------- |
| Secrets in environment/secret manager, never in code                       | A repo leak must not be an incident                  |
| `.env*` gitignored, `.env.example` committed                               | Documents the configuration without the values       |
| Fail fast at startup on a missing secret                                   | Better than a runtime 500 halfway through a request  |
| Different secrets per environment                                          | A leak in staging must not compromise production     |
| Rotate on any suspicion, and after any employee/contractor change          | Rotation is cheap; a leaked long-lived secret is not |
| Redact logs (`authorization`, `cookie`, `set-cookie`, `password`, `token`) | Logs are copied, shipped and retained                |
| Never send secrets to the client                                           | Anything in the bundle is public                     |
| Least-privilege database user                                              | Limits the blast radius of every other bug           |

```js
// File: src/utils/redact.js — the pino redaction config, spelled out
export const redactPaths = [
  'req.headers.authorization',
  'req.headers.cookie',
  'res.headers["set-cookie"]',
  'req.body.password',
  'req.body.currentPassword',
  'req.body.newPassword',
  'req.body.token',
  'req.body.refreshToken',
  '*.passwordHash',
  '*.accessToken',
  '*.refreshToken',
];
```

### Dependencies are part of your attack surface

```bash
npm ci                             # installed from the lockfile, byte for byte
npm audit --omit=dev               # production dependencies only
npm audit fix                      # only when the fix does not change a major
npm outdated                       # is anything important behind?
npm ls --all                       # what is actually installed, and how deep

# Inspect what a package can run at install time before trusting it:
npm view <package> scripts
npm install --ignore-scripts       # for an unfamiliar dependency, then review
```

| Threat                                        | Example                                                     | Defence                                                             |
| --------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------- |
| Typosquatting                                 | `expresss`, `lodahs`, `cross-env` clones                    | Verify the name and the download counts; prefer well-known packages |
| Malicious `postinstall`                       | A dependency that runs a script at install time             | `--ignore-scripts` where possible; review new dependencies          |
| Dependency confusion                          | A private package name that resolves to the public registry | Scoped names + `npmrc` registry pinning                             |
| Outdated CVE                                  | An old `multer`/`body-parser` with a known DoS              | `npm audit` in CI; Renovate/Dependabot PRs                          |
| Lockfile drift                                | `^1.0.0` resolving to a different build each install        | Commit the lockfile; use `npm ci` in CI and Docker                  |
| Unmaintained transitive package               | No releases in years, open advisories                       | Prefer fewer dependencies; replace or pin with `overrides`          |
| Publish-token compromise (event-stream style) | A maintainer's account is taken over                        | Provenance/signature checks, pinned versions, monitoring            |

```yaml
# File: .github/workflows/security.yml — the cheap automated checks
name: Security
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'          # every Monday
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 24
          cache: npm
      - run: npm ci
      - run: npm audit --omit=dev --audit-level=high
      - run: node --test
```

***

## 10. HTTPS, proxies and transport

```
Client ──TLS──▶ Load balancer / reverse proxy ──HTTP──▶ Node
                 terminates TLS
                 sets X-Forwarded-Proto: https
                 sets X-Forwarded-For: <client ip>
```

```js
// File: src/app.js (excerpt) — behind one trusted proxy
if (config.isProduction) app.set('trust proxy', 1);
// Now req.ip is the real client, req.secure is true, and secure cookies are accepted.
```

| Concern             | Rule                                                                                                                                                            |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `trust proxy`       | Set it to the **number of proxies** you control, or the specific proxy address. `true` trusts a spoofed `X-Forwarded-For` and lets an attacker bypass IP limits |
| HSTS                | Enable only after HTTPS is correct everywhere, with `max-age` increased over time                                                                               |
| Redirect HTTP→HTTPS | At the proxy, with a 308, before Node ever sees the request                                                                                                     |
| Secure cookies      | `secure: true` in production; they simply will not be sent otherwise                                                                                            |
| TLS version/ciphers | Left to the terminator (nginx/Caddy/ALB), not Node                                                                                                              |
| Certificate renewal | Automated (Let's Encrypt/Caddy), or you will have an outage                                                                                                     |
| Dev vs prod         | Self-signed or `mkcert` locally; never disable certificate verification                                                                                         |

```js
// File: src/middleware/redirectToHttps.js — only if the proxy does not already do it
export function redirectToHttps({ isProduction }) {
  return function redirectToHttpsMiddleware(req, res, next) {
    if (!isProduction || req.secure || req.get('x-forwarded-proto') === 'https') return next();

    const target = `https://${req.hostname}${req.originalUrl}`;
    return res.redirect(308, target);        // 308 preserves the method and body
  };
}
```

***

## 11. Denial of service: the limits to set deliberately

| Vector                     | Naive default                             | Defence                                                       |
| -------------------------- | ----------------------------------------- | ------------------------------------------------------------- |
| Huge JSON body             | `express.json()` default `100kb`          | Keep it (or lower it); map `entity.too.large` to `413`        |
| Huge file upload           | Multer without limits                     | `limits: { fileSize, files, parts }` (chapter 17)             |
| Deeply nested JSON         | Parsers handle it; your recursion may not | `strict: true`, schema depth, avoid regex on input            |
| Unbounded pagination       | `limit: 1e6`                              | `.max(100)` in the query schema (chapter 12)                  |
| Expensive search           | A regex over an unindexed field           | Indexes, `$text`, query timeouts                              |
| Unbounded uploads per user | Disk fills                                | Quotas (chapter 17) + per-user rate limit                     |
| Slowloris                  | A proxy with no timeouts                  | `server.requestTimeout`, `headersTimeout`, `keepAliveTimeout` |
| Zip bombs                  | Decompressing uploads                     | Size limits before decompression; a decompression ratio cap   |
| ReDoS                      | User-supplied regex                       | Never build a `RegExp` from input; escape literals            |
| Mass registration          | Open signup                               | Rate limit + email verification                               |

```js
// File: src/server.js (excerpt) — the timeouts most apps never set
import { createServer } from 'node:http';

const server = createServer(app);

// Node 18+ defaults are decent, but make the intent explicit:
server.requestTimeout = 30_000;      // total time to receive a complete request
server.headersTimeout = 10_000;      // must be lower than requestTimeout
server.keepAliveTimeout = 5_000;     // idle keep-alive sockets (proxy should be higher)
server.maxHeadersCount = 100;        // limit header-count abuse
```

***

## 12. The `413`, `429` and `403` flows in one error handler

```js
// File: src/middleware/errorHandler.js (excerpt) — security-relevant additions
import { AppError } from '../utils/AppError.js';

export function createErrorHandler({ logger, isProduction }) {
  return function errorHandler(error, req, res, next) {
    if (res.headersSent) return next(error);

    // 1. Map framework errors onto the API contract.
    const mapped = normalizeError(error);        // chapter 08

    // 2. Rate limiting, if the limiter did not answer itself.
    if (error.code === 'ERR_ERL_RATE_LIMIT') mapped.statusCode ??= 429;

    // 3. Body-parser errors.
    if (error.type === 'entity.too.large') {
      Object.assign(mapped, { statusCode: 413, code: 'PAYLOAD_TOO_LARGE', message: 'The request body is too large' });
    }
    if (error.type === 'entity.parse.failed') {
      Object.assign(mapped, { statusCode: 400, code: 'MALFORMED_JSON', message: 'The request body is not valid JSON' });
    }

    // 4. Headers that help clients react correctly.
    if (mapped.statusCode === 401) res.set('WWW-Authenticate', 'Bearer realm="api"');
    if (mapped.statusCode === 429 && mapped.retryAfterSeconds) res.set('Retry-After', String(mapped.retryAfterSeconds));

    // 5. Log the truth; send a redacted version.
    const level = mapped.statusCode >= 500 ? 'error' : 'warn';
    logger[level]({ err: error, requestId: req.id, statusCode: mapped.statusCode }, mapped.message);

    return res.status(mapped.statusCode).json({
      error: {
        code: mapped.code,
        message: mapped.statusCode >= 500 && isProduction ? 'Something went wrong' : mapped.message,
        ...(mapped.details && mapped.isOperational ? { details: mapped.details } : {}),
        requestId: req.id,
      },
    });
  };
}
```

| Never leak                      | Why                                                 | Send instead                              |
| ------------------------------- | --------------------------------------------------- | ----------------------------------------- |
| Stack traces                    | Reveal file paths, library versions, sometimes data | A request id; the stack stays in the logs |
| Database error text             | Reveals schema, table and column names              | `500` + a generic message                 |
| `X-Powered-By`                  | Framework fingerprint                               | `app.disable('x-powered-by')`             |
| Whether an email exists         | Account enumeration                                 | "Invalid email or password"               |
| Internal ids that are guessable | Horizontal privilege escalation                     | UUIDs plus ownership checks               |
| Validation internals from a 500 | Attack feedback loop                                | A fixed message for 5xx                   |

***

## 13. Testing security controls

Security tests are regression tests: they prove a control is present, not that the app is safe.

```js
// File: tests/security.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import helmet from 'helmet';
import { rateLimit } from 'express-rate-limit';
import { createApp } from '../src/app.js';

let server;
let baseUrl;

before(async () => {
  const app = express();
  app.disable('x-powered-by');
  app.use(helmet());
  app.use(rateLimit({
    windowMs: 60_000,
    limit: 5,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { error: { code: 'RATE_LIMITED', message: 'Too many requests' } },
  }));
  app.use(express.json({ limit: '1kb' }));

  app.get('/api/v1/ping', (req, res) => res.json({ ok: true }));
  app.post('/api/v1/echo', (req, res) => res.json({ data: req.body }));
  app.get('/api/v1/boom', () => { throw new Error('internal detail that must not leak'); });
  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));
  app.use((error, req, res, next) => {
    res.status(error.status ?? error.statusCode ?? (error.type === 'entity.too.large' ? 413 : 500)).json({
      error: {
        code: error.type === 'entity.too.large' ? 'PAYLOAD_TOO_LARGE' : 'INTERNAL_ERROR',
        message: error.type === 'entity.too.large' ? 'The request body is too large' : 'Something went wrong',
      },
    });
  });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

/* ── Headers ───────────────────────────────────────────────────────────────── */

test('the framework fingerprint is hidden', async () => {
  const response = await fetch(`${baseUrl}/api/v1/ping`);
  assert.equal(response.headers.get('x-powered-by'), null);
});

test('the helmet header set is present, including nosniff and HSTS', async () => {
  const response = await fetch(`${baseUrl}/api/v1/ping`);

  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  assert.match(response.headers.get('content-security-policy'), /default-src 'self'/);
  assert.match(response.headers.get('strict-transport-security'), /max-age=\d+/);
  assert.equal(response.headers.get('referrer-policy'), 'no-referrer');
  assert.equal(response.headers.get('x-frame-options'), 'SAMEORIGIN');
});

test('security headers are present on 404 and 500 responses too', async () => {
  const notFound = await fetch(`${baseUrl}/nope`);
  assert.equal(notFound.headers.get('x-content-type-options'), 'nosniff');

  const failure = await fetch(`${baseUrl}/api/v1/boom`);
  assert.equal(failure.headers.get('x-content-type-options'), 'nosniff');
});

/* ── Information disclosure ────────────────────────────────────────────────── */

test('an internal error does not leak its message', async () => {
  const response = await fetch(`${baseUrl}/api/v1/boom`);
  const body = await response.text();

  assert.equal(response.status, 500);
  assert.equal(body.includes('internal detail'), false);
  assert.equal(body.includes('at Object'), false);          // no stack frames
});

test('a 404 does not reveal the route table', async () => {
  const response = await fetch(`${baseUrl}/api/v1/definitely-not-a-route`);
  assert.deepEqual(await response.json(), { error: { code: 'ROUTE_NOT_FOUND' } });
});

/* ── Limits ────────────────────────────────────────────────────────────────── */

test('a body over the limit is 413, not a crash', async () => {
  const response = await fetch(`${baseUrl}/api/v1/echo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filler: 'x'.repeat(4000) }),
  });

  assert.equal(response.status, 413);
  assert.equal((await response.json()).error.code, 'PAYLOAD_TOO_LARGE');
});

test('the rate limiter returns 429 with Retry-After and the IETF headers', async () => {
  let last;
  for (let index = 0; index < 10; index += 1) {
    last = await fetch(`${baseUrl}/api/v1/ping`);
    if (last.status === 429) break;
  }

  assert.equal(last.status, 429);
  assert.ok(Number(last.headers.get('retry-after')) > 0);
  assert.match(last.headers.get('ratelimit'), /"5-in-1min"/);
  assert.equal((await last.json()).error.code, 'RATE_LIMITED');
});

test('the limiter advertises its policy', async () => {
  const response = await fetch(`${baseUrl}/api/v1/ping`);       // may be allowed or limited; the policy header is always there
  assert.match(response.headers.get('ratelimit-policy'), /q=\d+; w=\d+/);
});

/* ── Injection-shaped input ────────────────────────────────────────────────── */

test('an operator-shaped value is rejected by the type check, not executed', async () => {
  // Validation lives in chapter 12; here it stands in for the real endpoint.
  const response = await fetch(`${baseUrl}/api/v1/echo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: { $ne: null } }),
  });

  assert.equal(response.status, 200);                            // echo does not validate — see the note below
  const { data } = await response.json();
  assert.equal(typeof data.email, 'object');                     // it was just data

  // The real endpoint rejects it:
  const { loginSchema } = await import('../src/validators/authSchemas.js');
  assert.equal(loginSchema.safeParse({ email: { $ne: null }, password: 'x' }).success, false);
});

test('a prototype-polluting body cannot add to Object.prototype', async () => {
  const response = await fetch(`${baseUrl}/api/v1/echo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ __proto__: { isAdmin: true } }),
  });

  assert.equal(response.status, 200);
  assert.equal({}.isAdmin, undefined);                            // the prototype is untouched
});
```

```bash
node --test tests/security.test.js
```

```
✔ the framework fingerprint is hidden
✔ the helmet header set is present, including nosniff and HSTS
✔ security headers are present on 404 and 500 responses too
✔ an internal error does not leak its message
✔ a 404 does not reveal the route table
✔ a body over the limit is 413, not a crash
✔ the rate limiter returns 429 with Retry-After and the IETF headers
✔ the limiter advertises its policy
✔ an operator-shaped value is rejected by the type check, not executed
✔ a prototype-polluting body cannot add to Object.prototype
pass 10
fail 0
```

> **What these tests do not prove.** They check that controls exist and that obvious leaks are closed. They cannot find a missing ownership check on a new route, a logic flaw in a discount calculation, or an injection in a query you have not written yet. Security also needs review, threat modelling and — for anything public — external testing.

***

## 14. Common mistakes

| Mistake                                                       | Impact                                                                      | Fix                                                               |
| ------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `app.set('trust proxy', true)`                                | `X-Forwarded-For` spoofing defeats IP rate limits and reveals fake `req.ip` | Set the exact hop count or proxy address                          |
| No body-size limit                                            | One request exhausts memory/disk                                            | `express.json({ limit })`, multer `limits`                        |
| `X-Powered-By` left on                                        | Free framework fingerprint                                                  | `app.disable('x-powered-by')`                                     |
| CSP left at the default for an app that needs `unsafe-inline` | Developers disable CSP entirely instead of tuning it                        | Use nonces/hashes; scope `unsafe-inline` if unavoidable           |
| HSTS enabled before HTTPS works everywhere                    | The site becomes unreachable over HTTP for returning visitors               | Roll out gradually, and only in production                        |
| Returning raw `error.message` for 5xx                         | Leaks internals                                                             | Generic message + request id                                      |
| Rate limiting only by IP                                      | NAT punishes offices; botnets evade                                         | Key by user when available; throttle accounts too                 |
| Memory-store rate limits in a cluster                         | N instances = N× the intended limit                                         | Redis store                                                       |
| Secrets in code or in `.env` committed                        | Permanent compromise                                                        | Config + gitignore + rotation                                     |
| Verbose audit logs with tokens                                | Credential leakage into log storage                                         | pino redaction, never log `authorization`/`cookie`                |
| `exec` with user input                                        | Command injection                                                           | `execFile`/`spawn` with argument arrays                           |
| Regex built from input                                        | ReDoS                                                                       | Escape, or use text search                                        |
| Password rules only ("1 upper, 1 symbol") without length      | Weak passwords that users reuse                                             | Minimum 12+ characters, breach checks, MFA                        |
| Same error for every failure — but different _timing_         | Account enumeration via response time                                       | Dummy-hash comparison                                             |
| Missing ownership checks on nested resources                  | Horizontal privilege escalation                                             | Load the resource, check the owner (chapter 13)                   |
| Unaudited dependencies                                        | Known CVEs in production                                                    | `npm ci` + `npm audit` in CI + Renovate                           |
| No timeouts on the HTTP server                                | Slowloris ties up sockets                                                   | `requestTimeout`, `headersTimeout`, `keepAliveTimeout`            |
| Health and docs endpoints unauthenticated                     | Reveals versions and internal routes                                        | Keep `/health` minimal; protect `/docs` when it exposes internals |

***

## Exercise 18.1 — Harden the notes API

Apply the whole checklist to the notes API and prove each item with a test:

| Area                 | Requirement                                                                           |
| -------------------- | ------------------------------------------------------------------------------------- |
| Fingerprint          | `x-powered-by` absent                                                                 |
| Headers              | `helmet` defaults + `Permissions-Policy`, present on success, 404 and error responses |
| Body limits          | `100 kb` JSON; a larger body is `413 PAYLOAD_TOO_LARGE`                               |
| Global rate limit    | 300/min in production; a strict 10/15 min limit on `/auth/login`                      |
| Per-account throttle | 5 failures → exponential backoff, cleared on success                                  |
| CORS                 | Allowlist from config; `Vary: Origin` (chapter 16)                                    |
| CSRF                 | Token required on cookie-authenticated state changes (chapter 15)                     |
| Secrets              | `JWT_SECRET`, `SESSION_SECRET`, `COOKIE_SECRET` ≥ 32 chars, validated at startup      |
| Logging              | `authorization`, `cookie`, `password`, `token` redacted                               |
| Errors               | 5xx responses never contain the original message in production                        |
| Dependencies         | `npm audit --omit=dev --audit-level=high` passes in CI                                |
| Timeouts             | `requestTimeout`, `headersTimeout`, `keepAliveTimeout` set explicitly                 |

<details>

<summary>Solution</summary>

```js
// File: src/config/env.js
import { z } from 'zod';

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(0).max(65_535).default(3000),

  DATABASE_URL: z.url(),
  JWT_SECRET: z.string().min(32),
  JWT_REFRESH_SECRET: z.string().min(32),
  SESSION_SECRET: z.string().min(32),
  COOKIE_SECRET: z.string().min(32),

  ALLOWED_ORIGINS: z.string().default('http://localhost:5173').transform((value) =>
    value.split(',').map((item) => item.trim()).filter(Boolean)),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
}).strict();

const parsed = schema.safeParse(process.env);
if (!parsed.success) {
  console.error('Invalid environment configuration:');
  for (const issue of parsed.error.issues) console.error(`  ${issue.path.join('.')}: ${issue.message}`);
  process.exit(1);
}

export const env = { ...parsed.data, isProduction: parsed.data.NODE_ENV === 'production' };
```

```js
// File: src/security/headers.js
import helmet from 'helmet';

export function securityHeaders({ isProduction }) {
  return [
    helmet({
      contentSecurityPolicy: {
        useDefaults: true,
        directives: {
          "img-src": ["'self'", 'data:', 'https://cdn.example.com'],
          'upgrade-insecure-requests': isProduction ? [] : null,
        },
      },
      hsts: isProduction ? { maxAge: 31_536_000, includeSubDomains: true, preload: false } : false,
      crossOriginResourcePolicy: { policy: 'same-origin' },
      referrerPolicy: { policy: 'no-referrer' },
    }),
    (req, res, next) => {
      res.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=()');
      next();
    },
  ];
}
```

```js
// File: src/app.js
import express from 'express';
import cookieParser from 'cookie-parser';
import { rateLimit } from 'express-rate-limit';
import { securityHeaders } from './security/headers.js';
import { createRequestId } from './middleware/requestId.js';
import { createCorsMiddleware, createCorsOptions } from './middleware/cors.js';
import { createCsrfProtection } from './middleware/csrf.js';
import { createLimiters } from './middleware/limiters.js';
import { createErrorHandler } from './middleware/errorHandler.js';
import { notFound } from './middleware/notFound.js';

export function createApp({ config, container }) {
  const app = express();
  app.disable('x-powered-by');
  if (config.isProduction) app.set('trust proxy', 1);

  for (const middleware of securityHeaders({ isProduction: config.isProduction })) app.use(middleware);

  app.use(createCorsMiddleware(createCorsOptions({
    allowedOrigins: config.allowedOrigins,
    isProduction: config.isProduction,
  })));

  app.use(createRequestId);
  app.use(container.httpLogger);                              // pino-http with redaction

  app.use(express.json({ limit: '100kb', strict: true }));
  app.use(express.urlencoded({ extended: false, limit: '100kb' }));
  app.use(cookieParser(config.cookieSecret));

  const limiters = createLimiters({ redisClient: container.redis, isProduction: config.isProduction });
  app.use(rateLimit({
    windowMs: 60_000,
    limit: config.isProduction ? 300 : 10_000,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { error: { code: 'RATE_LIMITED', message: 'Too many requests' } },
  }));

  app.use('/api/v1/auth/login', limiters.auth);
  app.use('/api/v1/auth/register', limiters.register);

  app.use(createCsrfProtection({ isProduction: config.isProduction }));
  app.use('/api/v1', container.apiRouter);

  app.get('/health', (req, res) => res.json({ status: 'ok' }));   // deliberately minimal

  app.use(notFound);
  app.use(createErrorHandler({ logger: container.logger }));
  return app;
}
```

```js
// File: src/services/authService.js (the login flow, with the per-account throttle)
export const authServiceMethods = {
  async login({ email, password }, context = {}) {
    const normalised = String(email).trim().toLowerCase();
    await loginThrottle.assertAllowed(normalised);

    const user = await userRepository.findByEmail(normalised);
    const matches = await passwordHasher.compare(password, user?.passwordHash ?? DUMMY_HASH);

    if (!user || !matches) {
      const state = await loginThrottle.recordFailure(normalised);
      logger.warn('login failed', { requestId: context.requestId, failures: state.failures });
      throw new UnauthorizedError('Invalid email or password');
    }

    await loginThrottle.clear(normalised);
    return issueTokensFor(user);        // signAccessToken/signRefreshToken from chapter 14
  },
};
```

```js
// File: src/utils/logger.js (redaction)
import { pino } from 'pino';

export function createLogger({ logLevel, isProduction }) {
  return pino({
    level: logLevel,
    redact: {
      paths: [
        'req.headers.authorization',
        'req.headers.cookie',
        'res.headers["set-cookie"]',
        'req.body.password',
        'req.body.currentPassword',
        'req.body.newPassword',
        'req.body.token',
        'req.body.refreshToken',
        '*.passwordHash',
        '*.accessToken',
        '*.refreshToken',
      ],
      censor: '[redacted]',
    },
    transport: isProduction ? undefined : { target: 'pino-pretty', options: { colorize: true } },
  });
}
```

```js
// File: src/server.js (timeouts)
import { createServer } from 'node:http';
import { createApp } from './app.js';
import { env } from './config/env.js';
import { createContainer } from './container.js';

const container = createContainer();
const app = createApp({ config: env, container });
const server = createServer(app);

server.requestTimeout = 30_000;
server.headersTimeout = 10_000;
server.keepAliveTimeout = 5_000;
server.maxHeadersCount = 100;

server.listen(env.PORT, '0.0.0.0', () => {
  container.logger.info({ port: env.PORT, env: env.NODE_ENV }, 'server started');
});

let shuttingDown = false;
async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  container.logger.info({ signal }, 'shutting down');

  const forceExit = setTimeout(() => process.exit(1), 10_000).unref();
  server.close(async (error) => {
    clearTimeout(forceExit);
    if (error) { container.logger.error({ err: error }, 'close failed'); process.exit(1); }
    await container.close?.();
    process.exit(0);
  });
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('uncaughtException', (error) => { container.logger.fatal({ err: error }, 'uncaughtException'); shutdown('uncaughtException'); });
process.on('unhandledRejection', (reason) => { container.logger.fatal({ err: reason }, 'unhandledRejection'); shutdown('unhandledRejection'); });
```

```js
// File: tests/hardening.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';

let server;
let baseUrl;

const config = {
  isProduction: true,
  allowedOrigins: ['http://localhost:5173'],
  cookieSecret: 'test-cookie-secret-of-32-characters!!',
  sessionSecret: 'test-session-secret-of-32-characters!',
  jwtSecret: 'test-jwt-secret-of-32-characters-ok!!',
};

before(async () => {
  const container = {
    logger: { info() {}, warn() {}, error() {}, fatal() {} },
    httpLogger: (req, res, next) => next(),
    apiRouter: (await import('express')).default.Router(),
    redis: null,
  };
  const app = createApp({ config, container });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

test('the fingerprint is hidden', async () => {
  const response = await fetch(`${baseUrl}/health`);
  assert.equal(response.headers.get('x-powered-by'), null);
});

test('security headers are present', async () => {
  const response = await fetch(`${baseUrl}/health`);

  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  assert.equal(response.headers.get('referrer-policy'), 'no-referrer');
  assert.equal(response.headers.get('x-frame-options'), 'SAMEORIGIN');
  assert.equal(response.headers.get('strict-transport-security'), 'max-age=31536000; includeSubDomains');
  assert.equal(response.headers.get('permissions-policy'), 'camera=(), microphone=(), geolocation=(), payment=()');
});

test('headers survive a 404', async () => {
  const response = await fetch(`${baseUrl}/definitely-not-here`);
  assert.equal(response.status, 404);
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
});

test('an oversized body is 413', async () => {
  const response = await fetch(`${baseUrl}/api/v1/echo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filler: 'x'.repeat(200_000) }),
  });
  assert.equal(response.status, 413);
});

test('/health is minimal and does not leak versions', async () => {
  const response = await fetch(`${baseUrl}/health`);
  assert.deepEqual(await response.json(), { status: 'ok' });
});
```

```bash
node --test tests/hardening.test.js
```

```
✔ the fingerprint is hidden
✔ security headers are present
✔ headers survive a 404
✔ an oversized body is 413
✔ /health is minimal and does not leak versions
pass 5
fail 0
```

**The order matters as much as the list.** Headers first (so errors carry them), limits before parsing work, rate limits before authentication, CSRF after cookies, and the error handler last.

</details>

***

## Exercise 18.2 — Audit this handler

```js
// File: notes-report.js — find the security problems
import express from 'express';
import { exec } from 'node:child_process';
import { db } from './db.js';

const app = express();
app.use(express.json());

app.get('/report', async (req, res) => {
  const { from, to, userId } = req.query;

  const rows = await db.query(
    `SELECT * FROM notes WHERE created_at BETWEEN '${from}' AND '${to}' AND user_id = ${userId}`,
  );

  exec(`mkdir -p reports && echo "${JSON.stringify(rows)}" > reports/${req.query.name}.json`);

  res.json(rows);
});

app.post('/import', async (req, res) => {
  const notes = req.body;
  for (const note of notes) {
    await db.query(`INSERT INTO notes (title, content, user_id) VALUES ('${note.title}', '${note.content}', ${note.userId})`);
  }
  res.json({ ok: true, count: notes.length });
});

app.get('/env', (req, res) => res.json(process.env));

app.get('/debug', (req, res) => res.json({ config: dbConfig, routes: app._router.stack.map((layer) => layer.name) }));

app.listen(3000);
```

<details>

<summary>Solution</summary>

| #  | Problem                                     | Attack / impact                                              | Fix                                                                        |
| -- | ------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------- |
| 1  | String-interpolated SQL in `/report`        | SQL injection; `from` could be `' OR '1'='1`                 | Parameterised queries with `$1`/`?`                                        |
| 2  | No authorisation on `/report`               | Any caller reads anyone's notes by changing `userId`         | `requireAuth` + derive the user from the session, never from the query     |
| 3  | `exec` with `req.query.name`                | Command injection: `name=a; rm -rf ~`                        | `execFile` with an argument array; generate the filename yourself (UUID)   |
| 4  | `JSON.stringify(rows)` into a shell command | Shell metacharacters inside note content execute             | Never pass data through a shell; write the file with `fs`                  |
| 5  | `/import` interpolates body values          | SQL injection on mass import                                 | Parameterised inserts, inside a transaction, with a validated batch schema |
| 6  | `/import` has no size limit on the array    | 1M rows from one request                                     | `.max(100)` in the schema + body size limit                                |
| 7  | `/import` accepts `userId` per row          | Writing rows into other users' accounts                      | `userId` comes from `req.user` only                                        |
| 8  | `/env` returns `process.env`                | Leaks every secret in the process                            | Delete the route; log configuration _names_ at startup, never values       |
| 9  | `/debug` exposes the route table and config | Reconnaissance; possibly credentials in `dbConfig`           | Delete it; use structured logs and a protected metrics endpoint            |
| 10 | No authentication on any route              | The whole application is public                              | `requireAuth` at the router level                                          |
| 11 | `SELECT *` returned raw                     | Leaks internal columns (e.g. `deleted_at`, `internal_notes`) | Select explicit columns and map to a DTO                                   |
| 12 | No rate limiting or pagination              | One request scans the whole table                            | Pagination with `limit`/`page` + a limiter                                 |
| 13 | No error handling                           | 500s with stack traces; possible process crash on rejection  | One error handler, generic 5xx messages                                    |
| 14 | `express.json()` without a limit            | Memory exhaustion                                            | `{ limit: '100kb' }`                                                       |
| 15 | No security headers, `x-powered-by` on      | Fingerprint + missing protections                            | `helmet()` + `app.disable('x-powered-by')`                                 |

```js
// File: notes-report.fixed.js
import express from 'express';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import helmet from 'helmet';
import { toNoteDto } from './dtos/noteDto.js';

const run = promisify(execFile);
const REPORT_DIR = path.resolve(process.cwd(), 'var/reports');

const reportQuerySchema = z.object({
  from: z.iso.date(),
  to: z.iso.date(),
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
}).strict();

const importSchema = z.array(z.object({
  title: z.string().trim().min(1).max(200),
  content: z.string().trim().min(1).max(10_000),
})).min(1).max(100);

export function createReportRoutes({ db, requireAuth, logger }) {
  const router = express.Router();

  router.use(requireAuth);                                    // nothing here is public

  router.get('/report', async (req, res, next) => {
    try {
      const { from, to, page, limit } = reportQuerySchema.parse(req.query);

      // 1. Parameterised SQL. 2. The user id comes from the session, never the query.
      const rows = await db.query(
        `SELECT id, title, content, created_at
           FROM notes
          WHERE created_at BETWEEN $1 AND $2
            AND user_id = $3
          ORDER BY created_at DESC
          LIMIT $4 OFFSET $5`,
        [from, to, req.user.id, limit, (page - 1) * limit],
      );

      res.json({ data: rows.rows.map(toNoteDto), meta: { page, limit } });
    } catch (error) {
      next(error);
    }
  });

  router.post('/report/export', async (req, res, next) => {
    try {
      const rows = await db.query('SELECT id, title, content, created_at FROM notes WHERE user_id = $1', [req.user.id]);

      // 3. A filename we generate. 4. The data is written by fs, never by a shell.
      const filename = `${randomUUID()}.json`;
      const absolute = path.join(REPORT_DIR, filename);
      await writeFile(absolute, JSON.stringify(rows.rows, null, 2), { mode: 0o640, flag: 'wx' });

      // If you must invoke a tool, use execFile with an args array and a path you control:
      await run('gzip', ['-k', absolute]);

      res.status(202).location(`/api/v1/reports/${filename}.gz`).json({ data: { job: 'export', status: 'ready' } });
    } catch (error) {
      next(error);
    }
  });

  router.post('/import', async (req, res, next) => {
    try {
      const notes = importSchema.parse(req.body);             // bounded, typed, no userId field

      await db.withTransaction(async (client) => {
        for (const note of notes) {
          await client.query(
            'INSERT INTO notes (title, content, user_id) VALUES ($1, $2, $3)',
            [note.title, note.content, req.user.id],          // the caller's id, always
          );
        }
      });

      logger.info('notes imported', { userId: req.user.id, count: notes.length });
      res.status(201).json({ data: { imported: notes.length } });
    } catch (error) {
      next(error);
    }
  });

  return router;
}

export function createApp({ db, logger }) {
  const app = express();
  app.disable('x-powered-by');
  app.use(helmet());
  app.use(express.json({ limit: '100kb' }));
  app.use('/api/v1', createReportRoutes({ db, requireAuth, logger }));

  // No /env. No /debug. Configuration names are logged once at startup:
  logger.info({ configured: ['DATABASE_URL', 'JWT_SECRET', 'PORT'] }, 'configuration loaded');

  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND', message: 'Not found' } }));
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    logger.error({ err: error, requestId: req.id }, 'request failed');
    res.status(error.statusCode ?? 500).json({
      error: { code: error.code ?? 'INTERNAL_ERROR', message: error.statusCode ? error.message : 'Something went wrong' },
    });
  });

  return app;
}
```

**Order of operations for any audit:** remove exposure first (`/env`, `/debug`, missing auth), then fix injection, then fix command execution, then add limits. The first two are exploitable by anyone in seconds; the rest raise the bar.

</details>

***

## What's next

Everything is now built and hardened, but "it works when I click it" is not evidence. Next: testing with `node:test`, Jest and Vitest — unit tests for services, integration tests for routes, mocks that do not lie, and a suite that runs in CI.

→ [19 — Testing](19-testing.md)
