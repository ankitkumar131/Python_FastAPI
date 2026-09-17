# 08 — Dependencies: provide what a handler needs

[Previous](07-crud.md) · [Course map](00-course-guide.md) · [Next](09-async-and-lifespan.md)

## What is dependency injection?

A dependency is something a function needs to do its job: pagination rules, an authenticated user, a database session. **Dependency injection** means an outside coordinator supplies that thing instead of the function creating it itself. Think of a chef receiving washed ingredients rather than rebuilding the sink for each dish.

FastAPI allows you to write a provider function and declare `Depends(provider)`. It inspects the provider's inputs, calls it as part of request preparation and passes its result into the endpoint. This solves repeated setup, inconsistent checks and hard-to-replace resources in tests.

`Depends` does not mean “make a global singleton.” By default the same dependency is evaluated once per request for equivalent dependency use, and its result is reused within that request. A new request gets its own evaluation. `use_cache=False` requests another evaluation when reuse would be wrong. Do not turn caching off merely because you misunderstand its scope.

## Sub-dependencies and syntax

A provider can depend on another provider. This forms a directed dependency graph: values must be prepared before their consumers. FastAPI evaluates that graph and includes declared request inputs in OpenAPI. A plain helper function called by you does not receive magical dependency resolution.

`Annotated[Pagination, Depends(pagination)]` means “this argument is a Pagination value; ask the pagination callable to provide it.” Pass the callable itself, **not** `Depends(pagination())`, which would run immediately during import with the wrong inputs.

Run `python -m uvicorn examples.dependencies:app --reload`.

## Example

### File: `examples/dependencies.py`

```python
from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends, FastAPI, Query

@dataclass
class Pagination:
    limit: int
    offset: int

def pagination(limit: Annotated[int, Query(ge=1, le=100)] = 10, offset: Annotated[int, Query(ge=0)] = 0) -> Pagination:
    return Pagination(limit, offset)

def page_label(page: Annotated[Pagination, Depends(pagination)]) -> str:
    return f"offset={page.offset};limit={page.limit}"

app = FastAPI()

@app.get("/products")
def products(page: Annotated[Pagination, Depends(pagination)], label: Annotated[str, Depends(page_label)]):
    return {"limit": page.limit, "offset": page.offset, "label": label}

@app.get("/orders")
def orders(page: Annotated[Pagination, Depends(pagination)]):
    return {"limit": page.limit, "offset": page.offset}
```

## Code Explanation

### Line 1

dataclass generates an initializer and useful representation for a simple internal value container.

### Line 2

Attach dependency/query metadata to types.

### Line 3

Import the dependency declaration, app and bounded query declaration.

### Line 4

This blank line separates logical parts; Python does not execute it.

### Line 5

Ask Python to generate routine class methods; this is not a Pydantic input model.

### Line 6

Group related validated request options into one internal value.

### Line 7

Store the requested page size.

### Line 8

Store the number of entries to skip.

### Line 9

This blank line separates logical parts; Python does not execute it.

### Line 10

FastAPI reads and validates these query parameters when resolving this provider.

### Line 11

Package the validated options for downstream functions.

### Line 12

This blank line separates logical parts; Python does not execute it.

### Line 13

This provider has its own dependency, demonstrating a graph rather than a single level.

### Line 14

Produce a diagnostic label from the same page options.

### Line 15

This blank line separates logical parts; Python does not execute it.

### Line 16

Create the lesson application.

### Line 17

This blank line separates logical parts; Python does not execute it.

### Line 18

Register a collection operation.

### Line 19

FastAPI resolves both branches; pagination is reused within this request by default.

### Line 20

Use ready-to-use values instead of repeating parsing logic.

### Line 21

This blank line separates logical parts; Python does not execute it.

### Line 22

Reuse the same page rules for a second resource.

### Line 23

This separate request receives its own resolved Pagination object.

### Line 24

A second handler stays consistent without duplicating constraints.

## Test it and internal flow

GET `/products?limit=2&offset=3` → `{"limit":2,"offset":3,"label":"offset=3;limit=2"}`. GET `/orders?limit=0` → 422 before `orders` runs. `/docs` shows limit and offset even though they are declared in a dependency rather than directly on the endpoint.

