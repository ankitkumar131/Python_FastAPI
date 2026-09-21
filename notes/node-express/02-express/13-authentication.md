# 13 — Authentication

> **Where this fits:** Chapters 01–12 build an API that anyone can call. This chapter decides _who_ the caller is. It covers the Express wiring — middleware, `req.user`, protection boundaries. The deep dives live in the dedicated section: hashing in 04-authentication/02-password-hashing.md _(not available in this published source revision)_, tokens in 03-jwt.md _(not available in this published source revision)_ and 04-access-refresh-tokens.md _(not available in this published source revision)_, OAuth in 05-oauth.md _(not available in this published source revision)_, and roles in 06-role-based-access.md _(not available in this published source revision)_.

***

## 1. Authentication versus authorisation

Two questions that sound alike and fail differently:

| Question          | Name                       | Failure status     | Failure meaning                       |
| ----------------- | -------------------------- | ------------------ | ------------------------------------- |
| Who is calling?   | **Authentication** (authn) | `401 Unauthorized` | "I do not know who you are — sign in" |
| May they do this? | **Authorisation** (authz)  | `403 Forbidden`    | "I know who you are — you may not"    |

> `401 Unauthorized` is a badly named status: it actually means **unauthenticated**. Remember the pair: **401 = identify yourself**, **403 = not allowed**.

```
Register                          Login                            Protected request
────────                          ─────                            ─────────────────
POST /auth/register               POST /auth/login                 GET /notes
  email + password                  email + password                 Authorization: Bearer <token>
        │                                 │                                │
        ▼                                 ▼                                ▼
  hash password            compare against stored hash          verify token / load session
        │                                 │                                │
        ▼                                 ▼                                ▼
  store user               issue token / start session            req.user = { id, role }
        │                                 │                                │
        ▼                                 ▼                                ▼
  201 Created              201/200 + token                          200 OK (authorised)
```

### The words you will meet

| Term            | Meaning                                                                             |
| --------------- | ----------------------------------------------------------------------------------- |
| **Credentials** | What the user presents to prove identity (email + password, an OTP, a passkey)      |
| **Principal**   | The identity the server has established — usually a user id                         |
| **Authn**       | Turning credentials into a principal                                                |
| **Authz**       | Deciding what that principal may do                                                 |
| **Session**     | Server-side record of a signed-in user; the client holds only an opaque session id  |
| **Token**       | A signed, self-contained statement (e.g. "user 7, role USER, expires 15:00")        |
| **Hash**        | A one-way transformation; the database stores hashes, never passwords               |
| **Claim**       | A field inside a token: `sub`, `role`, `exp`, `iat`, `jti`                          |
| **Bearer**      | The party holding the token may use it — so tokens must be protected like passwords |
| **RBAC**        | Role-based access control: permissions are attached to roles, users get roles       |

***

## 2. How the client carries its identity

Two mainstream designs. Everything else is a variation.

```
Sessions (stateful)                        Tokens (stateless)

Browser                                    Browser
  │ Cookie: sid=abc123                        │ Authorization: Bearer eyJhbGciOi...
  ▼                                          ▼
Express                                    Express
  │ look up abc123 in a store                │ verify the signature with a secret
  ▼                                          ▼
Store (Redis / database)                   Nothing stored per user
  { userId: 7, role: 'USER', … }              claims are inside the token
```

|                        | **Session cookie**              | **Access token (JWT)**                              |
| ---------------------- | ------------------------------- | --------------------------------------------------- |
| Where the state lives  | Server (Redis, database)        | Inside the token                                    |
| What the client stores | Opaque session id               | Signed claims (readable by anyone)                  |
| Revocation             | Delete the session — instant    | Hard: valid until `exp` (see `jti` denylists)       |
| Logout                 | Server deletes the record       | Client discards the token; server cannot force it   |
| Scale                  | Every request touches the store | No per-request lookup (good for many services)      |
| Fits                   | Browser apps (same site)        | APIs, mobile, service-to-service                    |
| Common attack          | CSRF (mitigated by `SameSite`)  | XSS stealing the token, if stored in `localStorage` |
| Size                   | \~30 bytes                      | 300–1200 bytes, sent on every request               |

The notes API uses **tokens** in this chapter and the next two, because APIs are called by many kinds of clients. Chapter 15 adds the cookie-based session variant for the same API.

***

## 3. The authentication middleware contract

Whatever the mechanism, the request pipeline is identical:

```
request ──▶ authenticate ──▶ requireAuth ──▶ requireRole('ADMIN') ──▶ handler
             (parse only)     (must be      (authorisation)           (req.user is
                              signed in)                              guaranteed)
```

| Middleware             | Job                                                                        | On failure                         |
| ---------------------- | -------------------------------------------------------------------------- | ---------------------------------- |
| `authenticate`         | Read the credential, verify it, attach `req.user` if valid. Never rejects. | — (goes to `next()`)               |
| `requireAuth`          | Reject when `req.user` is missing                                          | `401` + `WWW-Authenticate: Bearer` |
| `requireRole('ADMIN')` | Reject when the role does not match                                        | `403`                              |
| `optionalAuth`         | Attach `req.user` when present, but let anonymous callers through          | —                                  |

Splitting "parse" from "require" is what makes public-but-personalised endpoints easy: a product page can show "Add to cart" to anonymous visitors and "Add to wishlist" to signed-in ones, with no duplicated token parsing.

