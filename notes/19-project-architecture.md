# 19 — Project architecture: one request through all the layers

[Previous](18-testing.md) · [Course map](00-course-guide.md) · [Next](20-configuration-logging-security.md)

## Why split a working single file?

A single file is excellent while learning. As the app grows, HTTP parsing, business decisions, SQL and configuration change for different reasons. Splitting by responsibility makes those changes easier to test and review. Think of a shop: reception accepts requests, a manager enforces rules, a stock clerk retrieves records. None needs to duplicate the others' job.

An **APIRouter** is a group of route registrations you can attach to an app with `include_router`. It is not a running server or separate process. `prefix="/products"` adds a path prefix to all its operations; `tags=["products"]` groups them in docs. Router dependencies can enforce shared prerequisites, but sensitive operations still need appropriate action/resource checks.

A **service** coordinates a business operation and owns its transaction boundary. A **repository** encapsulates storage queries; it does not decide HTTP status codes. **Models** represent storage, **schemas** represent external data shapes, and **dependencies** supply request-owned resources. These names are conventions, not magic folders FastAPI scans automatically. Explicit imports and include_router connect the app.

Do not add layers mechanically. If a repository only hides a trivial query and causes more confusion than reuse, a small app can put that query in a service. What matters is explicit ownership and boundaries, not having the most directories.

## Complete project structure

```text
examples/
└── catalog/
    ├── __init__.py
    ├── main.py
    ├── database.py
    ├── models.py
    ├── schemas.py
    ├── repositories.py
    ├── services.py
    └── routes/
        ├── __init__.py
        └── products.py
requirements.txt
```

Both `__init__.py` files are intentionally empty package markers. main creates/composes the app; database supplies sessions; models declares the table; schemas owns allowed input/output; repositories executes queries; services validates operation outcomes/commits; routes connects HTTP to the service.

This catalogue demonstrates persistent create/list/read/replace/delete in a production-style structure. It intentionally does not pretend to be a complete production product: endpoints are anonymous, SQLite is the default, and table creation is for the local lab. Apply chapter 15's identity/permission boundary, chapter 12's migration lifecycle and chapter 21's operational controls before exposing mutations publicly.

## Installation / run

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m uvicorn examples.catalog.main:app --reload
```

The first command installs the full example dependency bundle. The second imports `app` from the package's main module. Do not run `python examples/catalog/main.py` and expect relative imports to behave the same; package imports supply the context for `from .database import ...`.

Open `/docs` to create and retrieve a product. `catalog.db` is created in the current working directory. No other lesson server should occupy port 8000 at the same time.

## Example

### File: `examples/catalog/models.py`

```python
from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "catalog_products"
    __table_args__ = (CheckConstraint("price_minor >= 0", name="ck_catalog_price"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    price_minor: Mapped[int]
```

## Code Explanation

### Line 1

Import storage constraints and a bounded text column type.

### Line 2

Import typed table mapping tools.

### Line 3

This blank line separates logical parts; Python does not execute it.

### Line 4

Collect all catalogue table metadata.

### Line 5

Keep this shared base minimal.

### Line 6

This blank line separates logical parts; Python does not execute it.

### Line 7

Define persistence independently of HTTP.

### Line 8

Use an explicit table name distinct from earlier standalone labs.

### Line 9

Enforce the price invariant for every writer.

### Line 10

Store the generated stable identifier.

### Line 11

Enforce name uniqueness at the database boundary.

### Line 12

Store a required integer amount.

## Example

### File: `examples/catalog/schemas.py`

```python
from pydantic import BaseModel, ConfigDict, Field

class ProductWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)

class ProductRead(ProductWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
```

## Code Explanation

### Line 1

Define public data validation without importing database state.

### Line 2

This blank line separates logical parts; Python does not execute it.

### Line 3

Describe a complete editable representation for create/replace.

### Line 4

Reject caller-controlled extra attributes and normalize edge whitespace.

### Line 5

Require a nonblank name bounded to storage capacity.

### Line 6

Accept only a nonnegative actual integer price.

### Line 7

This blank line separates logical parts; Python does not execute it.

### Line 8

Extend safe input fields with server-generated output data.

### Line 9

Read fields from ORM instances returned by services.

### Line 10

Expose identity in output, never as caller-selected creation state.

## Example

### File: `examples/catalog/database.py`

```python
from typing import Annotated
from fastapi import Depends, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

def make_engine(url: str):
    return create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False} if url.startswith("sqlite:") else {})

