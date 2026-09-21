# 09 — Synchronous work, async/await, and application lifespan

[Previous](08-dependencies.md) · [Course map](./) · [Next](10-database-foundations.md)

## What problem does async solve?

An API often waits: a database is searching, a remote service is replying, a socket is receiving data. **I/O (Input/Output)** means exchanging data with files, networks or devices. **I/O-bound** work spends much of its time waiting for those operations. **CPU-bound** work spends time computing, such as encoding video or processing a large image.

Synchronous code performs a call and does not continue until that call returns. Asynchronous code can suspend at an awaitable operation, allowing other tasks to progress while it waits. Imagine one waiter taking another table's order while the kitchen cooks. The waiter is not cooking every meal faster; waiting periods overlap.

**Concurrency** means several activities make progress during overlapping time periods. **Parallelism** means activities actually execute at the same instant on different execution resources. Async provides concurrency, not automatic CPU parallelism.

## `async`, `await`, coroutines and the event loop

`async def` declares a **coroutine function**. Calling it produces a coroutine object rather than running the complete result immediately. `await` cooperatively waits for an awaitable and resumes when it completes. It is legal inside asynchronous code. You cannot `await` an ordinary integer or synchronous database result.

The **event loop** coordinates runnable tasks and I/O readiness. While one task awaits supported I/O, the loop can run another. A long blocking call inside an async handler prevents that thread's event loop from serving its other tasks. Merely adding `async` does not transform synchronous libraries.

A **thread pool** is a limited group of worker threads used to run synchronous work without occupying the event-loop thread. FastAPI runs normal `def` endpoints and normal dependency providers through this machinery. An ordinary helper you call yourself is not automatically moved: calling `blocking_helper()` inside `async def` still blocks unless you explicitly offload it.

## Which function type should I choose?

| Work                                                    | Good starting choice           | Why                                                    |
| ------------------------------------------------------- | ------------------------------ | ------------------------------------------------------ |
| Synchronous SQLAlchemy session, synchronous HTTP client | Normal `def` route/provider    | Framework offloads the handler's blocking work         |
| Async HTTPX or async database driver                    | `async def` and `await`        | Allows waiting without holding the event loop          |
| Short in-memory computation                             | Either, kept short             | Async is not required for arithmetic                   |
| Heavy CPU work                                          | Separate process/worker system | Threads/async do not automatically provide CPU scaling |

For conventional CPython builds, the **GIL (Global Interpreter Lock)** limits simultaneous Python bytecode execution in threads. Native libraries can release it; optional free-threaded builds have different trade-offs. Regardless of build, long CPU work inside an event loop harms responsiveness. Measure your workload rather than quoting universal async speedups.

## Lifespan: once per worker, not once per request

An HTTP client maintains a **connection pool**, reusable connections avoiding repeated network setup. Creating a client per request throws that benefit away. Keeping it global at import time can create cleanup and test problems. **Lifespan** provides startup before requests and cleanup during shutdown.

`asynccontextmanager` turns an async single-yield generator into an async context manager: code before yield acquires resources; code after yield releases them. `async with` enters and leaves a resource supporting asynchronous setup/cleanup. Application lifespan runs once per app process/worker, not once across all machines.

**HTTPX** is an HTTP client library, not the server. `AsyncClient` supports awaitable outbound requests. An upstream service is another service this API calls. We use a fixed URL rather than a caller-supplied arbitrary destination, avoiding the beginning of a server-side request forgery vulnerability.

Install, if needed: `python -m pip install httpx`. Run `python -m uvicorn examples.async_lifespan:app --reload`.

## Example

### File: `examples/async_lifespan.py`

```python
import asyncio
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, Request

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
        app.state.http = client
        yield

app = FastAPI(lifespan=lifespan)

@app.get("/wait")
async def wait():
    await asyncio.sleep(0.01)
    return {"ready": True}

@app.get("/upstream")
async def upstream(request: Request):
    try:
        response = await request.app.state.http.get("https://example.com")
        response.raise_for_status()
    except httpx.TimeoutException as error:
        raise HTTPException(504, "Upstream timed out") from error
    except httpx.HTTPError as error:
        raise HTTPException(502, "Upstream unavailable") from error
    return {"upstream_status": response.status_code}
```

## Code Explanation

### Line 1

Import Python's standard asynchronous coordination tools.

### Line 2

Import a decorator that converts an async yield function into a managed lifecycle.

### Line 3

Import the outbound HTTP client library.

### Line 4

Import the app, controlled HTTP errors and request context.

### Line 5

This blank line separates logical parts; Python does not execute it.

### Line 6

Make the next function suitable for FastAPI's lifespan parameter.

### Line 7

Define asynchronous application startup and shutdown for this worker.

### Line 8

Create a reusable client with finite timeouts; the context closes it on exit.

### Line 9