```js
// File: src/middleware/auth.js
import { UnauthorizedError, ForbiddenError } from '../utils/AppError.js';

/**
 * Verifies the credential and attaches req.user when it is valid.
 * Never throws: a bad credential simply means "anonymous" at this stage.
 */
export function createAuthenticate({ tokenService, userRepository, logger }) {
  return async function authenticate(req, res, next) {
    try {
      const header = req.get('authorization') ?? '';
      const [scheme, value] = header.split(' ');

      if (scheme !== 'Bearer' || !value) {
        req.authError = 'missing-credential';       // used by requireAuth for the exact 401 reason
        return next();
      }

      const claims = await tokenService.verifyAccessToken(value);   // throws on bad signature/expiry

      // The token is authentic, but the user may have been deleted or demoted since it was issued.
      const user = await userRepository.findById(claims.sub);
      if (!user) {
        req.authError = 'user-no-longer-exists';
        return next();
      }

      req.user = { id: user.id, role: user.role, email: user.email };
      return next();
    } catch (error) {
      // Invalid/expired token: record the reason, stay anonymous.
      req.authError = error.code === 'TOKEN_EXPIRED' ? 'token-expired' : 'invalid-token';
      logger.warn('authentication failed', { requestId: req.id, reason: req.authError });
      return next();
    }
  };
}

/** Turns "anonymous" into a 401 with the precise reason. Use on routes that require a user. */
export function requireAuth(req, res, next) {
  if (req.user) return next();

  res.set('WWW-Authenticate', 'Bearer realm="api", error="invalid_token"');
  const messages = {
    'missing-credential': 'An Authorization: Bearer <token> header is required',
    'invalid-token': 'The access token is invalid',
    'token-expired': 'The access token has expired',
    'user-no-longer-exists': 'The account no longer exists',
  };

  return res.status(401).json({
    error: {
      code: req.authError === 'token-expired' ? 'TOKEN_EXPIRED' : 'UNAUTHENTICATED',
      message: messages[req.authError] ?? 'Authentication is required',
      requestId: req.id,
    },
  });
}

/** Role-based authorisation. Coarse-grained: the same rule for every call. */
export function requireRole(...allowed) {
  const allowedSet = new Set(allowed);

  return function requireRoleMiddleware(req, res, next) {
    if (!req.user) {
      throw new UnauthorizedError('Authentication is required');    // reaches the error handler
    }

    if (!allowedSet.has(req.user.role)) {
      throw new ForbiddenError('You do not have permission to perform this action', {
        requiredRoles: [...allowedSet],
        actualRole: req.user.role,
      });
    }

    return next();
  };
}

/** For endpoints that personalise the response but work for anonymous callers too. */
export function optionalAuth(authenticate) {
  return function optionalAuthMiddleware(req, res, next) {
    return authenticate(req, res, () => {
      req.user ??= null;                 // explicit: "we looked, nobody is signed in"
      next();
    });
  };
}
```

> **Express 5 note:** a `throw` inside a synchronous middleware is caught by Express and routed to the error handler, and the same is true for rejected promises from `async` middleware. That is why `requireRole` can simply throw while `authenticate` — which must never fail the request — uses `try/catch` and calls `next()`.

### Wiring it once, at the top of the router tree

```js
// File: src/routes/index.js
import { Router } from 'express';
import { createNoteRouter } from './noteRoutes.js';
import { createAuthRouter } from './authRoutes.js';

export function createApiRouter({ controllers, middleware }) {
  const router = Router();

  // 1. Parse credentials for every request — cheap for anonymous callers.
  router.use(middleware.authenticate);

  // 2. Public endpoints first.
  router.use('/auth', createAuthRouter({ controllers }));

  // 3. Protected resources: requireAuth is applied once, at the mount point.
  router.use('/notes', middleware.requireAuth, createNoteRouter({ controllers, middleware }));

  // 4. Admin-only area.
  router.use('/admin', middleware.requireAuth, middleware.requireRole('ADMIN'), createAdminRouter({ controllers }));

  return router;
}
```

```js
// File: src/app.js (excerpt) — request pipeline order, top to bottom
app.use(requestId);
app.use(pinoHttp);
app.use(helmet());
app.use(cors(corsOptions));
app.use(express.json({ limit: '100kb' }));
app.use('/api/v1', createApiRouter({ controllers, middleware }));
app.use(notFound);
app.use(createErrorHandler({ logger }));
```

| Placement rule                                      | Reason                                                         |
| --------------------------------------------------- | -------------------------------------------------------------- |
| `authenticate` early, before routers                | Every route gets `req.user` (or `null`) without repeating code |
| `requireAuth` at the **mount point**, not per route | One place to audit; impossible to forget on a new route        |
| `requireRole` after `requireAuth`                   | Role checks need an identity                                   |
| `optionalAuth` only on specific public routes       | Otherwise anonymous access leaks into protected areas          |

***

## 4. Registration and login in Express

The chapters use interfaces so the HTTP layer stays testable and the mechanisms stay swappable.

```js
// File: src/utils/passwordHasher.js (interface + a development implementation)
import { randomBytes, scrypt as scryptCallback, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';

const scrypt = promisify(scryptCallback);

/**
 * In production prefer argon2id, or bcryptjs when native builds are a problem.
 * This scrypt implementation is dependency-free and shows the exact contract:
 *   hash(plain) → string, compare(plain, hash) → boolean.
 * Details and trade-offs: 04-authentication/02-password-hashing.md
 */
export function createPasswordHasher({ keyLength = 64 } = {}) {
  return {
    async hash(plain) {
      const salt = randomBytes(16).toString('hex');
      const derived = await scrypt(plain, salt, keyLength);
      return `scrypt$${salt}$${derived.toString('hex')}`;
    },

    async compare(plain, stored) {
      const [algorithm, salt, expectedHex] = String(stored).split('$');
      if (algorithm !== 'scrypt' || !salt || !expectedHex) return false;

      const derived = await scrypt(plain, salt, expectedHex.length / 2);
      const expected = Buffer.from(expectedHex, 'hex');
      return derived.length === expected.length && timingSafeEqual(derived, expected);
    },
  };
}
```

