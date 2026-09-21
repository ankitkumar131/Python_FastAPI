# 06 — Response contracts, status codes and errors

[Previous](05-pydantic.md) · [Course map](./) · [Next](07-crud.md)

## What is a response model, and why do we need one?

Input models protect your function from unsuitable data. Response models protect the **public contract** from unsuitable output. Think of packing an order: internal warehouse notes should not appear on the customer's label. A public user model includes ID and display name but not a password hash.

`response_model=PublicUser` on a route tells FastAPI to validate and serialize ordinary returned data according to that shape. Undeclared fields are filtered out. Missing or invalid required output is a programming error, normally producing a server error rather than a 422 client-input error. Response filtering is a useful safety layer, not an excuse to pass secrets around unnecessarily.

## Exceptions versus returning an error object

An **exception** changes control flow. `raise HTTPException(status_code=404, detail="...")` stops normal processing and lets the framework build an HTTP error response. `return HTTPException(...)` merely returns an object; it is not the intended mechanism.

A **custom exception handler** translates a chosen exception type into a consistent response. Use one when business rules should not depend directly on HTTP details. Do not convert every exception into 400: an unexpected database failure is not a caller's typo.

`Response` represents a complete HTTP response; `JSONResponse` produces JSON, `PlainTextResponse` text, and `RedirectResponse` a redirect. A returned Response instance generally bypasses automatic response-model validation/serialization: you are taking responsibility for the output. Use it deliberately, not to hide validation failures.

## Complete example and syntax

Run `python -m uvicorn examples.responses:app --reload`. Open `/docs`, then try `/users/1`, `/users/2` and `/stock/20`.

## Example

### File: `examples/responses.py`

```python
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel

app = FastAPI()

class PublicUser(BaseModel):
    id: int
    name: str

class OutOfStock(Exception):
    pass

@app.exception_handler(OutOfStock)
async def out_of_stock_handler(request: Request, error: OutOfStock):
    return JSONResponse(status_code=409, content={"detail": "Insufficient stock"})

@app.get("/users/{user_id}", response_model=PublicUser)
def get_user(user_id: int):
    if user_id != 1:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": 1, "name": "Asha", "password_hash": "never-public"}

@app.delete("/users/{user_id}", status_code=204, response_class=Response)
def delete_user(user_id: int):
    return Response(status_code=204)

@app.get("/stock/{quantity}")
def stock(quantity: int):
    if quantity > 5:
        raise OutOfStock()
    return {"available": True}

@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"

@app.get("/old-users", include_in_schema=False)
def old_users():
    return RedirectResponse("/users/1", status_code=307)
```

## Code Explanation

### Line 1

Import the app, HTTP-aware exception, request metadata object and raw response class.

### Line 2

Import response implementations for JSON, text and redirects.

### Line 3

Import output-schema support.

### Line 4

This blank line separates logical parts; Python does not execute it.

### Line 5

Create the independent lesson app.

### Line 6

This blank line separates logical parts; Python does not execute it.

### Line 7

List only fields permitted to leave the server.

### Line 8

Require a numeric public identifier.

### Line 9

Require the public display name; no password-related field exists.

### Line 10

This blank line separates logical parts; Python does not execute it.

### Line 11

Create a domain-specific exception independent of HTTP status codes.

### Line 12

The inherited exception behaviour is sufficient; pass supplies a legal empty class body.

### Line 13

This blank line separates logical parts; Python does not execute it.

### Line 14

Register a translation for this exception type only.

### Line 15

FastAPI supplies request context and the exception. Async syntax is explained fully in chapter 09; no blocking work is done here.

### Line 16

Build a conflict response with a stable public message, not raw internal error text.

### Line 17

This blank line separates logical parts; Python does not execute it.

### Line 18

Register a read endpoint with an explicit public response schema.

### Line 19

Validate the path ID as an integer.

### Line 20

In this tiny dataset only user 1 exists.

### Line 21

Stop execution and produce the conventional JSON detail error.

### Line 22

The declared model filters password\_hash from the response; real code should also minimize secret handling.

