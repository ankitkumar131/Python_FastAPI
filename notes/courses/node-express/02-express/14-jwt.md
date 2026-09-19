# 14 — JWT (JSON Web Tokens)

> **Where this fits:** Chapter 13 wired authentication middleware but treated the token as a black box.
> This chapter opens it: what a JWT is, how it is signed and verified, why it cannot be revoked, and how
> the access + refresh pattern fixes that. The dedicated deep dive is
> 04-authentication/03-jwt.md *(not available in this published source revision)*; here the focus is the Express
> implementation.

---

## 1. What a JWT actually is

> **A JWT (JSON Web Token) is a cryptographically signed, URL-safe string that carries a set of claims
> (key–value facts) about a subject. Anyone can read it. Only someone with the signing key can produce a
> valid one.**

```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9   .   eyJzdWIiOiJ1MSIsInJvbGUiOiJVU0VSIiwiaWF0IjoxNzg5NzEzNjY0LCJleHAiOjE3ODk3MTQ1NjR9   .   4oQ0n1J3c-8mWQ…
└──────────────── header ───────────────┘   └────────────────────────── payload ──────────────────────────┘   └──── signature ────┘
```

Three parts, separated by dots. The first two are **base64url**, not encryption — `atob` (or one line of
Node) reveals them:

```js
// File: inspect-jwt.js
/** Decode a JWT's header and payload UNVERIFIED — useful for debugging, never for security. */
export function inspectToken(token) {
  const [header, payload, signature] = String(token).split('.');
  if (!header || !payload || !signature) return { valid: false, reason: 'not three dot-separated parts' };

  const decode = (part) => JSON.parse(Buffer.from(part, 'base64url').toString('utf8'));
  return { valid: true, header: decode(header), payload: decode(payload), signatureBytes: Buffer.from(signature, 'base64url').length };
}

console.log(inspectToken(token));
```

```text
{
  valid: true,
  header: { alg: 'HS256', typ: 'JWT' },
  payload: {
    sub: 'u1',
    role: 'USER',
    iat: 1789713664,        // issued at  (seconds since the epoch)
    exp: 1789714564,        // expires at (iat + 900 = 15 minutes)
    aud: 'notes-web',
    iss: 'notes-api'
  },
  signatureBytes: 32
}
```

| Part | Contains | Trustworthy? |
| --- | --- | --- |
| **Header** | `alg` (the signing algorithm) and `typ` | No — the client sends it; hence always pin the algorithm server-side |
| **Payload** | Claims: `sub`, `role`, `exp`, whatever you choose | **No**, until the signature is verified. Base64 is not security |
| **Signature** | `HMAC(header + "." + payload, secret)` or an RSA/ECDSA equivalent | The only part an attacker cannot forge without the key |

```text
HS256 signing                                  Verification
─────────────                                  ────────────
signature = HMAC-SHA256(                       signature' = HMAC-SHA256(header + "." + payload, secret)
  secret,                                      if signature' === signature (timing-safe):
  base64url(header) + "." + base64url(payload)     claims are authentic
)                                              also check: exp, nbf, iss, aud
```

> **"Signed" means tamper-evident, not secret.** Never put a password, a national id or a credit-card
> number in a payload. The `sub` (user id) is fine; a role is fine; a secret is not.

---

## 2. Registered claims

| Claim | Meaning | Example | Why it matters |
| --- | --- | --- | --- |
| `sub` | Subject — who the token is about | `"u1"` | Use it to load the user; never trust a `userId` inside the token if you can reload |
| `iss` | Issuer | `"notes-api"` | Reject tokens minted by another service that shares a key |
| `aud` | Audience — who the token is for | `"notes-web"` | A token for the mobile app should not open the web API |
| `exp` | Expiry (seconds) | `iat + 900` | The only defence after a token leaks |
| `iat` | Issued at | `1789713664` | Useful for "password changed after this token?" checks |
| `nbf` | Not before | `1789713664` | Rarely needed; for scheduled access |
| `jti` | Unique token id | UUID | Needed for revocation lists (see §5) |

Private claims (`role`, `plan`, `orgId`) are allowed and useful — but keep the payload small: it is sent
on **every** request, and it is readable by anyone who can see the traffic.

---

## 3. Signing and verifying with `jsonwebtoken`

```bash
npm install jsonwebtoken
```

```js
// File: src/utils/tokenService.js
import jwt from 'jsonwebtoken';
import { randomUUID } from 'node:crypto';
import { AppError } from './AppError.js';

export function createTokenService({ secret, refreshSecret, issuer, audience, accessTtl = '15m', refreshTtl = '30d' }) {
  if (typeof secret !== 'string' || secret.length < 32) {
    throw new Error('JWT secret must be at least 32 characters — generate one with: openssl rand -base64 48');
  }

  const accessOptions = { algorithm: 'HS256', issuer, audience, expiresIn: accessTtl };
  const refreshOptions = { algorithm: 'HS256', issuer, audience, expiresIn: refreshTtl };

  return {
    accessTokenTtlSeconds: typeof accessTtl === 'number' ? accessTtl : 15 * 60,

    /** short-lived token for API calls */
    signAccessToken({ sub, role }) {
      return jwt.sign({ role }, secret, { ...accessOptions, subject: String(sub) });
    },

    /** long-lived token used only at /auth/refresh. Has a jti so it can be revoked. */
    signRefreshToken({ sub }) {
      return jwt.sign({ jti: randomUUID() }, refreshSecret, { ...refreshOptions, subject: String(sub) });
    },

    /** Throws on bad signature, wrong algorithm, wrong issuer/audience, expiry. */
    verifyAccessToken(token) {
      return jwt.verify(token, secret, { algorithms: ['HS256'], issuer, audience });
    },

    verifyRefreshToken(token) {
      return jwt.verify(token, refreshSecret, { algorithms: ['HS256'], issuer, audience });
    },

    /** For logs and audit trails: the payload without verification. Never an authorisation input. */
    peek(token) {
      return jwt.decode(token);
    },
  };
}
```

```js
// File: token-demo.mjs
import { createTokenService } from './src/utils/tokenService.js';

const tokens = createTokenService({
  secret: 'dev-access-secret-that-is-at-least-32-chars',
  refreshSecret: 'dev-refresh-secret-that-is-at-least-32-chars',
  issuer: 'notes-api',
  audience: 'notes-web',
});

const access = tokens.signAccessToken({ sub: 'u1', role: 'USER' });
console.log(access.split('.').length, 'parts,', access.length, 'characters');
console.log(tokens.verifyAccessToken(access));
console.log(tokens.peek(access));
```