> The **hasher** contract is deliberately narrow: `hash` and `compare`. Nothing in the Express layer ever sees a plain-text password again after the service is done with it. Chapter 13's job is the HTTP boundary, not the cryptography.

```js
// File: src/validators/authSchemas.js
import { z } from 'zod';

export const registerSchema = z
  .object({
    email: z.email('must be a valid email address').max(254),
    password: z.string().min(12, 'must be at least 12 characters').max(200),
    name: z.string().trim().min(1, 'required').max(100),
  })
  .strict();

export const loginSchema = z
  .object({
    email: z.email().max(254),
    password: z.string().min(1, 'required').max(200),
  })
  .strict();
```

```js
// File: src/dtos/userDto.js
/** Public shape of a user. Never includes passwordHash, tokens or internal flags. */
export function toUserDto(user) {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    createdAt: user.createdAt,
  };
}
```

```js
// File: src/controllers/authController.js
import { toUserDto } from '../dtos/userDto.js';

export function createAuthController({ authService }) {
  return {
    async register(req, res, next) {
      try {
        const user = await authService.register(req.validated.body);
        res.status(201).location(`/api/v1/users/${user.id}`).json({ data: toUserDto(user) });
      } catch (error) {
        next(error);
      }
    },

    async login(req, res, next) {
      try {
        const { user, accessToken, refreshToken, expiresIn } = await authService.login(req.validated.body, {
          userAgent: req.get('user-agent') ?? null,
          ip: req.ip,
        });

        // Refresh token in an httpOnly cookie; access token in the body. Explained in chapters 14–15.
        res.cookie('refreshToken', refreshToken, {
          httpOnly: true,
          sameSite: 'strict',
          secure: req.app.get('env') === 'production',
          path: '/api/v1/auth',
          maxAge: 30 * 24 * 60 * 60 * 1000,
        });

        res.status(200).json({
          data: { user: toUserDto(user) },
          meta: { accessToken, tokenType: 'Bearer', expiresIn },
        });
      } catch (error) {
        next(error);
      }
    },

    async me(req, res) {
      // requireAuth guarantees req.user exists.
      res.json({ data: req.user });
    },

    async logout(req, res, next) {
      try {
        await authService.logout(req.user ?? null, { refreshToken: req.cookies?.refreshToken ?? null });
        res.clearCookie('refreshToken', { path: '/api/v1/auth' });
        res.status(204).end();
      } catch (error) {
        next(error);
      }
    },
  };
}
```

```js
// File: src/services/authService.js
import { randomUUID } from 'node:crypto';
import { ConflictError, UnauthorizedError } from '../utils/AppError.js';

const normaliseEmail = (email) => String(email).trim().toLowerCase();

export function createAuthService({ userRepository, passwordHasher, tokenService, refreshTokenStore, logger }) {
  /**
   * A hash that no password will ever match. Comparing against it when the user is
   * unknown keeps the response time similar, so the API does not reveal which emails exist.
   */
  const DUMMY_HASH = 'scrypt$0000000000000000000000000000000000000000$' + '00'.repeat(64);

  return {
    async register({ email, password, name }) {
      const normalised = normaliseEmail(email);

      if (await userRepository.existsByEmail(normalised)) {
        throw new ConflictError('That email is already registered', { field: 'email' });
      }

      const user = await userRepository.create({
        email: normalised,
        name: name.trim(),
        passwordHash: await passwordHasher.hash(password),
        role: 'USER',                                    // never client-supplied
        createdAt: new Date().toISOString(),
      });

      logger.info('user registered', { userId: user.id });
      return user;
    },

    async login({ email, password }, context = {}) {
      const user = await userRepository.findByEmail(normaliseEmail(email));
      const hash = user?.passwordHash ?? DUMMY_HASH;
      const matches = await passwordHasher.compare(password, hash);

      if (!user || !matches) {
        // One message for both cases: never confirm that an email exists.
        logger.warn('login failed', { requestId: context.requestId, email: normaliseEmail(email) });
        throw new UnauthorizedError('Invalid email or password');
      }

      const accessToken = await tokenService.signAccessToken({ sub: user.id, role: user.role });
      const refreshToken = await tokenService.signRefreshToken({ sub: user.id, jti: randomUUID() });

      await refreshTokenStore.save(refreshToken, { userId: user.id, userAgent: context.userAgent, ip: context.ip });

      return { user, accessToken, refreshToken, expiresIn: tokenService.accessTokenTtlSeconds };
    },

    async logout(user, { refreshToken }) {
      if (refreshToken) await refreshTokenStore.revoke(refreshToken);
      logger.info('user logged out', { userId: user?.id ?? null });
    },
  };
}
```

```js
// File: src/routes/authRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { registerSchema, loginSchema } from '../validators/authSchemas.js';

export function createAuthRouter({ controllers, middleware }) {
  const router = Router();
  const { auth } = controllers;

  router.post('/register', validate(registerSchema), auth.register);
  router.post('/login', validate(loginSchema), auth.login);
  router.get('/me', middleware.requireAuth, auth.me);
  router.post('/logout', middleware.requireAuth, auth.logout);

  return router;
}
```

