# 07 — A complete in-memory CRUD API

[Previous](06-responses-and-errors.md) · [Course map](./) · [Next](08-dependencies.md)

## What are we building, and why?

CRUD connects the isolated route concepts into one resource lifecycle. Create a product, read it, change it, then delete it. We deliberately use an in-memory dictionary before introducing a database, so HTTP and validation behaviour remain visible.

**Teaching boundary:** this store disappears on restart and is not shared across server workers. A lock protects this example's read/modify/write sequences within one process, not across machines. Real persistence and concurrency control arrive in chapters 10–12. Do not deploy this as a catalogue database.

A **lock** is a synchronization primitive: only one thread can hold it at a time. Because normal `def` endpoints may execute in multiple threads, operations involving several dictionary steps need coordination. Short dictionary operations are okay here; do not hold this lock across slow I/O.

## PUT versus PATCH: specify the contract

Our PUT replaces a product's editable representation: required name and price must be supplied, omitted description resets to null. Our PATCH changes only supplied fields. Name and price may be omitted in PATCH but may not explicitly be null; description may be cleared with null. `exclude_unset=True` preserves this distinction.

We keep IDs server-controlled and use nonnegative integer `price_minor` rather than float money. A rupee has 100 paise; `12000` means ₹120 when the currency is INR. This course assumes one currency per catalogue unless an endpoint explicitly says otherwise.

Run `python -m uvicorn examples.crud:app --reload`. All code is in one file:

## Example

### File: `examples/crud.py`

```python
from itertools import count
from threading import Lock
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)
    description: str | None = Field(default=None, max_length=500)

class ProductPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=80)
    price_minor: int | None = Field(default=None, ge=0, strict=True)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name", "price_minor")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("Omit this field instead of sending null")
        return value

class ProductPublic(ProductCreate):
    id: int

app = FastAPI()
store: dict[int, ProductPublic] = {}
ids = count(1)
lock = Lock()

@app.post("/products", response_model=ProductPublic, status_code=201)
def create_product(data: ProductCreate, response: Response):
    with lock:
        product = ProductPublic(id=next(ids), **data.model_dump())
        store[product.id] = product
    response.headers["Location"] = f"/products/{product.id}"
    return product

@app.get("/products", response_model=list[ProductPublic])
def list_products(limit: Annotated[int, Query(ge=1, le=100)] = 10, offset: Annotated[int, Query(ge=0)] = 0):
    with lock:
        return [store[key] for key in sorted(store)][offset:offset + limit]

@app.get("/products/{product_id}", response_model=ProductPublic)
def get_product(product_id: int):
    with lock:
        if product_id not in store:
            raise HTTPException(404, "Product not found")
        return store[product_id]

@app.put("/products/{product_id}", response_model=ProductPublic)
def replace_product(product_id: int, data: ProductCreate):
    with lock:
        if product_id not in store:
            raise HTTPException(404, "Product not found")
        store[product_id] = ProductPublic(id=product_id, **data.model_dump())
        return store[product_id]

@app.patch("/products/{product_id}", response_model=ProductPublic)
def patch_product(product_id: int, data: ProductPatch):
    with lock:
        if product_id not in store:
            raise HTTPException(404, "Product not found")
        merged = {**store[product_id].model_dump(), **data.model_dump(exclude_unset=True)}
        store[product_id] = ProductPublic.model_validate(merged)
        return store[product_id]

@app.delete("/products/{product_id}", status_code=204, response_class=Response)
def delete_product(product_id: int):
    with lock:
        if product_id not in store:
            raise HTTPException(404, "Product not found")
        del store[product_id]
    return Response(status_code=204)
```

## Code Explanation

### Line 1

count produces successive IDs without reusing a deleted dictionary length.

### Line 2

A lock coordinates concurrent synchronous endpoint threads in this one process.

### Line 3

Support query constraints alongside type hints.

### Line 4