### Line 23

This blank line separates logical parts; Python does not execute it.

### Line 24

Document a no-content result and use a bodyless response class.

### Line 25

This demonstrates HTTP semantics only, not persistent deletion.

### Line 26

Send an empty body; returning a message with 204 would be contradictory.

### Line 27

This blank line separates logical parts; Python does not execute it.

### Line 28

Add a domain-failure demonstration.

### Line 29

Parse the requested quantity.

### Line 30

Pretend only five units are currently available.

### Line 31

Transfer control to the registered domain exception handler.

### Line 32

Return normal data when the domain condition succeeds.

### Line 33

This blank line separates logical parts; Python does not execute it.

### Line 34

Explicitly document plain-text output rather than JSON.

### Line 35

A lightweight liveness-style demonstration.

### Line 36

This is text because the configured response class is PlainTextResponse.

### Line 37

This blank line separates logical parts; Python does not execute it.

### Line 38

Keep a compatibility redirect out of generated docs.

### Line 39

Handle requests to the old path.

### Line 40

Tell the client to use the new relative URL while preserving the method.

## Test it and what happens internally

`GET /users/1` returns `{"id":1,"name":"Asha"}` with no `password_hash`. `/users/2` returns 404 and `{"detail":"User not found"}`. `/users/abc` fails input validation with 422. `/stock/20` returns 409 from the exception handler. DELETE `/users/1` returns 204 and zero body bytes. `/health` returns text `ok`. A browser usually follows `/old-users` automatically.

FastAPI selects the endpoint and validates input. A raised HTTPException is handled as a deliberate HTTP outcome; a raised OutOfStock is translated by its handler. Otherwise output goes through the declared response contract unless the handler has returned an already built Response. Unexpected exceptions should be logged internally and give a generic 500 response in production.

## Real-world example / when to use

Public user serialization is essential in registration, profile reads and admin endpoints with different fields. Domain exception translation is useful when an inventory service is reused by HTTP endpoints and jobs. Prefer direct `HTTPException` for straightforward route-local failures; do not create an elaborate exception hierarchy for every tiny app.

Choose 201 when a resource was created, 202 when work is only accepted, 200 when returning an updated representation and 204 when there is no representation. A `Location` response header can identify a newly created resource. Multiple documented error outcomes can be added with `responses={404: {"description": "Not found"}}`; that metadata documents behaviour but does not implement the error branch.

## Common Mistakes and Best Practices

* Returning `{"error": ...}` with 200 confuses clients and metrics.
* Returning the registration model exposes passwords if it is also the response model.
* Raw `JSONResponse(content=data)` bypasses response-model filtering; filter deliberately first.
* Catching all exceptions and echoing `str(error)` can leak SQL, filesystem paths or credentials.
* Setting a status in docs does not create a database row; runtime implementation still matters.
* Do not customize validation errors merely to remove useful locations. If customizing, do not blindly echo sensitive request input.

## Practice

Return a public product with `id` and `name`, while hiding internal `cost_minor`. Return 404 for IDs other than 1.

## Expected Result and Solution

GET `/products/1` → `{"id":1,"name":"Pen"}`; GET `/products/2` → 404.

### File: `examples/practice_responses.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
class PublicProduct(BaseModel):
    id: int
    name: str
app = FastAPI()
@app.get("/products/{product_id}", response_model=PublicProduct)
def product(product_id: int):
    if product_id != 1:
        raise HTTPException(404, "Product not found")
    return {"id": 1, "name": "Pen", "cost_minor": 100}
```

Lines 1–2 import the web/error and model tools. Line 3 creates the public schema; lines 4–5 allow only ID and name. Line 6 creates the app. Line 7 attaches the schema to the route. Line 8 receives the parsed ID. Lines 9–10 stop missing reads. Line 11 includes an internal field that the response schema excludes. Save and run `python -m uvicorn examples.practice_responses:app --reload`.

## Summary

Inputs and outputs are separate contracts. Correct error statuses are part of the public API, while private diagnostic details belong in controlled logs.
