# 22 — Performance, monitoring and production practices

[Previous](21-docker-and-deployment.md) · [Course map](./) · [Next](23-reference-and-troubleshooting.md)

## What is performance, and why measure first?

Performance is not a framework slogan. It is how quickly and reliably the whole system serves useful work under a particular load. **Latency** is time per operation; **throughput** is completed operations per time; **concurrency** is work in progress; **capacity** is sustainable load while meeting requirements. Averages can hide bad tails: p95 latency means 95% of observed requests completed within that duration, while the slowest 5% took longer.

A queue grows when arrivals exceed service capacity. Adding async tasks or workers can make the queue larger without increasing database capacity. The best first optimization is often removing unnecessary work: bound queries, fix N+1 loading, avoid repeated client setup, return fewer fields and add an appropriate index.

Measure realistic authenticated operations with realistic data sizes. A hello-world benchmark says little about a write endpoint hashing passwords or joining large tables. Load-test only systems you own or have permission to test, and do not run destructive tests against production by accident.

## Query planning, relationships and eager loading

A **query plan** describes how the database will locate/join/filter rows. An index helps queries whose predicates/order match its structure; it is not a magic accelerator for every query. PostgreSQL's `EXPLAIN` shows a proposed plan; `EXPLAIN ANALYZE` actually executes the operation and measures it, so be especially careful with writes and production load.

The next complete program makes the chapter 11 relationship discussion concrete. It uses SQLAlchemy with an in-memory SQLite database so no external service is needed. `relationship` builds object navigation; `ForeignKey` enforces the stored link when the database enforces foreign keys. `selectinload` explicitly fetches related suppliers without one lazy query per product.

Run `python examples/query_loading.py`.

## Example

### File: `examples/query_loading.py`

```python
from sqlalchemy import ForeignKey, String, create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, selectinload

class Base(DeclarativeBase):
    pass

class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    products: Mapped[list["Product"]] = relationship(back_populates="supplier")

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    supplier: Mapped[Supplier] = relationship(back_populates="products")

engine = create_engine("sqlite://")

@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, record):
    connection.execute("PRAGMA foreign_keys=ON")

try:
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        supplier = Supplier(name="PaperCo")
        session.add_all([Product(name="Pen", supplier=supplier), Product(name="Book", supplier=supplier)])
        session.commit()
    with Session(engine) as session:
        statement = select(Product).options(selectinload(Product.supplier)).order_by(Product.id).limit(10)
        products = session.scalars(statement).all()
        output = [{"name": product.name, "supplier": product.supplier.name} for product in products]
    print(output)
finally:
    engine.dispose()
```

## Code Explanation

### Line 1

Import a referential constraint, text type, engine, connection hooks and SELECT construction.

### Line 2

Import mappings, sessions, object navigation and explicit eager loading.

### Line 3

This blank line separates logical parts; Python does not execute it.

### Line 4

Collect this self-contained demonstration's table metadata.

### Line 5

No custom base behaviour is needed.

### Line 6

This blank line separates logical parts; Python does not execute it.

### Line 7

Map one supplier, which can supply many products.

### Line 8

Name the storage table.

### Line 9

Define stable supplier identity.

### Line 10

Store the supplier's name.

### Line 11

Expose the related product collection; the quoted forward reference names a class defined later.

### Line 12

This blank line separates logical parts; Python does not execute it.

### Line 13

Map products with supplier references.

### Line 14

Name the related table.

### Line 15

Define product identity.

### Line 16

Store a bounded name.

### Line 17

Store/enforce the reference and index lookups by supplier.

### Line 18

Expose object navigation, keeping both in-memory relationship sides coordinated.

### Line 19

This blank line separates logical parts; Python does not execute it.

### Line 20

Use a transient database solely for this query demonstration.

### Line 21

This blank line separates logical parts; Python does not execute it.

### Line 22

Register setup whenever this engine opens a physical connection.

### Line 23

Receive the low-level driver connection and its pool record.

### Line 24

Make SQLite actually enforce declared foreign-key constraints.

### Line 25

This blank line separates logical parts; Python does not execute it.

### Line 26

Always release engine resources after the demonstration.

### Line 27

Create both related tables and declared indexes for this disposable database.

### Line 28

Start one unit of work to seed records.

### Line 29

Construct a parent row object.

### Line 30

Stage children referencing the same parent; normal save-update behaviour also stages that parent.