```bash
BASE=http://localhost:3000/api/v1

# Register
curl -i -X POST "$BASE/auth/register" -H 'Content-Type: application/json' \
  -d '{"email":"ankit@example.com","password":"supersecret123","name":"Ankit"}'
```

```
HTTP/1.1 201 Created
Location: /api/v1/users/1
Content-Type: application/json; charset=utf-8

{"data":{"id":"1","email":"ankit@example.com","name":"Ankit","role":"USER","createdAt":"2026-09-18T09:00:00.000Z"}}
```

```bash
# Login (note the Set-Cookie for the refresh token, and the access token in the body)
curl -i -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"ankit@example.com","password":"supersecret123"}'
```

```
HTTP/1.1 200 OK
Set-Cookie: refreshToken=eyJhbGciOiJIUzI1NiIsInR5cCI6...; Path=/api/v1/auth; HttpOnly; SameSite=Strict
Content-Type: application/json; charset=utf-8

{"data":{"user":{"id":"1","email":"ankit@example.com","name":"Ankit","role":"USER"}},
 "meta":{"accessToken":"eyJhbGciOiJIUzI1NiIsInR5cCI6...","tokenType":"Bearer","expiresIn":900}}
```

```bash
TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6...     # paste meta.accessToken from the login response

curl -s "$BASE/auth/me" -H "Authorization: Bearer $TOKEN"          # 200 + the user
curl -s "$BASE/auth/me" -H "Authorization: Bearer not-a-real-token" # 401 TOKEN_EXPIRED or UNAUTHENTICATED
curl -s "$BASE/auth/me"                                             # 401 UNAUTHENTICATED
curl -s -X POST "$BASE/notes" -H 'Content-Type: application/json' -d '{"title":"T","content":"C"}'   # 401
curl -s -X POST "$BASE/notes" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"T","content":"C"}'                                  # 201
```

***

## 5. Protecting resources, and the ownership rule

Coarse authorisation ("must be signed in", "must be an admin") is middleware. Fine-grained authorisation ("may edit _this_ note") needs the data, so it lives in the service — chapter 11 showed it as `ForbiddenError`. The two combine like this:

```js
// File: src/routes/noteRoutes.js
export function createNoteRoutes({ controller, middleware }) {
  const router = Router();

  // Everything below requires a signed-in user.
  router.use(middleware.requireAuth);

  router.get('/', controller.list);
  router.post('/', validate(createNoteSchema), controller.create);

  router.get('/:id', middleware.loadNote, controller.getOne);
  router.patch('/:id', middleware.loadNote, middleware.requireOwner, validate(patchNoteSchema), controller.update);
  router.delete('/:id', middleware.loadNote, middleware.requireOwner, controller.remove);

  // A separate, clearly-marked admin area.
  router.delete('/:id/force', middleware.requireRole('ADMIN'), controller.forceRemove);

  return router;
}
```

```js
// File: src/middleware/loadNote.js
import { NotFoundError } from '../utils/AppError.js';

/**
 * Loads the resource once and stores it on req.locals. Returning 404 (not 403) for a
 * note that does not exist avoids leaking whether an id is real.
 */
export function createLoadNote({ noteService }) {
  return async function loadNote(req, res, next) {
    try {
      const note = await noteService.getById(req.params.id);
      if (!note) throw new NotFoundError(`Note ${req.params.id} not found`);
      res.locals.note = note;
      return next();
    } catch (error) {
      return next(error);
    }
  };
}

/** Ownership check: needs the loaded resource, so it runs after loadNote. */
export function requireOwner(req, res, next) {
  const note = res.locals.note;
  if (note.authorId === req.user.id || req.user.role === 'ADMIN') return next();

  return res.status(403).json({
    error: {
      code: 'FORBIDDEN',
      message: 'You can only modify your own notes',
      requestId: req.id,
    },
  });
}
```

| Boundary                         | Where                                        | Returns     |
| -------------------------------- | -------------------------------------------- | ----------- |
| Signed in?                       | `requireAuth` (mount point)                  | `401`       |
| Has the right role?              | `requireRole('ADMIN')`                       | `403`       |
| Does the row exist?              | `loadNote`                                   | `404`       |
| Does the user own the row?       | `requireOwner` / service rule                | `403`       |
| Does the business rule allow it? | Service (`ConflictError`, `ValidationError`) | `409`/`422` |

> **Ordering matters for privacy.** Loading and checking ownership gives `404` for a note belonging to someone else _only if you make it so_. The `requireOwner` above returns `403` — which reveals that the row exists. That is a deliberate trade-off: a blog API can be open about existence, while a health API should return `404` for anything the caller may not see. Pick one policy and document it.

***

## 6. The session-based alternative

Same flow, different carrier. Express has an official middleware, `express-session`, and the notes API uses it in chapter 15 with a Redis store.

```js
// File: src/middleware/session.js (preview — full version in chapter 15)
import session from 'express-session';
import { RedisStore } from 'connect-redis';

export function createSessionMiddleware({ redisClient, secret, isProduction }) {
  return session({
    name: 'sid',                                   // do not advertise the framework default
    secret,                                        // from config, never hard-coded
    store: new RedisStore({ client: redisClient, prefix: 'sess:' }),
    resave: false,
    saveUninitialized: false,
    rolling: true,                                 // refresh the expiry on activity
    cookie: {
      httpOnly: true,                              // JavaScript cannot read it (XSS mitigation)
      sameSite: 'lax',                             // blocks most CSRF; 'strict' for sensitive apps
      secure: isProduction,                        // HTTPS only
      maxAge: 1000 * 60 * 60 * 8,                  // 8 hours
    },
  });
}
```