Import app, errors, input bounds and bodyless responses.

### Line 5

Import request/output modelling and a partial-update validator.

### Line 6

This blank line separates logical parts; Python does not execute it.

### Line 7

Describe the complete editable product representation.

### Line 8

Reject unknown keys and strip string edges before string constraints are checked.

### Line 9

Require a nonblank bounded name.

### Line 10

Require a nonnegative actual integer amount.

### Line 11

Allow omitted/null text but bound non-null descriptions.

### Line 12

This blank line separates logical parts; Python does not execute it.

### Line 13

Define a distinct partial-update contract, not a copy of the create requirements.

### Line 14

Reject spelling mistakes and normalize strings consistently.

### Line 15

The default permits omission; the validator below rejects explicitly supplied null.

### Line 16

Permit omission, but require a valid integer if the caller supplies this field.

### Line 17

Both omission and explicit clearing are meaningful for description.

### Line 18

This blank line separates logical parts; Python does not execute it.

### Line 19

Check only supplied field values; default None values are not validated in this patch model.

### Line 20

Supply the class as the first argument to the validator.

### Line 21

The same rule accepts either a validated name or price.

### Line 22

Detect an explicit null supplied by the client.

### Line 23

Explain how to leave the existing value unchanged.

### Line 24

Preserve the accepted non-null update.

### Line 25

This blank line separates logical parts; Python does not execute it.

### Line 26

Reuse safe editable fields in the response contract.

### Line 27

Add the server-generated identifier, which callers cannot set during creation.

### Line 28

This blank line separates logical parts; Python does not execute it.

### Line 29

Create this lesson's independent app.

### Line 30

Store validated products by ID in memory only.

### Line 31

Start generated IDs at one.

### Line 32

Share one lock for operations on this store and counter.

### Line 33

This blank line separates logical parts; Python does not execute it.

### Line 34

Define resource creation and its public response.

### Line 35

Receive a validated body and the response metadata object supplied by FastAPI.

### Line 36

Make ID allocation plus storage one protected operation in this process.

### Line 37

Allocate an ID and expand the validated editable fields into a complete product.

### Line 38

Save the object under its new identifier.

### Line 39

Point the client to the resource using an f-string that inserts the ID.

### Line 40

Return a validated public representation.

### Line 41

This blank line separates logical parts; Python does not execute it.

### Line 42

Define a bounded collection read.

### Line 43

Limit bounds page size; offset skips a nonnegative number of entries.

### Line 44

Take a consistent snapshot while other requests might edit the dictionary.

### Line 45

Sort IDs, build the ordered list, then take the requested slice.

### Line 46

This blank line separates logical parts; Python does not execute it.

### Line 47

Define individual reads after the fixed collection route.

### Line 48

Receive an integer path ID.

### Line 49

Coordinate access with writers.

### Line 50

A syntactically valid ID may still have no resource.

### Line 51

Report missing data rather than a parsing error.

### Line 52

Return the existing immutable-by-convention stored object.

### Line 53

This blank line separates logical parts; Python does not execute it.

### Line 54

Define full replacement of an existing product's editable state.

### Line 55

Require the complete create-shaped body; ID comes only from the path.

### Line 56

Check and replace atomically within the process.

### Line 57

This API chooses update-only PUT rather than create-at-known-ID semantics.

### Line 58

Reject replacement of an absent product.

### Line 59

Replace all editable fields, including defaults for omitted optional fields.

### Line 60

Return the new representation with HTTP 200.

### Line 61

This blank line separates logical parts; Python does not execute it.

### Line 62

Define partial updates using the distinct patch contract.

### Line 63

Validate only the fields the patch permits.

### Line 64

Protect the read/merge/write sequence from another thread's simultaneous edit.

### Line 65

Ensure there is something to update.

### Line 66

Stop before attempting a missing dictionary lookup.

### Line 67

Overlay explicitly supplied changes, retaining omitted fields and preserving an explicit null description.

