# 23 — Version ledger, troubleshooting and final project assessment

[Previous](22-performance-and-operations.md) · [Course map](./) · [Advanced labs](24-advanced-pattern-labs.md)

## Official-source ledger: checked on 2026-09-17

These notes use original explanations and examples. The following official references were consulted for version-sensitive behaviour; they are further reading, not substitutes for the lessons.

| Official reference                                                                                                               | What was checked / where it matters                                                                               |
| -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| [FastAPI: dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)                  | Single-yield cleanup, dependency trees and evolving lifecycle timing; chapter 08                                  |
| [FastAPI: lifespan](https://fastapi.tiangolo.com/advanced/events/)                                                               | Lifespan is preferred over legacy startup/shutdown event decorators; chapter 09                                   |
| [Pydantic: v2 migration](https://docs.pydantic.dev/latest/migration/)                                                            | model\_dump/model\_validate, validator changes, from\_attributes and required/nullable semantics; chapter 05      |
| [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)                                                | Separate settings package, environment reading, prefixes, defaults and configuration sources; chapter 20          |
| [SQLAlchemy 2 ORM quick start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)                                            | DeclarativeBase, Mapped, mapped\_column and select-based queries; chapters 11/22                                  |
| [MongoDB: migration to PyMongo Async](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/) | AsyncMongoClient, async method differences and Motor deprecation date; chapter 13                                 |
| [FastAPI: OAuth2/JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)                                                | PyJWT, pwdlib/Argon2, password verification and bearer dependency mechanics; chapters 14/15                       |
| [FastAPI: testing](https://fastapi.tiangolo.com/tutorial/testing/)                                                               | TestClient and pytest interface; chapter 18                                                                       |
| [Starlette: TestClient](https://starlette.dev/testclient/)                                                                       | Current httpx2 preference, httpx fallback deprecation, context-managed lifespan and WebSocket testing; chapter 18 |

Additional primary references for production decisions and deeper study:

* [OAuth 2.0 Security Best Current Practice, RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html): modern authorization-flow and refresh-token security requirements. The local password-exchange lab is not a recommended new delegated OAuth flow.
* [ASGI specification](https://asgi.readthedocs.io/en/latest/): server/application event contract.
* [Uvicorn settings](https://www.uvicorn.org/settings/): supported server arguments and deployment/proxy options.
* [FastAPI deployment concepts](https://fastapi.tiangolo.com/deployment/concepts/): HTTPS, replication, memory and startup responsibilities.
* [SQLAlchemy async documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html): async engines/sessions, explicit I/O and concurrent-session ownership.
* [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html): revision environments and migration commands.
* [Starlette middleware](https://starlette.dev/middleware/): middleware ordering, CORS wrapping and lower-level ASGI alternatives.
* [OWASP API Security](https://owasp.org/www-project-api-security/): API threat categories, including object-level authorization and resource consumption.

The first table records directly consulted pages; the second is a reading list, not a claim that every linked page was fully audited. Documentation and package releases evolve. Recheck security-sensitive advice during real deployment upgrades.

## Tested dependency snapshot and reproducibility

The authoring sandbox resolved and ran these central versions:

| Component         | Tested version                                                   |
| ----------------- | ---------------------------------------------------------------- |
| Python            | 3.11.2                                                           |
| FastAPI           | 0.141.1                                                          |
| Starlette         | 1.6.0                                                            |
| Pydantic          | 2.13.5                                                           |
| pydantic-settings | 2.15.0                                                           |
| SQLAlchemy        | 2.0.54                                                           |
| Alembic           | 1.20.0                                                           |
| Uvicorn           | 0.53.0                                                           |
| PyMongo           | 4.18.1 (driver import/API only; no real MongoDB integration run) |
| PyJWT             | 2.14.0                                                           |
| pwdlib            | 0.3.1                                                            |
| HTTPX             | 0.28.1 (outbound-client examples)                                |
| httpx2            | 2.13.0 (current Starlette TestClient backend)                    |
| pytest            | 9.1.1                                                            |

`requirements.txt` defines compatible learning ranges. `requirements-tested.lock` records the complete resolved sandbox environment with exact versions. `requirements-runtime.txt` is a deliberately smaller **direct dependency** set for the catalogue Docker lab; it is not a transitive hash-verified production lock.

To reproduce the sandbox package set in a compatible Linux/Python environment:

```bash
python -m pip install -r requirements-tested.lock
python -m pip check
python -m pytest -q
python tools/check_course.py
```

Line 1 installs the recorded versions. Line 2 checks installed dependency consistency. Line 3 executes tests. Line 4 checks note ordering/local links, Python snippet syntax and printed complete Python files against their runnable copies. A freeze snapshot can contain platform-specific packages (for example uvloop); Windows users should install the portable requirement ranges or generate a lock for their platform rather than assuming one environment's freeze is universal.

Python 3.11 is the minimum used syntax family here (`StrEnum`, `Self`, union annotations and built-in generic types). Python 3.12+ is recommended for a new project, and the Dockerfile chooses 3.12. That container was supplied as a buildable lab, **not claimed as a locally executed Docker build**.

### Verification results and honest limits

The original course verification had **18 passing tests**, exercising earlier foundations plus async client lifecycle/error translation, settings parsing/redaction, async SQLite persistence, scoped cross-account access and conditional responses. Tests run without a network listener or real outbound service requests; HTTP calls in the lifecycle tests use a controlled MockTransport.

The subsequent GitBook dashboard/importer adds 16 offline tests; the expanded repository suite passes **34 tests**. Repository-level publishing instructions are in `GITBOOK.md`.

A fresh SQLite Alembic upgrade reached `0001_products`; a second upgrade made no extra schema changes. The relationship, Python prerequisite and password scripts were also run. `pip check` reported no broken requirements. The documentation checker and bytecode/syntax checks are part of the final verification commands.

One warning remains in the installed **Starlette 1.6.0** implementation: its type alias refers to deprecated `anyio.abc.BlockingPortal`. This is upstream library code, not a deprecated pattern taught by these notes; it was not hidden by globally suppressing warnings. The separate deprecated-httpx-backend warning was resolved by installing the officially preferred httpx2.

Real PostgreSQL/MySQL/MongoDB servers, Docker image execution, managed identity-provider integration, public HTTPS/proxy behaviour and production load/restore exercises were **not** executed in this sandbox. Their lessons include commands and expected checks, not invented successful integration results. Before deployment, run those labs against the actual infrastructure and database versions you choose.

## Recognize older tutorials without copying their mistakes

| Older/common pattern                                          | Current course approach / reasoning                                                                            |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Pydantic `.dict()`, `.json()`, `.parse_obj()`                 | `.model_dump()`, `.model_dump_json()`, `.model_validate()`                                                     |
| `class Config: orm_mode = True`                               | `ConfigDict(from_attributes=True)` for reading object attributes                                               |
| `@validator`, `@root_validator`                               | `@field_validator`, `@model_validator` with explicit modes/returns                                             |
| BaseSettings imported from pydantic                           | Import from pydantic\_settings                                                                                 |
| Nullable annotation assumed omittable                         | Add an explicit default when omission is permitted                                                             |
| Startup/shutdown decorators for new apps                      | Lifespan context for paired resource setup/cleanup                                                             |
| Global ORM Session                                            | App-lived engine plus request/unit-of-work session                                                             |
| Legacy query API copied everywhere                            | `select`, `Session.get`, typed SQLAlchemy 2 mappings                                                           |
| Motor for new MongoDB apps                                    | AsyncMongoClient from modern PyMongo                                                                           |
| Passlib/python-jose copied unquestioningly for a new tutorial | Current official FastAPI teaching uses pwdlib/Argon2 and PyJWT; existing deployments need deliberate migration |
| Token signature checked without claim policy                  | Require expiry/subject, verify audience/issuer, constrain algorithm and purpose                                |
| JWT logout claimed to invalidate every existing access token  | State the actual revocation design and residual access lifetime                                                |
| Old test guidance assumes one HTTPX backend indefinitely      | Follow the resolved Starlette-compatible TestClient guidance and test upgrades                                 |

Legacy does not mean every existing app must be rewritten immediately. Understand the migration path, test behaviour and avoid mixing incompatible old/new APIs inside one model graph.

## Troubleshooting: symptom → cause → exact next step

| Symptom                                        | Likely cause                                                              | Diagnosis / correction                                                                                                    |
| ---------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: fastapi`                 | Wrong interpreter/environment                                             | `python -c "import sys; print(sys.executable)"`, then `python -m pip show fastapi`; install through that same interpreter |
| Uvicorn cannot import module                   | Wrong working directory/module target                                     | From repository root run `python -m uvicorn examples.first:app --reload`                                                  |
| Circular import / partially initialized module | Routes import main while main imports routes                              | Move shared resources/contracts into independent modules; do not import main.app in routers                               |
| `Address already in use`                       | Earlier server holds the port                                             | Stop it or use `--port 8001` and update the client URL                                                                    |
| Browser cannot reach remote app                | Bound to loopback or wrong browser host                                   | Bind `--host 0.0.0.0`, use forwarded HTTPS URL; not localhost on the user's separate computer                             |
| 404 despite successful startup                 | Path/method/router not registered                                         | Inspect `/docs` and verify include\_router; `/` is not automatically every resource                                       |
| 405                                            | Path exists with another method                                           | Send the documented method; CORS permission does not create a handler                                                     |
| 307 unexpectedly                               | Trailing-slash redirect                                                   | Use the declared path consistently and inspect redirect Location                                                          |
| 422                                            | Request source/type/constraint mismatch                                   | Read detail.loc; check form vs JSON, path vs query, required vs nullable                                                  |
| Validation fails for response model            | Server returned an invalid public representation                          | Fix the handler/model mapping; do not blame caller input or expose internal traceback                                     |
| Changes disappear on reload                    | In-memory lesson or missing commit                                        | Use persistent storage and commit before success; check actual SQLite path                                                |
| SQLite `no such table`                         | Lifespan not entered or wrong database file                               | Use `with TestClient(app)`; inspect working directory and migration URL                                                   |
| `PendingRollbackError`                         | Session reused after a failed transaction                                 | Roll back expected failures and close sessions reliably                                                                   |
| Detached instance / async lazy I/O error       | Unloaded ORM attributes accessed after lifetime or without explicit await | Eager-load needed relationships and construct the response while resources are valid                                      |
| Coroutine never awaited / not serializable     | Missing await or returning coroutine                                      | Await async work; normal sync results are not awaitables                                                                  |
| API stalls under async load                    | Blocking code on event loop                                               | Replace with async-compatible I/O or deliberately use/offload synchronous handlers                                        |
| Missing JWT\_SECRET startup error              | Configuration intentionally fails closed                                  | Generate a local high-entropy value and provide it to the process; never add a weak fallback                              |
| Token endpoint returns 422                     | JSON sent to a form endpoint                                              | Use form username/password (`data=` in tests), not `json=`                                                                |
| 401 vs 403 confusion                           | Authentication and authorization conflated                                | 401: proof missing/invalid; 403: identity valid but action forbidden; some resource policies conceal with 404             |
| Browser says CORS but curl works               | Browser origin policy or actual server failure without CORS headers       | Inspect network status/preflight, exact scheme/host/port and error response; do not wildcard credentials                  |
| `.env` changes do nothing                      | Not loaded or cached settings                                             | Confirm SettingsConfigDict env\_file, cwd/prefix, environment precedence, then restart/clear test cache                   |
| Docker image runs but is unreachable           | EXPOSE mistaken for publishing or loopback bind inside container          | Publish with `-p` and bind Uvicorn to 0.0.0.0                                                                             |
| Container cannot write SQLite                  | Wrong volume permissions/path                                             | Use the owned `/data` mount and absolute DATABASE\_URL from the Dockerfile                                                |
| Multiple workers see different logins/data     | Process-local dictionary mistaken for shared storage                      | Replace with durable transactional storage; more workers cannot fix the architecture                                      |

Read the final traceback exception, the first relevant line in **your** source, and the operation being attempted. Avoid random dependency upgrades/downgrades without first identifying the incompatible interface.

## Final connected project: assessment rubric

You have completed the course when you can build and explain a catalogue/order API with the following evidence. Use the supplied examples as references, not as an excuse to skip design choices.

### Beginner milestone

* Explain method + route + parameters + handler + serialization for a request without reading definitions aloud.
* Implement create/list/read/replace/patch/delete with clear omission/null semantics, bounded lists and meaningful codes.
* Show valid and invalid nested Pydantic input and prove private fields are excluded from output.

### Intermediate milestone

* Persist products/orders using one chosen database and explain keys, indexes, relationships and a transaction boundary.
* Write/review a migration against existing data rather than recreating the database.
* Authenticate and check both action permission and resource ownership.
* Explain why password hashes, access JWTs and refresh-token digests have different purposes.
* Test errors, rollback, cross-account access, dependency cleanup and token replay.

### Advanced/production-style milestone

* Separate routers, schemas, models, services, repositories, dependencies and configuration where that separation adds clarity.
* Use app-lived engines/clients, request-owned sessions and task-owned resources correctly.
* Choose sync/async based on the full driver stack and measure blocking/pool behaviour.
* Define durable refresh transitions, idempotent business operations and an outbox/worker policy for critical follow-up work.
* Deploy with HTTPS, controlled proxy trust, private databases, least privilege, reviewed migrations, readiness/draining and persistent data.
* Define latency/error SLOs, sanitized logs, bounded-cardinality metrics, traces where useful, and restore objectives with an exercised runbook.

### Challenge and solution strategy

**Challenge:** Two authenticated users attempt to reserve the last product while one client's response times out. Prevent overselling, cross-account access and duplicate orders; preserve a reliable confirmation job.

**Expected result:** At most one successful stock reservation, one stored result per idempotency key/body, no user can read another user's private order, and an eventual retrying worker can deliver confirmation without relying on the web process staying alive.

**Solution strategy:** Validate the request; resolve verified identity; check permission; begin one database transaction; claim a unique idempotency key/request fingerprint; conditionally decrement available stock; create the owner-scoped order and outbox event; store the operation result; commit; return the public order. On an identical retry, return the stored result; on key/body mismatch, conflict. A relay publishes the outbox event, and the consumer deduplicates by event ID. Read/write queries include verified owner/tenant conditions. Tests deliberately race requests and interrupt responses against the actual chosen database. A local Python lock or “async everywhere” cannot replace this design.

This is a design assessment rather than a falsely labelled deployable payment system. The earlier chapters provide the concrete components, and the rubric names the additional concurrency/infrastructure evidence needed for your particular production project.

## Final summary

You are not finished when you can type `@app.get`. You understand FastAPI when you can trace the whole request, explain each validation/security/storage boundary, predict failure behaviour, and prove your choices with tests. Continue consulting official documentation, measuring your own workloads and treating production readiness as an ongoing engineering responsibility.

## Complete learning dependency file

### File: `requirements.txt`

```
fastapi[standard]>=0.121,<1
pydantic>=2.10,<3
pydantic-settings>=2.7,<3
sqlalchemy>=2.0,<2.1
alembic>=1.14,<2
psycopg[binary]>=3.2,<4
pymysql>=1.1,<2
pymongo>=4.13,<5
pyjwt>=2.10,<3
pwdlib[argon2]>=0.2,<1
httpx>=0.28,<1
pytest>=8,<10

httpx2>=2.13,<3
aiosqlite>=0.21,<1
```

The first line installs FastAPI with its standard optional tools, including the server and form parsing. The next two select Pydantic v2 validation and its settings companion. SQLAlchemy is constrained to its stable 2.0 family; Alembic supplies migrations. Psycopg's binary extra and PyMySQL provide PostgreSQL/MySQL drivers. PyMongo supplies BSON and async MongoDB connectivity. PyJWT signs/verifies JWTs; pwdlib's Argon2 extra hashes passwords. HTTPX serves the explicit outbound-client labs; pytest runs tests. The blank line is only spacing. httpx2 supports the current Starlette TestClient backend, and aiosqlite supplies the async SQLite lab driver. Version comparisons bound compatibility families, not security guarantees. Re-resolve and test upgrades regularly, and consult the lock snapshot when reproducing the verified sandbox.