```js
// File: login handler using sessions
async function loginWithSession(req, res, next) {
  try {
    const user = await authService.verifyCredentials(req.validated.body);

    // Prevents session fixation: a new session id after a successful login.
    req.session.regenerate((error) => {
      if (error) return next(error);

      req.session.userId = user.id;
      req.session.role = user.role;
      return req.session.save((saveError) => {
        if (saveError) return next(saveError);
        return res.json({ data: { user: toUserDto(user) } });
      });
    });
  } catch (error) {
    next(error);
  }
}
```

| Session pitfall                    | Consequence                                                           | Fix                                                          |
| ---------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------ |
| Default `MemoryStore`              | Sessions vanish on restart; leaks memory; unusable beyond one process | Redis (or a database) store                                  |
| Session id never rotated           | Session fixation                                                      | `req.session.regenerate()` on login                          |
| `sameSite` not set                 | CSRF via cross-site form posts                                        | `lax` or `strict` + a CSRF token for state-changing requests |
| `secure` not set in production     | The cookie travels over plain HTTP                                    | `secure: isProduction`                                       |
| Storing big objects in the session | Every request transfers and deserialises them                         | Store an id; load the user when needed                       |
| No expiry                          | Sessions live forever                                                 | `maxAge` + `rolling` + store-side TTL                        |

***

## 7. Testing authentication

Tests that skip authentication only prove the happy path. Every protected endpoint needs a table of "without a token", "with a bad token", "with another user's token".

```js
// File: tests/auth.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import cookieParser from 'cookie-parser';
import { createAuthenticate, requireAuth, requireRole } from '../src/middleware/auth.js';
import { UnauthorizedError, ForbiddenError } from '../src/utils/AppError.js';

/* ── A fake token service: no real signing, deterministic claims ───────────────── */
const tokenService = {
  accessTokenTtlSeconds: 900,
  async signAccessToken(claims) { return `valid.${Buffer.from(JSON.stringify(claims)).toString('base64url')}`; },
  async signRefreshToken() { return 'refresh-token'; },
  async verifyAccessToken(token) {
    const [prefix, payload] = String(token).split('.');
    if (prefix !== 'valid') throw Object.assign(new Error('invalid'), { code: 'INVALID_TOKEN' });
    return JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
  },
};

const users = [
  { id: '1', email: 'owner@example.com', role: 'USER' },
  { id: '2', email: 'other@example.com', role: 'USER' },
  { id: '9', email: 'admin@example.com', role: 'ADMIN' },
];

const userRepository = { async findById(id) { return users.find((user) => user.id === id) ?? null; } };
const logger = { warn() {}, info() {} };

const notes = [
  { id: 'n1', title: 'First', authorId: '1' },
  { id: 'n2', title: 'Second', authorId: '2' },
];

let server;
let baseUrl;

before(async () => {
  const app = express();
  app.use(cookieParser());
  app.use((req, res, next) => { req.id = 'test'; next(); });
  app.use(createAuthenticate({ tokenService, userRepository, logger }));

  const loadNote = (req, res, next) => {
    const note = notes.find((item) => item.id === req.params.id);
    if (!note) return res.status(404).json({ error: { code: 'NOT_FOUND' } });
    res.locals.note = note;
    return next();
  };
  const requireOwner = (req, res, next) => {
    if (res.locals.note.authorId === req.user.id || req.user.role === 'ADMIN') return next();
    return next(new ForbiddenError('not your note'));
  };

  const router = express.Router();
  router.get('/notes/:id', requireAuth, loadNote, (req, res) => res.json({ data: res.locals.note }));
  router.patch('/notes/:id', requireAuth, loadNote, requireOwner, (req, res) => res.json({ data: { ...res.locals.note, ...req.body } }));
  router.get('/admin/stats', requireAuth, requireRole('ADMIN'), (req, res) => res.json({ data: { users: 3 } }));

  app.use('/api/v1', router);
  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    const statusCode = error.statusCode ?? 500;
    return res.status(statusCode).json({ error: { code: error.code ?? 'INTERNAL_ERROR', message: error.message } });
  });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1`;
});

after(() => new Promise((resolve) => server.close(resolve)));

async function loginAs(id) {
  const user = users.find((item) => item.id === id);
  return tokenService.signAccessToken({ sub: user.id, role: user.role });
}

const request = (path, { method = 'GET', token, body } = {}) =>
  fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

test('an anonymous caller gets 401 with WWW-Authenticate', async () => {
  const response = await request('/notes/n1');
  assert.equal(response.status, 401);
  assert.match(response.headers.get('www-authenticate'), /Bearer/);

  const payload = await response.json();
  assert.equal(payload.error.code, 'UNAUTHENTICATED');
});

test('a malformed token is 401, not 500', async () => {
  const response = await request('/notes/n1', { token: 'garbage' });
  assert.equal(response.status, 401);
  assert.equal((await response.json()).error.code, 'UNAUTHENTICATED');
});

test('a valid token for a deleted user is 401', async () => {
  const ghost = await tokenService.signAccessToken({ sub: '404', role: 'USER' });
  const response = await request('/notes/n1', { token: ghost });
  assert.equal(response.status, 401);
});