def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session

Db = Annotated[Session, Depends(get_session)]
```

## Code Explanation

### Line 1

Define a reusable dependency annotation.

### Line 2

Read app-owned resources and declare request injection.

### Line 3

Build engines with pools for the chosen driver.

### Line 4

Own ORM work per request, not globally.

### Line 5

This blank line separates logical parts; Python does not execute it.

### Line 6

Keep construction configurable for deployment and tests.

### Line 7

Share the engine while applying only driver-appropriate connection options.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Resolve the engine from the running app, allowing multiple isolated app instances in tests.

### Line 10

Create and reliably close one request session.

### Line 11

Lend the session while the request executes; services commit successful writes explicitly.

### Line 12

This blank line separates logical parts; Python does not execute it.

### Line 13

Reuse this annotation in routes without sharing Session instances.

## Example

### File: `examples/catalog/repositories.py`

```python
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Product

class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, product_id: int) -> Product | None:
        return self.session.get(Product, product_id)

    def list(self, limit: int, offset: int) -> list[Product]:
        return list(self.session.scalars(select(Product).order_by(Product.id).offset(offset).limit(limit)))

    def add(self, product: Product) -> None:
        self.session.add(product)

    def delete(self, product: Product) -> None:
        self.session.delete(product)
```

## Code Explanation

### Line 1

Build parameterized SELECT expressions.

### Line 2

Accept an explicitly provided unit of work.

### Line 3

Import the storage model from this package.

### Line 4

This blank line separates logical parts; Python does not execute it.

### Line 5

Encapsulate storage access, without importing HTTP exceptions.

### Line 6

Receive the transaction/session owned by the caller.

### Line 7

Retain it for this repository instance only.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Represent missing data as absence, not an HTTP outcome.

### Line 10

Query the primary key through this session.

### Line 11

This blank line separates logical parts; Python does not execute it.

### Line 12

Accept validated bounds from the caller.

### Line 13

Execute ordered pagination inside SQL, not after reading all rows.

### Line 14

This blank line separates logical parts; Python does not execute it.

### Line 15

Stage insertion without choosing the business commit boundary.

### Line 16

Let the service decide when related changes are committed.

### Line 17

This blank line separates logical parts; Python does not execute it.

### Line 18

Stage a removal inside the caller's unit of work.

### Line 19

Do not commit independently here.

## Example

### File: `examples/catalog/services.py`

```python
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .models import Product
from .repositories import ProductRepository
from .schemas import ProductWrite

class ProductMissing(Exception):
    pass

class ProductConflict(Exception):
    pass

class ProductService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = ProductRepository(session)

    def get(self, product_id: int) -> Product:
        product = self.repo.get(product_id)
        if product is None:
            raise ProductMissing()
        return product

    def save(self, product: Product) -> Product:
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise ProductConflict() from error
        self.session.refresh(product)
        return product

    def create(self, data: ProductWrite) -> Product:
        product = Product(**data.model_dump())
        self.repo.add(product)
        return self.save(product)

    def replace(self, product_id: int, data: ProductWrite) -> Product:
        product = self.get(product_id)
        product.name = data.name
        product.price_minor = data.price_minor
        return self.save(product)

    def delete(self, product_id: int) -> None:
        self.repo.delete(self.get(product_id))
        self.session.commit()
