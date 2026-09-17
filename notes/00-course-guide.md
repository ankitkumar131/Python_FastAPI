# FastAPI: from your first request to a production-style backend

Welcome! We will build a small product catalogue, then learn how to protect and deploy APIs. You do not need previous FastAPI experience. Read in order, run the examples, deliberately send bad input, and do the exercises before looking at their solutions.

The repository's root `README.md` preserves the original course brief. This file is the course entrance.

## Reading order

| Chapter | What you will understand |
|---|---|
| [01 — Python prerequisites](01-python-prerequisites.md) | Functions, types, classes, imports, exceptions, contexts, generators |
| [02 — The web and HTTP](02-web-http-rest.md) | Backend, API, REST, URLs, methods, JSON, headers, status codes, CRUD |
| [03 — FastAPI and your first application](03-fastapi-first-application.md) | Installation, framework choices, ASGI stack, Uvicorn, generated documentation |
| [04 — Routes and request inputs](04-routing-and-inputs.md) | Path/query/header/cookie/body inputs and validation |
| [05 — Pydantic in depth](05-pydantic.md) | Required/nullable fields, nested data, validators, serialization |
| [06 — Responses and errors](06-responses-and-errors.md) | Public schemas, HTTP status, exceptions, handlers, custom responses |
| [07 — Complete in-memory CRUD](07-crud.md) | Create/read/replace/patch/delete and resource lifecycle |
| [08 — Dependencies](08-dependencies.md) | Reuse, sub-dependencies, caching, cleanup and scopes |
| [09 — Async and lifespan](09-async-and-lifespan.md) | Event loop, blocking work, async clients, resource lifetime |
| [10 — Database foundations](10-database-foundations.md) | SQL, NoSQL, tables, transactions, relationships, pools |
| [11 — SQLAlchemy](11-sqlalchemy.md) | Persistent CRUD, typed mappings, sessions and rollback |
| [12 — SQL servers and migrations](12-sql-servers-and-migrations.md) | PostgreSQL, MySQL, drivers, Alembic and schema evolution |
| [13 — MongoDB](13-mongodb.md) | Documents, async PyMongo, ObjectId and bounded queries |
| [14 — Authentication foundations](14-authentication-foundations.md) | Identity, passwords, registration, sessions, threats |
| [15 — Tokens and permissions](15-tokens-and-authorization.md) | JWT, OAuth2, bearer access, refresh rotation, roles and ownership |
| [16 — Middleware and CORS](16-middleware-and-cors.md) | Cross-cutting request processing and browser-origin rules |
| [17 — Files, jobs and WebSockets](17-files-jobs-websockets.md) | Multipart input, streaming, background work and live communication |
| [18 — Testing](18-testing.md) | Pytest, TestClient, overrides, isolation and integration tests |
| [19 — Project architecture](19-project-architecture.md) | Complete router → service → repository → database project |
| [20 — Configuration, logging and security](20-configuration-logging-security.md) | Validated settings, secrets, logs and defensive design |
| [21 — Docker and deployment](21-docker-and-deployment.md) | Images, containers, deployment, HTTPS, workers and backups |
| [22 — Performance and operations](22-performance-and-operations.md) | Measurement, indexes, caching, monitoring and production exercises |
| [23 — Reference and troubleshooting](23-reference-and-troubleshooting.md) | Source ledger, version differences, error diagnosis and final project rubric |
| [24 — Advanced pattern labs](24-advanced-pattern-labs.md) | Complete async SQL, scope/ownership and conditional-GET extensions |

## How examples work

Each chapter states which file to run. Standalone examples **do not share an app**. `examples/first.py` and `examples/inputs.py` are separate lessons, not two files to paste into one application. The architecture chapter is the explicitly connected multi-file project. Its complete files are both printed in the notes and present under `examples/catalog/`.

Run repository commands from the repository root unless instructed otherwise. `python -m uvicorn examples.first:app --reload` means import `app` from `examples/first.py`. The local URLs in lessons refer to **your own computer**. In a remote development environment bind to `0.0.0.0` and open the environment's forwarded HTTPS URL instead. Never put a server's `localhost` address into browser code running on another computer.

Python code uses Python 3.11+ syntax and modern library APIs; Python 3.12+ is recommended for a fresh project. The sandbox verification used Python 3.11.2; the supplied container selects Python 3.12 and is not claimed as a locally tested image. Version-sensitive guidance was checked against official documentation on **2026-09-17**; the source ledger is in chapter 23. Dependency ranges select stable releases rather than claiming a particular patch will always be newest. A tested package snapshot is supplied separately after validation. Do not upgrade production dependencies blindly.

## A recurring mental model

```text
Client chooses method + URL + headers + optional body
  → HTTP server receives bytes
  → route identifies operation
  → dependencies and input validation prepare arguments
  → endpoint coordinates business rules and data access
  → response schema validates/filters output
  → response is encoded and sent back to client
```

Each arrow will become concrete. Validation is checking shape and constraints; it is not permission checking. A correctly shaped product ID may still belong to someone else. Similarly, writing a database model does not automatically create a secure API.

## Learning milestones

1. After chapter 06, explain every line of a small API without memorizing it.
2. After chapter 13, persist data and explain what survives a restart.
3. After chapter 18, authenticate callers and prove both success and rejection with tests.
4. After chapter 22, structure and deploy a service while naming what can fail.

### Honesty about production

An in-memory dictionary, local SQLite file, or toy login is useful for learning, not a claim of production readiness. Every such boundary is marked. Production also requires operational decisions: account recovery, legal/privacy requirements, distributed concurrency, incident response and restore testing. The course teaches these boundaries instead of hiding them behind a working `/docs` page.