FastAPI sees that products needs Pagination and label; label also needs Pagination. It extracts query values, calls pagination, caches the result for this request, builds label and finally calls products. A provider can raise HTTPException and prevent the handler from running, which is useful for authentication later.

## Dependencies with yield: borrowing resources safely

Some resources need both creation and cleanup. A database session must be closed even if an endpoint raises. A single-yield dependency expresses that lifecycle. `try/finally` guarantees cleanup when execution leaves the protected section. The following independently runnable example uses an in-memory text stream so no database knowledge is needed yet.

### File: `examples/yield_dependency.py`

```python
from io import StringIO
from typing import Annotated
from fastapi import Depends, FastAPI
app = FastAPI()
def get_buffer():
    buffer = StringIO()
    try:
        yield buffer
    finally:
        buffer.close()
@app.get("/message")
def message(buffer: Annotated[StringIO, Depends(get_buffer)]):
    buffer.write("hello")
    return {"message": buffer.getvalue()}
```

Line 1 imports a text stream backed by memory. Lines 2–3 import metadata and framework tools. Line 4 creates the app. Line 5 defines a resource provider. Line 6 allocates the stream. Line 7 begins protected use. Line 8 lends the stream while pausing the generator. Lines 9–10 guarantee closure afterwards. Line 11 registers a route. Line 12 requests the borrowed stream. Line 13 writes text and line 14 reads it before closure. Save and run `python -m uvicorn examples.yield_dependency:app --reload`; `/message` returns `{"message":"hello"}`.

### Cleanup scope matters

Current FastAPI supports `Depends(provider, scope="function")` for yield dependencies: cleanup occurs after the endpoint function but before the response is sent. The default yield dependency scope is `"request"`: cleanup occurs after the response is sent, which allows a streaming response to consume a borrowed resource. A request-scoped dependency cannot depend on a function-scoped yield resource that would disappear before its own cleanup; function-scoped dependencies can depend on longer-lived ones.

Older FastAPI releases changed yield cleanup timing. Do not rely on a tutorial's historical timing; consult the official dependency lifecycle documentation linked in chapter 23 and test your installed version. This course's requirements select a release family supporting explicit scopes.

Do not defer a database commit until cleanup after a success response: a commit can fail after the client was told success. Commit inside the operation; use dependency cleanup to close/rollback resources. Do not reuse a request session in a background task; the task should create and close its own resource.

## When to use / when NOT to use

Use dependencies for repeated request preparation, resource ownership and checks. Use a normal function for a simple calculation with explicit arguments. Dependencies are not a replacement for all function calls. Do not hide essential business decisions in a maze of providers with side effects.

Decorator-level `dependencies=[Depends(check)]` runs checks whose return values the handler does not need. Router-level dependencies apply to an entire group; chapter 19 introduces routers. A dependency can also be a callable class instance, but begin with ordinary provider functions because their execution is easier to trace.

## Common Mistakes / best practices

Calling a provider while declaring Depends, returning instead of yielding when cleanup is required, yielding more than once, swallowing exceptions in cleanup, and assuming request caching lasts across users are common errors. Keep dependency graphs small, deterministic and named by the resource provided. Prefer `Annotated` to preserve clean type information. Test replacement providers using `app.dependency_overrides` (chapter 18).

## Practice

Create a `/report` endpoint that reuses pagination and returns the inclusive start offset and exclusive end offset of the requested slice.

## Expected Result / Solution

`/report?offset=3&limit=2` → `{"start":3,"end":5}`.

Append to the complete `examples/dependencies.py`:

```python
@app.get("/report")
def report(page: Annotated[Pagination, Depends(pagination)]):
    return {"start": page.offset, "end": page.offset + page.limit}
```

Line 1 registers the route. Line 2 requests the existing reusable provider. Line 3 computes boundaries from already validated values. No imports are missing because this is an explicitly named extension of the complete file. The same server command applies; reload will notice your edit.

## Summary

Dependencies are request-aware suppliers, not global variables. Their lifetimes will become central when we introduce real clients and sessions next.