```text
3 parts, 209 characters
{ role: 'USER', sub: 'u1', iat: 1789713664, exp: 1789714564, aud: 'notes-web', iss: 'notes-api' }
{ role: 'USER', sub: 'u1', iat: 1789713664, exp: 1789714564, aud: 'notes-web', iss: 'notes-api' }
```

### What verification failures look like

Every failure is a thrown error with a `name` you can translate into a status code. These outputs are
from `jsonwebtoken` 9.x:

| Situation | Error `name` | `error.message` | Answer to the client |
| --- | --- | --- | --- |
| Signature does not match (tampered, wrong key) | `JsonWebTokenError` | `invalid signature` | `401 UNAUTHENTICATED` |
| `exp` in the past | `TokenExpiredError` | `jwt expired` (has `error.expiredAt`) | `401 TOKEN_EXPIRED` |
| `algorithms` does not include the token's `alg` | `JsonWebTokenError` | `invalid algorithm` | `401 UNAUTHENTICATED` |
| Wrong `iss` or `aud` | `JsonWebTokenError` | `jwt issuer invalid. expected: …` / `jwt audience invalid` | `401 UNAUTHENTICATED` |
| Unsigned token (`alg: none`) | `JsonWebTokenError` | `jwt signature is required` | `401 UNAUTHENTICATED` |
| Token is not three parts | `JsonWebTokenError` | `jwt malformed` | `401 UNAUTHENTICATED` |

```js
// File: translate-token-errors.js
import jwt from 'jsonwebtoken';
import { AppError, UnauthorizedError } from './utils/AppError.js';

export function verifyOrThrow(token, secret, options) {
  try {
    return jwt.verify(token, secret, options);
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      // The client must know this specific case: it should call /auth/refresh, not /auth/login.
      throw new AppError('The access token has expired', { statusCode: 401, code: 'TOKEN_EXPIRED', cause: error });
    }
    if (error.name === 'JsonWebTokenError' || error.name === 'NotBeforeError') {
      throw new UnauthorizedError('The access token is invalid', { cause: error });
    }
    throw error;                                     // programming error, not a client error
  }
}
```

### `jose` — the modern alternative

`jose` is ESM-first, uses the Web Crypto API, and has no heavyweight dependencies:

```bash
npm install jose
```

```js
// File: jose-example.mjs
import { SignJWT, jwtVerify, errors } from 'jose';

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

const token = await new SignJWT({ role: 'USER' })
  .setProtectedHeader({ alg: 'HS256' })
  .setSubject('u1')
  .setIssuedAt()
  .setIssuer('notes-api')
  .setAudience('notes-web')
  .setExpirationTime('15m')
  .sign(secret);

const { payload, protectedHeader } = await jwtVerify(token, secret, { issuer: 'notes-api', audience: 'notes-web' });
console.log(protectedHeader.alg, payload.sub, payload.role);

try {
  await jwtVerify(`${token}x`, secret);
} catch (error) {
  if (error instanceof errors.JWTExpired) console.log('expired', error.code);          // ERR_JWT_EXPIRED
  else console.log('invalid', error.code);                                             // ERR_JWS_SIGNATURE_VERIFICATION_FAILED
}
```

```text
HS256 u1 USER
invalid ERR_JWS_SIGNATURE_VERIFICATION_FAILED
```

| | `jsonwebtoken` 9.x | `jose` 6.x |
| --- | --- | --- |
| Module system | CommonJS (works in ESM via default import) | Native ESM only |
| Crypto backend | Node `crypto` | Web Crypto (`crypto.subtle`) — also runs in Deno, Bun, Workers |
| API style | `sign` / `verify` callbacks-free | Fluent builders (`new SignJWT().setSubject()…`) + promises |
| Algorithms | HS/RS/PS/ES | HS/RS/PS/ES/EdDSA + JWK/JWKS/encryption |
| Errors | `TokenExpiredError`, `JsonWebTokenError` | Typed `JOSEError` subclasses with `code` strings |
| Best for | Existing Express codebases | New ESM projects, edge runtimes, key rotation with JWKS |

Both are correct choices. These notes use `jsonwebtoken` in the Express chapters because it is what most
existing projects use, and show `jose` where a modern ESM example is clearer.

---

## 4. Access tokens and refresh tokens

A long-lived token is convenient and dangerous. The standard split:

```text
Login
  │
  ├─ access token   exp: 15 minutes   → Authorization: Bearer …   on every API call
  └─ refresh token  exp: 30 days      → sent ONLY to /auth/refresh

API call with an expired access token
  │
  ▼
401 TOKEN_EXPIRED  ──▶ client calls POST /auth/refresh with the refresh token
                          │
                          ├─ valid   → new access token + NEW refresh token (rotation)
                          └─ invalid → 401, the client must sign in again
```

| | Access token | Refresh token |
| --- | --- | --- |
| Lifetime | 5–15 minutes | 7–30 days |
| Carried in | `Authorization: Bearer` header | `httpOnly` cookie (browser) or secure storage (mobile) |
| Verified by | Signature + claims only | Signature + claims + **presence in the server-side store** |
| Revocable | Only via a short-lived denylist | Yes — delete from the store |
| Stored server-side | No | Yes (`jti`, user, device, IP, expiry) |
| Why | Cheap, stateless per-request checks | Long sessions without long-lived credentials |

```text
Rotation and reuse detection (the important part)
─────────────────────────────────────────────────
Every refresh consumes its token and issues a new one.
    refresh#1 → new access + refresh#2 (refresh#1 marked used)
    refresh#2 → new access + refresh#3 (refresh#2 marked used)

If refresh#1 is presented AGAIN, one of two things happened:
  • the client retried a lost response, or
  • an attacker stole a copy and is replaying it.
The safe response: revoke the whole family of tokens for that user/device and force a sign-in.
```

---

## 5. Revocation: the hard part

A JWT is valid until `exp` — that is the price of statelessness. Four ways to regain control:

| Strategy | How | Cost | When |
| --- | --- | --- | --- |
| **Short expiry** | 5–15 minute access tokens | A leaked token works for ≤ 15 minutes | Always — the baseline |
| **Refresh-token store** | Delete the row on logout or password change | One lookup per refresh (once per 15 min) | Always, for the refresh token |
| **Denylist by `jti`** | Keep revoked ids in Redis with TTL = remaining lifetime | Memory grows with revocations; one check per request | "Log out everywhere", admin bans, incident response |
| **Token version claim** | Store `tokenVersion` on the user; embed it in the token; bump to revoke all tokens | One user lookup per request (cheap, often cached) | Services that already load the user |

