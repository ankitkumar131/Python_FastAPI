# 05 — Pydantic: building trustworthy data shapes

[Previous](04-routing-and-inputs.md) · [Course map](00-course-guide.md) · [Next](06-responses-and-errors.md)

## What is it, and what problem does it solve?

Pydantic is a library that turns declared Python types and rules into runtime data validation and serialization. Imagine a quality-control desk: it checks every parcel's labels before the warehouse accepts it. Without a model, every endpoint repeats “does name exist, is price an integer, is the address complete?” and eventually the rules disagree.

**BaseModel** is the parent class providing this machinery. A **field** is a named, typed attribute on a model. A model is not a database table; creating one validates data in memory. It neither inserts rows nor proves authorization.

**Type coercion** is conversion between compatible representations. In normal non-strict validation an integer field can accept `"42"` and produce `42`. This can be convenient for external data but surprising at a strict boundary. `Field(strict=True)` asks for the proper input type rather than that conversion. Constraints like `ge=0` apply in addition to the type. Do not assume Pydantic accepts every imaginable conversion; write tests for your contract.

## Required, nullable and defaulted are different questions

| Declaration | May the key be omitted? | May its value be null? |
|---|---|---|
| `name: str` | No | No |
| `name: str = "Unknown"` | Yes | No |
| `name: str | None` | No | Yes |
| `name: str | None = None` | Yes | Yes |

A default answers “what if the key is absent?” Nullability answers “is an explicit null allowed?” This distinction becomes critical in PATCH: omitted means leave unchanged, while explicit null may mean clear a field. `Optional[str]` is another spelling of `str | None`; it does not imply a default in Pydantic v2.

Use `Field(default_factory=list)` for a fresh collection per instance. Although Pydantic handles many mutable defaults safely, factories state the intention explicitly and generalize to ordinary Python code. Model defaults are not all validated by default; set `validate_default=True` when defaults must pass the same rules.

## Nested structures, collections and enums

A nested model is a field whose type is another model, like an address inside a supplier. Validation descends into that object. `list[str]` checks every member; `dict[str, int]` checks keys and values. A **string enumeration** lists named allowed choices, such as `draft` or `active`; it prevents inconsistent spellings and improves generated docs.

A **field validator** handles a rule for one field. A **model validator** handles relationships between fields. Run “before” validators on raw input only when you need normalization before ordinary validation; run “after” validators on already validated values. Validators should be deterministic and fast. Querying a database inside one mixes data-shape checks with I/O and makes both tests and async behaviour harder.

## Complete example: run without a web server

Run `python examples/pydantic_models.py` after installing chapter 03's packages. This demonstrates that Pydantic works independently of FastAPI.

## Example

### File: `examples/pydantic_models.py`

```python
from enum import StrEnum
from typing import Self
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

class State(StrEnum):
    draft = "draft"
    active = "active"

class Supplier(BaseModel):
    name: str = Field(min_length=1)
    city: str

class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)
    sale_price_minor: int | None = Field(default=None, ge=0, strict=True)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    stock_by_city: dict[str, int] = Field(default_factory=dict)
    supplier: Supplier
    state: State = State.draft

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value

    @model_validator(mode="after")
    def valid_sale(self) -> Self:
        if self.sale_price_minor is not None and self.sale_price_minor > self.price_minor:
            raise ValueError("Sale price cannot exceed regular price")
        return self

if __name__ == "__main__":
    product = ProductCreate.model_validate({"name": " Pen ", "price_minor": 2000, "supplier": {"name": "PaperCo", "city": "Pune"}})
    print(product.model_dump(mode="json"))
    print(product.model_dump_json())
    try:
        ProductCreate.model_validate({"name": "Pen", "price_minor": "2000", "supplier": {"name": "PaperCo"}})
    except ValidationError as error:
        print(error.errors())
```

## Code Explanation

### Line 1

Import Python's enumeration type whose members also behave as strings.

### Line 2

Self describes an instance of the class containing this annotation.

### Line 3

Import model building, configuration, constraints, error reporting and two validation decorators.

### Line 4

This blank line separates logical parts; Python does not execute it.

### Line 5

Define the finite set of allowed catalogue states.

### Line 6

One allowed string value, accessible as State.draft.

### Line 7

The other allowed value; strings such as published are rejected.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Describe a nested JSON object rather than leaving its structure unspecified.

