# 18 — Testing: prove the contract instead of hoping it works

[Previous](17-files-jobs-websockets.md) · [Course map](./) · [Next](19-project-architecture.md)

## What is a test, and why do we need it?

A test executes code and checks a specific expected result. Manual `/docs` experiments teach behaviour, but they are difficult to repeat after every change. Automated tests make the API contract executable. Think of a checklist a machine can rerun without forgetting the negative cases.

A **unit test** isolates a small rule/function. An **integration test** checks components working together, such as SQLAlchemy and a real PostgreSQL server. An **API test** sends requests through the app boundary. An **end-to-end test** includes the real deployed stack and client path. A TestClient test is valuable but does not prove reverse-proxy configuration, TLS, network behaviour or all streaming timing.

**pytest** discovers functions named `test_*` in matching files and reports assertions. An **assertion** says a condition must be true; if false, the test fails. A **fixture** supplies reusable setup/cleanup, such as a temporary database or client. `yield` fixtures have setup before yield and cleanup afterwards. **Isolation** means tests do not depend on another test's leftovers or real user data.

**TestClient** provides a synchronous HTTPX-style interface to an ASGI app without opening a network port. `with TestClient(app)` starts/stops lifespan, so shared clients/engines exist just as during server operation. Merely constructing TestClient without its context does not reliably exercise lifespan. Tests should not require a running Uvicorn server.

## Current testing-library compatibility

The checked Starlette 1.6 documentation and runtime prefer **httpx2** for TestClient; fallback to plain httpx is deprecated there. The FastAPI testing page still demonstrates httpx. The full requirements therefore install httpx2 for modern TestClient and retain httpx for the explicitly taught outbound-client/MockTransport examples. Test code still imports `TestClient` from FastAPI; do not change it to an invented FastAPI-specific client. Let FastAPI declare its compatible Starlette range instead of pinning an incompatible Starlette independently. Chapter 23 records the exact tested versions and one remaining upstream warning.

## Installation and execution

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m pytest tests/test_auth.py -q
```

Line 1 installs dependencies. Line 2 runs all tests quietly (`-q`). Line 3 runs only authentication tests. Run from the repository root. Pytest's temporary-path fixture creates files outside the production database path and removes them according to its retention policy.

The authentication tests supply a deterministic **test-only** key and reset the in-memory store. Never use that key for a real deployment. They test token behaviour, not whether a production secret is configured correctly.

## Complete API tests for earlier lessons

The following files are included and runnable. The architecture chapter's tests import its supplied app factory; you can read that chapter's implementation next if the factory is new to you. A factory is simply a function creating a new app with chosen configuration.

## Example

### File: `tests/test_basics.py`

```python
from itertools import count
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from examples import crud, dependencies, inputs, io_features, middleware, responses
from examples.first import app as first_app
from examples.pydantic_models import ProductCreate

@pytest.fixture
def crud_client():
    crud.store.clear()
    crud.ids = count(1)
    with TestClient(crud.app) as client:
        yield client
    crud.store.clear()

def test_first_and_input_validation():
    with TestClient(first_app) as client:
        assert client.get("/").json() == {"message": "Hello World"}
    with TestClient(inputs.app) as client:
        assert client.get("/products/featured").status_code == 200
        assert client.get("/products/abc").status_code == 422
        assert client.get("/products?limit=101").status_code == 422
        assert client.post("/discount", json={"percent": 15}).json() == {"percent": 15}
        assert client.post("/discount", json=15).status_code == 422

def test_pydantic_rules():
    data = {"name": " Pen ", "price_minor": 2000, "supplier": {"name": "PaperCo", "city": "Pune"}}
    assert ProductCreate.model_validate(data).name == "Pen"
    with pytest.raises(ValidationError):
        ProductCreate.model_validate({**data, "price_minor": "2000"})
    with pytest.raises(ValidationError):
        ProductCreate.model_validate({**data, "sale_price_minor": 3000})

