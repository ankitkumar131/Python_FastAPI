# 05 — Request and Response

> **Where this fits:** Every handler you write is `(req, res)` or `(req, res, next)`. Chapter 03 mapped
> URLs to handlers; this chapter is the reference for the two objects those handlers receive — what
> each property holds, which methods exist, what Express adds beyond `node:http`, and the failure modes
> each one invites.

---

## 1. Where `req` and `res` come from

```js
// File: inheritance.js
import http from 'node:http';
import express from 'express';

const app = express();

app.get('/demo', (req, res) => {
  // Express extends Node's own objects:
  console.log('req is an IncomingMessage:', req instanceof http.IncomingMessage);     // true
  console.log('res is a ServerResponse  :', res instanceof http.ServerResponse);      // true

  // …and adds its own properties on top:
  console.log('added:', {
    hasParams: 'params' in req,
    hasQuery: 'query' in req,
    hasRes: 'res' in req,           // req.res → back-reference to the response
    hasReq: 'req' in res,           // res.req → back-reference to the request
  });

  res.json({ ok: true });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

That inheritance explains everything else in this chapter:

| Layer | What it contributes |
| --- | --- |
| `node:http` | `req.headers`, `req.rawHeaders`, `req.socket`, `res.writeHead`, `res.end`, `res.write`, streams, socket-level concerns |
| Express prototype | `req.params`, `req.query`, `req.get()`, `req.accepts()`, `res.json()`, `res.status()`, `res.send()`, `res.cookie()`, … |
| Middleware | Adds whatever it wants: `req.body`, `req.cookies`, `req.user`, `req.id`, `res.locals.something` |

**Anything you can do with `node:http`, you can still do through `req`/`res`.** `res.writeHead()` and
`res.end()` work perfectly fine in Express — but calling them directly bypasses Express's helpers, so
you lose ETag handling, `Content-Type` inference, and the automatic `Content-Length`.

---

## 2. `req` — the complete reference

### Properties

| Property | Type | Example value | Notes |
| --- | --- | --- | --- |
| `req.method` | `string` | `'GET'` | Always upper-case |
| `req.url` | `string` | `'/?sort=asc'` | Path **relative to the mount point**, with query |
| `req.originalUrl` | `string` | `'/api/v1/notes?sort=asc'` | Never rewritten — use it for logs and error messages |
| `req.path` | `string` | `'/api/v1/notes'` | Path only, relative to the mount, no query |
| `req.baseUrl` | `string` | `'/api/v1'` | The mount prefix, set by `app.use('/api/v1', router)` |
| `req.headers` | `object` | `{ host: 'localhost:3000', … }` | Header **names lower-cased**; values are strings (arrays for repeated headers) |
| `req.rawHeaders` | `string[]` | `['Host', 'localhost:3000', …]` | Original casing and order — for signature verification |
| `req.params` | `object` | `{ id: '42' }` | Always strings; wildcards are arrays |
| `req.query` | `object` | `{ sort: 'asc', page: '2' }` | Always strings (or arrays/objects, see ch. 06) |
| `req.body` | `any` | `{ title: 'x' }` | `undefined` unless a body parser ran |
| `req.cookies` | `object` | `{ sid: 'abc' }` | `undefined` unless `cookie-parser` ran |
| `req.signedCookies` | `object` | `{ sid: 'abc' }` | Verified cookies only (requires a secret) |
| `req.hostname` | `string` | `'localhost'` | From `Host`/`X-Forwarded-Host`; no port |
| `req.protocol` | `string` | `'http'` / `'https'` | Honours `X-Forwarded-Proto` when `trust proxy` is set |
| `req.secure` | `boolean` | `false` | `req.protocol === 'https'` |
| `req.ip` | `string` | `'127.0.0.1'` | Client IP; with `trust proxy`, the left-most untrusted address |
| `req.ips` | `string[]` | `['203.0.113.9', '10.0.0.1']` | The `X-Forwarded-For` chain, when trusted |
| `req.subdomains` | `string[]` | `['api']` for `api.example.com` | Offsets honoured |
| `req.fresh` | `boolean` | `true` | Conditional request matches the would-be response (`If-None-Match`/`If-Modified-Since`) |
| `req.stale` | `boolean` | `false` | `!req.fresh` |
| `req.xhr` | `boolean` | `false` | Based on `X-Requested-With: XMLHttpRequest` — client-settable, so **not** an authorisation signal |
| `req.route` | `object` | `{ path: '/:id', methods: {...} }` | Only inside a matched route |
| `req.res` / `req.app` | object | — | Back-references |
| `req.socket` | `Socket` | — | Raw TCP socket: `readyState`, `remoteAddress`, TLS info |

### Methods

| Method | Returns | Example |
| --- | --- | --- |
| `req.get(name)` | Header value (case-insensitive) | `req.get('content-type')` → `'application/json; charset=utf-8'` |
| `req.header(name)` | Alias of `req.get` | `req.header('Referer')` |
| `req.accepts(types)` | The best match, or `false` | `req.accepts(['json', 'html'])` → `'html'` |
| `req.acceptsCharsets(list)` | Best charset or `false` | `req.acceptsCharsets(['utf-8'])` |
| `req.acceptsEncodings(list)` | Best encoding or `false` | `req.acceptsEncodings(['gzip', 'br'])` |
| `req.acceptsLanguages(list)` | Best language or `false` | `req.acceptsLanguages(['en', 'hi'])` |
| `req.is(type)` | The matched content type, `false`, or `null` | `req.is('application/json')` → `'application/json'` |
| `req.range(size, options)` | Parsed `Range` header | `req.range(1000)` → `[{ start: 0, end: 99 }]` |

```js
// File: req-methods.js
import express from 'express';

