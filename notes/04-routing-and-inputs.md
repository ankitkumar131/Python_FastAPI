# 04 — Routes and the different places input can live

[Previous](03-fastapi-first-application.md) · [Course map](00-course-guide.md) · [Next](05-pydantic.md)

## What is request parsing, and why do we need it?

The URL `/products/12?limit=3` arrives as network data, not as Python integer arguments. Parsing separates the request into components; validation checks whether those components satisfy our contract. FastAPI inspects the handler signature (its parameters and annotations) to arrange both. This removes repeated string conversion and error-response code from each handler.

Think of a receptionist distributing incoming forms: the address identifies the customer, the preferences section carries options, and an attached document contains detailed data. Mixing these locations makes clients guess how to communicate.

## How FastAPI chooses an input source

| Declaration | Source | Why / when to use |
|---|---|---|
| Parameter named in `/products/{product_id}` | Path | Required resource identity |
| Scalar `limit: int = 10` not in the path | Query | Simple optional collection option |
| Parameter typed as a Pydantic model | JSON body | Structured data to create/update |
| `Annotated[str, Header()]` | Header | Request metadata |
| `Annotated[str | None, Cookie()] = None` | Cookie | Browser-carried state |
| `Annotated[int, Body()]` | Body | Explicitly put a scalar in a body |

A **cookie** is a small name/value item browsers store and send according to domain, path and security rules. It is client-controlled input, not proof of identity on its own. Authentication cookies require additional protections (chapter 14). `Header` and `Cookie` are declarations describing where to read; neither authenticates the caller.

`Path`, `Query`, `Body` and `Header` also accept validation/documentation metadata. `ge=1` means greater than or equal to one, `le=100` at most 100, `min_length` and `max_length` constrain string length. A regular expression is a pattern describing allowed text; prefer simple constraints over overly complex patterns.

Before using a structured body, we need **BaseModel**: Pydantic's parent class that reads annotated attributes and builds validation rules. A subclass describes a data shape. `class ProductCreate(BaseModel): name: str` says a product creation object requires a string name. An instance holds already validated values; chapter 05 expands this mechanism.

## Complete example

Start with `python -m uvicorn examples.inputs:app --reload`. This uses the packages installed in chapter 03. The example echoes inputs rather than saving them, so it needs no database.

## Example

### File: `examples/inputs.py`

```python
from typing import Annotated
from fastapi import Body, Cookie, FastAPI, Header, Path, Query
from pydantic import BaseModel, Field

app = FastAPI()

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0)

@app.get("/products/featured")
def featured():
    return {"id": 1, "name": "Notebook"}

@app.get("/products/{product_id}")
def get_product(
    product_id: Annotated[int, Path(ge=1)],
    currency: Annotated[str, Query(pattern="^(INR|USD)$")] = "INR",
    user_agent: Annotated[str | None, Header()] = None,
    theme: Annotated[str | None, Cookie()] = None,
):
    return {"id": product_id, "currency": currency, "agent": user_agent, "theme": theme}

@app.get("/products")
def list_products(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    tags: Annotated[list[str] | None, Query()] = None,
):
    return {"limit": limit, "tags": tags or []}

@app.post("/products", status_code=201)
def create_product(product: ProductCreate):
    return product

@app.post("/discount")
def discount(percent: Annotated[int, Body(ge=0, le=100, embed=True)]):
    return {"percent": percent}
```

## Code Explanation

### Line 1

Import the container for a type plus framework metadata.

### Line 2

Import the app and declarations for the five input locations used below.

### Line 3

BaseModel builds structured validation; Field attaches constraints to model attributes.

### Line 4

This blank line separates logical parts; Python does not execute it.

### Line 5

Create this lesson's independent application.

### Line 6

This blank line separates logical parts; Python does not execute it.

### Line 7

Define the contract for a JSON object used when creating a product.

### Line 8

Require text between one and eighty characters; no default means the key must be supplied.

### Line 9

Require a nonnegative integer amount in minor currency units.

### Line 10

This blank line separates logical parts; Python does not execute it.

### Line 11

Register the fixed path before the variable path so `featured` is not interpreted as an ID.

### Line 12

This handler requires no caller arguments.

### Line 13

Return one fixed example product.

### Line 14

This blank line separates logical parts; Python does not execute it.

### Line 15

Curly braces define the required path placeholder.

### Line 16

Start a multiline function signature; lines inside parentheses continue it.

### Line 17

Match the path placeholder, convert its text to an integer and require at least one.

### Line 18

Read a query string, defaulting to INR. Anchors require the entire value to be INR or USD.

### Line 19

Read `User-Agent`: Header normally converts Python underscores to HTTP hyphens. Missing is allowed.

### Line 20

Read the optional `theme` cookie; never assume it is trustworthy.

### Line 21

Close the signature and begin the body.

### Line 22

Echo validated values so you can see their sources; no currency conversion is performed.

### Line 23

This blank line separates logical parts; Python does not execute it.

### Line 24