### Line 31

Persist all related rows in one transaction.

### Line 32

Use a fresh session so earlier tracked instances do not hide loading behaviour.

### Line 33

Fetch a bounded product page plus explicitly loaded suppliers in a separate batched query.

### Line 34

Execute the product query and the eager supplier query.

### Line 35

Read already loaded relationships rather than issuing a lazy query for each product.

### Line 36

The plain dictionaries remain usable after session closure.

### Line 37

Cleanup applies even after an unexpected SQL/model failure.

### Line 38

Release connection resources.

## Expected result and internal query flow

The program prints Pen and Book, each with supplier PaperCo. SQLAlchemy reads up to ten products, gathers their supplier IDs, then loads the suppliers using a bounded additional query. Accessing `product.supplier.name` uses the loaded identity map rather than one query per row. `selectinload` can batch further for very large sets; do not promise exactly two queries for every possible input/database limit.

In an API, put this statement in the repository and declare an explicit nested response model. Read required fields while the session is valid or construct public dictionaries/models before closing it. Choose `joinedload` (loading using SQL joins) when appropriate, but understand row multiplication and the need for result deduplication for collection joins. Eager-loading everything can be expensive too.

## Pagination: offset versus keyset

Offset pagination asks the database to skip N rows. It is easy to understand and supports page-number interfaces, but large offsets can be expensive and concurrent inserts/deletes shift page boundaries. A stable order is mandatory; unordered LIMIT results are not a reliable page contract.

**Keyset/cursor pagination** asks for rows after the last seen ordering key: `WHERE id > last_id ORDER BY id LIMIT page_size`. It often scales better with a matching index. For nonunique ordering, include a tie-breaker such as `(created_at, id)`. A **cursor** in an API is the continuation marker; it differs from a database driver's result iterator. Encode and validate cursor contents, bind them to filters/tenant where needed, and do not treat opaque encoding as authentication.

For a repository using our integer IDs, the query expression is:

```python
statement = select(Product).where(Product.id > last_id).order_by(Product.id).limit(page_size)
```

This is a one-line query **fragment** for the repository, not a separate application. It selects product rows, filters after the last seen ID, applies a deterministic order and bounds output. `last_id`/`page_size` must already be validated and any ownership/filter rules must also be present. It trades arbitrary page-number jumps for efficient continuation.

## Caching and conditional requests

A **cache** stores previously computed/retrieved results for reuse. Use it for expensive repeat reads with acceptable staleness, not as the sole store for irreplaceable data. A **TTL (Time To Live)** limits how long an entry may remain valid. Cache invalidation decides when changed data makes a cached value stale; naming a TTL does not solve all consistency requirements.

A cache key must include everything affecting the result: filters, page, representation version and tenant/user permissions when relevant. Caching private user data under a public URL-only key can leak it to other users. In-process caches are per worker; a shared system such as Redis (an in-memory data service with multiple data structures/persistence options) can coordinate caching across processes, but needs its own capacity/security/failure policy.

**ETag** is an HTTP response validator identifying a representation version. A client sends `If-None-Match`; if unchanged, a server may return 304 with no body. For writes, `If-Match` can implement optimistic concurrency (perform the write only if the caller edited the version still current), returning 412 Precondition Failed on conflict. The version check and update must be atomic in the database; checking in Python then later writing still races.

Use `Cache-Control: private` or `no-store` as appropriate for user/credential data. `public, max-age=...` is for intentionally cacheable public responses, not token endpoints. Avoid caching transient errors as successes. A **cache stampede** occurs when many callers recompute an expired item simultaneously; bounded coalescing/refresh strategies can reduce it without creating one global bottleneck.

## Timeouts, retries, idempotency and overload

Set finite connect/read/write/pool-acquisition timeouts and an overall request/job budget where needed. A timeout is not proof that a remote operation failed to happen. Retry transient failures only when the operation is safe or protected by idempotency; use bounded exponential backoff with jitter (increasing delay plus randomness) to avoid synchronized retry storms.

For POST payment/order creation, an **idempotency key** identifies one intended operation. Persist key + request fingerprint + state/result under a unique constraint. Repeating the same key/body returns the stored result; reusing the key with a different body should conflict. Coordinate concurrent attempts transactionally. An in-memory set disappears on restart and is not a durable payment guarantee.