```js
// File: src/services/tokenRevocation.js
/**
 * A bounded denylist. After the token's own expiry passes, the entry is useless,
 * so the TTL is set to exactly the remaining lifetime — memory is self-cleaning.
 */
export function createRevocationStore({ cache }) {
  const key = (jti) => `revoked:jti:${jti}`;

  return {
    async revoke(jti, expiresAtSeconds) {
      const ttlSeconds = Math.max(0, expiresAtSeconds - Math.floor(Date.now() / 1000));
      if (ttlSeconds === 0) return;
      await cache.set(key(jti), '1', { ttlSeconds });
    },

    async isRevoked(jti) {
      return (await cache.get(key(jti))) !== null;
    },
  };
}
```

```js
// File: src/middleware/auth.js (excerpt) — denial check inside the verifier
import { UnauthorizedError } from '../utils/AppError.js';

export function createAuthenticate({ tokenService, userRepository, revocationStore, logger }) {
  return async function authenticate(req, res, next) {
    try {
      const [scheme, token] = (req.get('authorization') ?? '').split(' ');
      if (scheme !== 'Bearer' || !token) {
        req.authError = 'missing-credential';
        return next();
      }

      const claims = tokenService.verifyAccessToken(token);

      // "Sign out everywhere" and emergency bans: a handful of Redis GETs per request.
      if (claims.jti && (await revocationStore.isRevoked(claims.jti))) {
        req.authError = 'token-revoked';
        return next();
      }

      const user = await userRepository.findById(claims.sub);
      if (!user) {
        req.authError = 'user-no-longer-exists';
        return next();
      }

      // Password changes invalidate tokens issued before the change.
      if (claims.iat < Math.floor(new Date(user.passwordChangedAt).getTime() / 1000)) {
        req.authError = 'token-outdated';
        return next();
      }

      req.user = { id: user.id, role: user.role, email: user.email };
      return next();
    } catch (error) {
      req.authError = error.code === 'TOKEN_EXPIRED' ? 'token-expired' : 'invalid-token';
      logger.warn('authentication failed', { requestId: req.id, reason: req.authError });
      return next();
    }
  };
}
```

> **`iat` has one-second resolution.** A token issued in the same second as a password change can slip
> through a `claims.iat < passwordChangedAt` check. Compare with `<=` for password changes, or bump a
> numeric `tokenVersion` instead — it has no granularity problem.

---

## 6. Where clients should keep tokens

| Storage | XSS can steal it? | CSRF applies? | Survives reload? | Verdict |
| --- | --- | --- | --- | --- |
| `localStorage` / `sessionStorage` | **Yes — one `innerHTML` bug and the token is gone** | No | Yes | Avoid for long-lived tokens |
| In-memory JS variable | No | No | No (lost on reload) | Good for short access tokens |
| `httpOnly` cookie | No (JS cannot read it) | **Yes — needs `SameSite` and/or CSRF tokens** | Yes | Best for refresh tokens |
| Mobile secure storage | No | n/a | Yes | The mobile equivalent of `httpOnly` |
| URL / query string | Total: it lands in logs, referrers, history | n/a | n/a | Never |

**The pattern these notes use:** access token returned in the response body and kept in memory by the
client (15 minutes of exposure at most); refresh token in an `httpOnly`, `SameSite=Strict`,
`Secure` cookie scoped to `/api/v1/auth`, so only the refresh endpoint ever receives it.

```js
// File: refresh-cookie.js — the cookie flags, one by one
res.cookie('refreshToken', refreshToken, {
  httpOnly: true,     // document.cookie cannot read it → XSS cannot exfiltrate it
  sameSite: 'strict', // the browser will not send it on cross-site requests → CSRF is contained
  secure: isProduction, // HTTPS only; keep false locally while using plain HTTP
  path: '/api/v1/auth', // sent to the refresh/logout endpoints and nowhere else
  maxAge: 30 * 24 * 60 * 60 * 1000, // 30 days; must match the refresh token's exp
});
```

---

## 7. The full refresh flow in Express

```js
// File: src/services/refreshTokenStore.js — in-memory here, Redis in 03-databases/05-redis
import { randomUUID } from 'node:crypto';

/**
 * Records every issued refresh token so that it can be revoked, rotated and
 * checked for reuse. The hash is stored, never the token itself.
 */
export function createRefreshTokenStore({ hasher }) {
  /** jti → { userId, familyId, tokenHash, expiresAt, usedAt, revokedAt, userAgent, ip } */
  const records = new Map();

  return {
    async save({ jti, userId, tokenHash, expiresAt, familyId = randomUUID(), userAgent, ip }) {
      records.set(jti, {
        userId, familyId, tokenHash, expiresAt, userAgent, ip,
        usedAt: null, revokedAt: null,
      });
      return familyId;
    },

    async findByJti(jti) {
      return records.get(jti) ?? null;
    },

    async markUsed(jti) {
      const record = records.get(jti);
      if (record) record.usedAt = new Date().toISOString();
    },

    async revoke(jti) {
      const record = records.get(jti);
      if (record) record.revokedAt = new Date().toISOString();
    },

    /** Reuse detection: if a token that was already used comes back, kill the whole family. */
    async revokeFamily(familyId) {
      for (const record of records.values()) {
        if (record.familyId === familyId) record.revokedAt = new Date().toISOString();
      }
    },

    async listActiveForUser(userId) {
      return [...records.values()].filter((record) => record.userId === userId && !record.revokedAt);
    },
  };
}
```

