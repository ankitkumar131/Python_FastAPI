# 24 — Advanced pattern labs: async SQL, scoped access and conditional responses

[Course map](00-course-guide.md) · [Reference](23-reference-and-troubleshooting.md)

These optional, complete labs deepen concepts already introduced. Finish the main sequence first. Each remains a separately runnable application with an explicit lifetime and contract.

## Lab A — Async SQLAlchemy: make the whole I/O path consistent

### What, why and how?

An AsyncSession exposes awaitable database operations so a handler can suspend during database I/O rather than occupying the event-loop thread. This requires an async engine **and** an async-capable driver, not just `async def`. Think of a restaurant where both the waiter and the kitchen's notification system cooperate; changing only the waiter's job title does not create notifications.

`create_async_engine` selects the async engine path. `async_sessionmaker` is a configurable factory for new sessions. `async with` closes each session on exit. `await session.execute/scalars/commit/refresh` performs I/O cooperatively. `session.add` only changes local tracked state, so it is not awaited.

The lab uses **aiosqlite**, an async adapter for SQLite. It uses worker-thread coordination around SQLite operations; it does not turn SQLite into a high-throughput multi-writer server. For PostgreSQL, an async engine with the appropriate Psycopg configuration or asyncpg driver is another choice. Benchmark before switching an already-correct synchronous application.

A single AsyncSession must not be shared among concurrently executing tasks. One request creating independent concurrent database work needs deliberate separate units of work. Operations requiring one transaction are often better performed sequentially inside that one session.

### Installation / commands

```bash
python -m pip install 'aiosqlite>=0.21,<1'
python -m uvicorn examples.async_sql:app --reload
```

Line 1 installs the SQLite async adapter (also in the full course requirements). Line 2 starts this isolated app. It writes async-products.db; production still needs migrations and access control.

## Example

### File: `examples/async_sql.py`

```python
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from examples.sqlalchemy_app import Base, Product, ProductCreate, ProductPublic

@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine("sqlite+aiosqlite:///./async-products.db")
    app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield
    finally:
        await engine.dispose()

app = FastAPI(lifespan=lifespan)

async def get_session(request: Request):
    async with request.app.state.sessions() as session:
        yield session

Db = Annotated[AsyncSession, Depends(get_session)]

@app.post("/products", response_model=ProductPublic, status_code=201)
async def create(data: ProductCreate, db: Db):
    product = Product(**data.model_dump())
    db.add(product)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(409, "Product conflicts with stored data") from error
    await db.refresh(product)
    return product

@app.get("/products/{product_id}", response_model=ProductPublic)
async def retrieve(product_id: int, db: Db):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product
```

## Code Explanation

### Line 1

Manage engine startup and disposal.

### Line 2

Combine session types with dependency declarations.

### Line 3

Import routing, injection, controlled errors and app-state access.

### Line 4

Catch expected storage constraint failures.

### Line 5

Use the async engine/session API consistently.

### Line 6

Reuse the already explained table and schemas; importing does not run the earlier app's lifespan.

### Line 7

This blank line separates logical parts; Python does not execute it.

### Line 8

Define startup/shutdown for this independent app.

### Line 9

Create resources on the running app's loop.

### Line 10

Select an explicitly async-capable SQLite driver URL.

### Line 11

Build a session factory; keep loaded fields readable after commit rather than implicitly expiring them.

### Line 12

Arrange engine cleanup even after setup or runtime failure.

### Line 13

Borrow an async connection in a transaction context for disposable schema setup.

### Line 14

Bridge SQLAlchemy's synchronous metadata operation through its async connection API; this is not arbitrary blocking-code offload.

### Line 15

Serve requests after demo tables exist.

### Line 16

Finish the app lifecycle.

### Line 17

Dispose async pool resources through their awaitable API.

### Line 18

This blank line separates logical parts; Python does not execute it.

### Line 19

Attach resource ownership to this app.

### Line 20

This blank line separates logical parts; Python does not execute it.

### Line 21

Request-local async dependency.

### Line 22

Create a fresh AsyncSession and guarantee async cleanup.