def test_crud_lifecycle(crud_client):
    client = crud_client
    created = client.post("/products", json={"name": "Pen", "price_minor": 2000, "description": "Blue"})
    assert created.status_code == 201
    assert created.headers["location"] == "/products/1"
    patched = client.patch("/products/1", json={"description": None})
    assert patched.json()["price_minor"] == 2000
    assert patched.json()["description"] is None
    assert client.patch("/products/1", json={"name": None}).status_code == 422
    assert client.put("/products/1", json={"price_minor": 3000}).status_code == 422
    assert client.put("/products/1", json={"name": "Book", "price_minor": 3000}).status_code == 200
    deleted = client.delete("/products/1")
    assert deleted.status_code == 204 and deleted.content == b""
    assert client.get("/products/1").status_code == 404

def test_response_filtering():
    with TestClient(responses.app) as client:
        assert client.get("/users/1").json() == {"id": 1, "name": "Asha"}
        assert client.get("/stock/20").status_code == 409

def test_dependency_override():
    def fixed_page():
        return dependencies.Pagination(limit=2, offset=4)
    dependencies.app.dependency_overrides[dependencies.pagination] = fixed_page
    try:
        with TestClient(dependencies.app) as client:
            assert client.get("/products").json()["label"] == "offset=4;limit=2"
    finally:
        dependencies.app.dependency_overrides.clear()