test('the authenticated owner can read and update their note', async () => {
  const token = await loginAs('1');

  const read = await request('/notes/n1', { token });
  assert.equal(read.status, 200);

  const updated = await request('/notes/n1', { method: 'PATCH', token, body: { title: 'Renamed' } });
  assert.equal(updated.status, 200);
  assert.equal((await updated.json()).data.title, 'Renamed');
});

test("another user's note is 403 (they are authenticated, not authorised)", async () => {
  const token = await loginAs('2');
  const response = await request('/notes/n1', { method: 'PATCH', token, body: { title: 'Hijacked' } });
  assert.equal(response.status, 403);
});

test('an admin bypasses the ownership rule', async () => {
  const token = await loginAs('9');
  const response = await request('/notes/n1', { method: 'PATCH', token, body: { title: 'Moderated' } });
  assert.equal(response.status, 200);
});

test('role-protected routes reject the wrong role and accept the right one', async () => {
  const user = await request('/admin/stats', { token: await loginAs('1') });
  assert.equal(user.status, 403);

  const admin = await request('/admin/stats', { token: await loginAs('9') });
  assert.equal(admin.status, 200);
  assert.deepEqual((await admin.json()).data, { users: 3 });
});

test('a missing note is 404 before the ownership check runs', async () => {
  const response = await request('/notes/missing', { token: await loginAs('1') });
  assert.equal(response.status, 404);
});
```

```bash
node --test tests/auth.test.js
```

```
✔ an anonymous caller gets 401 with WWW-Authenticate
✔ a malformed token is 401, not 500
✔ a valid token for a deleted user is 401
✔ the authenticated owner can read and update their note
✔ another user's note is 403 (they are authenticated, not authorised)
✔ an admin bypasses the ownership rule
✔ role-protected routes reject the wrong role and accept the right one
✔ a missing note is 404 before the ownership check runs
pass 8
fail 0
```

***

## 8. Common mistakes

| Mistake                                              | Why it is a mistake                                             | Correct approach                                                                                |
| ---------------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Returning 403 when the caller is not signed in       | The client cannot tell whether to show a login form or an error | `401` when unauthenticated, `403` when forbidden                                                |
| One message for "unknown email" and "wrong password" | It leaks which emails are registered                            | One message: "Invalid email or password"                                                        |
| Registering with a client-supplied `role`            | Privilege escalation                                            | Server assigns `USER`; promotion is a separate protected operation                              |
| `requireAuth` on each route by hand                  | One new route forgotten = an open door                          | Apply at the mount point                                                                        |
| Checking the role in the controller                  | Duplication and drift                                           | `requireRole` middleware + service rules                                                        |
| Trusting `req.user` before `requireAuth`             | `undefined` dereferences become 500s                            | Order the pipeline: parse → require → role → handler                                            |
| Putting the token in `localStorage`                  | Any XSS steals it                                               | `httpOnly` cookie for refresh; short-lived access token                                         |
| Sessions in the default `MemoryStore`                | Lost on restart, unusable across processes                      | Redis/database store                                                                            |
| No session rotation on login                         | Session fixation                                                | `req.session.regenerate()`                                                                      |
| Storing passwords with `md5`/`sha256`                | Fast hashes are brute-forced quickly                            | `argon2id`/bcrypt/scrypt with a per-user salt                                                   |
| Logging tokens or passwords                          | Logs are shared, copied and retained                            | Redact: never log `authorization`, `password`, `token`                                          |
| JWT secret in the code                               | Permanent compromise if the repo leaks                          | Configuration/environment, rotated periodically                                                 |
| `verify` without an algorithm allowlist              | `alg: none` and key-confusion attacks                           | Pin algorithms; never trust the header                                                          |
| No token expiry                                      | A stolen token works forever                                    | Short access tokens + refresh flow                                                              |
| Async middleware without handling rejections         | Unhandled rejections crash the process in older code            | Express 5 forwards them — but still `try/catch` around credential parsing so failures stay 401s |
| Ownership checks in the controller                   | Repeated, inconsistent                                          | Middleware for loading, service for the rule                                                    |

***

## Exercise 13.1 — Protect the notes API

Extend the notes API so that:

| Requirement               | Detail                                                                                   |
| ------------------------- | ---------------------------------------------------------------------------------------- |
| `POST /auth/register`     | Creates a `USER`; never accepts a client-supplied role                                   |
| `POST /auth/login`        | Returns `{ data: { user }, meta: { accessToken, expiresIn } }`, `401` on bad credentials |
| `GET /auth/me`            | Returns the current user; requires a token                                               |
| `GET /notes`              | Requires a token; lists only the caller's notes (admins see all)                         |
| `POST /notes`             | Requires a token; `authorId` comes from `req.user.id`                                    |
| `PATCH/DELETE /notes/:id` | Requires a token **and** ownership (admins bypass)                                       |
| `GET /admin/users`        | Requires the `ADMIN` role                                                                |
| Every 401                 | Sends `WWW-Authenticate: Bearer` and never reveals whether an email exists               |

Write tests covering: anonymous, bad token, deleted user, wrong user, admin, and the exact status codes.

<details>

<summary>Solution</summary>

```js
// File: src/services/noteService.js (excerpt) — ownership-aware listing
export function createNoteService({ noteRepository }) {
  return {
    async listForUser({ actor, page, limit }) {
      const filter = actor.role === 'ADMIN' ? {} : { authorId: actor.id };
      const { items, total } = await noteRepository.list({ filter, offset: (page - 1) * limit, limit });
      return { items, total };
    },
  };
}
```

```js
// File: src/controllers/noteController.js (excerpt)
export function createNoteController({ noteService }) {
  return {
    async list(req, res, next) {
      try {
        const { page, limit } = req.validated.query;
        const { items, total } = await noteService.listForUser({ actor: req.user, page, limit });
        res.json({
          data: items.map(toNoteDto),
          meta: { page, limit, total, pages: Math.ceil(total / limit) },
        });
      } catch (error) {
        next(error);
      }
    },

    async create(req, res, next) {
      try {
        const note = await noteService.create(req.validated.body, { actor: req.user });
        res.status(201).location(`/api/v1/notes/${note.id}`).json({ data: toNoteDto(note) });
      } catch (error) {
        next(error);
      }
    },
  };
}
```

```js
// File: src/routes/noteRoutes.js — the full protected router
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { createNoteSchema, patchNoteSchema } from '../validators/noteSchemas.js';

