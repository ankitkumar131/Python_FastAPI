# 21 — Docker, deployment and the path to a running service

[Previous](20-configuration-logging-security.md) · [Course map](00-course-guide.md) · [Next](22-performance-and-operations.md)

## What is deployment, and why is it more than running Uvicorn?

Deployment puts a particular version of an application into an environment where intended clients can reach it reliably. It includes dependencies, configuration, network policy, persistence, startup, upgrades, monitoring and recovery. A process running on your laptop is not automatically a reliable service.

A **Docker image** is a packaged filesystem/configuration template. A **container** is a running instance with isolated process/filesystem/network boundaries, sharing the host kernel. An image is the recipe; containers are meals prepared from it. Containers are not full virtual machines, not automatically secure and not automatically durable.

A **Dockerfile** describes image build steps. `FROM` selects a base; `WORKDIR` sets a working directory; `COPY` adds files; `RUN` executes build-time commands; `ENV` sets defaults; `USER` selects runtime identity; `CMD` chooses the default process. **Layers** cache filesystem changes, so copying dependency metadata before frequently changing code avoids reinstalling everything on each edit.

A **volume** is storage with a lifecycle separate from an individual container. Without an intentional persistence plan, replacing a container can lose data. Logs normally go to stdout/stderr for collection, not an ever-growing file inside the container.

## Complete local container build for chapter 19

This image runs the **anonymous SQLite catalogue lab**, not the in-memory authentication app. Do not publicly expose writes unchanged. The runtime dependency file includes only packages needed by this project, not every course's MongoDB/password/testing dependency. Direct versions below match the verified package family; reproducible release pipelines should also lock transitive dependencies and pin the base image digest after review.

### File: `requirements-runtime.txt`

```text
fastapi==0.141.1
uvicorn==0.53.0
pydantic==2.13.5
SQLAlchemy==2.0.54
psycopg[binary]==3.3.5
```

Line 1 installs the API framework. Line 2 installs the HTTP/ASGI server. Line 3 pins the validation library. Line 4 pins ORM storage support. Line 5 supplies PostgreSQL connectivity when you configure that database. SQLite needs no extra pip driver. These exact direct pins are a documented tested snapshot, not a recommendation to stop applying security updates.

### File: `.dockerignore`

```text
.git
.venv
**/__pycache__
.pytest_cache
.env
.env.*
*.db
*.db-*
*.log
notes
tests
```

Lines 1–4 exclude repository history, installed local packages and caches. Lines 5–6 keep local environment/secret files out of the build context. Lines 7–9 exclude data/logs. Lines 10–11 exclude teaching/test content from image context. The **build context** is the directory tree Docker can copy from; keeping secrets out matters even if the current Dockerfile does not copy every file.

## Example

### File: `Dockerfile`

```text
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-runtime.txt /app/requirements-runtime.txt
RUN python -m pip install --no-cache-dir -r requirements-runtime.txt
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app && mkdir /data && chown app:app /data
COPY examples/__init__.py /app/examples/__init__.py
COPY examples/catalog /app/examples/catalog
ENV DATABASE_URL=sqlite:////data/catalog.db
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "examples.catalog.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Code Explanation

### Line 1

Start from the supported Python 3.12 slim Linux image; production can pin an audited digest for reproducibility.

### Line 2

Avoid cache-file writes and flush Python output promptly for container log collection.

### Line 3

Make all following relative paths and the runtime working directory explicit.

### Line 4

Copy dependency declarations before app code to preserve the dependency-install cache layer.

### Line 5

Install the selected runtime packages without retaining pip's download cache in the image.

### Line 6

Create an unprivileged runtime identity and a writable data directory without making the whole image writable by that user.

### Line 7

Preserve the outer package import marker required by the module path.

### Line 8

Include the complete catalogue package, not unrelated lesson apps or secrets.

### Line 9

Place the local lab database in an explicit persistent mount location, using SQLite's absolute-path URL form.

### Line 10

Drop root privileges before running the application.

### Line 11

Document the intended container port; this alone does not publish it on the host.

### Line 12

Run Uvicorn directly in exec form so termination signals reach it; no reload and one worker for this SQLite lab.

## Build, run and test: exact commands

Install Docker using its supported instructions for your operating system, start the engine, then run from the repository root:

```bash
docker build -t fastapi-catalog:lesson .
docker volume create fastapi-catalog-data
docker run --name fastapi-catalog -p 127.0.0.1:8000:8000 -v fastapi-catalog-data:/data fastapi-catalog:lesson
```

Line 1 builds an image from the current directory (`.`); `-t` names/tags it. Line 2 creates persistent named storage. Line 3 starts a named container, publishes port 8000 only on local loopback and mounts the volume at the writable data directory. The process remains attached so logs are visible. Open `http://127.0.0.1:8000/docs` and create/read products. If another local server owns port 8000, map `127.0.0.1:8001:8000` and open port 8001 instead.

In another terminal:

