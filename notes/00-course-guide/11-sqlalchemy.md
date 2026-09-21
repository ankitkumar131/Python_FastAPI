# 11 — SQLAlchemy 2: persistent products and request-scoped sessions

[Previous](10-database-foundations.md) · [Course map](./) · [Next](12-sql-servers-and-migrations.md)

## What is an ORM, and why SQLAlchemy?

**ORM (Object-Relational Mapping)** maps rows to programming-language objects. Instead of unpacking tuples and writing every INSERT, define a mapped class and use instances. SQLAlchemy provides SQL expression tools (**Core**) and an ORM. It does not remove SQL, constraints or the need to understand query cost.

`DeclarativeBase` collects mapped classes. `Mapped[int]` describes a managed typed attribute; `mapped_column` defines storage details; `__tablename__` names the table. Storage models and Pydantic HTTP schemas have different responsibilities. Separating them prevents accidental exposure of every column.

An **engine** holds database/driver configuration and a pool, not one request's transaction. A **Session** tracks ORM objects and coordinates a unit of work. Sessions are mutable and unsafe to share concurrently between requests/tasks. A request commonly borrows its own session from a yield dependency.

`add` stages an object; `flush` sends pending SQL without committing; `commit` commits; `refresh` reloads stored/generated values; `rollback` resets a failed transaction; `close` releases resources. `select(Product)` builds a statement. `session.scalars(statement)` executes and exposes mapped objects. `session.get(Product, id)` looks up a primary key, potentially reusing the session's identity map (its tracked instance cache).

## Installation and lifecycle

`python -m pip install "sqlalchemy>=2,<2.1"` installs the ORM; SQLite's driver is built into Python. Run `python -m uvicorn examples.sqlalchemy_app:app --reload`. Startup creates `products.db` in the working directory; rows survive reload.

**Teaching boundary:** `create_all` creates missing tables, not schema evolution. Production uses migrations. Authentication has not been applied, so do not publicly deploy this demo.

## Example

### File: `examples/sqlalchemy_app.py`

```python
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import CheckConstraint, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("price_minor >= 0", name="ck_products_price"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    price_minor: Mapped[int]

class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)

class ProductPublic(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int

engine = create_engine("sqlite:///./products.db", connect_args={"check_same_thread": False})

def get_session():
    with Session(engine) as session:
        yield session

Db = Annotated[Session, Depends(get_session)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    try:
        yield
    finally:
        engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.post("/products", response_model=ProductPublic, status_code=201)
def create_product(data: ProductCreate, db: Db):
    product = Product(**data.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Product conflicts with stored data") from error
    db.refresh(product)
    return product

@app.get("/products", response_model=list[ProductPublic])
def list_products(db: Db, limit: Annotated[int, Query(ge=1, le=100)] = 10, offset: Annotated[int, Query(ge=0)] = 0):
    return db.scalars(select(Product).order_by(Product.id).offset(offset).limit(limit)).all()

def require_product(product_id: int, db: Session) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product

@app.get("/products/{product_id}", response_model=ProductPublic)
def get_product(product_id: int, db: Db):
    return require_product(product_id, db)

@app.put("/products/{product_id}", response_model=ProductPublic)
def replace_product(product_id: int, data: ProductCreate, db: Db):
    product = require_product(product_id, db)
    product.name = data.name
    product.price_minor = data.price_minor
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Product conflicts with stored data") from error
    db.refresh(product)
    return product

@app.delete("/products/{product_id}", status_code=204, response_class=Response)
def delete_product(product_id: int, db: Db):
    db.delete(require_product(product_id, db))
    db.commit()
    return Response(status_code=204)
```

## Code Explanation

### Line 1

Manage startup and shutdown explicitly.

### Line 2

Attach dependency and query metadata to types.

### Line 3

Import web routing, injection, errors, bounds and no-content output.

### Line 4

Define boundary schemas independently of storage.

### Line 5

Import constraints, column types, engine construction and SELECT expressions.