### Line 10

Require a nonempty supplier name.

### Line 11

Require a city string; no default means this key cannot be omitted.

### Line 12

This blank line separates logical parts; Python does not execute it.

### Line 13

Define the external input contract for a product.

### Line 14

Reject unexpected top-level keys and validate default values as well.

### Line 15

Require a bounded name; whitespace-only text is handled below.

### Line 16

Accept a nonnegative integer, not a numeric string or boolean.

### Line 17

Allow omission or null; a supplied integer must be nonnegative.

### Line 18

Missing and explicit null are both allowed here.

### Line 19

Allocate a separate list for each product and validate every member as text.

### Line 20

Validate a string-to-integer mapping; negative stock is not prohibited by this type alone.

### Line 21

Require an object satisfying Supplier's own rules, including its city field.

### Line 22

Default to draft and otherwise accept only enum choices.

### Line 23

This blank line separates logical parts; Python does not execute it.

### Line 24

Register a rule applied after ordinary validation of name.

### Line 25

Receive the model class as cls instead of requiring an existing product instance.

### Line 26

Pydantic supplies the already validated string as value.

### Line 27

Remove whitespace at both ends.

### Line 28

An all-whitespace name becomes empty after stripping.

### Line 29

ValueError is translated into a structured validation error.

### Line 30

Validators must return the accepted or normalized field value.

### Line 31

This blank line separates logical parts; Python does not execute it.

### Line 32

Run this cross-field rule after the complete model has been validated.

### Line 33

self is the validated product; return the same model instance on success.

### Line 34

Only compare a supplied sale price, and reject a sale higher than the regular price.

### Line 35

Report a model-level rule failure.

### Line 36

Preserve the validated instance; forgetting this return breaks the contract.

### Line 37

This blank line separates logical parts; Python does not execute it.

### Line 38

Execute the demonstration only when this file is run, not when its models are imported elsewhere.

### Line 39

Validate a Python dictionary, fill defaults and normalize the name.

### Line 40

Produce a Python dictionary with JSON-compatible values, including the enum's string value.

### Line 41

Serialize directly to JSON text, useful outside a FastAPI return value.

### Line 42

Intentionally test invalid data without ending the demonstration.

### Line 43

A strict integer rejects the string and the nested supplier lacks city.

### Line 44

Catch Pydantic's structured error rather than a web-specific HTTP error.

### Line 45

Print individual errors with locations such as price_minor and supplier.city.

## Test matrix: do not test only the happy path

Start with this valid base input:

```json
{"name":"Pen","price_minor":2000,"supplier":{"name":"PaperCo","city":"Pune"}}
```

It produces name `Pen`, price 2000, sale/description null, empty tags/stock and draft state.

| Change to the base input | Valid? / explanation |
|---|---|
| Name `" Pen "` | Yes; normalized to `"Pen"` |
| Name `"   "` | No; custom field validator rejects blank text |
| Price `"2000"` or `true` | No; strict integer prevents coercion |
| Price `-1` | No; lower-bound failure |
| Description omitted or null | Both valid, default is null |
| Supplier missing `city` | No; nested required-field error |
| Tags `["school","blue"]` | Valid list of strings |
| Tags `[{}]` | Invalid list member type |
| Stock `{"Pune":3}` | Valid typed dictionary |
| Stock `{"Pune":"many"}` | Invalid integer value |
| State `"active"` / `"published"` | First valid, second not in enum |
| Sale price 2500 | Invalid cross-field relationship |
| Extra top-level `admin: true` | Invalid because `extra="forbid"` |

The Supplier model has its own configuration; the parent's `extra="forbid"` is not a blanket rule on every independent nested model. Add its own configuration if you want strict unknown-key handling there too.

## Serialization, deserialization and request/response models

- `ProductCreate.model_validate(data)` validates Python data.
- `ProductCreate.model_validate_json(text)` parses JSON text and validates it. Bad JSON raises a validation error too.
- `product.model_dump()` yields Python data, potentially retaining types such as enum objects.
- `product.model_dump(mode="json")` yields JSON-compatible Python values.
- `product.model_dump_json()` yields JSON **text**. Usually do not return this string from an endpoint; return the model.
- `model_dump(exclude_unset=True)` includes only fields explicitly supplied. This is useful for PATCH; it is not the same as `exclude_none=True`, which would discard an intentional null.
- `ConfigDict(from_attributes=True)` permits reading fields from object attributes, such as SQLAlchemy row objects, rather than only mappings.