```js
// File: src/services/authService.js (refresh + logout, extending chapter 13)
import { randomUUID, createHash } from 'node:crypto';
import { AppError, UnauthorizedError } from '../utils/AppError.js';

const hashToken = (token) => createHash('sha256').update(token).digest('hex');

export function createAuthService({
  userRepository, passwordHasher, tokenService, refreshTokenStore, logger,
}) {
  /* … register() and login() from chapter 13, with login storing the refresh record … */

  return {
    async login({ email, password }, context = {}) {
      const user = await userRepository.findByEmail(String(email).trim().toLowerCase());
      const ok = await passwordHasher.compare(password, user?.passwordHash ?? DUMMY_HASH);
      if (!user || !ok) throw new UnauthorizedError('Invalid email or password');

      const accessToken = tokenService.signAccessToken({ sub: user.id, role: user.role });
      const refreshToken = tokenService.signRefreshToken({ sub: user.id });
      const { jti, exp } = tokenService.verifyRefreshToken(refreshToken);

      await refreshTokenStore.save({
        jti,
        userId: user.id,
        tokenHash: hashToken(refreshToken),
        expiresAt: exp,
        userAgent: context.userAgent,
        ip: context.ip,
      });

      logger.info('login succeeded', { userId: user.id });
      return { user, accessToken, refreshToken, expiresIn: tokenService.accessTokenTtlSeconds };
    },

    /**
     * Exchanges a refresh token for a new pair.
     * Rotation: the presented token is marked used and a brand-new one is issued.
     * Reuse detection: a used token presented again revokes the entire family.
     */
    async refresh(presentedToken) {
      const { jti, sub, exp } = tokenService.verifyRefreshToken(presentedToken);
      const record = await refreshTokenStore.findByJti(jti);

      // Unknown (forged, or from a store that was wiped) → refuse.
      if (!record) throw new UnauthorizedError('The refresh token is no longer valid');

      // Revoked (logout, password change, incident response) → refuse.
      if (record.revokedAt) throw new UnauthorizedError('The refresh token has been revoked');

      // Already used → replay. This is the attack signal: revoke the whole family.
      if (record.usedAt) {
        await refreshTokenStore.revokeFamily(record.familyId);
        logger.warn('refresh token reuse detected — family revoked', { userId: record.userId, jti });
        throw new UnauthorizedError('The refresh token has already been used; please sign in again');
      }

      // The stored hash must match the presented token.
      if (record.tokenHash !== hashToken(presentedToken)) {
        throw new UnauthorizedError('The refresh token is invalid');
      }

      // Rotation happens even if the response is lost: the client keeps the newest token it received.
      await refreshTokenStore.markUsed(jti);

      const user = await userRepository.findById(sub);
      if (!user) throw new UnauthorizedError('The account no longer exists');

      const accessToken = tokenService.signAccessToken({ sub: user.id, role: user.role });
      const refreshToken = tokenService.signRefreshToken({ sub: user.id });
      const next = tokenService.verifyRefreshToken(refreshToken);

      await refreshTokenStore.save({
        jti: next.jti,
        userId: user.id,
        tokenHash: hashToken(refreshToken),
        expiresAt: next.exp,
        familyId: record.familyId,              // same family → reuse detection still works
        userAgent: record.userAgent,
        ip: record.ip,
      });

      logger.info('tokens refreshed', { userId: user.id });
      return { user, accessToken, refreshToken, expiresIn: tokenService.accessTokenTtlSeconds };
    },

    async logout({ refreshToken }) {
      if (!refreshToken) return;
      const { jti } = tokenService.verifyRefreshToken(refreshToken);
      await refreshTokenStore.revoke(jti);
      logger.info('logout', { jti });
    },

    /** "Sign out of all devices" — revoke every active refresh token for the user. */
    async logoutAll(userId) {
      const active = await refreshTokenStore.listActiveForUser(userId);
      for (const record of active) await refreshTokenStore.revoke(record.jti);
      return active.length;
    },
  };
}
```

```js
// File: src/routes/authRoutes.js (excerpt) — refresh and logout endpoints
router.post('/refresh', async (req, res, next) => {
  try {
    const presented = req.cookies?.refreshToken;
    if (!presented) {
      return res.status(401).json({
        error: { code: 'UNAUTHENTICATED', message: 'No refresh token was provided', requestId: req.id },
      });
    }

    const { user, accessToken, refreshToken, expiresIn } = await authService.refresh(presented);

    // Rotate the cookie as well: the old refresh token is now dead.
    res.cookie('refreshToken', refreshToken, refreshCookieOptions);
    return res.json({ data: { user: toUserDto(user) }, meta: { accessToken, tokenType: 'Bearer', expiresIn } });
  } catch (error) {
    // A failed refresh must clear the cookie, or the browser keeps sending a dead token.
    res.clearCookie('refreshToken', { path: '/api/v1/auth' });
    return next(error);
  }
});
```

```bash
BASE=http://localhost:3000/api/v1

# 1. Log in and capture both tokens
curl -s -c /tmp/cookies.txt -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"ankit@example.com","password":"supersecret123"}' > /tmp/login.json
ACCESS=$(node -e "console.log(JSON.parse(require('fs').readFileSync('/tmp/login.json')).meta.accessToken)")

# 2. Use the access token
curl -s "$BASE/notes" -H "Authorization: Bearer $ACCESS"

# 3. Refresh (the cookie jar carries the httpOnly refresh token)
curl -s -b /tmp/cookies.txt -c /tmp/cookies.txt -X POST "$BASE/auth/refresh"

# 4. Replaying the OLD refresh token is now detected
```

```text
Step 3 → 200 with a brand-new access token and a rotated Set-Cookie.
Step 4 → 401 UNAUTHENTICATED, body: "The refresh token has already been used; please sign in again"
          and every refresh token in that family is revoked.
```

---

## 8. Algorithms, secrets and the attacks that matter

| Algorithm | Key type | Signs | Verifies | Use when |
| --- | --- | --- | --- | --- |
| `HS256` | One shared secret (32+ bytes) | Any holder of the secret | Any holder of the secret | One service, or services you fully trust |
| `RS256` | Private key signs, public key verifies | Only the private-key holder | Anyone with the public key | Separate issuers/verifiers, JWKS endpoints |
| `ES256` | ECDSA key pair | Private key | Public key | Smaller tokens than RSA, same trust split |
| `EdDSA` | Ed25519 key pair | Private key | Public key | Modern default where supported |
| `none` | No key | — | — | **Never accept it** |

```text
Algorithm confusion attack
──────────────────────────
Naive verifier:  jwt.verify(token, PUBLIC_KEY)              // expecting RS256
Attacker sends:  a token signed with HMAC using the PUBLIC KEY as the secret
Result:          the naive verifier computes an HMAC with the same bytes and it matches
Defence:         always pass algorithms: ['RS256'] — the token header is never trusted
```

| Rule | Why |
| --- | --- |
| Always pass `algorithms: [...]` | Stops `alg: none` and confusion attacks |
| Secrets come from configuration, never the source | A leaked repo must not mean forged tokens |
| Use at least 32 random bytes for HS256 | `openssl rand -base64 48` |
| Rotate secrets | Support two keys briefly: verify with the old, sign with the new (`kid` header) |
| Different secrets for access and refresh tokens | A leaked access secret must not mint refresh tokens |
| Validate `iss` and `aud` | A token from another environment or app must not work here |
| Never accept a token from the query string | URLs leak into logs, history and referrers |
| Log `jti`, never the token | Logs are copied around; a JWT is a credential |

```js
// File: key-rotation.js — verify with either key, sign with the newest
export function createVerifier({ currentSecret, previousSecret }) {
  return function verify(token) {
    try {
      return jwt.verify(token, currentSecret, { algorithms: ['HS256'] });
    } catch (error) {
      if (previousSecret && error.name === 'JsonWebTokenError') {
        return jwt.verify(token, previousSecret, { algorithms: ['HS256'] });   // grace period
      }
      throw error;
    }
  };
}
```

---

## 9. Common mistakes