### Line 6

Recognize expected database constraint failures.

### Line 7

Import typed mapping and unit-of-work sessions.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Collect metadata from mapped subclasses.

### Line 10

No extra base behaviour is needed.

### Line 11

This blank line separates logical parts; Python does not execute it.

### Line 12

Map product instances to stored rows.

### Line 13

Name the SQL table.

### Line 14

Enforce the invariant even for non-API writers.

### Line 15

Declare the integer primary key.

### Line 16

Require a name and enforce uniqueness at the database boundary.

### Line 17

Infer a required integer column.

### Line 18

This blank line separates logical parts; Python does not execute it.

### Line 19

Describe caller-editable data only.

### Line 20

Reject extra keys and trim before length checks.

### Line 21

Require a bounded nonblank name.

### Line 22

Require an actual nonnegative integer.

### Line 23

This blank line separates logical parts; Python does not execute it.

### Line 24

Reuse safe fields in public output.

### Line 25

Allow reading ORM attributes; inherited configuration is merged.

### Line 26

Expose the generated ID only in output.

### Line 27

This blank line separates logical parts; Python does not execute it.

### Line 28

Build a reusable engine; relaxing SQLite thread affinity does not make sessions concurrently shareable.

### Line 29

This blank line separates logical parts; Python does not execute it.

### Line 30

Keep the dependency synchronous to match this driver.

### Line 31

Create a new session and arrange automatic closure.

### Line 32

Lend it to the request; cleanup releases resources and rolls back uncommitted work.

### Line 33

This blank line separates logical parts; Python does not execute it.

### Line 34

Name a reusable annotation, not a shared Session instance.

### Line 35

This blank line separates logical parts; Python does not execute it.

### Line 36

Convert a single-yield function to a lifecycle context.

### Line 37

Perform brief demo setup before serving requests.

### Line 38

Create missing tables only; production migrations are separate.

### Line 39

Ensure graceful cleanup.

### Line 40

Serve requests while the engine is available.

### Line 41

Run during normal shutdown even after an error.

### Line 42

Dispose pooled connections.

### Line 43

This blank line separates logical parts; Python does not execute it.

### Line 44

Connect the lifecycle to this app.

### Line 45

This blank line separates logical parts; Python does not execute it.

### Line 46

Describe durable creation and its public output.

### Line 47

Receive a validated body and request-owned session.

### Line 48

Build a storage object from allowed boundary fields.

### Line 49

Stage the insert without yet claiming durability.

### Line 50

A database uniqueness race can still fail despite application checks.

### Line 51

Flush SQL and commit before sending success.

### Line 52

Valid inputs can still conflict with stored data.

### Line 53

Reset the failed transaction before further use.

### Line 54

Return safe conflict text instead of driver SQL details.

### Line 55

Read generated/stored values such as the ID.

### Line 56

Pydantic reads public attributes and filters output.

### Line 57

This blank line separates logical parts; Python does not execute it.

### Line 58

Expose bounded persistent collection reads.

### Line 59

Validate pagination and borrow a session.

### Line 60

Execute ordered bounded SQL and materialize only the selected objects.

### Line 61

This blank line separates logical parts; Python does not execute it.

### Line 62

A normal helper receives explicit arguments.

### Line 63

Look up the primary key.

### Line 64

Distinguish database absence from type validation.

### Line 65

Translate absence to the API contract.

### Line 66

Return the tracked ORM instance.

### Line 67

This blank line separates logical parts; Python does not execute it.

### Line 68

Register one-resource reads.

### Line 69

Borrow a separate session for this request.

### Line 70

Reuse the lookup rule.

### Line 71

This blank line separates logical parts; Python does not execute it.

### Line 72

Replace the complete editable representation.

### Line 73

Require all create-shaped fields.

### Line 74

Load or fail with 404.

### Line 75

Track a mapped name change.

### Line 76

Track the new price.

### Line 77