```bash
docker logs fastapi-catalog
docker stop fastapi-catalog
docker start fastapi-catalog
```

Logs shows captured output. Stop sends a graceful termination request; Uvicorn can finish in-flight work and exit lifespan subject to time limits. Start restarts the same container. Data should persist in the named volume. Removing a container is separate from removing its volume; never run destructive volume cleanup against valuable data without backup/confirmation.

For a remote preview environment, the application already binds to `0.0.0.0`. Publishing to an accessible preview port may require an environment-specific host mapping instead of loopback. Use the platform's forwarded HTTPS URL; `0.0.0.0` is never a browser URL. Do not make an unauthenticated teaching catalogue internet-writable just to get a screenshot.

## What happens internally?

Docker builds layers, installs packages and copies the package. At runtime it mounts the data volume, starts the exec-form process as user 10001, and Uvicorn imports the app. Lifespan creates the engine/demo schema. The host's published port forwards traffic into the container's port; the server must bind beyond container loopback to receive it. Stopping the container signals the server, which exits lifespan and disposes pools. The separate volume remains.

## Production topology and HTTPS

```text
Browser/mobile/client
  → DNS + HTTPS
  → reverse proxy/load balancer (certificate, size/rate limits, routing)
  → private Uvicorn workers/containers
  → private database and outbound services
```

A **reverse proxy** receives requests on behalf of backend servers; a **load balancer** distributes them across instances. **TLS termination** means the edge handles HTTPS encryption, often forwarding internally over a controlled connection. Re-encrypt internal hops when the threat model requires it. Certificates need automated renewal and expiry monitoring.

A proxy may send `X-Forwarded-For` or `X-Forwarded-Proto` to describe the original client/protocol. Trust those headers only from known proxies, not arbitrary internet clients. Uvicorn's `--proxy-headers` and `--forwarded-allow-ips` configure this trust. Do not set a wildcard unless network isolation guarantees every connection is from trusted infrastructure. Incorrect trust can affect rate limits, generated URLs and secure redirects.

If a proxy removes a prefix such as `/api`, configure ASGI `root_path` appropriately so docs/generated URLs understand the external prefix. This does not register a new route prefix by itself. Test actual externally visible `/docs` and `/openapi.json` URLs, not only local imports.

## Workers, replicas and process supervision

A **worker** is a server process with its own Python memory and pools. Uvicorn can run multiple workers with `--workers N` for suitable deployments; an orchestrator can instead run one process per container and multiple replicas. Do not combine reload and production worker management. No universal worker formula fits every app: memory, CPU, database pool budgets and workload measurements determine the count.

A **process supervisor/orchestrator** restarts failed processes and manages desired instances. More workers do not share dictionaries, WebSocket client lists or in-memory refresh state. Use shared durable storage/pub-sub and idempotent jobs. Avoid a deprecated prebuilt “FastAPI magic workers” image when a small maintained Python image and explicit server command suffice.

## Deployment procedure: a safe repeatable sequence

1. Test/scan dependencies and build a versioned immutable image (immutable means do not silently change the artifact behind an existing release identity).
2. Configure secrets, exact allowed origins, trusted proxies, private database networking and resource budgets outside the image.
3. Back up and verify recovery assumptions. Apply reviewed backward-compatible migrations **once**, separate from worker startup. Replace the lab's create_all lifecycle accordingly.
4. Start new instances and wait for readiness. **Liveness** asks “is this process functioning?” **Readiness** asks “can this instance currently accept useful traffic?” Avoid restarting every instance simply because one shared database briefly fails.
5. Shift traffic gradually, verify real authenticated workflows/metrics, then drain old instances. Draining stops new traffic while allowing current requests/connections a bounded completion period.
6. If metrics degrade, roll back code using an artifact compatible with the new schema. Schema rollback may be destructive; forward repair is often safer. Record who deployed what and when.

## When to use / not use; common mistakes

Containers standardize packaging but are optional; a managed platform or supervised virtual-machine process can also deploy FastAPI correctly. Do not build a container orchestration system for a trivial internal tool without a need. Do not bake `.env` into images, run root unnecessarily, expose databases publicly, assume EXPOSE publishes a port, bind Uvicorn only to container localhost, keep valuable data only in writable container layers, or use `--reload` in production.

## Practice / Expected Result / Solution

**Beginner:** Build the image and GET `/health/live` → `{"status":"ok"}`.
**Intermediate:** Create a product, stop/start the container and read it again. The named volume preserves it.
**Challenge:** Explain why scaling this lab to four workers does not make its authentication lesson production-safe.

The exact build/run commands above are the complete first two solutions. Challenge: this image does not include that auth app; even if composed, four workers would each have independent in-memory user/refresh stores, so login and refresh may hit inconsistent state. Replace state with durable, transactionally coordinated storage before scaling. Production writes also need verified-user/permission dependencies and migration-controlled schema setup.

## Summary

Deployment is controlled operation of a versioned service. Docker packages it; it does not supply correct persistence, permissions, migrations, proxy trust or recovery automatically.