| Mistake | Why it is dangerous | Fix |
| --- | --- | --- |
| Treating the payload as secret | Base64 is not encryption | Encrypt separately (JWE) if you must carry secrets |
| `jwt.decode()` used for authorisation | It skips signature verification entirely | `jwt.verify()` with pinned algorithms |
| No `algorithms` option | `alg: none` and confusion attacks | `{ algorithms: ['HS256'] }` |
| Long-lived access tokens ("30d") | A stolen token is a month of access | 5–15 minutes + refresh tokens |
| No refresh rotation | A stolen refresh token is reusable forever | Rotate, store, detect reuse |
| Refresh token stored in `localStorage` | XSS steals a 30-day credential | `httpOnly` cookie or secure storage |
| Logout only deletes the client-side token | The token keeps working until `exp` | Server-side refresh revocation + optional denylist |
| Storing the refresh token in plain text | A database leak hands over every session | Store a SHA-256 hash of the token |
| One secret shared by all services | Any service can mint tokens for the others | Per-audience keys, or asymmetric keys |
| `role` in the token never re-checked | A demoted user keeps admin rights until expiry | Reload the user, or keep access tokens short |
| Big payloads (`permissions: [200 items]`) | Every request carries kilobytes | Short tokens; look up permissions server-side |
| `userId` trusted from the payload without a lookup | Deleted users keep working | `sub` + `findById` |
| Same secret in dev and production | A dev leak compromises production | Per-environment secrets, rotated on exposure |
| Tokens in URLs | Logs, referrers, history | `Authorization` header or `httpOnly` cookie |
| `expiresIn` given `Date`/seconds confusion | Tokens that last 60 years (`expiresIn: 60` is 60 s; `expiresIn: '60'` is 60 ms) | Use the string form (`'15m'`) and assert `exp - iat` in tests |

---

## 10. Testing tokens

```js
// File: tests/token.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createTokenService } from '../src/utils/tokenService.js';
import { createAuthService } from '../src/services/authService.js';
import { createRefreshTokenStore } from '../src/services/refreshTokenStore.js';
import { createHash } from 'node:crypto';

const tokenService = createTokenService({
  secret: 'test-access-secret-that-is-at-least-32-chars',
  refreshSecret: 'test-refresh-secret-that-is-at-least-32-chars',
  issuer: 'notes-api',
  audience: 'notes-web',
  accessTtl: '15m',
  refreshTtl: '30d',
});

const users = [{ id: 'u1', email: 'ankit@example.com', passwordHash: 'hashed:supersecret123', role: 'USER' }];
const userRepository = {
  async findById(id) { return users.find((user) => user.id === id) ?? null; },
  async findByEmail(email) { return users.find((user) => user.email === email) ?? null; },
};
const passwordHasher = {
  hash: async (plain) => `hashed:${plain}`,
  compare: async (plain, hash) => hash === `hashed:${plain}`,
};
const logger = { info() {}, warn() {}, error() {} };

let authService;

before(() => {
  authService = createAuthService({
    userRepository, passwordHasher, tokenService,
    refreshTokenStore: createRefreshTokenStore(),
    logger,
  });
});

test('an access token carries sub, role, iss, aud and a 15-minute expiry', () => {
  const token = tokenService.signAccessToken({ sub: 'u1', role: 'USER' });
  const claims = tokenService.verifyAccessToken(token);

  assert.equal(claims.sub, 'u1');
  assert.equal(claims.role, 'USER');
  assert.equal(claims.iss, 'notes-api');
  assert.equal(claims.aud, 'notes-web');
  assert.equal(claims.exp - claims.iat, 15 * 60);
});

test('a token signed with another secret is rejected', () => {
  const other = createTokenService({
    secret: 'a-different-secret-of-at-least-32-chars!!',
    refreshSecret: 'another-refresh-secret-32-chars-long-ok!',
    issuer: 'notes-api', audience: 'notes-web',
  });
  const token = other.signAccessToken({ sub: 'u1', role: 'USER' });

  assert.throws(() => tokenService.verifyAccessToken(token), { name: 'JsonWebTokenError', message: 'invalid signature' });
});

test('a tampered payload is rejected', () => {
  const token = tokenService.signAccessToken({ sub: 'u1', role: 'USER' });
  const [header, payload, signature] = token.split('.');
  const forgedPayload = Buffer.from(JSON.stringify({ sub: 'u1', role: 'ADMIN', exp: 9_999_999_999 })).toString('base64url');

  assert.throws(
    () => tokenService.verifyAccessToken(`${header}.${forgedPayload}.${signature}`),
    { name: 'JsonWebTokenError' },
  );
});

test('an expired token throws TokenExpiredError with expiredAt', () => {
  const soon = createTokenService({
    secret: 'test-access-secret-that-is-at-least-32-chars',
    refreshSecret: 'test-refresh-secret-that-is-at-least-32-chars',
    issuer: 'notes-api', audience: 'notes-web', accessTtl: '-1s',
  });
  const token = soon.signAccessToken({ sub: 'u1', role: 'USER' });

  try {
    tokenService.verifyAccessToken(token);
    assert.fail('expected the token to be expired');
  } catch (error) {
    assert.equal(error.name, 'TokenExpiredError');
    assert.ok(error.expiredAt instanceof Date);
  }
});

test('a token with the wrong audience or issuer is rejected', () => {
  const other = createTokenService({
    secret: 'test-access-secret-that-is-at-least-32-chars',
    refreshSecret: 'test-refresh-secret-that-is-at-least-32-chars',
    issuer: 'another-api', audience: 'another-web',
  });
  const token = other.signAccessToken({ sub: 'u1', role: 'USER' });

  assert.throws(() => tokenService.verifyAccessToken(token), { name: 'JsonWebTokenError', message: /jwt issuer invalid/ });
});

test('login issues an access token and a stored refresh token', async () => {
  const { accessToken, refreshToken } = await authService.login({ email: 'ankit@example.com', password: 'supersecret123' });

  assert.equal(tokenService.verifyAccessToken(accessToken).sub, 'u1');
  const refreshClaims = tokenService.verifyRefreshToken(refreshToken);
  assert.ok(refreshClaims.jti);
  assert.equal(refreshClaims.sub, 'u1');
});

test('refresh rotates the token and the old one stops working', async () => {
  const first = await authService.login({ email: 'ankit@example.com', password: 'supersecret123' });

  const second = await authService.refresh(first.refreshToken);
  assert.notEqual(second.refreshToken, first.refreshToken);

  // The rotated token is fine…
  const third = await authService.refresh(second.refreshToken);
  assert.notEqual(third.refreshToken, second.refreshToken);

  // …and reusing the very first one is detected as a replay.
  await assert.rejects(() => authService.refresh(first.refreshToken), /already been used/);

  // Reuse revokes the whole family: the token issued in step 2 is dead too.
  await assert.rejects(() => authService.refresh(second.refreshToken), /revoked|already been used/);
});

test('logout revokes the refresh token', async () => {
  const { refreshToken } = await authService.login({ email: 'ankit@example.com', password: 'supersecret123' });
  await authService.logout({ refreshToken });

  await assert.rejects(() => authService.refresh(refreshToken), /revoked/);
});

test('logoutAll kills every active refresh token for the user', async () => {
  const a = await authService.login({ email: 'ankit@example.com', password: 'supersecret123' });
  const b = await authService.login({ email: 'ankit@example.com', password: 'supersecret123' });

  const revoked = await authService.logoutAll('u1');
  assert.ok(revoked >= 2);

  await assert.rejects(() => authService.refresh(a.refreshToken), /revoked/);
  await assert.rejects(() => authService.refresh(b.refreshToken), /revoked/);
});

test('the refresh store keeps a hash of the token, never the token itself', async () => {
  const store = createRefreshTokenStore();
  const { refreshToken } = await (async () => {
    const service = createAuthService({
      userRepository, passwordHasher,
      tokenService: {
        ...tokenService,
        signRefreshToken: () => 'refresh-token-value',
        verifyRefreshToken: () => ({ jti: 'jti-1', sub: 'u1', exp: Math.floor(Date.now() / 1000) + 60 }),
        accessTokenTtlSeconds: 900,
        signAccessToken: () => 'access',
      },
      refreshTokenStore: store, logger,
    });
    return service.login({ email: 'ankit@example.com', password: 'supersecret123' });
  })();

  const record = await store.findByJti('jti-1');
  assert.equal(record.tokenHash, createHash('sha256').update(refreshToken).digest('hex'));
  assert.equal(JSON.stringify(record).includes(refreshToken), false);
});
```