Updating a name can violate uniqueness too.

### Line 78

Persist both edits in one transaction.

### Line 79

Catch integrity conflicts, not every programming error.

### Line 80

Restore the session after failed work.

### Line 81

Avoid exposing database internals.

### Line 82

Load committed output values.

### Line 83

Return the public representation.

### Line 84

This blank line separates logical parts; Python does not execute it.

### Line 85

Describe bodyless persistent deletion.

### Line 86

Receive path identity and session.

### Line 87

Load or fail, then stage deletion.

### Line 88

Commit before reporting success.

### Line 89

Send no body.

## Test it

POST `{"name":"Notebook","price_minor":12000}` in `/docs` → 201 with ID. Restart and GET that ID: it remains. Duplicate the name → 409. Negative price → 422 before SQL. PUT a new name/price; DELETE then GET → 404. Use the actual returned ID; a persistent database may already contain rows.

## What happens internally / real-world use

The dependency opens a session. Constructing Product creates a Python object. Add enrolls it in pending changes. Commit generates parameterized SQL and commits the transaction. Refresh reloads values. The response schema reads public fields. Cleanup closes the session and releases its connection back to the reusable engine.

An inventory API can use this pattern. Group stock reservation and order creation in the service's transaction; do not independently commit every helper if the business action must be all-or-nothing.

## Relationships and the N+1 trap

One supplier can have many products. A foreign key stores/enforces the linkage; SQLAlchemy `relationship()` offers object navigation. **Lazy loading** fetches related rows upon attribute access. Reading 100 products then each supplier can issue one list query plus 100 more: the **N+1 query problem**. Eager loading with `selectinload` retrieves related rows in bounded extra queries. We return to query planning in chapter 22.

Do not serialize unloaded relationships after session closure. Async sessions especially require explicit I/O because arbitrary attribute access cannot transparently await. Load the related data your output contract needs, not every relationship recursively.

## Async SQLAlchemy

`create_async_engine`, `async_sessionmaker` and `AsyncSession` support an async-capable driver, with awaits for execution, commit and refresh. Changing only `def` to `async def` in this synchronous example blocks the loop rather than modernizing the database code. Each independent concurrent task needs its own session/unit of work. Synchronous SQLAlchemy remains a valid modern choice.

## When to use / not use; common mistakes

Use ORM mapping for record-oriented application work; SQLAlchemy Core or reviewed SQL can be clearer for specialized bulk queries. Do not load millions of rows to filter them in Python. Avoid global sessions, forgotten commits, missing rollbacks and accidental lazy loads. `check_same_thread` is SQLite-specific, not a PostgreSQL/MySQL setting. `create_all` does not migrate existing columns. Prefer `session.get` and `select` over legacy `session.query(...).get(...)` tutorials.

## Best Practices

Separate schemas from tables, make session ownership explicit, use constraints and commit before success. Keep transactions short and inspect generated SQL when performance surprises you.

## Practice

**Beginner:** Prove persistence by restarting after creation. **Intermediate:** Trigger a duplicate 409, then successfully create a different name. **Challenge:** Add a maximum-price query filter.

## Expected Result / Solution

The complete app already solves the first two tasks: restart preserves IDs; rollback isolates failed writes. For the challenge keep the existing GET collection decorator but replace its function with:

```python
def list_products(db: Db, max_price: Annotated[int, Query(ge=0)] = 100000, limit: Annotated[int, Query(ge=1, le=100)] = 10):
    statement = select(Product).where(Product.price_minor <= max_price).order_by(Product.id).limit(limit)
    return db.scalars(statement).all()
```

Line 1 declares bounded inputs and the dependency. Line 2 builds filtered, ordered, bounded SQL. Line 3 executes it. GET `/products?max_price=3000` returns only matching products; negative max\_price → 422. No imports beyond the complete file are needed.

## Summary

Pydantic controls boundary shape, SQLAlchemy maps objects, the database enforces constraints, and the transaction owns related writes.