### Line 23

Lend the session only to this request's unit of work.

### Line 24

This blank line separates logical parts; Python does not execute it.

### Line 25

Reuse the session dependency annotation, not an instance.

### Line 26

This blank line separates logical parts; Python does not execute it.

### Line 27

Create a product through a fully async I/O stack.

### Line 28

Receive the validated body and request-owned AsyncSession.

### Line 29

Construct a normal mapped Python object.

### Line 30

Stage local state; add is not an awaitable SQL operation.

### Line 31

Handle database races/constraints at the commit boundary.

### Line 32

Await the flush/commit before announcing success.

### Line 33

Translate expected integrity conflicts without swallowing unrelated errors.

### Line 34

Restore the async session's transaction state.

### Line 35

Return a stable public conflict message.

### Line 36

Explicitly load committed/generated values while the session is open.

### Line 37

The reused public schema reads loaded attributes without implicit lazy I/O.

### Line 38

This blank line separates logical parts; Python does not execute it.

### Line 39

Retrieve one persisted row asynchronously.

### Line 40

Resolve a separate session for this request.

### Line 41

Await the primary-key lookup.

### Line 42

Treat absence as an explicit HTTP outcome.

### Line 43

Do not serialize None as a valid product.

### Line 44

Serialize the loaded public fields before cleanup.

### Test / internal flow / practical use

POST a unique name and nonnegative price in `/docs`: expect 201 with ID. GET it → 200; duplicate name → 409; negative price → 422. Startup creates an async engine/factory. Each request creates one session, awaits database work, then closes it; shutdown disposes the engine. An async API that also calls async upstream services can use this consistent stack without blocking synchronous database calls in its handler.

### When to use / not use; common mistakes and best practices

Use when your database driver and request workload benefit from async concurrency. A normal `def` plus synchronous Session is often simpler and remains valid. Do not await `add`, omit awaits on commit/query, share one session across `gather` tasks, or trigger lazy relationship loading during output serialization. `expire_on_commit=False` avoids some implicit refreshes; it is not permission to serve arbitrarily stale data forever.

### Practice / expected result / solution

Create a product then restart this app and GET the same ID. The file-backed database preserves it. Trigger a duplicate name, then create another name: rollback isolates the failure and the next operation succeeds. The complete POST/GET implementation above solves both exercises; compare every awaited operation with the synchronous chapter 11 version and explain why local `add` is different.

## Lab B — OAuth scopes and resource ownership with verified identity

### What is the difference between declaration and enforcement?

A scope is a named allowed action. `Security(provider, scopes=[...])` declares required OAuth scopes and passes them through the dependency graph. `SecurityScopes` lets the provider inspect the collected required scopes. Your policy must still compare those requirements against trusted permissions. FastAPI will not grant permission merely because a route displays a lock in Swagger UI.

This lab **extends** the complete local auth app from chapter 15 by importing its app object and registering more routes. It deliberately reuses its verified current-user dependency and JWT configuration; it does not invent a second login flow. The local token endpoint does not implement delegated requested-scope issuance. The permissions below are current server-side role policy, while the route declarations express required actions. A real OAuth resource server must validate a trusted issuer's delegated token scope contract too, usually intersected with current account policy.

Ownership is another condition: two users may both have `orders:read`, but each should read only their own order. A role check alone cannot express that distinction. This lab stores the stable verified subject ID as owner at creation rather than accepting an owner ID from the caller.

Run with the chapter 15 JWT_SECRET configured: `python -m uvicorn examples.scoped_access:app --reload`. Accounts/orders remain in-memory and single-process: this is an access-policy lab, not production storage.

## Example

### File: `examples/scoped_access.py`