### Line 68

Revalidate the complete merged representation instead of using unchecked model\_copy updates.

### Line 69

Send the updated public model.

### Line 70

This blank line separates logical parts; Python does not execute it.

### Line 71

Define deletion with no response body.

### Line 72

Parse the resource ID.

### Line 73

Protect the existence check and deletion together.

### Line 74

A second delete will reach this branch.

### Line 75

The differing result does not violate DELETE's idempotent intended effect.

### Line 76

Remove the dictionary entry.

### Line 77

Return an actually empty response.

## Test the complete flow

```bash
curl -i -X POST http://127.0.0.1:8000/products -H 'Content-Type: application/json' -d '{"name":"Notebook","price_minor":12000,"description":"A5"}'
curl -i http://127.0.0.1:8000/products/1
curl -i -X PATCH http://127.0.0.1:8000/products/1 -H 'Content-Type: application/json' -d '{"description":null}'
curl -i -X PUT http://127.0.0.1:8000/products/1 -H 'Content-Type: application/json' -d '{"name":"Large notebook","price_minor":15000}'
curl -i -X DELETE http://127.0.0.1:8000/products/1
curl -i http://127.0.0.1:8000/products/1
```

Line 1 creates ID 1 in a fresh process and returns 201 plus Location. Line 2 reads it. Line 3 clears the description while keeping name/price. Line 4 fully replaces editable fields and defaults description to null. Line 5 deletes it with 204 and no body. Line 6 now returns 404. Use the ID actually returned if the process already contains data.

Bad inputs: empty name, negative price, unexpected `id`, or PATCH `{"name":null}` → 422. An empty PATCH `{}` is accepted as a no-op in this contract; explicitly rejecting it is also reasonable if documented. GET with `limit=1000` → 422.

## What happens internally / real-world connection

Input parsing constructs the appropriate create or patch model. The handler acquires the lock, checks resource existence, modifies the dictionary, and returns a public model. FastAPI prepares the response outside the business operation. Validation and resource existence are different stages. The database version will replace the dictionary and lock with sessions, transactions and database constraints; the external contract can remain similar.

## When to use / when not to use

Use an in-memory store to teach HTTP, prototype disposable state or build isolated tests. Never assume it survives reload, shares data across workers, or provides a distributed transaction. Use server-controlled IDs and bounded listing in real APIs. Offset pagination is simple for small collections; large changing collections often need cursor/keyset pagination (chapter 22).

## Common Mistakes and Best Practices

`len(store) + 1` can reuse an existing ID after deletion. A module-level dictionary without coordination can suffer check-then-act races. PUT using a patch model makes replacement semantics unclear. `exclude_none=True` discards explicit clearing, while dumping all PATCH defaults can erase values the caller omitted. Validate the merged result, especially if future cross-field rules are added. For concurrent production updates, use a version column or conditional writes rather than “last writer wins” accidentally.

## Practice

**Beginner:** Create two products and list only one using query parameters.

**Intermediate:** Clear a description without changing the price.

**Challenge:** Demonstrate that PUT requires a name but PATCH does not, and that explicit null price fails.

## Expected Result / Solution

Use the complete `examples/crud.py` above; no additional app code is required.

1. POST `{"name":"Pen","price_minor":2000}` and POST `{"name":"Book","price_minor":12000}`. GET `/products?limit=1&offset=0` returns the first created remaining product in a one-element array.
2. PATCH the returned ID with `{"description":null}`. The output price equals the previous price.
3. PUT that ID with `{"price_minor":3000}` → 422 for missing name. PATCH the same body → 200 with retained name. PATCH `{"price_minor":null}` → 422 from `not_null`.

The complete executable proof of these behaviours is in the test chapter; reusing the implementation avoids copying a second slightly different CRUD API.

## Summary

You can now implement a complete resource lifecycle. Next we remove repeated preparation from handlers using dependencies.