export function createNoteRoutes({ controller, middleware }) {
  const router = Router();

  router.use(middleware.requireAuth);                    // everything below is protected

  router.get('/', validate(listNotesSchema, 'query'), controller.list);
  router.post('/', validate(createNoteSchema), controller.create);

  router.get('/:id', middleware.loadNote, controller.getOne);
  router.patch('/:id', middleware.loadNote, middleware.requireOwner, validate(patchNoteSchema), controller.update);
  router.delete('/:id', middleware.loadNote, middleware.requireOwner, controller.remove);

  return router;
}
```

```js
// File: src/routes/index.js — the API surface, in one readable file
export function createApiRouter({ controllers, middleware }) {
  const router = Router();

  router.use(middleware.authenticate);                    // parse credentials for everyone
  router.use('/auth', createAuthRoutes({ controllers, middleware }));
  router.use('/notes', createNoteRoutes({ controllers, middleware }));
  router.use('/admin', middleware.requireAuth, middleware.requireRole('ADMIN'), createAdminRoutes({ controllers }));

  return router;
}
```

```js
// File: tests/notes.auth.test.js — the boundary table
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';

/* … build the app exactly as in §7, with an in-memory note repository … */

const cases = [
  { name: 'GET /notes anonymous',            method: 'GET',    path: '/notes',            expected: 401 },
  { name: 'POST /notes anonymous',           method: 'POST',   path: '/notes',            expected: 401 },
  { name: 'GET /notes bad token',            method: 'GET',    path: '/notes', token: 'x', expected: 401 },
  { name: 'GET /notes owner',                method: 'GET',    path: '/notes', token: 'u1', expected: 200 },
  { name: 'PATCH someone else’s note',       method: 'PATCH',  path: '/notes/n2', token: 'u1', expected: 403 },
  { name: 'PATCH own note',                  method: 'PATCH',  path: '/notes/n1', token: 'u1', expected: 200 },
  { name: 'PATCH own note as admin',         method: 'PATCH',  path: '/notes/n1', token: 'admin', expected: 200 },
  { name: 'DELETE own note',                 method: 'DELETE', path: '/notes/n1', token: 'u1', expected: 204 },
  { name: 'GET /admin/users as USER',        method: 'GET',    path: '/admin/users', token: 'u1', expected: 403 },
  { name: 'GET /admin/users as ADMIN',       method: 'GET',    path: '/admin/users', token: 'admin', expected: 200 },
];

for (const item of cases) {
  test(item.name, async () => {
    const response = await call(item);
    assert.equal(response.status, item.expected);
  });
}

test('the anonymous 401 advertises the scheme', async () => {
  const response = await call({ method: 'GET', path: '/notes' });
  assert.equal(response.status, 401);
  assert.match(response.headers.get('www-authenticate'), /^Bearer/);
});

test('a login failure is indistinguishable from an unknown email', async () => {
  const unknown = await post('/auth/login', { email: 'nobody@example.com', password: 'supersecret123' });
  const wrong = await post('/auth/login', { email: 'ankit@example.com', password: 'wrong-password-1' });

  assert.equal(unknown.status, 401);
  assert.equal(wrong.status, 401);
  assert.deepEqual(await unknown.json(), await wrong.json());     // identical bodies
});

test('registration ignores a client-supplied role', async () => {
  await post('/auth/register', { email: 'sneaky@example.com', password: 'supersecret123', name: 'S', role: 'ADMIN' });
  assert.equal((await post('/auth/register', { email: 'sneaky@example.com', password: 'supersecret123', name: 'S' })).status, 422);
  // …and the created user (when registered without the extra key) is a USER.
});
```

</details>

***

## Exercise 13.2 — Find the authentication bugs

```js
// File: auth.js — six bugs hide in this file
import jwt from 'jsonwebtoken';
import { User } from './models/User.js';

const SECRET = 'my-super-secret-key-123';

export async function register(req, res) {
  const { email, password, role } = req.body;
  const user = await User.create({ email, password, role: role || 'USER' });
  res.json({ data: user });
}

export async function login(req, res) {
  const { email, password } = req.body;
  const user = await User.findOne({ email });
  if (!user || user.password !== password) {
    return res.status(403).json({ message: 'Wrong email or unknown password' });
  }
  const token = jwt.sign({ userId: user.id, role: user.role }, SECRET);
  res.json({ token, user });
}