```bash
node --test tests/token.test.js
```

```text
✔ an access token carries sub, role, iss, aud and a 15-minute expiry
✔ a token signed with another secret is rejected
✔ a tampered payload is rejected
✔ an expired token throws TokenExpiredError with expiredAt
✔ a token with the wrong audience or issuer is rejected
✔ login issues an access token and a stored refresh token
✔ refresh rotates the token and the old one stops working
✔ logout revokes the refresh token
✔ logoutAll kills every active refresh token for the user
✔ the refresh store keeps a hash of the token, never the token itself
pass 10
fail 0
```

---

## Exercise 14.1 — Add token refresh to the notes API

Implement, with tests:

| Requirement | Detail |
| --- | --- |
| `POST /auth/refresh` | Reads the refresh token from the `httpOnly` cookie; returns a new access token and a rotated refresh cookie |
| Rotation | Each refresh token is single-use; the used one is recorded as used |
| Reuse detection | Presenting a used token revokes the entire family and returns `401` |
| `/auth/logout` | Revokes the current refresh token and clears the cookie |
| `/auth/logout-all` | Revokes every refresh token for the user (requires an access token) |
| Access-token denylist | "Sign out everywhere" also blocks existing access tokens until they expire |
| `401` shapes | `TOKEN_EXPIRED` when the access token expired, `UNAUTHENTICATED` for everything else |
| Tests | Rotation, replay, family revocation, logout, logout-all, expired access token, and "no cookie" |

<details>
<summary>Solution</summary>

```js
// File: src/services/revocationStore.js
/**
 * Redis in production. In-memory here so the exercise runs with no infrastructure.
 * TTL is the token's remaining lifetime: the entry disappears exactly when the
 * token would have expired anyway, so the set cannot grow without bound.
 */
export function createRevocationStore() {
  const entries = new Map();     // jti → expiresAtMs

  return {
    async revoke(jti, expSeconds) {
      entries.set(jti, expSeconds * 1000);
    },

    async isRevoked(jti) {
      const expiresAt = entries.get(jti);
      if (expiresAt === undefined) return false;
      if (expiresAt <= Date.now()) { entries.delete(jti); return false; }   // self-cleaning
      return true;
    },
  };
}
```

```js
// File: src/services/authService.js (complete token part)
import { createHash, randomUUID } from 'node:crypto';
import { UnauthorizedError } from '../utils/AppError.js';

const sha256 = (value) => createHash('sha256').update(value).digest('hex');
const DUMMY_HASH = 'scrypt$0000000000000000000000000000000000000000$' + '00'.repeat(64);

export function createAuthService({ userRepository, passwordHasher, tokenService, refreshTokenStore, revocationStore, logger }) {
  async function issuePair(user, { familyId, userAgent, ip }) {
    const accessToken = tokenService.signAccessToken({ sub: user.id, role: user.role });
    const refreshToken = tokenService.signRefreshToken({ sub: user.id });
    const refreshClaims = tokenService.verifyRefreshToken(refreshToken);

    await refreshTokenStore.save({
      jti: refreshClaims.jti,
      userId: user.id,
      tokenHash: sha256(refreshToken),
      expiresAt: refreshClaims.exp,
      familyId: familyId ?? randomUUID(),
      userAgent, ip,
    });

    return { accessToken, refreshToken, expiresIn: tokenService.accessTokenTtlSeconds };
  }

  return {
    async login({ email, password }, context = {}) {
      const user = await userRepository.findByEmail(String(email).trim().toLowerCase());
      const ok = await passwordHasher.compare(password, user?.passwordHash ?? DUMMY_HASH);
      if (!user || !ok) throw new UnauthorizedError('Invalid email or password');

      const tokens = await issuePair(user, context);
      return { user, ...tokens };
    },

    async refresh(presented, context = {}) {
      const { jti, sub } = tokenService.verifyRefreshToken(presented);
      const record = await refreshTokenStore.findByJti(jti);

      if (!record) throw new UnauthorizedError('The refresh token is no longer valid');
      if (record.revokedAt) throw new UnauthorizedError('The refresh token has been revoked');

      if (record.usedAt) {
        await refreshTokenStore.revokeFamily(record.familyId);
        logger.warn('refresh token reuse detected', { userId: record.userId, jti });
        throw new UnauthorizedError('The refresh token has already been used; please sign in again');
      }

      if (record.tokenHash !== sha256(presented)) throw new UnauthorizedError('The refresh token is invalid');

      await refreshTokenStore.markUsed(jti);

      const user = await userRepository.findById(sub);
      if (!user) throw new UnauthorizedError('The account no longer exists');

      const tokens = await issuePair(user, {
        familyId: record.familyId,
        userAgent: record.userAgent ?? context.userAgent,
        ip: record.ip ?? context.ip,
      });

      logger.info('tokens refreshed', { userId: user.id });
      return { user, ...tokens };
    },

    async logout({ refreshToken, accessToken }) {
      if (refreshToken) {
        const { jti } = tokenService.verifyRefreshToken(refreshToken);
        await refreshTokenStore.revoke(jti);
      }
      if (accessToken) {
        const claims = tokenService.verifyAccessToken(accessToken);
        // Only worth denying for the remaining lifetime.
        await revocationStore.revoke(claims.jti ?? `sub:${claims.sub}:iat:${claims.iat}`, claims.exp);
      }
    },

    async logoutAll(userId, { accessToken }) {
      const active = await refreshTokenStore.listActiveForUser(userId);
      for (const record of active) await refreshTokenStore.revoke(record.jti);

      if (accessToken) {
        const claims = tokenService.verifyAccessToken(accessToken);
        await revocationStore.revoke(`user:${userId}:before:${claims.iat}`, claims.exp);
      }

      return active.length;
    },
  };
}
```