```

## Code Explanation

### Line 1

Translate expected persistence conflicts to domain errors.

### Line 2

Own one operation's transaction through the supplied session.

### Line 3

Construct/update storage objects.

### Line 4

Delegate SQL lookup details to the repository.

### Line 5

Use the validated operation input contract.

### Line 6

This blank line separates logical parts; Python does not execute it.

### Line 7

Describe domain absence without selecting an HTTP status here.

### Line 8

Standard exception behaviour is enough.

### Line 9

This blank line separates logical parts; Python does not execute it.

### Line 10

Describe a conflict with stored data.

### Line 11

Keep the domain type independent of FastAPI.

### Line 12

This blank line separates logical parts; Python does not execute it.

### Line 13

Coordinate product operations and successful transaction boundaries.

### Line 14

Accept a request-owned session, making the dependency explicit and testable.

### Line 15

Keep access to commit/rollback operations.

### Line 16

Ensure repository work participates in this same transaction.

### Line 17

This blank line separates logical parts; Python does not execute it.

### Line 18

Turn storage absence into an operation-level failure.

### Line 19

Ask the repository to query.

### Line 20

Interpret a missing row.

### Line 21

Let the HTTP adapter translate it later.

### Line 22

Return a tracked, existing product.

### Line 23

This blank line separates logical parts; Python does not execute it.

### Line 24

Centralize commit/error handling for create and replace.

### Line 25

Treat integrity conflicts as expected domain failures.

### Line 26

Persist the complete operation before returning success.

### Line 27

Do not accidentally convert unrelated programming/network errors to conflicts.

### Line 28

Restore transaction state after the database rejected the write.

### Line 29

Preserve private exception chaining while exposing a stable domain category.

### Line 30

Reload committed/generated values.

### Line 31

Return the persisted representation.

### Line 32

This blank line separates logical parts; Python does not execute it.

### Line 33

Define the create business operation.

### Line 34

Copy only schema-approved fields to storage.

### Line 35

Stage the row in this session.

### Line 36

Commit once at the operation boundary.

### Line 37

This blank line separates logical parts; Python does not execute it.

### Line 38

Replace an existing product's editable fields.

### Line 39

Enforce existence before mutation.

### Line 40

Set the complete new name.

### Line 41

Set the complete new price.

### Line 42

Persist together and translate expected conflicts.

### Line 43

This blank line separates logical parts; Python does not execute it.

### Line 44

Define deletion as one unit of work.

### Line 45

Resolve existence, then stage deletion.

### Line 46

Commit before the route returns 204.

## Example

### File: `examples/catalog/routes/products.py`

```python
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from ..database import Db
from ..schemas import ProductRead, ProductWrite
from ..services import ProductService

router = APIRouter(prefix="/products", tags=["products"])

def get_service(db: Db) -> ProductService:
    return ProductService(db)

Service = Annotated[ProductService, Depends(get_service)]

@router.post("", response_model=ProductRead, status_code=201)
def create(data: ProductWrite, service: Service, response: Response):
    product = service.create(data)
    response.headers["Location"] = f"/products/{product.id}"
    return product

@router.get("", response_model=list[ProductRead])
def listing(service: Service, limit: Annotated[int, Query(ge=1, le=100)] = 10, offset: Annotated[int, Query(ge=0)] = 0):
    return service.repo.list(limit, offset)

@router.get("/{product_id}", response_model=ProductRead)
def retrieve(product_id: int, service: Service):
    return service.get(product_id)

@router.put("/{product_id}", response_model=ProductRead)
def replace(product_id: int, data: ProductWrite, service: Service):
    return service.replace(product_id, data)

@router.delete("/{product_id}", status_code=204, response_class=Response)
def delete(product_id: int, service: Service):
    service.delete(product_id)
    return Response(status_code=204)
