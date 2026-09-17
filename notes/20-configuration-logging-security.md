# 20 — Configuration, environment variables, logging and defensive design

[Previous](19-project-architecture.md) · [Course map](00-course-guide.md) · [Next](21-docker-and-deployment.md)

## Configuration: what is it and why separate it from code?

Configuration changes how the same code runs in different environments: database URLs, allowed frontend origins, timeout values, log level and secrets. Keeping it outside source avoids editing a program to deploy it and reduces accidental credential commits. Think of the same appliance with different safe settings, not a different appliance for every room.

An environment variable is text attached to a process. `bool(os.getenv("DEBUG"))` is a common bug: the nonempty string `"false"` is truthy in Python. **pydantic-settings** provides `BaseSettings`, which loads and validates configuration into typed fields. It is a separate package in Pydantic v2, not `from pydantic import BaseSettings`.

A `.env` file stores local name=value settings. It is **not automatically read by every Python process**; our settings class explicitly enables it. It is not encrypted or a production secret manager. Do not commit real `.env` files. A `.env.example` documents safe placeholders. Environment values normally override dotenv values; explicit constructor arguments have still higher priority under the default source order. Custom settings sources can change that order.

A **secret manager** is a controlled service/storage system providing credentials to authorized deployments, with auditing and rotation. Environment variables are convenient but may still appear in process inspection, crash reports or platform configuration. Limit who can read them and avoid printing complete settings objects.

`SecretStr` reduces accidental disclosure by masking common representations. `.get_secret_value()` deliberately extracts plaintext for the component that needs it. This is not encryption in memory and does not protect against logging the extracted value.

## Complete settings and logging app

**Logging** records diagnostic events. Levels commonly include DEBUG (fine diagnostic details), INFO (normal significant events), WARNING (unexpected but handled conditions), ERROR (operation failure) and CRITICAL (severe service failure). Use a named logger per module and configure handlers/format centrally.

**Structured logging** records named fields, commonly as JSON objects, so tools can search by request ID/status/duration rather than parse prose. The minimal example uses standard text logging to teach configuration; chapter 22 discusses collecting structured telemetry. Never log raw authorization headers, cookies, passwords, refresh tokens or complete sensitive request bodies.

Install `python -m pip install pydantic-settings` if not using the bundle. Run `python -m uvicorn examples.settings_app:app --reload`.

## Example

### File: `examples/settings_app.py`

```python
import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated, Literal
from fastapi import Depends, FastAPI
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="CATALOG_", extra="ignore")
    app_name: str = "Catalogue"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    page_limit: int = Field(default=20, ge=1, le=100)
    webhook_secret: SecretStr | None = None

@lru_cache
def get_settings() -> Settings:
    return Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger(__name__).info("application started")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/info")
def info(settings: Annotated[Settings, Depends(get_settings)]):
    return {"name": settings.app_name, "page_limit": settings.page_limit}
```

## Code Explanation

### Line 1

Use Python's standard event logging system.

### Line 2

Validate/configure the app once per worker at startup.

### Line 3

Cache an immutable-by-convention settings instance rather than reparsing files on every request.

### Line 4

Annotated carries dependencies; Literal restricts text to listed choices.

### Line 5

Create the app and expose a settings provider to routes/tests.

### Line 6

Declare bounds and a masked secret wrapper.

### Line 7

Import Pydantic v2's separate configuration-loading library.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Load declared typed fields from configured environment sources.

### Line 10

Read a local dotenv file, prefix environment names and permit unrelated shared dotenv keys deliberately.

### Line 11

Default a non-secret display name; CATALOG_APP_NAME overrides it.

### Line 12

Parse textual boolean settings correctly, unlike bool(nonempty_string).

### Line 13

Fail early for unsupported logging levels.

### Line 14

Validate configuration bounds just as we validate request bounds.

### Line 15

Optional for this demo; a real required integration should omit the default and fail when missing.

### Line 16

This blank line separates logical parts; Python does not execute it.

### Line 17

Reuse the no-argument provider's result; this is process-level settings caching, not request dependency caching.

### Line 18

Offer one replaceable configuration provider.

### Line 19

Read environment/dotenv and validate before returning a typed object.

### Line 20

This blank line separates logical parts; Python does not execute it.

### Line 21

Attach startup validation/configuration to the app lifecycle.

### Line 22

Run before requests are accepted.

### Line 23

Fail startup if configuration cannot be validated.

### Line 24

Configure a simple handler if logging has not already been configured by the host.

### Line 25

Emit a non-sensitive startup event, not a full settings dump.

### Line 26

Serve requests with validated configuration available.

### Line 27

This blank line separates logical parts; Python does not execute it.

### Line 28

Wire startup to this lesson's app.

### Line 29

This blank line separates logical parts; Python does not execute it.

### Line 30

Expose only explicitly public information.

### Line 31

Inject the same replaceable settings provider into the route.

### Line 32

Do not return the complete model or its secret field.