```python
from itertools import count
from threading import Lock
from typing import Annotated
from fastapi import Depends, HTTPException, Security
from fastapi.security import SecurityScopes
from examples.auth import app, current_user

permissions = {"reader": {"orders:read", "orders:create"}, "admin": {"orders:read", "orders:create", "products:write"}}
orders: dict[int, dict] = {}
ids = count(1)
order_lock = Lock()

def permitted(required: SecurityScopes, user: Annotated[dict, Depends(current_user)]) -> dict:
    allowed = permissions.get(user["role"], set())
    if not set(required.scopes).issubset(allowed):
        raise HTTPException(403, "Insufficient permission")
    return user

@app.post("/orders", status_code=201)
def create_order(user: Annotated[dict, Security(permitted, scopes=["orders:create"])]):
    with order_lock:
        order_id = next(ids)
        orders[order_id] = {"id": order_id, "owner_id": user["id"], "status": "new"}
        return orders[order_id].copy()

@app.get("/orders/{order_id}")
def get_order(order_id: int, user: Annotated[dict, Security(permitted, scopes=["orders:read"])]):
    with order_lock:
        order = orders.get(order_id)
        if order is None or order["owner_id"] != user["id"]:
            raise HTTPException(404, "Order not found")
        return order.copy()

@app.post("/inventory/recount", dependencies=[Security(permitted, scopes=["products:write"])])
def recount():
    return {"accepted": True}
```

## Code Explanation

### Line 1

Allocate local example order IDs monotonically.

### Line 2

Protect this additional teaching store's transitions.

### Line 3

Attach verified-user and security-scope dependencies.

### Line 4

Declare ordinary authentication and action-specific security requirements.

### Line 5

Read the required scope strings collected from Security declarations.

### Line 6

Extend the already complete local login app, including its lifespan and verified identity provider.

### Line 7

This blank line separates logical parts; Python does not execute it.

### Line 8

Define trusted server-side role permissions; callers cannot set this map through JSON.

### Line 9

Keep this explicit disposable store separate from the auth store.

### Line 10

Generate local order identities.

### Line 11

Coordinate check/read/write sequences within this process only.

### Line 12

This blank line separates logical parts; Python does not execute it.

### Line 13

Receive action requirements and an already cryptographically verified, current user.

### Line 14

Unknown roles receive no permissions by default.

### Line 15

Require every declared permission, not just any one of them.

### Line 16

Authentication succeeded, but the action is forbidden.

### Line 17

Provide identity for further ownership checks.

### Line 18

This blank line separates logical parts; Python does not execute it.

### Line 19

Add a minimal order resource to the existing auth app.

### Line 20

Declare and enforce the create action against verified identity.

### Line 21

Make local ID allocation/storage atomic.

### Line 22

Allocate an ID controlled by the server.

### Line 23

Derive ownership from verified subject, never caller input.

### Line 24

Return a snapshot rather than exposing a mutable shared dictionary reference.

### Line 25

This blank line separates logical parts; Python does not execute it.

### Line 26

Add a resource-specific protected read.

### Line 27

Enforce broad action permission first.

### Line 28

Protect lookup and ownership evaluation against local writes.

### Line 29

Retrieve the candidate resource.

### Line 30

Also require ownership; a valid reader token is insufficient for another account's order.

### Line 31

Intentionally conceal existence of another user's resource with the same missing response.

### Line 32

Only the authorized owner receives its representation.

### Line 33

This blank line separates logical parts; Python does not execute it.

### Line 34

Require a privileged action even though its returned identity is not used in the body.

### Line 35

Reader accounts never reach this handler.

### Line 36

A minimal permission demonstration, not an implemented inventory-recount job.

### Test it / expected results

Register/log in as asha and bela. Asha POSTs `/orders` and receives an ID. Asha GETs it → 200. Bela GETs the same ID with her own valid token → 404. Either reader POSTing `/inventory/recount` → 403. A request without a token → 401. These are different failures at different trust boundaries.

### What happens internally / when to use

Security declarations collect requirements; `permitted` first resolves current_user (bearer extraction → signature/claims → active account), then checks the server policy. The endpoint subsequently checks ownership. Use action scopes for capabilities and owner/tenant predicates for resource boundaries. In SQL prefer a query filtered by both ID and owner to minimize accidental unscopeable reads; in MongoDB include both in the filter.

Do not equate a token-request form's untrusted requested scopes with granted privileges. Do not let a newly added role inherit all permissions by default. Recheck ownership on writes/deletes and nested resources, not just GET. Use a consistent 403 versus concealed-404 policy and test cross-account access explicitly.