A **circuit breaker** temporarily stops repeated calls to a failing dependency and probes for recovery. It limits cascading failures but adds state/operational complexity; introduce it only with a clear failure policy. **Load shedding** rejects excess work early (often 429/503) instead of allowing unbounded queues to exhaust the process. Bound thread work, pools, uploads, JSON body size and WebSocket buffers as well as request counts.

## Monitoring and observability: know what is happening

**Monitoring** tracks known signals and alerts on bad conditions. **Observability** means being able to infer internal behaviour from external telemetry, including unfamiliar failures. Three common signals are:

* **Logs:** discrete events, with structured fields such as request ID, operation, status, duration and error category; redact secrets and personal data.
* **Metrics:** aggregated numeric measurements over time, such as request rate, error ratio, latency histograms, queue age and pool wait. A histogram groups observations into buckets so percentiles can be estimated.
* **Traces:** linked timing spans following one request across components/services. A span represents one operation, such as an outgoing HTTP call or database query. OpenTelemetry is a vendor-neutral instrumentation/export standard, not a storage dashboard by itself.

Prometheus is a common metric collection/query system; Grafana commonly visualizes metrics. Error trackers group exceptions and provide diagnostics. Use official maintained integrations, filter sensitive attributes before export, and remember telemetry is another outbound data boundary.

A **metric label** divides measurements by dimension. Use route templates such as `/products/{product_id}`, not every actual ID. Unbounded user IDs/URLs produce high **cardinality** (too many distinct time series), overwhelming storage and exposing sensitive data. Secure telemetry endpoints and avoid exposing internal metrics anonymously to the internet.

An **SLI (Service Level Indicator)** measures a user-relevant property, such as successful requests or latency. An **SLO (Service Level Objective)** is its target over a time window. An **error budget** is the allowed amount of failure under that target. Choose realistic goals, then alert on sustained user impact/budget burn rather than every isolated CPU spike. Define what counts as success: a deliberately returned 404 or rejected invalid login is not automatically a server incident.

## Practical production runbook

A **runbook** is a concrete response procedure for an operational event. For rising p95 latency:

1. Verify the affected routes, time window, request rate and deployment changes.
2. Separate client/proxy/server time; check error ratio, CPU/memory, event-loop lag, thread/pool wait and database slow queries/locks.
3. If only a new release regressed, reduce traffic or roll back a schema-compatible artifact.
4. If an upstream fails, bound waiting/retries and degrade intentionally rather than fan out more requests.
5. Preserve sanitized evidence, communicate impact and verify recovery from the client's perspective.

Backups need restore drills. **RPO (Recovery Point Objective)** is tolerable data loss measured in time; **RTO (Recovery Time Objective)** is tolerable restoration time. A backup job succeeding does not prove either objective. Test restoring into a separate environment and validating record counts/critical workflows.

## When to use / not use; common mistakes and best practices

Optimize demonstrated bottlenecks. Do not add Redis to avoid fixing a bad SQL query or add workers beyond the database connection budget. Do not label server middleware time as complete client latency. Avoid unbounded lists, all-fields serialization, missing indexes, lazy loads in loops, blocking async handlers, retry storms and high-cardinality metrics. Use representative tests and record before/after measurements so an “optimization” is falsifiable.

## Practice

**Beginner:** Run the relationship program and explain why ForeignKey and relationship are both present. **Intermediate:** Design a page after ID 50 with at most 20 rows. **Challenge:** A create-order request times out after commit. Design a retry-safe outcome and name three signals to monitor.

## Expected Result / Solution

Beginner: both products show PaperCo. The foreign key constrains stored references; relationship provides Python navigation and selectinload controls fetching.

Intermediate: use the complete program's fresh read session and replace its statement with `select(Product).where(Product.id > 50).order_by(Product.id).limit(20)`. This two-record seed returns an empty list, correctly, because neither ID exceeds 50. Seed higher IDs if testing nonempty continuation; ordering and bounds remain the same.

Challenge: record a unique idempotency key and request fingerprint with the order/result in a transaction. A retry with the same key/body retrieves the existing result, not another order; changed body conflicts. If downstream effects exist, use an outbox and consumer deduplication. Monitor operation success/error ratio, p95/p99 latency and pending outbox/queue age. Also inspect duplicate/replayed-key counts and database pool wait when diagnosing failures.

## Summary

Production quality means bounded work, safe retries, measured latency, controlled state and evidence-driven operations. FastAPI is one cooperating component in that system.