## File: `.env.example` / exact commands

```dotenv
CATALOG_APP_NAME=Catalogue workshop
CATALOG_DEBUG=false
CATALOG_LOG_LEVEL=INFO
CATALOG_PAGE_LIMIT=20
```

Line 1 changes a non-secret display name. Line 2 selects a parsed false boolean. Line 3 chooses a supported log level. Line 4 selects a bounded integer default page size. The checked-in example also contains comments explaining where other lessons read secrets/URLs; comments do not configure values.

To opt into the local example settings:

```bash
cp .env.example .env
python -m uvicorn examples.settings_app:app --reload
```

`cp` copies the template to the explicitly loaded local filename. In PowerShell use `Copy-Item .env.example .env`. Do not overwrite a real existing .env without preserving its values. After startup `/info` returns the configured name and page_limit, never the optional secret.

Environment override example: `export CATALOG_PAGE_LIMIT=5` in bash, or `$env:CATALOG_PAGE_LIMIT = '5'` in PowerShell, then restart the process. Setting 0, 101 or nonnumeric text fails startup validation. Cached settings do not dynamically reread a modified file; restart, or clear `get_settings.cache_clear()` deliberately in a test. Caching does not make mutable settings objects safe to change from handlers.

## What happens internally?

BaseSettings assembles sources, maps the configured prefix/field names, parses textual values and runs Pydantic validation. The provider caches the result. Lifespan uses it to configure logging; dependencies reuse it. Explicit public output avoids leaking secrets even if a new secret field is added later.

Logging events pass through level filters and handlers to a destination, usually stderr/stdout in containers. Uvicorn has its own access/error loggers; `basicConfig` does not necessarily override a host's existing logging configuration. For production use an explicit central logging configuration and a collector. Logger calls with `%s` arguments defer string formatting; f-strings compute eagerly. Use exception stack traces internally for unexpected failures, but return a generic public error.

## Security: connect protections to actual threats

| Threat / why it matters | Concrete defensive action | Common false assurance |
|---|---|---|
| SQL injection | Bound values, allowlisted sort columns | “We use Pydantic, therefore SQL strings are safe” |
| Object-level access failure | Filter by owner/tenant and check permission on every action | “The user is logged in” |
| Mass assignment (setting protected fields through input) | Separate strict write schemas from ORM models | Passing arbitrary JSON to `setattr` on a user record |
| SSRF (Server-Side Request Forgery) | Fixed/allowlisted outbound destinations, private-network protections, redirect policy | Accepting any URL then fetching it with server credentials |
| Path traversal | Server-generated storage names, controlled directories/access checks | Joining uploads with untrusted `../../...` filenames |
| Credential guessing and resource exhaustion | Distributed rate limits, input/size/concurrency/time bounds | An in-memory counter behind ten independent workers |
| XSS/CSRF | Appropriate browser storage, output handling, CSRF controls, secure cookies | “CORS is enabled, so cookies are safe” |
| Secret leakage | No sensitive logs, least-privilege credentials, rotation, secret storage | Masking one field then logging raw request bodies |
| Supply-chain compromise | Reviewed dependencies, locks, vulnerability scans, minimal images | Installing an unreviewed similarly named package |

**Least privilege** means giving accounts only the actions they require: the application database user need not be a database superuser. **Rate limiting** caps accepted work per interval; a distributed gateway/shared store is usually needed across replicas. Key limits carefully behind proxies—blindly trusting an attacker-supplied forwarded IP lets clients evade limits.

A **threat model** is a written analysis of assets, attackers, trust boundaries and likely failures. Draw browser → proxy → API → database/upstream; identify where untrusted data crosses each boundary and choose a control. Security is not a final decorator.

## When to use / not use; common mistakes and best practices

Use environment settings for deployment differences, not per-user request state. Do not cache a user's token as global configuration. `.env` is useful locally but not a safe artifact to bake into an image. Do not default missing production signing keys to "secret". Do not set debug error pages in production; traces can reveal internals. Avoid full query-string/access logs if your legacy clients put sensitive values in URLs; fix the transport as well as redacting logs.

## Practice

**Beginner:** Set page_limit to 5 and verify `/info`.
**Intermediate:** Set page_limit to 0 and verify startup fails rather than silently using 20.
**Challenge:** Add a required API integration secret without exposing it publicly.

## Expected Result / Solution

The first two tasks use the existing provider and commands above. For the challenge replace `webhook_secret: SecretStr | None = None` with `webhook_secret: SecretStr` and set CATALOG_WEBHOOK_SECRET through a secret-aware deployment mechanism. That declaration requires a value; the existing `/info` return remains the complete safe output solution. A real integration should additionally validate adequate secret strength/format and use `.get_secret_value()` only at the verification boundary. Tests should clear the provider cache before changing environment values.

## Summary

Configuration is validated external input too. Logs should explain failures without becoming a second secret database. Security controls must match concrete trust boundaries.