const app = express();
app.use(express.json());

app.post('/inspect', (req, res) => {
  res.json({
    // Headers — always look them up with req.get(); do not index req.headers with mixed case.
    contentType: req.get('content-type'),
    userAgent: req.get('user-agent') ?? null,

    // Content-type detection. Returns null when there is no body, false when it does not match.
    isJson: req.is('application/json'),        // 'application/json' | false | null
    isForm: req.is('urlencoded'),              // false

    // Content negotiation, from the Accept header (see §7).
    bestFormat: req.accepts(['json', 'html']),
    language: req.acceptsLanguages(['en', 'hi', 'de']) ?? 'en',

    // Client context — all of these mean something different behind a proxy (see ch. 20).
    ip: req.ip,
    hostname: req.hostname,
    protocol: req.protocol,
    secure: req.secure,
    method: req.method,
    originalUrl: req.originalUrl,

    // Range requests (used by res.sendFile for partial downloads).
    range: req.range(1024),
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
curl -s -X POST http://localhost:3000/inspect \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/html' \
  -H 'Accept-Language: de-DE,de;q=0.9' \
  -H 'Range: bytes=0-99' \
  -d '{}'
```

```json
{
  "contentType": "application/json",
  "userAgent": "curl/8.7.1",
  "isJson": "application/json",
  "isForm": false,
  "bestFormat": "html",
  "language": "de",
  "ip": "127.0.0.1",
  "hostname": "localhost",
  "protocol": "http",
  "secure": false,
  "method": "POST",
  "originalUrl": "/inspect",
  "range": [{ "start": 0, "end": 99 }]
}
```

### What Express 5 removed from `req`

| Removed | Replace with | Why |
| --- | --- | --- |
| `req.param(name)` | `req.params.name`, or `req.query.name` / `req.body.name` explicitly | The old method guessed which source to use — a security hazard (a query parameter could override a path parameter) |

---

## 3. `res` — the response lifecycle

A response moves through exactly one path:

```text
1. handler runs
2. set status        res.status(201)
3. set headers       res.set('Location', '/notes/1')
4. send the body     res.json({…})   ← headers + body go out here
5. 'finish' event    res.on('finish', …)   ← the response has been flushed
```

| Check | Meaning |
| --- | --- |
| `res.headersSent` | `true` after the headers have been written — you can no longer set them |
| `res.writableEnded` | `true` after `res.end()` — the body is complete |
| `res.finished` | **Deprecated** — use `writableEnded` |

```js
// File: response-events.js
import express from 'express';

const app = express();

app.get('/slow', (req, res) => {
  const startedAt = process.hrtime.bigint();

  // 'finish' fires when the response has been flushed to the socket.
  res.on('finish', () => {
    const ms = Number(process.hrtime.bigint() - startedAt) / 1e6;
    console.log(JSON.stringify({ status: res.statusCode, ms: Number(ms.toFixed(2)), event: 'finish' }));
  });

  // 'close' fires when the connection is gone — including client disconnects
  // (req.destroyed / res.destroyed are true by then). Use it to stop work.
  res.on('close', () => {
    if (!res.writableEnded) {
      console.log(JSON.stringify({ event: 'close', aborted: true, url: req.originalUrl }));
    }
  });

  setTimeout(() => {
    if (res.writableEnded) return;           // the client already disconnected
    res.json({ ok: true });
  }, 300);
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
# Trigger the normal path:
curl -s http://localhost:3000/slow
# {"event":"finish","status":200,"ms":301.55}

# Trigger the aborted path: start it, then cancel with Ctrl+C before 300ms.
# {"event":"close","aborted":true,"url":"/slow"}
```

---

## 4. `res` — the complete reference

| Method | Purpose | Sets |
| --- | --- | --- |
| `res.status(code)` | Set the status (chainable) | Status code |
| `res.sendStatus(code)` | Set the status and send its reason phrase as the body | Status + body |
| `res.send(body)` | Send a string, `Buffer`, object or array | `Content-Type` inferred, `Content-Length`, ETag |
| `res.json(obj)` | `JSON.stringify` + `application/json` | `Content-Type: application/json; charset=utf-8` |
| `res.end([data])` | Finish the response, no helpers | Nothing extra |
| `res.set(field, value)` / `res.header(...)` | Set one or many headers | Headers |
| `res.append(field, value)` | Add a value to an existing header | Header |
| `res.get(field)` | Read a header that *will* be sent | — |
| `res.type(type)` / `res.contentType(type)` | Set `Content-Type` (extension, mime name or full type) | `Content-Type` |
| `res.format(obj)` | Content negotiation | `Content-Type`, `Vary: Accept` |
| `res.location(path)` | Set `Location` without sending | `Location` |
| `res.redirect([status], path)` | Send a redirect (default `302`) | Status, `Location`, body, `Vary: Accept` |
| `res.cookie(name, value, opts)` | Set a cookie | `Set-Cookie` |
| `res.clearCookie(name, opts)` | Expire a cookie | `Set-Cookie` |
| `res.attachment([filename])` | Set `Content-Disposition: attachment` | `Content-Disposition`, `Content-Type` |
| `res.download(path, [name], [cb])` | Send a file as an attachment | `Content-Disposition`, `Content-Type`, `Content-Length` |
| `res.sendFile(path, [opts], [cb])` | Send a file (supports `Range`, `ETag`, `Cache-Control`) | `Content-Type` from the extension |
| `res.vary(field)` | Add to `Vary` | `Vary` |
| `res.links(obj)` | Set `Link` headers | `Link` |
| `res.locals` | Per-response scratch space for templates/middleware | — |
| `res.jsonp(obj)` | JSON with a callback wrapper (off unless enabled) | `Content-Type: text/javascript` |
| `res.render(view, locals)` | Render a template (needs a view engine) | `Content-Type: text/html` |

**Everything except the terminal calls returns `res`**, so calls chain:

```js
// File: chaining.js
import express from 'express';

const app = express();

app.post('/api/v1/notes', (req, res) => {
  const note = { id: '1', title: 'Chained' };

  res
    .status(201)
    .set('Location', `/api/v1/notes/${note.id}`)
    .set({ 'X-Request-Id': 'abc-123', 'Cache-Control': 'no-store' })
    .type('application/json')
    .json({ data: note });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

### `res.send` — content types by value

Express infers `Content-Type` from the argument. Verified behaviour:

| Value | `Content-Type` sent |
| --- | --- |
| `res.send('plain text')` | `text/html; charset=utf-8` ← **surprising** |
| `res.send({ a: 1 })` | `application/json; charset=utf-8` |
| `res.send(Buffer.from('bytes'))` | `application/octet-stream` |
| `res.send('<p>hi</p>')` | `text/html; charset=utf-8` |
| `res.json({ a: 1 })` | `application/json; charset=utf-8` |

> **`res.send('string')` defaults to HTML.** For a JSON API, always use `res.json()`, or set the type
> explicitly (`res.type('text/plain').send('pong')`). Getting this wrong means clients receive HTML
> where they expect JSON.

### `res.sendStatus` — small and precise

```js
// File: send-status.js
import express from 'express';

const app = express();

app.get('/no-content', (req, res) => {
  res.sendStatus(204);        // 204, NO body, no Content-Type (a 204 may not have a body)
});

app.get('/teapot', (req, res) => {
  res.sendStatus(418);        // 418 with the body "I'm a Teapot" and text/plain
});

app.get('/manual-204', (req, res) => {
  res.status(204).end();      // the explicit form — clearer about intent
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
curl -i localhost:3000/no-content | head -4
```

```http
HTTP/1.1 204 No Content
```

```bash
curl -i localhost:3000/teapot | head -4
```

```http
HTTP/1.1 418 I'm a Teapot
Content-Type: text/plain; charset=utf-8

I'm a Teapot
```

### Headers: the safe patterns

```js
// File: res-headers.js
import express from 'express';

const app = express();

app.get('/headers', (req, res) => {
  // 1. Simple set
  res.set('X-Api-Version', 'v1');

  // 2. Multiple at once — no validation of the values, so sanitise anything user-supplied
  res.set({ 'X-Request-Id': 'abc', 'Cache-Control': 'no-store' });

  // 3. Append to a repeatable header
  res.append('Link', '</page/2>; rel="next"');
  res.append('Link', '</page/9>; rel="last"');

  // 4. Read back what will be sent
  const cacheControl = res.get('Cache-Control');

  // 5. Content type by extension, mime name, or full type
  const typ = res.type('json').get('Content-Type');       // 'application/json; charset=utf-8'

  res.json({ cacheControl, typ, links: res.get('Link') });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

> **Never put user input directly into a header value.** Newline characters (`\r\n`) in a header value
> enable *response splitting*, where an attacker injects a whole second response. Node throws on
> invalid header characters — sanitise anyway, and prefer allowlists for anything reflected.

---

## 5. Sending files

```js
// File: res-files.js
import express from 'express';
import path from 'node:path';

const app = express();
const PUBLIC_DIR = path.resolve(import.meta.dirname, 'public');

// Serve a whole directory (see ch. 17 for caching, ranges and security details).
app.use('/static', express.static(PUBLIC_DIR, { maxAge: '1h', index: false }));

app.get('/report.pdf', (req, res, next) => {
  // sendFile requires an ABSOLUTE path (or set the `root` option).
  res.sendFile(path.join(PUBLIC_DIR, 'report.pdf'), { root: PUBLIC_DIR }, (error) => {
    if (!error) return;
    // The response may already be partially sent — delegate to the error handler.
    next(error);
  });
});

app.get('/download', (req, res) => {
  // download() sets Content-Disposition: attachment with a safe filename.
  res.download(path.join(PUBLIC_DIR, 'report.pdf'), 'quarterly-report.pdf');
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
curl -s -I localhost:3000/report.pdf | head -6
curl -s -I localhost:3000/download | grep -i content-disposition
# content-disposition: attachment; filename="quarterly-report.pdf"
```

`res.sendFile` handles `ETag`, `Last-Modified`, `Cache-Control` and `Range` requests for you — which is
why it is preferred over `fs.createReadStream(...).pipe(res)` for static content.
[17 — File Upload](17-file-upload.md) covers uploads; [01-nodejs/09-streams.md](../01-nodejs/09-streams.md)
covers streaming responses when you need custom behaviour.

---

## 6. Cookies

```js
// File: res-cookies.js
import express from 'express';

const app = express();

app.post('/login', (req, res) => {
  res
    .cookie('sid', 'opaque-session-id', {
      httpOnly: true,          // JavaScript cannot read it → mitigates XSS cookie theft
      secure: true,            // HTTPS only (keep false on localhost over http)
      sameSite: 'lax',         // 'strict' | 'lax' | 'none' — CSRF mitigation
      maxAge: 7 * 24 * 60 * 60 * 1000,   // milliseconds → Max-Age + Expires
      path: '/',
      // domain: 'example.com',   // omit to scope the cookie to the exact host
    })
    .json({ data: { loggedIn: true } });
});

app.post('/logout', (req, res) => {
  // Options MUST match those used to set the cookie, or the browser keeps it.
  res.clearCookie('sid', { httpOnly: true, secure: true, sameSite: 'lax', path: '/' });
  res.status(204).end();
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

Actual header produced:

```http
Set-Cookie: sid=opaque-session-id; Max-Age=604800; Path=/; Expires=…; HttpOnly; Secure; SameSite=Lax
```

Reading cookies requires middleware — `req.cookies` is `undefined` without it:

```js
// File: cookies-read.js
import express from 'express';
import cookieParser from 'cookie-parser';
import { env } from './config/env.js';

const app = express();

// Signed cookies: tamper-evident, but NOT encrypted — never put secrets in them.
app.use(cookieParser(env.cookieSecret));

app.get('/session', (req, res) => {
  res.json({
    cookies: req.cookies,               // { sid: 'opaque-session-id' }
    signed: req.signedCookies,          // only cookies signed with the secret
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

Full treatment — sessions, rotation, CSRF, `SameSite` trade-offs — in
[15 — Cookies and Sessions](15-cookies-sessions.md).

---

## 7. Content negotiation

The client says what it can accept in `Accept:`; the server chooses. `res.format` does it for you:

```js
// File: res-format.js
import express from 'express';

const app = express();

app.get('/api/v1/notes/:id', (req, res) => {
  const note = { id: req.params.id, title: 'Learn Node' };

  res.format({
    'application/json': () => res.json({ data: note }),
    'text/html': () => res.send(`<h1>${note.title}</h1>`),
    'text/plain': () => res.type('text/plain').send(`${note.id}: ${note.title}`),

    // Called when nothing matched. If you OMIT default, Express throws a 406 error.
    default: () => res.status(406).json({ error: { code: 'NOT_ACCEPTABLE' } }),
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

```bash
curl -s -i localhost:3000/api/v1/notes/42 -H 'Accept: text/html' | head -4
```

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Vary: Accept
```

```bash
curl -s localhost:3000/api/v1/notes/42 -H 'Accept: application/json'
# {"data":{"id":"42","title":"Learn Node"}}

curl -s localhost:3000/api/v1/notes/42 -H 'Accept: image/png'
# {"error":{"code":"NOT_ACCEPTABLE"}}   ← the `default` branch (a 406)
```

`req.accepts` gives you the same information for manual decisions:

| Request header | `req.accepts(['json', 'html'])` | `req.accepts('text/html')` |
| --- | --- | --- |
| `Accept: text/html` | `'html'` | `'text/html'` |
| `Accept: application/json` | `'json'` | `false` |
| *(absent)* | `'json'` (first listed wins, because `*/*` matches everything) | `'text/html'` |
| `Accept: image/png` | `false` | `false` |

---

## 8. Conditional requests and automatic `304`

Express computes an `ETag` for every response it sends with `res.send`/`res.json`, and it checks
`If-None-Match` for you. If the client's tag matches, **Express replaces your response with `304 Not
Modified` and sends no body** — the handler still runs, but the body is discarded.

```js
// File: caching.js
import express from 'express';
import { createHash } from 'node:crypto';

const app = express();
app.set('etag', 'strong');     // 'weak' (default) | 'strong' | false

const note = { id: '42', title: 'Learn Node', updatedAt: '2026-09-18T10:00:00.000Z' };

app.get('/auto', (req, res) => {
  res.json({ data: note });     // Express adds an ETag and handles If-None-Match
});

app.get('/custom-etag', (req, res) => {
  const body = JSON.stringify({ data: note });
  const etag = `"${createHash('sha256').update(body).digest('base64url').slice(0, 27)}"`;

  res.set({
    ETag: etag,
    'Cache-Control': 'private, max-age=0, must-revalidate',
    Vary: 'Authorization, Accept-Encoding',
  });

  // req.fresh compares the request's validators with the response's headers.
  if (req.fresh) {
    return res.status(304).end();     // same content: tell the client to reuse its copy
  }

  return res.type('application/json').send(body);
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

Verified with `curl`:

```bash
# 1. First request — learn the tag.
curl -s -i localhost:3000/auto | head -5
```

```http
HTTP/1.1 200 OK
ETag: W/"3c-Kq0Tt7HqQ0lP2yqWzM4aA0PdxYw"
Content-Type: application/json; charset=utf-8

{"data":{"id":"42","title":"Learn Node"}}
```

```bash
# 2. Conditional request with that tag → 304, no body, no Content-Type.
curl -s -i localhost:3000/auto -H 'If-None-Match: W/"3c-Kq0Tt7HqQ0lP2yqWzM4aA0PdxYw"' | head -5
```

```http
HTTP/1.1 304 Not Modified
ETag: W/"3c-Kq0Tt7HqQ0lP2yqWzM4aA0PdxYw"
```

| Behaviour | Value |
| --- | --- |
| `app.set('etag', …)` | `'weak'` (default), `'strong'`, or `false` to disable |
| Automatic ETag applies to | `res.send`, `res.json`, `res.sendFile`, and other body-sending helpers |
| `304` body | Always empty — clients must reuse their cached copy |
| `req.fresh` requires | A `GET`/`HEAD` request **and** a 2xx/304 status **and** a matching `ETag` or `Last-Modified` |
| `If-None-Match: *` | Matches if the resource exists at all |
| `Cache-Control` | The ETag decides *whether the content changed*; `Cache-Control` decides *whether to ask at all* |

> **`Vary` matters as much as `ETag`.** A per-user response without `Vary: Authorization` can be served
> to a different user by a shared cache. When in doubt, `Cache-Control: private` plus an explicit
> `Vary` list is the safe default for an authenticated API.

---

## 9. `res.locals` — per-response storage

```js
// File: res-locals.js
import express from 'express';

const app = express();

/** Middleware can attach data that later handlers (or templates) read. */
app.use((req, res, next) => {
  res.locals.requestId = crypto.randomUUID();
  res.locals.startedAt = Date.now();
  res.locals.user = null;                    // filled in by the auth middleware below
  next();
});

app.get('/me', (req, res) => {
  res.locals.user = { id: 'u1', name: 'Ankit' };     // not how you would do auth — see ch. 13
  res.json({
    requestId: res.locals.requestId,
    elapsedMs: Date.now() - res.locals.startedAt,
    user: res.locals.user,
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

| Property storage | Scope | Use for |
| --- | --- | --- |
| `req.foo = …` | This request | Data the chain passes forward (parsed input, authenticated user, request id) |
| `res.locals.foo = …` | This response | Data for templates and response-building only; conventionally UI/render data |
| `app.locals.foo = …` | The whole process | Settings shared by every request (app name, version) |

Both `req` and `res.locals` are **plain objects created per request**, so they are safe places to store
request-scoped data — and unsafe places to store anything expensive, because they are garbage-collected
when the request ends.

---

## 10. `next` — the rules, in one place

```js
// File: next-rules.js
import express from 'express';

const app = express();

// Rule 1: exactly one of "respond" or "call next()" on every code path.
app.get(
  '/a',
  (req, res, next) => {
    if (!req.get('authorization')) {
      return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });   // responded → no next()
    }
    req.user = { id: 'u1' };
    return next();                                                          // continue
  },
  (req, res) => res.json({ data: req.user }),
);

// Rule 2: next(error) jumps straight to the error handler.
app.get('/b', (req, res, next) => {
  next(new Error('something failed'));
});

// Rule 3: next('route') abandons the remaining handlers of THIS route (chapter 03).
app.get(
  '/c',
  (req, res, next) => {
    if (req.query.legacy) return next('route');
    return res.json({ mode: 'new' });
  },
  (req, res) => res.json({ mode: 'skipped-when-legacy' }),
);
app.get('/c', (req, res) => res.json({ mode: 'legacy' }));

// Rule 4: never pass a truthy non-Error to next() — Error objects carry stacks.
app.get('/d', (req, res, next) => {
  next(Object.assign(new Error('Not allowed'), { statusCode: 403, code: 'FORBIDDEN' }));
});

app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

app.use((error, req, res, next) => {
  const statusCode = error.statusCode ?? 500;
  if (res.headersSent) return next(error);            // the response already started — let Express finish
  return res.status(statusCode).json({
    error: { code: error.code ?? 'INTERNAL_ERROR', message: error.message },
  });
});

app.listen(0, '127.0.0.1', () => console.log('ready'));
```

| Call | Continues to |
| --- | --- |
| `next()` | The next handler in this route, then the next matching route |
| `next('route')` | The next matching **route definition** (skips the rest of this route's handlers) |
| `next('router')` | The parent router, leaving this router entirely |
| `next(error)` | The nearest error middleware (4 arguments) |
| *(nothing)* | Nowhere — the request hangs until it times out |

---

## 11. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| `res.send('text')` for a JSON API | Client gets `Content-Type: text/html` and tries to parse HTML | `res.json(...)` or `res.type('text/plain')` |
| Responding twice | `ERR_HTTP_HEADERS_SENT: Cannot set headers after they are sent to the client` | `return res.json(...)` everywhere; check `res.headersSent` in error middleware |
| `res.set()` after `res.send()` | Same error, thrown from inside your own handler | Set headers before the terminal call |
| Missing `return` before `res.json()` | Execution continues, then the second send throws | `return res.status(...).json(...)` |
| `res.status(204).json({…})` | The body is silently dropped (204 cannot have one) — confusing logs | `res.status(204).end()` |
| `res.status(200).json(null)` disguising a failure | Clients cannot tell "empty" from "missing" | `404` for missing, `200` with `[]` for empty lists |
| `res.sendFile('relative/path')` | `TypeError: path must be absolute` | `path.resolve(...)` or pass `{ root }` |
| Trusting `req.ip`/`req.protocol` behind a proxy | Always `127.0.0.1`/`http` — rate limiting and secure cookies break | `app.set('trust proxy', …)` (ch. 20) |
| `req.cookies` assumed to exist | `Cannot read properties of undefined` | Register `cookie-parser` (or handle `undefined`) |
| Reading `req.body` without a parser | `undefined` | `app.use(express.json())` before the routes |
| Changing `req.url`/`req.path` by hand | Breaks routing and logging | Use `req.originalUrl` for logs; never mutate these |
| `res.locals` used for secrets | Locals are exposed to templates | Keep secrets on `req` only, and never render them |
| Blocking work inside a handler | Every other request waits (ch. 14 of the Node section) | Move CPU work to a worker, or use async I/O |
| Forgetting `content-type` on a `POST` from curl | `req.body` is `undefined` and `express.json()` skips it | Always send `-H 'Content-Type: application/json'` |
| `res.format` without `default` | A `406 Not Acceptable` error surfaces as a 500 if the error handler ignores `error.status` | Provide `default`, and map `error.status` in the error handler |

---

## Exercise 5.1 — Build an inspection endpoint

Create `GET /api/v1/whoami` that returns:

```json
{
  "data": {
    "ip": "127.0.0.1",
    "protocol": "http",
    "secure": false,
    "method": "GET",
    "path": "/api/v1/whoami",
    "originalUrl": "/api/v1/whoami?verbose=1",
    "hostname": "localhost",
    "userAgent": "curl/8.7.1",
    "acceptsJson": true,
    "requestId": "…"
  },
  "meta": { "generatedAt": "2026-09-18T10:15:30.001Z", "durationMs": 0.08 }
}
```

Requirements:

1. `requestId` and a start timestamp are attached by middleware.
2. The response is only `application/json`; a client that sends `Accept: text/html` gets `406`.
3. The response is cacheable per client but must not be stored by shared caches, and it must declare
   that it varies by `Authorization`.
4. The response carries an `ETag`; a repeat request with `If-None-Match` must return `304` **without
   your handler doing anything.**

<details>
<summary>Solution</summary>

```js
// File: src/middleware/requestContext.js
import { randomUUID } from 'node:crypto';

/** Attach a request id and a start time to the request (chapters 05 and 20). */
export function requestContext(req, res, next) {
  req.id = req.get('x-request-id') ?? randomUUID();
  req.startedAt = process.hrtime.bigint();

  res.set('X-Request-Id', req.id);

  // A per-request helper so handlers never compute durations by hand.
  req.elapsedMs = () => Number(process.hrtime.bigint() - req.startedAt) / 1e6;

  next();
}
```

```js
// File: src/routes/whoamiRoutes.js
import { Router } from 'express';

export function createWhoamiRouter() {
  const router = Router();

  router.get('/whoami', (req, res) => {
    // 2. Content negotiation: reject anything that is not JSON.
    if (!req.accepts('application/json')) {
      return res.status(406).json({
        error: { code: 'NOT_ACCEPTABLE', message: 'This endpoint only produces application/json' },
      });
    }

    // 3. Cache directives: private (per client) + vary on Authorization.
    res.set({
      'Cache-Control': 'private, max-age=0, must-revalidate',
      Vary: 'Authorization, Accept-Encoding',
    });

    // 4. Express adds an ETag for res.json and answers If-None-Match itself.
    return res.json({
      data: {
        ip: req.ip,
        protocol: req.protocol,
        secure: req.secure,
        method: req.method,
        path: req.path,
        originalUrl: req.originalUrl,
        hostname: req.hostname,
        userAgent: req.get('user-agent') ?? null,
        acceptsJson: true,
        requestId: req.id,
      },
      meta: {
        generatedAt: new Date().toISOString(),
        durationMs: Number(req.elapsedMs().toFixed(2)),
      },
    });
  });

  return router;
}
```

```js
// File: src/app.js
import express from 'express';
import { requestContext } from './middleware/requestContext.js';
import { createWhoamiRouter } from './routes/whoamiRoutes.js';

export function createApp({ config = {} } = {}) {
  const app = express();
  app.disable('x-powered-by');

  // `trust proxy` must be configured before req.ip/protocol mean anything (ch. 20).
  app.set('trust proxy', config.trustProxy ?? false);
  app.set('etag', 'strong');

  app.use(requestContext);
  app.use('/api/v1', createWhoamiRouter());

  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    const statusCode = error.statusCode ?? error.status ?? 500;
    return res.status(statusCode).json({
      error: { code: error.code ?? 'INTERNAL_ERROR', message: error.message },
    });
  });

  return app;
}
```

```bash
# 1. Basic call
curl -s -i 'localhost:3000/api/v1/whoami?verbose=1' | head -8
```

```http
HTTP/1.1 200 OK
X-Request-Id: 6a1f3e2b-8f4a-4b1e-9a3d-5b2c9e0f1a77
ETag: "8f-3Qp0d1kLxY2vQd0Kd1lKm0aQd1x"
Vary: Authorization, Accept-Encoding
Cache-Control: private, max-age=0, must-revalidate
Content-Type: application/json; charset=utf-8
```

```bash
# 2. Negotiation
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' localhost:3000/api/v1/whoami -H 'Accept: text/html'
# 406 application/json; charset=utf-8

# 3. Conditional request — the handler runs but Express sends 304 and no body
ETAG=$(curl -s -D - -o /dev/null localhost:3000/api/v1/whoami | awk '/^ETag:/ {print $2}' | tr -d '\r')
curl -s -i localhost:3000/api/v1/whoami -H "If-None-Match: $ETAG" | head -4
```

```http
HTTP/1.1 304 Not Modified
ETag: "8f-3Qp0d1kLxY2vQd0Kd1lKm0aQd1x"
```

```bash
# 4. Request id propagates from the client when supplied
curl -s -D - -o /dev/null localhost:3000/api/v1/whoami -H 'X-Request-Id: my-trace-1' | grep -i x-request-id
# X-Request-Id: my-trace-1
```

**Why this is the right implementation**

| Requirement | How it is met | Why not the alternative |
| --- | --- | --- |
| Request id | Middleware sets `req.id`, and reuses an inbound `X-Request-Id` | Generating a new one blindly breaks distributed traces |
| JSON only | `req.accepts('application/json')` guard | Trusting the client to ask nicely produces HTML errors |
| Private caching | `Cache-Control: private` + `Vary: Authorization` | Without `Vary`, a shared cache can serve one user's response to another |
| `304` for free | `res.json` on a `GET` with `If-None-Match` | Hand-rolling `if (etag === …)` duplicates what Express already does correctly |

</details>

---

## Exercise 5.2 — Fix the broken handler

```js
// File: broken-handler.js
import express from 'express';
const app = express();

app.get('/api/v1/notes/:id', async (req, res) => {
  const note = await noteRepository.findById(req.params.id);

  res.status(200);
  res.set('X-Note-Source', 'cache');
  res.json({ data: note });
  res.set('X-Note-Found', note ? 'yes' : 'no');

  if (!note) {
    res.status(404).json({ error: { code: 'NOT_FOUND' } });
  }
});

app.listen(3000);
```

Identify every bug and write the corrected handler.

<details>
<summary>Solution</summary>

| # | Bug | What happens |
| --- | --- | --- |
| 1 | `res.set('X-Note-Found', …)` **after** `res.json()` | `ERR_HTTP_HEADERS_SENT` — the headers are already on the wire |
| 2 | `res.status(404).json(...)` after a `200` response | Second send → another `ERR_HTTP_HEADERS_SENT`; the client already got `200` |
| 3 | A missing note returns `200` first and `404` second | The client sees `200` with `{"data":null}` — a silent failure |
| 4 | Async handler with no `try/catch` | **In Express 5** a rejection is forwarded automatically (good), but the code still assumes no failure; add the guard anyway for clarity and log context |
| 5 | `res.status(200);` as a separate statement | Legal, but pointless and easy to misread as terminal — chaining is clearer |
| 6 | No validation of `:id` | Any string reaches the repository; a Mongo `ObjectId` cast throws a 500 instead of a 422 |
| 7 | No `Content-Type` reasoning | Fine here (`res.json` sets it) — noted because `res.send` would not |
| 8 | `app.listen(3000)` | Port and host are not configurable |

```js
// File: fixed-handler.js
import express from 'express';
import { z } from 'zod';

const app = express();
const IdSchema = z.string().regex(/^[0-9a-f]{24}$/i, 'must be a 24-character hex id');

app.get('/api/v1/notes/:id', async (req, res, next) => {
  try {
    // 1. Validate before touching the data layer.
    const parsed = IdSchema.safeParse(req.params.id);
    if (!parsed.success) {
      return res.status(422).json({
        error: {
          code: 'VALIDATION_ERROR',
          details: [{ field: 'id', message: parsed.error.issues[0].message }],
        },
      });
    }

    const note = await noteRepository.findById(parsed.data);

    // 2. Decide the outcome BEFORE sending anything.
    if (!note) {
      return res.status(404).json({
        error: { code: 'NOT_FOUND', message: `Note ${parsed.data} not found`, requestId: req.id },
      });
    }

    // 3. Set every header first, then send exactly once.
    res.set({ 'X-Note-Source': 'database', 'X-Note-Found': 'yes' });
    return res.status(200).json({ data: note });
  } catch (error) {
    // 4. Forward to the error middleware instead of crafting a response here.
    return next(error);
  }
});

const port = Number(process.env.PORT ?? 3000);
app.listen(port, '0.0.0.0', () => console.log(`listening on http://localhost:${port}`));
```

**The general rule this exercise teaches:** compute the *entire* decision (status + headers + body)
before the first byte leaves. A response is a single event, not a sequence of edits — once headers are
sent, every subsequent modification throws.

</details>

---

## What's next

You now know how to read the request and shape the response. Next: the three sources of user input —
path parameters, query strings and request bodies — with their types, traps and security rules.

→ [06 — Params, Query and Body](06-params-query-body.md)