```

## Code Explanation

### Line 1

Attach metadata to query/dependency types.

### Line 2

Import grouped routing, service injection, pagination bounds and response metadata.

### Line 3

Import the request-session annotation from the parent package.

### Line 4

Import public request/response contracts.

### Line 5

Import business coordination, not raw SQL queries.

### Line 6

This blank line separates logical parts; Python does not execute it.

### Line 7

Group related operations under one path prefix and docs tag.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Build a request-local service from the resolved session.

### Line 10

Construct the service without creating another session/pool.

### Line 11

This blank line separates logical parts; Python does not execute it.

### Line 12

Reuse the service dependency across operations.

### Line 13

This blank line separates logical parts; Python does not execute it.

### Line 14

Prefix plus empty suffix gives POST /products.

### Line 15

Keep the route focused on HTTP inputs/output metadata.

### Line 16

Delegate transaction/business work.

### Line 17

Point clients to the created resource.

### Line 18

Apply the public response model.

### Line 19

This blank line separates logical parts; Python does not execute it.

### Line 20

Expose collection retrieval under the same prefix.

### Line 21

Bound caller-selected pagination before storage access.

### Line 22

A simple read needs no extra transaction/business rule wrapper here.

### Line 23

This blank line separates logical parts; Python does not execute it.

### Line 24

Prefix composes the individual-resource path.

### Line 25

Validate identity and resolve the operation service.

### Line 26

Domain absence will be translated by the app's exception handler.

### Line 27

This blank line separates logical parts; Python does not execute it.

### Line 28

Declare full replacement with a public response contract.

### Line 29

Separate path identity from editable body data.

### Line 30

Delegate mutation and commit decisions.

### Line 31

This blank line separates logical parts; Python does not execute it.

### Line 32

Declare successful deletion with no body.

### Line 33

Resolve the service before executing deletion.

### Line 34

Commit or raise before constructing a success response.

### Line 35

Preserve the HTTP no-content contract.

## Example

### File: `examples/catalog/main.py`

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .database import make_engine
from .models import Base
from .routes.products import router
from .services import ProductConflict, ProductMissing

def create_app(database_url: str | None = None) -> FastAPI:
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./catalog.db")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(url)
        app.state.engine = engine
        try:
            Base.metadata.create_all(engine)
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Catalogue workshop", lifespan=lifespan)
    app.include_router(router)

    @app.exception_handler(ProductMissing)
    async def missing(request: Request, error: ProductMissing):
        return JSONResponse(status_code=404, content={"detail": "Product not found"})

    @app.exception_handler(ProductConflict)
    async def conflict(request: Request, error: ProductConflict):
        return JSONResponse(status_code=409, content={"detail": "Product conflicts with stored data"})

    @app.get("/health/live", tags=["health"])
    def live():
        return {"status": "ok"}

    return app

app = create_app()
```

## Code Explanation

### Line 1

Read a deployment-specific database URL without committing credentials.

### Line 2

Own engine startup/shutdown.

### Line 3

Construct the app and type exception-handler context.

### Line 4

Translate domain failures into safe HTTP bodies.

### Line 5

Import configurable storage construction.

### Line 6

Obtain this project's table metadata.

### Line 7

Import route registrations, not another running server.

### Line 8

Map domain error categories to HTTP semantics.

### Line 9

This blank line separates logical parts; Python does not execute it.

### Line 10

An application factory allows independent configured instances in tests/deployment.

### Line 11

Explicit test/config arguments win over environment, with a local demo fallback.

### Line 12

This blank line separates logical parts; Python does not execute it.

### Line 13

Create a lifecycle specific to this app instance.

### Line 14

Allocate resources only when the app starts, not on module import.

### Line 15

Build one engine/pool for this worker.

### Line 16

Make it available to request-session providers.

### Line 17

Ensure disposal even if setup/serving fails.

### Line 18

Local lab only: replace with a separate Alembic deployment step for production.

### Line 19

Serve requests after setup completes.

### Line 20

Release pools on graceful shutdown.

### Line 21

Do not leave this app's engine owned by a stale test/process.