```js
// File: src/controllers/authController.js (excerpt)
const refreshCookie = (isProduction) => ({
  httpOnly: true,
  sameSite: 'strict',
  secure: isProduction,
  path: '/api/v1/auth',
  maxAge: 30 * 24 * 60 * 60 * 1000,
});

export function createAuthController({ authService, isProduction }) {
  return {
    async refresh(req, res, next) {
      try {
        const presented = req.cookies?.refreshToken;
        if (!presented) {
          return res.status(401).json({
            error: { code: 'UNAUTHENTICATED', message: 'No refresh token was provided', requestId: req.id },
          });
        }

        const { user, accessToken, refreshToken, expiresIn } = await authService.refresh(presented, {
          userAgent: req.get('user-agent') ?? null,
          ip: req.ip,
        });

        res.cookie('refreshToken', refreshToken, refreshCookie(isProduction));
        return res.json({
          data: { user: toUserDto(user) },
          meta: { accessToken, tokenType: 'Bearer', expiresIn },
        });
      } catch (error) {
        res.clearCookie('refreshToken', { path: '/api/v1/auth' });
        return next(error);
      }
    },

    async logoutAll(req, res, next) {
      try {
        const revoked = await authService.logoutAll(req.user.id, {
          accessToken: (req.get('authorization') ?? '').split(' ')[1],
        });
        res.clearCookie('refreshToken', { path: '/api/v1/auth' });
        return res.json({ data: { revokedSessions: revoked } });
      } catch (error) {
        return next(error);
      }
    },
  };
}
```

```js
// File: tests/refresh.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import cookieParser from 'cookie-parser';
import { createTokenService } from '../src/utils/tokenService.js';
import { createRefreshTokenStore } from '../src/services/refreshTokenStore.js';
import { createAuthService } from '../src/services/authService.js';
import { createAuthController } from '../src/controllers/authController.js';
import { createAuthRoutes } from '../src/routes/authRoutes.js';

let server;
let baseUrl;

const users = [{ id: 'u1', email: 'ankit@example.com', passwordHash: 'hashed:supersecret123', role: 'USER', name: 'Ankit', createdAt: '2026-09-18T00:00:00.000Z' }];
const userRepository = {
  async findById(id) { return users.find((user) => user.id === id) ?? null; },
  async findByEmail(email) { return users.find((user) => user.email === email) ?? null; },
};

before(async () => {
  const tokenService = createTokenService({
    secret: 'test-access-secret-that-is-at-least-32-chars',
    refreshSecret: 'test-refresh-secret-that-is-at-least-32-chars',
    issuer: 'notes-api', audience: 'notes-web',
  });
  const refreshTokenStore = createRefreshTokenStore();
  const authService = createAuthService({
    userRepository,
    passwordHasher: { hash: async (plain) => `hashed:${plain}`, compare: async (plain, hash) => hash === `hashed:${plain}` },
    tokenService, refreshTokenStore,
    logger: { info() {}, warn() {}, error() {} },
  });
  const controller = createAuthController({ authService, isProduction: false });

  const app = express();
  app.use(cookieParser());
  app.use(express.json());
  app.use((req, res, next) => { req.id = 'rid'; next(); });
  app.use('/api/v1/auth', createAuthRoutes({ controller, authService, tokenService, userRepository }));

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1/auth`;
});

after(() => new Promise((resolve) => server.close(resolve)));

/** A tiny cookie jar, because fetch does not keep cookies for us. */
function createJar() {
  let cookie = '';
  return {
    header: () => (cookie ? { cookie } : {}),
    absorb: (response) => {
      const set = response.headers.getSetCookie?.() ?? [response.headers.get('set-cookie')].filter(Boolean);
      for (const item of set) cookie = item.split(';')[0];
    },
  };
}