### Practice / solution

Create one order per account and prove each account sees only its own resource. The complete lab implements this policy without accepting an owner field. Expected: own reads 200, other-account reads 404, malformed path ID 422, absent bearer 401. `tests/test_advanced.py` supplies executable proof. A challenge is moving this rule into a database query that includes the verified owner ID; retain the same external response contract and tests.

## Lab C — Conditional GET with ETag

### What, why and how?

ETag lets a client ask whether its cached representation is still current. If unchanged, 304 avoids retransmitting a body. It is useful for stable public resources such as a small catalogue description. It is not useful for credentials or private content unless cache policy and authorization are carefully designed.

An ETag is quoted opaque version text. This lab hashes the exact response bytes, so a content change automatically changes the validator. GET's If-None-Match uses weak comparison: both a strong tag and its `W/` weak form can match the same opaque tag. Lists of tags and `*` are handled for this generated hex-tag contract. A general parser must account for all valid entity-tag syntax; do not casually split arbitrary user-defined tags containing commas.

Run `python -m uvicorn examples.conditional:app --reload`.

## Example

### File: `examples/conditional.py`

```python
import hashlib
import json
from typing import Annotated
from fastapi import FastAPI, Header, Response

app = FastAPI()
body = json.dumps({"service": "catalogue", "version": 1}, sort_keys=True, separators=(",", ":")).encode()
etag = '"' + hashlib.sha256(body).hexdigest() + '"'

@app.get("/catalogue-info")
def catalogue_info(if_none_match: Annotated[str | None, Header()] = None):
    headers = {"ETag": etag, "Cache-Control": "public, max-age=60"}
    candidates = [value.strip().removeprefix("W/") for value in (if_none_match or "").split(",")]
    if "*" in candidates or etag in candidates:
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)
```

## Code Explanation

### Line 1

Generate a representation fingerprint, not a password hash.

### Line 2

Serialize the exact stable bytes whose version we identify.

### Line 3

Attach an HTTP-header input declaration to a type.

### Line 4

Import app, header extraction and explicit response construction.

### Line 5

This blank line separates logical parts; Python does not execute it.

### Line 6

Create this separate public-resource demo.

### Line 7

Produce deterministic UTF-8 JSON bytes; fixed separators/order avoid meaningless formatting changes.

### Line 8

Wrap the opaque representation hash in the quotes required by ETag syntax.

### Line 9

This blank line separates logical parts; Python does not execute it.

### Line 10

Serve an intentionally public, cacheable document.

### Line 11

Read the optional conditional request header through underscore-to-hyphen conversion.

### Line 12

Permit brief caching only because this representation contains no user-specific data.

### Line 13

Normalize this lab's simple hex-tag/list contract for GET weak comparison.

### Line 14

A current representation exists and matches the client's validator condition.

### Line 15

Send validator/cache metadata with no body when unchanged.

### Line 16

Otherwise send the exact bytes used to compute the ETag; explicit Response bypasses automatic model serialization deliberately.

### Test / practice / complete solution

GET `/catalogue-info` → 200 with JSON and an ETag response header. Repeat with `If-None-Match` equal to that quoted ETag → 304 and zero bytes. Send a different quoted tag → 200 and the representation. A weak prefix `W/` on the current tag also gives 304 for this GET contract. The complete application above implements the exercise; the accompanying tests assert these conditions.

### Internal behaviour / common mistakes / best practices

The handler reads the conditional header, compares against the version of the exact encoded bytes, and chooses full representation or bodyless validation response. Do not hash one serialization then return a differently serialized body. Do not return 304 with JSON content. Do not cache a user profile under this public cache policy. For conditional writes with If-Match, use atomic database version checks rather than adapting this read-only comparison into an unsafe check-then-write sequence.

## Summary

Advanced patterns are combinations of earlier fundamentals: consistent async resource ownership, verified identity plus action/resource checks, and explicit HTTP representation semantics. Understanding those foundations is more valuable than memorizing another decorator.
