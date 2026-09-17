# 13 — MongoDB with modern async PyMongo

[Previous](12-sql-servers-and-migrations.md) · [Course map](00-course-guide.md) · [Next](14-authentication-foundations.md)

## What is a document database?

MongoDB stores **documents** in **collections** inside databases. A document resembles a Python dictionary but is stored using **BSON (Binary JSON)**, which supports types beyond JSON, including ObjectId and dates. A collection groups related documents, similar in purpose but not identical to a SQL table.

Documents can embed nested information such as product specifications. This can make aggregate reads natural. References between documents are possible, but MongoDB does not provide relational foreign-key enforcement. Application/schema validation and access patterns still matter. Use embedding for bounded data commonly read together; use references for independently growing or frequently shared entities.

`ObjectId` is MongoDB's common generated identifier type. It is not JSON-native. Public APIs often expose it as a string and validate/convert incoming strings before querying. A malformed identifier is different from a valid identifier for a nonexistent document.

## Why PyMongo Async rather than Motor?

**PyMongo** is MongoDB's official Python driver. Its `AsyncMongoClient` supports async database operations. Official guidance recommends migrating Motor applications to PyMongo Async; Motor's deprecation date is May 14, 2026. New examples here do not use Motor. An async client belongs to the event loop that uses it, not arbitrary cross-thread sharing.

A client owns connection pools and should be long-lived. A **cursor** is a query-result iterator that retrieves data in batches. `find()` builds a cursor; awaiting each result or `to_list()` performs retrieval. Bound list size instead of materializing an entire collection.

## Installation / local database

```bash
python -m pip install 'pymongo>=4.13,<5'
docker run --name fastapi-mongo -p 127.0.0.1:27017:27017 -d mongo:8.0
python -m uvicorn examples.mongo_app:app --reload
```

Line 1 installs the modern driver. Line 2 starts a loopback-only **unauthenticated disposable lab** MongoDB; never expose this setup publicly. Line 3 runs the API. Use authenticated users, TLS and network restrictions for managed/production MongoDB. `MONGODB_URL` can override the local URL; URLs must not enter Git/logs.

## Example

### File: `examples/mongo_app.py`

```python
import os
from contextlib import asynccontextmanager
from typing import Annotated
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from pymongo import AsyncMongoClient

class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)

class ProductPublic(ProductCreate):
    id: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient(os.getenv("MONGODB_URL", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=3000)
    try:
        await client.admin.command("ping")
        app.state.products = client.catalog.products
        yield
    finally:
        await client.close()

app = FastAPI(lifespan=lifespan)

def parse_id(product_id: str) -> ObjectId:
    if not ObjectId.is_valid(product_id):
        raise HTTPException(422, "Invalid product ID")
    return ObjectId(product_id)

def public(document: dict) -> dict:
    return {"id": str(document["_id"]), "name": document["name"], "price_minor": document["price_minor"]}

@app.post("/products", response_model=ProductPublic, status_code=201)
async def create_product(data: ProductCreate, request: Request):
    document = data.model_dump()
    result = await request.app.state.products.insert_one(document)
    document["_id"] = result.inserted_id
    return public(document)

@app.get("/products", response_model=list[ProductPublic])
async def list_products(request: Request, limit: Annotated[int, Query(ge=1, le=100)] = 10):
    cursor = request.app.state.products.find({}).sort("_id", 1).limit(limit)
    return [public(document) async for document in cursor]

@app.get("/products/{product_id}", response_model=ProductPublic)
async def get_product(product_id: str, request: Request):
    document = await request.app.state.products.find_one({"_id": parse_id(product_id)})
    if document is None:
        raise HTTPException(404, "Product not found")
    return public(document)

@app.put("/products/{product_id}", response_model=ProductPublic)
async def replace_product(product_id: str, data: ProductCreate, request: Request):
    oid = parse_id(product_id)
    document = data.model_dump()
    result = await request.app.state.products.replace_one({"_id": oid}, document)
    if result.matched_count == 0:
        raise HTTPException(404, "Product not found")
    return public({"_id": oid, **document})

@app.delete("/products/{product_id}", status_code=204, response_class=Response)
async def delete_product(product_id: str, request: Request):
    result = await request.app.state.products.delete_one({"_id": parse_id(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Product not found")
    return Response(status_code=204)
```

## Code Explanation

### Line 1

Read the database URL from process configuration.

### Line 2

Manage the async client's lifetime.

### Line 3

Attach bounds to query parameters.

### Line 4

Import MongoDB's native ID type from PyMongo's bundled bson package, not a separate bson distribution.

### Line 5

Import app, errors, query rules, app-state access and no-content responses.

### Line 6

Build input/output contracts.

### Line 7

Use PyMongo's modern async driver.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Validate documents before writing them.

### Line 10

Reject unexpected keys such as raw MongoDB operators.

### Line 11

Require a bounded nonblank product name.

### Line 12

Require a nonnegative integer amount.

### Line 13

This blank line separates logical parts; Python does not execute it.

### Line 14

Reuse safe public fields.

### Line 15

Expose the BSON ObjectId as a JSON string.

### Line 16

This blank line separates logical parts; Python does not execute it.

### Line 17

Make startup/shutdown a managed async context.

### Line 18

Create one client for this worker/event loop.

### Line 19

Configure the connection and bound server-discovery waiting to three seconds.

### Line 20

Ensure cleanup even when ping/setup fails.

