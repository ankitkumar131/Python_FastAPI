# 16 — Middleware and Cross-Origin Resource Sharing

[Previous](15-tokens-and-authorization.md) · [Course map](00-course-guide.md) · [Next](17-files-jobs-websockets.md)

## What is middleware, and why does it exist?

**Middleware** wraps application request/response processing. It can inspect or alter a request before routing and inspect or alter the response afterwards. Think of an entrance/exit desk checking every package, regardless of which department processes it. Timing, request IDs and compression are cross-cutting concerns: repeating them in every route is error-prone.

The simple HTTP middleware form is `@app.middleware("http")` above an async function receiving `request` and `call_next`. `await call_next(request)` invokes the next layer and returns a response. Code before it runs on entry; code afterwards runs on return. Middleware is not the right place for product-specific stock rules or resource ownership checks needing route context; dependencies/services make those rules more explicit.

**Middleware order** resembles nested boxes. Later-added middleware generally wraps earlier layers, so request order and response order reverse. Exception layers complicate what a custom middleware sees: not every unhandled error necessarily passes through the same response modifications. For critical cross-cutting behaviour, understand the ASGI stack and test failures too. Pure ASGI middleware offers lower-level control and avoids some BaseHTTPMiddleware/context-variable limitations; begin with the simple HTTP form for a small timing lesson.

## CORS: a browser rule, not a security gate for all clients

An **origin** is scheme + host + port. `http://localhost:3000` and `http://localhost:8000` are different origins. Browsers enforce a **same-origin policy** restricting scripts reading responses from other origins. **CORS (Cross-Origin Resource Sharing)** is the server's way of allowing selected cross-origin browser interactions.

A request can reach your server even if the browser prevents JavaScript from reading the reply. Curl, backend clients and attackers are not constrained by browser CORS. CORS does not replace authentication, authorization or CSRF protection.

For certain methods/headers, a browser sends a **preflight** OPTIONS request asking whether the proposed operation is allowed. `CORSMiddleware` answers with the relevant Access-Control headers. “Simple” requests may not preflight but still have browser read restrictions. `allow_origins` names approved origins; `allow_methods` names verbs; `allow_headers` allows client-sent headers; `expose_headers` makes selected response headers readable to JavaScript.

**Credentials** include browser-managed cookies and HTTP authentication state. If using credentialed browser requests, enumerate trusted origins and other allowed values explicitly rather than mixing wildcard configuration with credentials. An explicit Authorization header usually triggers preflight permission for that header; cookies additionally require appropriate client credentials mode, flags and CSRF strategy.

Run `python -m uvicorn examples.middleware:app --reload`. The example permits only the intentional local frontend origin below. In a preview deployment use the actual approved frontend HTTPS origin, or serve frontend/API through the same origin using relative URLs.

## Example

### File: `examples/middleware.py`

```python
from time import perf_counter
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

@app.middleware("http")
async def trace_request(request: Request, call_next):
    started = perf_counter()
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Process-Time"] = f"{perf_counter() - started:.6f}"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

@app.get("/products")
def products():
    return [{"id": 1, "name": "Pen"}]
```

## Code Explanation

### Line 1

A monotonic high-resolution timer measures elapsed durations without wall-clock adjustments.

### Line 2

Generate server-controlled request identifiers for correlation.

### Line 3

Import the app and request metadata type.

### Line 4

Use tested browser-origin handling instead of manually implementing preflight rules.

### Line 5

This blank line separates logical parts; Python does not execute it.

### Line 6

Create the lesson app.

### Line 7

This blank line separates logical parts; Python does not execute it.

### Line 8

Register logic wrapping ordinary HTTP requests/responses.

### Line 9

Receive the request and the next layer's callable.

### Line 10

Record entry time before handler processing.

### Line 11

Store an ID on this request, not on shared app state.

### Line 12

Continue through routing, validation and the endpoint, yielding while it runs.

### Line 13

Return a correlation ID without trusting arbitrary unbounded client input.

### Line 14

Report measured elapsed seconds with six decimal places.

### Line 15

Preserve the downstream response/status/body rather than replacing it.

### Line 16

This blank line separates logical parts; Python does not execute it.

### Line 17

Add CORS outside the earlier registered HTTP timing middleware within the app's middleware stack.

### Line 18

Select the supplied CORS implementation.

### Line 19

Permit exactly this local frontend origin; no trailing slash belongs in an origin.

### Line 20

Allow credentialed requests from that trusted origin; still require CSRF controls if using cookies.

### Line 21

Limit browser-approved operations to those intentionally supported here.

### Line 22

Permit these client request headers during preflight.

### Line 23

Let frontend JavaScript read the custom response headers.

### Line 24

Finish middleware configuration.

### Line 25

This blank line separates logical parts; Python does not execute it.

### Line 26

Register a normal route with no duplicated timing/CORS logic.

### Line 27

This handler remains concerned only with product output.

### Line 28

Middleware decorates this response on its way out.

## Test it / internal flow

```bash
curl -i http://127.0.0.1:8000/products -H 'Origin: http://localhost:3000'
curl -i -X OPTIONS http://127.0.0.1:8000/products -H 'Origin: http://localhost:3000' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: authorization,content-type'
```

The first sends an Origin header and receives the product list, a matching allowed-origin header and request timing headers. The second simulates preflight and should be allowed. Change the origin to `https://untrusted.example`; its preflight is rejected and an ordinary response lacks permission for that origin. Curl can still read an ordinary HTTP response because it is not a browser.

The timing ends when `call_next` returns a response object, not necessarily after every streamed byte or background task. Do not label it end-to-end client latency. For CORS headers even on outer unhandled error responses, wrap the entire ASGI app with CORSMiddleware as Starlette documents rather than assuming inner middleware modifies every 500.

## When to use / not use; common mistakes

Use middleware for general request policy/telemetry, dependencies for route-aware prerequisites and services for business rules. Do not parse and log every body in middleware: bodies may contain passwords, huge uploads or streams, and consuming them incorrectly can disrupt downstream processing. Do not allow every origin with credentials to “fix” a development error. `localhost` and `127.0.0.1` are distinct hosts/origins. CORS allow_methods does not implement a missing POST route; an allowed preflight can still be followed by an actual 405.

Best practices: same-origin deployments when practical, exact environment-specific origin lists, explicit exposed headers, bounded request IDs, tested error paths and secret redaction. Do not reflect arbitrary Origin values with credentials.

## Practice / Expected Result / Solution

Permit a second trusted frontend at `https://shop.example.com` without opening all origins. Replace the origin line in the complete file with:

```python
    allow_origins=["http://localhost:3000", "https://shop.example.com"],
```

This single line adds one exact origin. Restart/reload, send each as Origin and expect the corresponding allow-origin response; `https://evil.example` still lacks permission. No database/authentication rules change because CORS is only browser-origin policy.

## Summary

Middleware wraps many operations consistently. CORS negotiates browser access to cross-origin responses; it is not a replacement for server-side access control.