def test_cors_and_io():
    with TestClient(middleware.app) as client:
        result = client.get("/products", headers={"Origin": "http://localhost:3000"})
        assert result.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert "x-request-id" in result.headers
        denied = client.options("/products", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
        assert denied.status_code == 400
    with TestClient(io_features.app) as client:
        result = client.post("/uploads", data={"label": "notes"}, files={"file": ("sample.txt", b"hello", "text/plain")})
        assert result.json() == {"label": "notes", "bytes": 5}
        too_large = client.post("/uploads", data={"label": "notes"}, files={"file": ("large.txt", b"x" * (1024 * 1024 + 1), "text/plain")})
        assert too_large.status_code == 413
        assert client.get("/numbers").text == "0\n1\n2\n"
        with client.websocket_connect("/ws/echo") as socket:
            socket.send_text("hello")
            assert socket.receive_text() == "echo: hello"
```

## Code Explanation

### Line 1

Reset the disposable CRUD ID sequence for reproducible tests.

### Line 2

Import test discovery helpers and fixtures.

### Line 3

Exercise ASGI requests without a live TCP server.

### Line 4

Assert model-level invalid-data behaviour directly.

### Line 5

Import the independent lesson apps explicitly.

### Line 6

Rename an imported app to avoid confusing it with the other lesson apps.

### Line 7

Test data validation independently of HTTP.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Register a reusable per-test setup/cleanup provider.

### Line 10

Supply a fresh in-memory store to each requesting test.

### Line 11

Remove previous products before the test starts.

### Line 12

Restart IDs for deterministic assertions.

### Line 13

Enter the app's lifecycle context.

### Line 14

Lend the client to the test function.

### Line 15

Clean state even after the test completes.

### Line 16

This blank line separates logical parts; Python does not execute it.

### Line 17

Check both a successful first request and rejected typed inputs.

### Line 18

Open the first lesson app.

### Line 19

Parse response JSON and verify its exact public data.

### Line 20

Use a separate app for request-source tests.

### Line 21

Fixed-route ordering must not interpret featured as an integer.

### Line 22

Invalid integer text is rejected before the endpoint.

### Line 23

Query bounds are part of the executable contract.

### Line 24

HTTPX's json parameter serializes the object and sets content type.

### Line 25

Embedded scalar shape differs from a bare number.

### Line 26

This blank line separates logical parts; Python does not execute it.

### Line 27

Exercise defaults, normalization and strict/nested failures without HTTP.

### Line 28

Establish valid reusable input.

### Line 29

Prove the field validator normalizes text.

### Line 30

Require this block to raise a validation failure.

### Line 31

A string fails the strict integer contract.

### Line 32

Require a cross-field failure too.

### Line 33

Sale price may not exceed regular price.

### Line 34

This blank line separates logical parts; Python does not execute it.

### Line 35

Pytest resolves the fixture by this parameter name.

### Line 36

Give the supplied client a short local name.

### Line 37

Create a valid complete resource.

### Line 38

Assert the status, not just returned data.

### Line 39

Verify discoverability of the created resource.

### Line 40

Explicitly clear a nullable field.

### Line 41

Omitted price must remain unchanged.

### Line 42

Explicit null must not be discarded by exclude\_none.

### Line 43

Omissible does not mean nullable for a required stored name.

### Line 44

Full replacement requires a name.

### Line 45

A complete replacement succeeds.

### Line 46

Delete the existing resource.

### Line 47

Assert actual no-content semantics.

### Line 48

Verify deletion affects later reads.

### Line 49

This blank line separates logical parts; Python does not execute it.

### Line 50

Check a privacy-sensitive response guarantee.

### Line 51

Start the response lesson app.

### Line 52

No password hash or extra internal field may escape.

### Line 53

Domain exceptions must translate to the documented status.

### Line 54

This blank line separates logical parts; Python does not execute it.

### Line 55

Demonstrate replacing a request provider without changing application code.

### Line 56

Define a deterministic test-only supplier.

### Line 57

Supply known internal values without parsing a query.

### Line 58

Map the original callable itself to its replacement.

### Line 59

Ensure global override state cannot leak into later tests.

### Line 60

Exercise the actual route with the replaced dependency graph.

### Line 61

The sub-dependency also receives the overridden page.

### Line 62

Cleanup runs even if an assertion fails.

### Line 63

Restore normal providers for subsequent requests/tests.

### Line 64

This blank line separates logical parts; Python does not execute it.

### Line 65

Check browser policy headers and special transport operations.

### Line 66

Start middleware application context.

### Line 67

Simulate an approved frontend origin.

### Line 68

Check the permission header rather than assuming 200 means browser access.

### Line 69

Verify middleware processed the response.

### Line 70

Simulate an unapproved preflight.

### Line 71

The configured CORS middleware rejects the disallowed preflight.

### Line 72

Open the file/stream/socket app.

### Line 73

Send multipart text plus an in-memory file.

### Line 74

Count actual bytes rather than filename/metadata claims.

### Line 75

Exercise the accepted-file size boundary.

### Line 76

Oversized file content must be rejected.

### Line 77

Check accumulated streaming content, not network chunk timing.

### Line 78

Open a real ASGI WebSocket conversation in-process.

### Line 79

Send a client message after handshake.

### Line 80

Verify bidirectional response behaviour.

## Example

### File: `tests/test_auth.py`

```python
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from fastapi.testclient import TestClient
from examples import auth

TEST_KEY = "test-only-not-for-production-" + "x" * 40

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", TEST_KEY)
    auth.users.clear()
    auth.refresh_records.clear()
    with TestClient(auth.app) as test_client:
        yield test_client
    auth.users.clear()
    auth.refresh_records.clear()

def register_and_login(client):
    result = client.post("/register", json={"username": "asha", "password": "a-long-example-passphrase"})
    assert result.status_code == 201 and "password_hash" not in result.json()
    login = client.post("/token", data={"username": "asha", "password": "a-long-example-passphrase"})
    assert login.status_code == 200
    return login.json()

def test_authentication_and_authorization(client):
    pair = register_and_login(client)
    assert client.get("/me").status_code == 401
    headers = {"Authorization": "Bearer " + pair["access_token"]}
    assert client.get("/me", headers=headers).json()["username"] == "asha"
    assert client.get("/admin", headers=headers).status_code == 403
    assert client.post("/token", data={"username": "asha", "password": "wrong"}).status_code == 401
    assert client.post("/register", json={"username": "evil", "password": "a-long-example-passphrase", "role": "admin"}).status_code == 422
    assert client.get("/me", headers={"Authorization": "Bearer broken"}).status_code == 401

def test_refresh_replay_and_logout(client):
    pair = register_and_login(client)
    rotated = client.post("/refresh", json={"refresh_token": pair["refresh_token"]})
    assert rotated.status_code == 200
    successor = rotated.json()["refresh_token"]
    assert client.post("/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401
    assert client.post("/refresh", json={"refresh_token": successor}).status_code == 401
    second = client.post("/token", data={"username": "asha", "password": "a-long-example-passphrase"}).json()
    assert client.post("/logout", json={"refresh_token": second["refresh_token"]}).status_code == 204
    assert client.post("/refresh", json={"refresh_token": second["refresh_token"]}).status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer " + second["access_token"]}).status_code == 200

def test_required_claims_and_account_state(client):
    pair = register_and_login(client)
    now = datetime.now(timezone.utc)
    claims = {"sub": auth.users["asha"]["id"], "exp": now + timedelta(minutes=5), "iat": now, "iss": auth.ISSUER, "aud": auth.AUDIENCE, "type": "access"}
    for changed in [{**claims, "aud": "other-api"}, {**claims, "exp": now - timedelta(seconds=30)}, {**claims, "type": "refresh"}, {key: value for key, value in claims.items() if key != "exp"}]:
        token = jwt.encode(changed, TEST_KEY, algorithm="HS256")
        assert client.get("/me", headers={"Authorization": "Bearer " + token}).status_code == 401
    token = jwt.encode(claims, "different-key-" + "z" * 40, algorithm="HS256")
    assert client.get("/me", headers={"Authorization": "Bearer " + token}).status_code == 401
    auth.users["asha"]["disabled"] = True
    assert client.get("/me", headers={"Authorization": "Bearer " + pair["access_token"]}).status_code == 401
```

## Code Explanation

### Line 1

Construct intentionally expired/wrongly scoped test claims.

### Line 2

Sign deliberately invalid-contract tokens with the test key to isolate claim validation.

### Line 3

Provide isolated test fixtures.

### Line 4

Exercise authentication routes without opening a port.

### Line 5

Import the complete local authentication lesson.

### Line 6

This blank line separates logical parts; Python does not execute it.

### Line 7

A deterministic key is acceptable only inside an isolated test environment.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Supply a fresh authentication app state to each test.

### Line 10

monkeypatch temporarily changes environment and restores it automatically.

### Line 11

Configure startup without exposing or relying on a real secret.

### Line 12

Remove prior accounts from the disposable store.

### Line 13

Remove prior login families too.

### Line 14

Enter lifespan so signing configuration exists.

### Line 15

Provide the client while its app is running.

### Line 16

Remove account state after use.

### Line 17

Remove token state after use.

### Line 18

This blank line separates logical parts; Python does not execute it.

### Line 19

Reuse successful setup while tests focus on different security assertions.

### Line 20

Register only allowed public fields.

### Line 21

Creation must never disclose the stored hash.

### Line 22

Use form encoding, not JSON, for OAuth2PasswordRequestForm.

### Line 23

Stop the test setup if credentials were unexpectedly rejected.

### Line 24

Return test-only access and refresh credentials.

### Line 25

This blank line separates logical parts; Python does not execute it.

### Line 26

Distinguish proof of identity from permission.

### Line 27

Obtain a reader login.

### Line 28

Missing identity is unauthenticated.

### Line 29

Transport access credentials through the intended header.

### Line 30

A valid token resolves current account state.

### Line 31

A reader is authenticated but lacks admin permission.

### Line 32

Wrong-password responses use a generic failure.

### Line 33

Registration cannot self-assign privileged fields.

### Line 34

Malformed credentials must not pass extraction-only checks.

### Line 35

This blank line separates logical parts; Python does not execute it.

### Line 36

Exercise stateful renewal and its explicitly limited revocation promise.

### Line 37

Start one token family.

### Line 38

Exchange the first credential exactly once.

### Line 39

A valid unused credential should rotate.

### Line 40

Retain the new credential for the replay test.

### Line 41

Reuse must fail and revoke the family.

### Line 42

The descendant must be revoked too, not only the old record.

### Line 43

A new login creates an independent family.

### Line 44

Revoke refresh ability for that login.

### Line 45

Logout prevents future renewal.

### Line 46

Document the limitation: already-issued access tokens remain valid until expiry/account invalidation.

### Line 47

This blank line separates logical parts; Python does not execute it.

### Line 48

A correct signature alone must not be sufficient.

### Line 49

Create the stable account subject for test tokens.

### Line 50

Use aware UTC timestamps matching the real verifier.

### Line 51

Establish a valid baseline claim set.

### Line 52

Vary audience, expiry, purpose and required-claim presence independently.

### Line 53

Sign with the known test key so each failure is about claims, not an unrelated signature mismatch.

### Line 54

All invalid contracts must be refused.

### Line 55

Sign a valid-looking claim set with an untrusted key.

### Line 56

A forged/untrusted signature must fail too.

### Line 57

Simulate trusted administration disabling the account.

### Line 58

Current account policy must override still-valid token time/signature.

## Example

### File: `tests/test_catalog.py`

```python
from fastapi.testclient import TestClient
from examples.catalog.main import create_app

def test_catalog_persistence_and_conflicts(tmp_path):
    url = f"sqlite:///{tmp_path / 'catalog.db'}"
    with TestClient(create_app(url)) as client:
        created = client.post("/products", json={"name": "Pen", "price_minor": 2000})
        assert created.status_code == 201
        product_id = created.json()["id"]
        assert client.post("/products", json={"name": "Pen", "price_minor": 3000}).status_code == 409
        assert client.post("/products", json={"name": "Book", "price_minor": -1}).status_code == 422
        assert len(client.get("/products?limit=1").json()) == 1
    with TestClient(create_app(url)) as client:
        assert client.get(f"/products/{product_id}").json()["name"] == "Pen"
        assert client.put(f"/products/{product_id}", json={"name": "Pencil", "price_minor": 1000}).status_code == 200
        deleted = client.delete(f"/products/{product_id}")
        assert deleted.status_code == 204 and deleted.content == b""
        assert client.get(f"/products/{product_id}").status_code == 404

def test_app_instances_are_isolated(tmp_path):
    first = create_app(f"sqlite:///{tmp_path / 'first.db'}")
    second = create_app(f"sqlite:///{tmp_path / 'second.db'}")
    with TestClient(first) as a, TestClient(second) as b:
        assert a.post("/products", json={"name": "Pen", "price_minor": 2000}).status_code == 201
        assert b.get("/products").json() == []
```

## Code Explanation

### Line 1

Exercise the complete layered project through HTTP.

### Line 2

Create isolated app instances with explicit database paths.

### Line 3

This blank line separates logical parts; Python does not execute it.

### Line 4

pytest supplies a private temporary directory for this test.

### Line 5

Choose a test-only database, never the real catalogue file.

### Line 6

Lifespan creates tables and owns this app's engine.

### Line 7

Drive routing, validation, service, repository and SQL together.

### Line 8

Successful commit must produce creation status.

### Line 9

Use the server-generated ID rather than assuming a sequence.

### Line 10

The database unique constraint should map to the domain/API conflict.

### Line 11

Invalid input must fail before database insertion.

### Line 12

Verify bounded collection output.

### Line 13

Restart with the same file but a new app/engine instance.

### Line 14

Prove committed data survives application shutdown.

### Line 15

Exercise complete replacement through the service boundary.

### Line 16

Delete the persisted record.

### Line 17

Assert both the correct code and empty body.

### Line 18

Confirm domain absence maps through the configured exception handler.

### Line 19

This blank line separates logical parts; Python does not execute it.

### Line 20

Configuration must not accidentally share one global session/engine.

### Line 21

Build the first app with its own storage.

### Line 22

Build a second independent app.

### Line 23

Run both application lifecycles in the same test process.

### Line 24

Write through the first app only.

### Line 25

The second app must not see another instance's data.

## Dependency overrides: why they work

`app.dependency_overrides[original_callable] = replacement_callable` changes resolution for that app. Use the original function object as the key, not its name string and not the result of calling it. Clear overrides in finally/fixture cleanup. Otherwise a fake authenticated administrator or fake database can accidentally persist into later tests.

An override is appropriate when testing a route independently of a slow external service. It does not replace integration tests proving the real provider works. A mock that always returns success cannot prove timeouts, retries or transaction behaviour.

## Async tests and lifespan

For tests that directly await async functions, use pytest's AnyIO integration or a deliberately configured async pytest plugin, and HTTPX `AsyncClient` with `ASGITransport(app=app)`. A **transport** is the client's lower-level mechanism delivering requests. HTTPX's ASGI transport by itself does not run application lifespan. Use a lifecycle manager (such as asgi-lifespan's LifespanManager) or explicitly start the app lifecycle. Do not assume changing TestClient to AsyncClient preserves setup automatically.

For a database test, prefer a fresh database or rollback-based isolation designed for your session topology. SQLite `:memory:` databases can be separate per connection unless pooling is intentionally configured; a temporary file is easier for this course. SQLite success does not prove PostgreSQL/MySQL SQL dialect, locking, collation or migration behaviour. Add dedicated service-backed tests before deployment.

## What is checked, and what is not?

The supplied suite checks first responses, source/bound validation, strict/model validation, CRUD semantics, response filtering, overrides, CORS preflight, file size checks, stream contents, socket echo, authentication failures, authorization, refresh replay/logout and real local SQLite persistence/isolation. It also validates the additional async/lifespan and configuration labs as described in chapter 23.

It does not claim to test real SMTP/email, MongoDB/PostgreSQL/MySQL servers, a reverse proxy, public HTTPS, distributed refresh races or production load in this environment. The migration smoke test is a separate command. Integration claims should reflect executed services, not just installed drivers.

## When to use / not use; mistakes and best practices

Test boundaries, negative cases and business invariants, not private implementation details on every line. Avoid test ordering dependencies, live production credentials and global state leakage. Check status, body and relevant headers. For validation errors prefer stable locations/types over exact English messages that can change across versions. Do not use sleeps to guess when work finished if a deterministic fixture/event can establish it.

**CI (Continuous Integration)** runs checks automatically for proposed changes. A typical pipeline installs an isolated dependency set, runs tests and documentation checks, then builds an image. Never publish/deploy an image merely because `pip install` succeeded.

## Practice

**Beginner:** Add an assertion that unknown product 999 returns 404. **Intermediate:** Test that a caller-supplied ID is rejected at creation. **Challenge:** Explain why a passing sequential refresh test does not prove multi-process atomicity.

## Expected Result / Solution

Inside `test_crud_lifecycle`, after obtaining client, add:

```python
    assert client.get("/products/999").status_code == 404
    assert client.post("/products", json={"id": 99, "name": "Pen", "price_minor": 2000}).status_code == 422
```

Line 1 tests resource absence. Line 2 proves the creation schema rejects a server-controlled field. The challenge answer: the local lock protects only one process, while a distributed deployment needs a database atomic transition and concurrent service-backed tests. Sequential success cannot demonstrate race safety across independent workers.

## Summary

Tests are executable explanations. Pair successful requests with malformed input, missing resources, forbidden operations and resource-lifecycle failures.

## Supplemental lifecycle and advanced test files

`tests/test_lifecycles.py` extends the core tests with controlled outbound responses, 502/504 error translation, client closure and typed settings. **MockTransport** is HTTPX's callback-driven transport: the callback receives a request and returns a chosen response or raises a chosen network exception without opening sockets. This isolates your timeout/error policy from actual network availability. `monkeypatch` temporarily replaces a callable or environment value; pytest restores it after the test. The original AsyncClient constructor is saved before replacement, avoiding accidental recursive construction.

`tests/test_advanced.py` checks chapter 24's async SQLite persistence, action scopes plus cross-account ownership, and strong/weak conditional-GET responses. These supplementary test implementations are supplied beside the fully printed core test files. The advanced chapter prints the complete applications being exercised. Read their assertions as additional solved exercises: each asserts an externally observable contract rather than internal helper call counts.