const login = async (jar) => {
  const response = await fetch(`${baseUrl}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'ankit@example.com', password: 'supersecret123' }),
  });
  jar.absorb(response);
  return response.json();
};

test('refresh rotates the cookie and returns a new access token', async () => {
  const jar = createJar();
  const first = await login(jar);
  const oldCookie = jar.header().cookie;

  const response = await fetch(`${baseUrl}/refresh`, { method: 'POST', headers: jar.header() });
  assert.equal(response.status, 200);
  jar.absorb(response);

  const body = await response.json();
  assert.equal(body.data.user.id, 'u1');
  assert.ok(body.meta.accessToken);
  assert.notEqual(jar.header().cookie, oldCookie);
  assert.ok(first.meta.accessToken);
});

test('replaying a rotated refresh token revokes the family', async () => {
  const jar = createJar();
  await login(jar);
  const firstCookie = jar.header().cookie;

  const second = await fetch(`${baseUrl}/refresh`, { method: 'POST', headers: { cookie: firstCookie } });
  assert.equal(second.status, 200);
  const rotated = (second.headers.getSetCookie?.() ?? [second.headers.get('set-cookie')])[0].split(';')[0];

  const replay = await fetch(`${baseUrl}/refresh`, { method: 'POST', headers: { cookie: firstCookie } });
  assert.equal(replay.status, 401);
  assert.match((await replay.json()).error.message, /already been used/);

  // The whole family is dead, including the token the legitimate client holds.
  const after = await fetch(`${baseUrl}/refresh`, { method: 'POST', headers: { cookie: rotated } });
  assert.equal(after.status, 401);
});

test('refresh without a cookie is 401 and does not crash', async () => {
  const response = await fetch(`${baseUrl}/refresh`, { method: 'POST' });
  assert.equal(response.status, 401);
  assert.equal((await response.json()).error.code, 'UNAUTHENTICATED');
});

test('logout revokes the refresh token', async () => {
  const jar = createJar();
  await login(jar);

  const logout = await fetch(`${baseUrl}/logout`, { method: 'POST', headers: jar.header() });
  assert.equal(logout.status, 204);

  const refresh = await fetch(`${baseUrl}/refresh`, { method: 'POST', headers: jar.header() });
  assert.equal(refresh.status, 401);
});

test('an expired access token is reported as TOKEN_EXPIRED', async () => {
  const tokenService = createTokenService({
    secret: 'test-access-secret-that-is-at-least-32-chars',
    refreshSecret: 'test-refresh-secret-that-is-at-least-32-chars',
    issuer: 'notes-api', audience: 'notes-web', accessTtl: '-1s',
  });
  const expired = tokenService.signAccessToken({ sub: 'u1', role: 'USER' });

  const { createAuthenticate, requireAuth } = await import('../src/middleware/auth.js');
  const probe = express();
  probe.use((req, res, next) => { req.id = 'rid'; next(); });
  probe.use(createAuthenticate({ tokenService, userRepository, revocationStore: { isRevoked: async () => false }, logger: { warn() {}, info() {} } }));
  probe.get('/me', requireAuth, (req, res) => res.json({ data: req.user }));
  probe.use((error, req, res, next) => res.status(error.statusCode ?? 500).json({ error: { code: error.code, message: error.message } }));

  const probeServer = probe.listen(0, '127.0.0.1');
  await new Promise((resolve) => probeServer.once('listening', resolve));

  const response = await fetch(`http://127.0.0.1:${probeServer.address().port}/me`, {
    headers: { Authorization: `Bearer ${expired}` },
  });
  assert.equal(response.status, 401);
  assert.equal((await response.json()).error.code, 'TOKEN_EXPIRED');

  await new Promise((resolve) => probeServer.close(resolve));
});
```

```bash
node --test tests/refresh.test.js
```

```text
✔ refresh rotates the cookie and returns a new access token
✔ replaying a rotated refresh token revokes the family
✔ refresh without a cookie is 401 and does not crash
✔ logout revokes the refresh token
✔ an expired access token is reported as TOKEN_EXPIRED
pass 5
fail 0
```

**Design notes**

| Decision | Reason |
| --- | --- |
| Refresh cookie scoped to `/api/v1/auth` | It is sent to two endpoints and nowhere else — the smallest possible exposure |
| Token stored as a SHA-256 hash | A store dump does not hand over live sessions |
| Family ids | Reuse detection must revoke *everything* descended from the stolen token |
| Rotation on every refresh | A stolen refresh token is usable once, and that use is detectable |
| `familyId` preserved across rotation | Otherwise the chain is lost and replay cannot be proved |
| Access token denylist for "log out everywhere" | Short expiry limits the damage, but incidents need an instant stop |
| Denylist TTL = remaining token lifetime | The set is self-cleaning; memory cannot grow unbounded |
| Distinct access/refresh secrets | Different blast radius if one leaks |

</details>

---

## Exercise 14.2 — Break this verifier

```js
// File: naive-jwt.js — eight problems
import jwt from 'jsonwebtoken';

const SECRET = 'secret';

export function signToken(user) {
  return jwt.sign({ userId: user.id, role: user.role, email: user.email, passwordHash: user.passwordHash }, SECRET);
}

export function getUserId(req) {
  const token = req.headers.authorization || req.query.token;
  const payload = jwt.decode(token.replace('Bearer ', ''));
  return payload.userId;
}

export function isAdmin(req) {
  const token = req.headers.authorization;
  const payload = jwt.verify(token, SECRET);
  return payload.role === 'ADMIN';
}
```

<details>
<summary>Solution</summary>

| # | Problem | Attack | Fix |
| --- | --- | --- | --- |
| 1 | `SECRET = 'secret'` in the source | Anyone with the repo forges any token | `config.jwtSecret`, ≥ 32 random bytes, rotated on exposure |
| 2 | No `expiresIn` | A leaked token works forever | `expiresIn: '15m'` (+ refresh tokens) |
| 3 | `passwordHash` inside the payload | The payload is readable by anyone; the hash is now exposed to every log and client | Never carry sensitive data; keep JWTs minimal |
| 4 | `email` in the payload | Personal data in a token that cannot be revoked or updated | Keep `sub` and `role`; look up the rest |
| 5 | `jwt.decode()` for `getUserId` | **No signature check at all** — anyone can forge a payload | `jwt.verify()` with pinned algorithms |
| 6 | Token accepted from `req.query.token` | Tokens leak via logs, referrers and browser history | `Authorization` header only |
| 7 | `jwt.verify(token, SECRET)` without `algorithms` | `alg: none`/confusion attacks | `{ algorithms: ['HS256'] }` + `iss`/`aud` |
| 8 | No `try/catch`; `verify` throws | A malformed token becomes a 500 instead of a 401 | Catch and map to `401`; never leak internals |
| 9 | `token.replace('Bearer ', '')` on a missing header | `Cannot read properties of undefined` → 500 | Check the scheme explicitly |
| 10 | Role taken from the token and never re-checked | A demoted user stays an admin for the token's lifetime | Reload the user; keep the token short-lived |

```js
// File: jwt.fixed.js
import jwt from 'jsonwebtoken';
import { config } from './config/env.js';
import { AppError, UnauthorizedError } from './utils/AppError.js';

const ALGORITHM = 'HS256';
const COMMON = { algorithm: ALGORITHM, issuer: config.jwtIssuer, audience: config.jwtAudience };

export function signAccessToken(user) {
  // Only what an authorisation decision needs — nothing sensitive, nothing large.
  return jwt.sign({ role: user.role }, config.jwtSecret, { ...COMMON, subject: String(user.id), expiresIn: '15m' });
}

export function verifyAccessToken(token) {
  try {
    return jwt.verify(token, config.jwtSecret, { algorithms: [ALGORITHM], issuer: config.jwtIssuer, audience: config.jwtAudience });
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      throw new AppError('The access token has expired', { statusCode: 401, code: 'TOKEN_EXPIRED', cause: error });
    }
    throw new UnauthorizedError('The access token is invalid', { cause: error });
  }
}

export function getUserId(req) {
  const [scheme, token] = (req.get('authorization') ?? '').split(' ');
  if (scheme !== 'Bearer' || !token) throw new UnauthorizedError('Authentication is required');
  return verifyAccessToken(token).sub;                 // verified claims only, never decode()
}

export function isAdmin(req) {
  const [scheme, token] = (req.get('authorization') ?? '').split(' ');
  if (scheme !== 'Bearer' || !token) throw new UnauthorizedError('Authentication is required');

  const claims = verifyAccessToken(token);
  // The role comes from the verified token, and the user is reloaded so a demotion applies immediately.
  return req.user?.id === claims.sub && claims.role === 'ADMIN';
}
```

**The three-line summary:** sign with a real secret and an expiry, verify with pinned algorithms and
claims, and keep nothing sensitive in the payload — it is public.

</details>

---

## What's next

Tokens are one way to carry identity. The other — the one that powered the web before JWTs and still
powers most browser sessions — is a cookie holding an opaque session id. Next: cookies and sessions, and
how to store them in Redis.

→ [15 — Cookies and Sessions](15-cookies-sessions.md)