Store the shared client on application state rather than borrowing a request-specific resource.

### Line 10

Signal startup completion; requests run while this context remains open.

### Line 11

This blank line separates logical parts; Python does not execute it.

### Line 12

Attach the lifecycle before the server starts handling requests.

### Line 13

This blank line separates logical parts; Python does not execute it.

### Line 14

A deterministic demonstration requiring no external network.

### Line 15

This handler may suspend cooperatively.

### Line 16

Simulate waiting without blocking the event loop; do not replace this with time.sleep in async code.

### Line 17

Resume and return once the timer completes.

### Line 18

This blank line separates logical parts; Python does not execute it.

### Line 19

Define a gateway-style endpoint calling another service.

### Line 20

Request gives access to this running application's shared state.

### Line 21

Anticipate network and upstream HTTP failures explicitly.

### Line 22

Reuse the client and yield to the loop during network waiting.

### Line 23

Treat unsuccessful upstream HTTP statuses as exceptions instead of silently reporting success.

### Line 24

Handle finite network timeouts separately.

### Line 25

Tell callers a gateway timeout occurred without exposing internal network details.

### Line 26

Handle other expected HTTP client failures.

### Line 27

Translate an upstream failure into a stable public error.

### Line 28

Return a small controlled result rather than blindly forwarding arbitrary upstream content.

## Test it / what happens internally

GET `/wait` returns `{"ready":true}`. GET `/upstream` returns an upstream status when outbound HTTPS is available; a restricted/offline environment can correctly yield 502 or 504. This is not a guaranteed network integration test.

Startup enters the client context and pauses at yield. Incoming async handlers run on the event loop. On `await`, a task can suspend while other tasks run. On shutdown the lifespan resumes and exits the async client context, closing pooled connections. Abrupt process termination may prevent graceful cleanup; durable correctness cannot depend solely on shutdown hooks.

FastAPI recommends lifespan instead of older `@app.on_event("startup")` / `shutdown` handlers. Do not configure both expecting both systems to run. Request-level dependencies and app lifespan solve different ownership problems: an engine/client may live for the application, but a database session belongs to a unit of work.

## Advanced concurrency without accidental overload

Independent awaitable operations can be scheduled together using `asyncio.TaskGroup`, a structured context that waits for child tasks and cancels siblings on failure. This is not always desirable: creating 50,000 tasks can exhaust connections and memory. A **semaphore** limits concurrent access to a resource. Use bounded concurrency and finite per-operation deadlines.

Cancellation is how a task is asked to stop, for example during shutdown. Use `finally` or context managers for cleanup and do not broadly suppress cancellation. A client disconnect does not automatically guarantee that every kind of handler or external operation has stopped; explicitly design cancellation-sensitive streaming or long-running workflows.

## When not to use async / common mistakes

* `async def` containing `requests.get`, synchronous database queries or `time.sleep` blocks the loop.
* `await sync_function()` does the blocking call first, then attempts to await its result. It is not offloading.
* Forgetting `await` can return a coroutine object, causing serialization errors or “coroutine was never awaited” warnings.
* Unlimited concurrency is not unlimited capacity: databases, threads and network sockets are finite.
* Async does not make a single SQL query execute faster or guarantee ordering between independent tasks.

Use normal `def` for synchronous integrations. When a small blocking helper must be called from async code, an explicit thread offload such as `await asyncio.to_thread(helper, argument)` may be appropriate. Do not pass a shared unsafe database session into unrelated threads/tasks. For heavy durable jobs use a worker architecture (chapter 17).

## Practice

**Beginner:** Add `/delay` that asynchronously waits 0.02 seconds.

**Intermediate:** Explain why `time.sleep(2)` in an async handler is harmful.

**Challenge:** Design a two-service dashboard without allowing either service to wait forever.

## Expected Result / Solution

Append to `examples/async_lifespan.py`:

```python
@app.get("/delay")
async def delay():
    await asyncio.sleep(0.02)
    return {"done": True}
```

Line 1 registers the operation. Line 2 makes it a coroutine function. Line 3 yields during a timer. Line 4 returns a JSON-compatible dictionary. `/delay` returns `{"done":true}` using the same server command.

Intermediate: `time.sleep` occupies the event-loop thread; other tasks in that loop cannot advance during it. Use `asyncio.sleep` only for actual asynchronous timing, not as a substitute for performing needed I/O.

Challenge solution: reuse one lifespan-managed AsyncClient with finite timeouts; schedule the two independent calls in a TaskGroup, handle their documented errors, cap concurrency to protect upstream capacity, and decide whether partial data or a 502/504 is the product contract. Do not retry non-idempotent operations blindly. The existing `/upstream` handler provides the complete single-call error-handling pattern to reuse.

## Summary

Async lets waiting overlap, lifespan gives shared resources a clear owner, and dependencies lend request resources. With these distinctions we can safely approach databases.