### Line 22

This blank line separates logical parts; Python does not execute it.

### Line 23

Create the configured ASGI application.

### Line 24

Register the product group's routes on this app.

### Line 25

This blank line separates logical parts; Python does not execute it.

### Line 26

Select the domain-to-HTTP mapping for missing products.

### Line 27

Receive framework-supplied context without exposing exception details.

### Line 28

Produce a stable public outcome.

### Line 29

This blank line separates logical parts; Python does not execute it.

### Line 30

Select the mapping for expected storage conflicts.

### Line 31

Keep HTTP concerns out of the repository/service.

### Line 32

Avoid leaking database constraint/SQL text.

### Line 33

This blank line separates logical parts; Python does not execute it.

### Line 34

A cheap process-liveness endpoint, not a claim that all dependencies work.

### Line 35

Do not query every remote dependency for liveness.

### Line 36

Let a process monitor verify that requests are being served.

### Line 37

This blank line separates logical parts; Python does not execute it.

### Line 38

Give tests/server the completely composed app instance.

### Line 39

This blank line separates logical parts; Python does not execute it.

### Line 40

Expose the conventional import target; lifespan has not run yet.

## Follow one real request through the complete system

POST `/products` sends JSON. Uvicorn receives it. FastAPI resolves `get_service` → `get_session`, validates ProductWrite and calls the route. The route delegates to ProductService. The service creates a mapped object, repository stages it and service commits. The database enforces constraints and supplies the ID. The route sets Location and returns an ORM object. ProductRead reads its attributes and serializes public JSON. The session closes after use; the engine survives for other requests.

Duplicate name raises IntegrityError → service rolls back and raises ProductConflict → the app's handler returns 409. A malformed body fails earlier with 422 and never reaches service creation logic. GET missing ID becomes repository None → ProductMissing → 404. Notice how each layer speaks in the terms appropriate to its job.

## Authentication integration boundary

Do not blindly import the chapter 15 global app and expect its routes/lifespan to appear here. In a real composition, turn auth routes into an APIRouter, replace its in-memory storage with durable account/refresh repositories, supply signing configuration in this app's lifespan/settings, and apply its verified-user/permission dependencies to catalogue mutations. `include_router` registers routes; it does not merge arbitrary apps' resources or security policy automatically. Mounting a sub-application is a different ASGI composition with its own OpenAPI/routing boundaries.

## When to use / not use; common mistakes and best practices

Use this structure once responsibilities begin changing independently. Do not create a dependency cycle such as main importing routes that import main.app. Shared contracts/resources should live in modules both can import without constructing another app. Avoid importing an ORM class under the same unqualified name as a Pydantic schema; `ProductWrite`, `ProductRead` and Product make responsibilities clear.

Repository methods stage/query; service methods own business transactions. Do not commit inside every repository method if several changes form one operation. Do not pretend every simple read requires five abstraction layers: this example deliberately delegates listing directly to the repository. Keep architecture useful, not ceremonial.

## Practice

**Beginner:** Add an `/about` route in main reporting this service's name.
**Intermediate:** Explain which layer should map ProductMissing to 404.
**Challenge:** Add stock reservation plus order creation without committing half the operation.

## Expected Result / Solution

Inside create_app, before `return app`, add:

```python
    @app.get("/about")
    def about():
        return {"service": "catalogue"}
```

Line 1 registers against this factory-created app. Line 2 declares the handler. Line 3 returns JSON-compatible data. `/about` returns 200 and the service name. The HTTP adapter/exception handler owns the 404 mapping; repositories should remain useful to non-HTTP callers. For the challenge, one service owns one session/transaction, performs a concurrency-safe stock change and stages the order, then commits once; any failure rolls back both. A remote payment requires an explicit workflow/outbox design, not a longer local transaction.

## Summary

Architecture is a map of responsibilities and lifetimes. The whole request remains understandable when each layer does one explainable job.