### Line 21

Verify database availability before accepting requests.

### Line 22

Select a database and collection; this is not a per-request client.

### Line 23

Serve requests with the shared collection handle.

### Line 24

Run graceful shutdown cleanup.

### Line 25

Close the async client's pools using its awaitable close API.

### Line 26

This blank line separates logical parts; Python does not execute it.

### Line 27

Attach resource lifecycle management.

### Line 28

This blank line separates logical parts; Python does not execute it.

### Line 29

Keep public string-to-native-ID conversion in one helper.

### Line 30

Check syntax before trying to build an ObjectId.

### Line 31

Distinguish malformed ID input from a missing document.

### Line 32

Convert a valid public ID to the BSON lookup type.

### Line 33

This blank line separates logical parts; Python does not execute it.

### Line 34

Centralize the storage-to-response transformation.

### Line 35

Convert only allowed fields and the non-JSON native identifier.

### Line 36

This blank line separates logical parts; Python does not execute it.

### Line 37

Define document creation.

### Line 38

Combine a validated body with application-state access.

### Line 39

Prepare a plain dictionary with allowed fields.

### Line 40

Await the database write and get its acknowledged result.

### Line 41

Explicitly attach the generated ID for output transformation.

### Line 42

Return the documented JSON-safe representation.

### Line 43

This blank line separates logical parts; Python does not execute it.

### Line 44

Register bounded listing before variable-ID routes.

### Line 45

Cap retrieval to prevent unbounded memory use.

### Line 46

Build an ordered bounded cursor; find itself is not awaited.

### Line 47

Retrieve batches asynchronously and transform each selected document.

### Line 48

This blank line separates logical parts; Python does not execute it.

### Line 49

Define single-document retrieval.

### Line 50

Receive the external string ID and collection access.

### Line 51

Query using a validated native ID, not arbitrary user-supplied filter operators.

### Line 52

A valid ObjectId may not exist.

### Line 53

Translate absence into HTTP semantics.

### Line 54

Serialize the stored document safely.

### Line 55

This blank line separates logical parts; Python does not execute it.

### Line 56

Define full replacement of the editable document fields.

### Line 57

Validate both ID syntax via the helper and body via Pydantic.

### Line 58

Convert the identifier once.

### Line 59

Prepare a complete replacement, not an unchecked update-operator dictionary.

### Line 60

Atomically replace one document while preserving MongoDB's ID.

### Line 61

Distinguish missing documents from successful no-change replacements.

### Line 62

Do not silently create when this contract promises update-only PUT.

### Line 63

Return the new public representation.

### Line 64

This blank line separates logical parts; Python does not execute it.

### Line 65

Define a bodyless delete operation.

### Line 66

Read the path ID and collection handle.

### Line 67

Perform a bounded delete by one validated identity.

### Line 68

A zero count means nothing was deleted.

### Line 69

Report absent resources consistently.

### Line 70

Send an empty successful response.

## Test it / expected results

In `/docs`, POST `{"name":"Pen","price_minor":2000}` → 201 with a 24-hex-character ID string. Copy that ID into GET/PUT/DELETE operations. Negative price or an extra `$where` field → 422. GET `/products/not-an-id` → 422; GET using a well-formed but absent ObjectId → 404. PUT valid name/price → 200; DELETE → 204. A stopped MongoDB prevents the startup ping from succeeding; do not report the app ready without its essential dependency.

## What happens internally / transactions and indexes

Pydantic validates input, PyMongo encodes a document into BSON, the client selects a server/connection, MongoDB executes the operation, and the driver decodes the result. The public transformation replaces native `_id` with a string `id`. A single-document write is atomic. Multi-document transactions require a suitable deployment, such as a replica set or sharded cluster; the simple standalone lab is not a transaction deployment.

MongoDB creates an index on `_id`. Add other indexes for demonstrated access patterns. For example a unique SKU (Stock Keeping Unit, a business product code) needs a database unique index as well as application validation. Index builds and collection validation should be managed intentionally, not raced on every request. A flexible schema still requires a plan for old documents missing new fields.

## When to use / not use; mistakes and best practices

Use documents for bounded aggregates frequently read together. Avoid unbounded embedded arrays, arbitrary caller-supplied query operators, a new client per request, or unbounded `to_list(None)` in a public listing. Do not install the unrelated `bson` PyPI package; PyMongo supplies its own. Do not return ObjectId directly in ordinary JSON. Do not await `find()` itself or forget to await `find_one`/writes/close. Use least-privilege database credentials, finite selection/operation deadlines and real integration tests.

## Practice / Solution

**Beginner:** Create/read a product and distinguish malformed-ID 422 from absent-ID 404.

**Intermediate:** Send PUT with identical data. Expected 200 even if no bytes needed changing: `matched_count`, not `modified_count`, determines existence.

**Challenge:** Design a price-only PATCH. Use a Pydantic patch schema permitting omission but rejecting null price (chapter 07), derive changes with `exclude_unset=True`, and apply `{"$set": changes}` using `update_one` with the parsed `_id`. Never accept the operator dictionary directly from the caller. A subsequent read can return the representation, but concurrent changes can intervene; `find_one_and_update` with `ReturnDocument.AFTER` returns the atomic update's resulting document. This distinction is why replacement and partial-update contracts deserve deliberate design.

## Summary

MongoDB changes storage shape, not the need for validated contracts, bounded work, access control or reliable resource ownership.