export function requireAuth(req, res, next) {
  const token = req.query.token || req.headers.authorization;
  const payload = jwt.verify(token, SECRET);
  req.user = payload;
  next();
}
```

<details>

<summary>Solution</summary>

| #  | Bug                                                                    | Impact                                                                | Fix                                                                                 |
| -- | ---------------------------------------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 1  | `role: role \|\| 'USER'` — client-supplied role                        | Anyone can register as `ADMIN`                                        | Assign `'USER'`; validate the body with `.strict()`; promotion via an admin route   |
| 2  | Passwords compared in plain text (`user.password !== password`)        | Passwords are stored unhashed → a database leak exposes every account | Store `passwordHash`; `await passwordHasher.compare()`                              |
| 3  | `res.json({ data: user })` returns the whole user document             | Leaks `passwordHash`, internal flags, tokens                          | Return a DTO                                                                        |
| 4  | `403` and different messages for "unknown email" and "wrong password"  | User enumeration; wrong status for "unauthenticated"                  | `401` + one message for both cases                                                  |
| 5  | `SECRET` hard-coded in the source                                      | Anyone with the repo can forge tokens forever                         | `config.jwtSecret` from the environment; rotate on exposure; fail fast when missing |
| 6  | `jwt.sign(...)` without `expiresIn`, and `verify` without `algorithms` | Tokens never expire; `alg` confusion attacks                          | `expiresIn: '15m'` + `algorithms: ['HS256']`                                        |
| 7  | `req.query.token` accepted                                             | Tokens end up in URLs, logs, referrers and browser history            | Only the `Authorization` header (or an `httpOnly` cookie)                           |
| 8  | `jwt.verify` can throw, with no `try/catch`                            | A malformed token becomes a 500 (or an unhandled rejection)           | Catch and respond `401` (as in `createAuthenticate`)                                |
| 9  | No `requireAuth` on any route                                          | The middleware exists but protects nothing                            | Mount it at the router level                                                        |
| 10 | `req.user = payload` trusts claims without loading the user            | A deleted or demoted user keeps working until expiry                  | Look up the user; use `sub` as the id                                               |

```js
// File: auth.fixed.js
import jwt from 'jsonwebtoken';
import { z } from 'zod';
import { AppError, UnauthorizedError } from './utils/AppError.js';
import { toUserDto } from './dtos/userDto.js';
import { config } from './config/env.js';                 // validates JWT_SECRET at startup

/** A hash no password matches: makes a failed login take the same time as a real one. */
const DUMMY_HASH = 'scrypt$0000000000000000000000000000000000000000$' + '00'.repeat(64);

const registerSchema = z
  .object({
    email: z.email().max(254),
    password: z.string().min(12).max(200),
    name: z.string().trim().min(1).max(100),
  })
  .strict();

const loginSchema = z.object({ email: z.email().max(254), password: z.string().min(1).max(200) }).strict();

export function createAuthService({ userRepository, passwordHasher }) {
  return {
    async register(input) {
      const payload = registerSchema.parse(input);          // role cannot be sent at all
      const user = await userRepository.create({
        email: payload.email.trim().toLowerCase(),
        name: payload.name,
        passwordHash: await passwordHasher.hash(payload.password),
        role: 'USER',
      });
      return toUserDto(user);
    },

    async login(input) {
      const { email, password } = loginSchema.parse(input);
      const user = await userRepository.findByEmail(email.trim().toLowerCase());
      const ok = await passwordHasher.compare(password, user?.passwordHash ?? DUMMY_HASH);
      if (!user || !ok) throw new UnauthorizedError('Invalid email or password');
      return { user: toUserDto(user) };
    },

    signAccessToken(user) {
      return jwt.sign({ sub: user.id, role: user.role }, config.jwtSecret, {
        algorithm: 'HS256',
        expiresIn: '15m',
        issuer: config.jwtIssuer,
        audience: config.jwtAudience,
      });
    },
  };
}

export async function loginHandler(req, res, next) {
  try {
    const { user } = await authService.login(req.validated.body);
    res.json({ data: { user }, meta: { accessToken: authService.signAccessToken(user), expiresIn: 900 } });
  } catch (error) {
    next(error);
  }
}

export function createRequireAuth({ userRepository }) {
  return async function requireAuth(req, res, next) {
    try {
      const header = req.get('authorization') ?? '';
      const [scheme, token] = header.split(' ');
      if (scheme !== 'Bearer' || !token) throw new UnauthorizedError('Authentication is required');

      const payload = jwt.verify(token, config.jwtSecret, {
        algorithms: ['HS256'],                              // never trust the token header
        issuer: config.jwtIssuer,
        audience: config.jwtAudience,
      });

      const user = await userRepository.findById(payload.sub);
      if (!user) throw new UnauthorizedError('Authentication is required');

      req.user = { id: user.id, role: user.role, email: user.email };
      return next();
    } catch (error) {
      if (error instanceof UnauthorizedError) return next(error);

      // Expired or invalid token: the client needs to know exactly which, so TOKEN_EXPIRED
      // uses AppError directly — the class defaults cover the other 401 cases.
      if (error.name === 'TokenExpiredError') {
        return next(new AppError('The access token has expired', { statusCode: 401, code: 'TOKEN_EXPIRED' }));
      }
      return next(new UnauthorizedError('The access token is invalid'));
    }
  };
}
```

**The one-line version:** never trust the client for identity, role or password handling; always hash, always expire, always load the user, always return a DTO.

</details>

***

## What's next

The login flow above returned "an access token" without explaining what one is. Next: JSON Web Tokens from the inside — signature, claims, expiry, algorithms, and the attacks that target them.

→ [14 — JWT](14-jwt.md)