Register a collection endpoint distinct from the individual-resource route.

### Line 25

Declare bounded pagination inputs.

### Line 26

Default to ten and reject zero, negative or excessively large limits.

### Line 27

Repeated `?tags=paper&tags=school` entries become a list; explicit Query avoids body inference.

### Line 28

Finish the signature.

### Line 29

Show the validated limit; absent or empty tags produce an empty list.

### Line 30

This blank line separates logical parts; Python does not execute it.

### Line 31

Describe a creation-style response with HTTP 201.

### Line 32

A BaseModel parameter is read from the JSON body and validated before this function runs.

### Line 33

FastAPI serializes the model. This echo lesson does not persist it.

### Line 34

This blank line separates logical parts; Python does not execute it.

### Line 35

Register a separate scalar-body demonstration.

### Line 36

`embed=True` requires an object with a `percent` key rather than a bare JSON number.

### Line 37

Return the validated percentage.

## Test it: valid and invalid requests

Use `/docs` to supply inputs or execute:

```bash
curl -i 'http://127.0.0.1:8000/products/12?currency=USD'
curl -i 'http://127.0.0.1:8000/products?limit=2&tags=paper&tags=school'
curl -i -X POST http://127.0.0.1:8000/products -H 'Content-Type: application/json' -d '{"name":"Notebook","price_minor":12000}'
```

The first command fetches ID 12 and echoes USD. The second echoes limit 2 and both tags; quoting prevents the shell interpreting `&`. The third chooses POST (`-X`), adds a header (`-H`) and sends a body (`-d`); expect 201 and the supplied product. A real creation implementation arrives in chapter 07.

| Request | Expected result and reason |
|---|---|
| `/products/12` | 200, integer ID 12, default INR |
| `/products/abc` | 422, cannot parse the ID as an integer |
| `/products/0` | 422, integer parses but violates the lower bound |
| `/products/12?currency=EUR` | 422, unsupported value |
| `/products?limit=101` | 422, exceeds the upper bound |
| POST product with `{"name":"","price_minor":-1}` | 422, two field constraints fail |
| POST product with no name | 422, required field missing |
| POST `/discount` with `{"percent":15}` | 200, valid embedded scalar |
| POST `/discount` with `15` | 422, expected the keyed object |

FastAPI's validation response has a `detail` list. Each entry usually includes `loc` (where the problem occurred), `msg` (human explanation) and `type` (error category). Exact wording can vary by library version. A location beginning `body` differs from one beginning `path` or `query`.

## What happens internally?

At registration FastAPI analyzes the parameter names, type hints and source declarations. Per request it extracts raw values, resolves dependencies if any, and asks validation machinery to build the typed arguments. If validation fails, the handler body does not run. If successful, `product_id` is already an `int` and `product` is a `ProductCreate` object. Returning a value starts response processing, not another input parsing pass.

## When to use it / when not to

Use paths for identities and queries for modifiers; use models for structured bodies. Headers are suitable for protocol metadata, not a hiding place for all business data. Cookies are useful for browser state, not a substitute for explicit access checks. Do not put huge filters in a URL; define a documented search-body operation when necessary. Do not use validation alone to decide whether a caller can read product 12.

## Common Mistakes

- Putting `/products/{product_id}` before `/products/featured` can make the variable route capture `featured` and return an integer-validation error.
- `name: str | None` **without** `= None` means required-but-nullable, not omittable.
- A list parameter without explicit `Query()` may be inferred as body data when you intended repeated URL values.
- Writing `product_id: str` and then manually calling `int()` discards automatic error handling; declare `int` from the start.
- An extra JSON key is ignored by Pydantic's default configuration; if unknown fields should fail, use `extra="forbid"` (next chapter).

## Best Practices

Declare bounds, document defaults, avoid unbounded listing and test rejection cases. Treat every input location as untrusted. Consistent resource naming makes the next CRUD chapter easier to navigate.

## Practice

Create `/orders/{order_id}` with a positive integer ID and a query `limit` defaulting to 5, allowed range 1–20. Return both values.

## Expected Result

`GET /orders/8?limit=2` → `{"order_id":8,"limit":2}`. `/orders/0` and `?limit=21` → 422.

## Solution

### File: `examples/practice_inputs.py`

```python
from typing import Annotated
from fastapi import FastAPI, Path, Query
app = FastAPI()
@app.get("/orders/{order_id}")
def order(order_id: Annotated[int, Path(ge=1)], limit: Annotated[int, Query(ge=1, le=20)] = 5):
    return {"order_id": order_id, "limit": limit}
```

Line 1 imports annotation metadata support. Line 2 imports the app and parameter rules. Line 3 instantiates the app. Line 4 registers the route. Line 5 declares the two distinct input sources with bounds. Line 6 returns validated values. Save and run `python -m uvicorn examples.practice_inputs:app --reload`; try the valid/invalid URLs in `/docs`.

## Summary

Input locations are part of the API contract. FastAPI can read and validate them before your business logic runs. Next we make that validation expressive enough for real data.