A **request model** describes what callers may send. A **response model** describes what callers may receive. They should differ when input contains passwords, internal flags or fields generated by the server. Never reuse a registration model containing a password as the public user response merely to avoid defining another class.

### Connect the same model to FastAPI

Save `examples/pydantic_api.py`:

```python
from fastapi import FastAPI
from examples.pydantic_models import ProductCreate
app = FastAPI()
@app.post("/products", response_model=ProductCreate)
def create(product: ProductCreate):
    return product
```

Line 1 imports the web framework. Line 2 reuses our complete model, not a duplicated set of rules. Line 3 creates the app. Line 4 registers the operation and its output contract; this particular model contains no secret fields. Line 5 declares body validation. Line 6 echoes validated data. Run `python -m uvicorn examples.pydantic_api:app --reload` and submit every test-matrix variant in `/docs`. Valid input returns 200; invalid input returns 422 before the handler runs. This is still an echo demo, not database creation.

## What happens internally?

At class creation Pydantic builds a schema from annotations and configuration. Its core validation engine uses that schema to traverse values, perform allowed conversions, collect structured errors and create model instances. “Before” validators can transform raw input; core validation establishes types; “after” validators inspect validated values. FastAPI integrates these rules with input locations and OpenAPI. Output serialization walks the declared schema to create the response representation.

## When to use / when NOT to use

Use models at external boundaries and for clear internal data contracts. Do not revalidate every local variable on every line without a reason. Do not use `model_construct()` on untrusted input: it bypasses validation. `model_copy(update=...)` does not validate supplied updates as a fresh model construction would; chapter 07 validates merged data explicitly.

Use custom validators for rules such as “sale price must be lower.” Do not use them for current-user permissions, remote calls or database uniqueness: those depend on runtime context and concurrency. Database unique constraints remain necessary even if a preliminary application check passes.

## Common Mistakes / current versus older tutorials

Pydantic v2 uses `model_dump`, `model_validate`, `field_validator`, `model_validator`, and `ConfigDict`. Older tutorials may show `.dict()`, `.parse_obj()`, `@validator`, `@root_validator` and `class Config: orm_mode = True`. Read those as migration clues, not the patterns for this course. Settings moved to `pydantic-settings` (chapter 20).

Forgetting to return a value from a validator, assuming a nullable field may be omitted, mixing v1/v2 nested models, and believing validation is authentication are common errors. Output validation failures indicate server bugs and should not expose internal data to the caller.

## Best Practices

Use separate create/update/public models, narrow types and meaningful constraints. Avoid accepting arbitrary dictionaries where a schema is known. Keep validation errors useful without echoing passwords into custom logs. Test defaults, omission, null, extra keys and nested failures separately.

## Practice

**Beginner:** Create an Address requiring `city` and a six-digit postal code string (leading zeroes must survive).

**Intermediate:** Reject unexpected address keys.

**Challenge:** Ensure a city containing only whitespace fails, but trim valid surrounding spaces.

## Expected Result

`{"city":" Pune ","postal_code":"411001"}` → city `Pune`. A five-digit code, blank city or extra `admin` key fails.

## Solution

### File: `examples/practice_address.py`

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator
class Address(BaseModel):
    model_config = ConfigDict(extra="forbid")
    city: str
    postal_code: str = Field(pattern=r"^[0-9]{6}$")
    @field_validator("city")
    @classmethod
    def clean_city(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("City cannot be blank")
        return value
print(Address(city=" Pune ", postal_code="411001").model_dump())
```

Line 1 imports the model tools. Line 2 declares the model. Line 3 forbids unknown keys. Line 4 requires text. Line 5 requires exactly six ASCII digits; the `r` prefix creates a raw Python string, useful for patterns. Lines 6–7 register a class-level validator. Line 8 declares its signature. Line 9 trims, lines 10–11 reject blank, and line 12 returns normalized text. Line 13 validates and prints. Save and run `python examples/practice_address.py`; then try the invalid inputs above and observe `ValidationError`.

## Summary

A model states what data means before business logic uses it. Next we will make the outgoing contract just as explicit as the incoming one.
