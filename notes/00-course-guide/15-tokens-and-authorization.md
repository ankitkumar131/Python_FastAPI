# 15 — JWT, OAuth2, bearer tokens, refresh rotation and permissions

[Previous](14-authentication-foundations.md) · [Course map](./) · [Next](16-middleware-and-cors.md)

## JWT: what is it and why use it?

A **JWT (JSON Web Token)** is a compact representation of claims. A signed JWT commonly has three dot-separated, Base64url-encoded parts: header, payload and signature. **Base64url** is a transport encoding, not encryption. Anyone holding the token can normally read its claims. Do not store passwords, signing secrets or unnecessary personal data in it.

A **claim** is a statement such as subject ID (`sub`), expiration (`exp`), issued-at time (`iat`), issuer (`iss`) or intended audience (`aud`). A signature lets the verifier detect changes and establish that a trusted key signed the data. It does not establish that the person currently holding a stolen token is its legitimate owner.

**HS256** signs/verifies with the same high-entropy shared secret. Every verifier knowing it can also sign tokens; that may be inappropriate across organizational trust boundaries. Asymmetric algorithms use a private signing key and a public verification key. Production identity providers often publish public verification keys in a **JWKS (JSON Web Key Set)**, a standardized key collection. Validate issuer/audience and manage key rotation rather than accepting any key URL advertised by an untrusted token.

**PyJWT** is the library used here. `jwt.encode` signs a claims dictionary; `jwt.decode` verifies using an explicit allowed algorithm list. Require security-critical claims, check issuer/audience, and do not read unverified claims as proof. `verify_signature=False` is not authentication.

## Access versus refresh tokens

An **access token** is presented to resource endpoints and should be short-lived. A **refresh token** is presented only to the token service to obtain new credentials. Rotation replaces a refresh credential after each use. Store a cryptographic digest of a random high-entropy refresh token rather than its reusable plaintext. A fast digest is suitable for a randomly generated 256-bit token; it is not suitable for weak human passwords.

A **token family** links refresh descendants from one login. Reuse of an already consumed refresh token can indicate theft, so revoke the whole family. Rotation must be atomic: two concurrent requests must not both exchange the same credential successfully. Retain used-token records until the family can no longer be valid, otherwise reuse detection loses its evidence.

Logout revokes refresh capability in our lesson. Already issued JWT access tokens remain usable until expiry unless you add a denylist/session-version lookup or another immediate-revocation design. Never promise “logout instantly invalidates all JWTs” if your verifier only checks a signature and time.

## OAuth2: protocol, not a token format

**OAuth 2.0 (Open Authorization)** is a framework for delegated authorization. Roles include the resource owner (usually the user), client (app requesting access), authorization server (issues access) and resource server (API). OAuth2 does not require JWT. **OpenID Connect (OIDC)** adds an identity layer, including an ID token; an ID token for a client is not automatically an API access token.

For modern third-party/browser/mobile delegated login, prefer **Authorization Code with PKCE (Proof Key for Code Exchange)** through a trusted provider. The client redirects to the provider, the user authenticates there, the provider returns a short-lived code, and the client exchanges it while proving possession of a verifier corresponding to its earlier challenge. Verify redirect URI, state and OIDC nonce where appropriate; use mature provider/client libraries rather than hand-rolling the flow.

FastAPI's `OAuth2PasswordBearer(tokenUrl="token")` extracts a Bearer credential and describes the security scheme in OpenAPI. It **does not** implement login, password checking, JWT verification or authorization. `OAuth2PasswordRequestForm` reads form fields named `username` and `password`; it does not read JSON.

The local username/password exchange below mirrors the official teaching pattern. The OAuth resource-owner password grant is not recommended for new delegated/public-client designs. Treat this as a first-party credential-mechanics lesson, not a production OAuth authorization server.

## Roles, permissions and ownership

A **role** groups capabilities, such as reader or admin. A **permission** names a specific action, such as `products:write`. A **scope** is a delegated permission string represented in a token/protocol. **RBAC (Role-Based Access Control)** derives access from roles. Ownership/tenant checks often need additional resource-specific rules: even a normal authenticated reader should not see another user's private orders.

Do not trust a caller's `role` JSON field. Store server-controlled roles and evaluate current account status. This example loads the current user from the store after verifying the JWT, so disabling an account can take effect immediately. It checks a server-stored role for `/admin`, not a self-asserted claim.

## Complete local learning app and explicit limitations

This example implements registration, login, access verification, protected identity, an admin gate, refresh rotation/reuse detection and logout. **Users and refresh records are in-memory** with a process lock. Restart loses accounts; multiple workers do not share them. It is deliberately single-process and not production-ready. Production needs durable users, unique constraints, atomic stored refresh transitions, rate limiting, email verification/recovery and operational controls. The earlier SQLAlchemy transaction lessons explain how to replace the storage boundary.

Install using the root requirements file. Generate a secret locally (not in chat):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

This imports Python's cryptographically secure random generator and prints 32 random bytes encoded as hex. Set the result for the process:

```bash
export JWT_SECRET='paste-your-locally-generated-value-here'
python -m uvicorn examples.auth:app --reload
```

PowerShell uses `$env:JWT_SECRET = 'paste-your-locally-generated-value-here'`. Never commit the real value; do not use that literal placeholder. The app fails startup if the value is missing/too short. Length is not proof of entropy: generate it randomly.

## Example

### File: `examples/auth.py`

```python
import hashlib
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Annotated
from uuid import uuid4
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field
from pwdlib import PasswordHash

hasher = PasswordHash.recommended()
dummy_hash = hasher.hash("not-a-real-user-password")
users: dict[str, dict] = {}
refresh_records: dict[str, dict] = {}
lock = Lock()
ISSUER = "fastapi-school"
AUDIENCE = "catalog-api"

class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-z0-9_]+$")
    password: str = Field(min_length=12, max_length=128)

class UserPublic(BaseModel):
    id: str
    username: str
    role: str

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str = Field(min_length=20, max_length=200)

@asynccontextmanager
async def lifespan(app: FastAPI):
    key = os.environ.get("JWT_SECRET", "")
    if len(key) < 32:
        raise RuntimeError("Set JWT_SECRET to a securely generated value of at least 32 characters")
    app.state.signing_key = key
    yield

app = FastAPI(lifespan=lifespan)
oauth2 = OAuth2PasswordBearer(tokenUrl="token", scopes={"orders:read": "Read own orders", "orders:create": "Create own orders", "products:write": "Change products"})

def unauthorized() -> HTTPException:
    return HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"})

def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def issue_pair(user: dict, key: str, family: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    access = jwt.encode({"sub": user["id"], "exp": now + timedelta(minutes=15), "iat": now, "iss": ISSUER, "aud": AUDIENCE, "type": "access"}, key, algorithm="HS256")
    refresh = secrets.token_urlsafe(32)
    refresh_records[digest(refresh)] = {"user_id": user["id"], "family": family or str(uuid4()), "expires": now + timedelta(days=7), "used": False, "revoked": False}
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

@app.post("/register", response_model=UserPublic, status_code=201)
def register(data: Registration):
    password_hash = hasher.hash(data.password)
    with lock:
        if data.username in users:
            raise HTTPException(409, "Username unavailable")
        user = {"id": str(uuid4()), "username": data.username, "password_hash": password_hash, "role": "reader", "disabled": False}
        users[data.username] = user
        return user.copy()

@app.post("/token", response_model=TokenPair)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], request: Request, response: Response):
    with lock:
        stored = users.get(form.username)
        user = stored.copy() if stored else None
    if len(form.password) > 128:
        raise unauthorized()
    valid = hasher.verify(form.password, user["password_hash"] if user else dummy_hash)
    if not valid or user is None or user["disabled"]:
        raise unauthorized()
    response.headers["Cache-Control"] = "no-store"
    with lock:
        if users[form.username]["disabled"]:
            raise unauthorized()
        return issue_pair(user, request.app.state.signing_key)

def current_user(token: Annotated[str, Depends(oauth2)], request: Request) -> dict:
    try:
        payload = jwt.decode(token, request.app.state.signing_key, algorithms=["HS256"], audience=AUDIENCE, issuer=ISSUER, options={"require": ["sub", "exp", "iat", "iss", "aud", "type"]})
        if payload["type"] != "access" or not isinstance(payload["sub"], str):
            raise unauthorized()
    except InvalidTokenError as error:
        raise unauthorized() from error
    with lock:
        user = next((entry for entry in users.values() if entry["id"] == payload["sub"]), None)
        if user is None or user["disabled"]:
            raise unauthorized()
        return user.copy()

@app.get("/me", response_model=UserPublic)
def me(user: Annotated[dict, Depends(current_user)]):
    return user

def require_admin(user: Annotated[dict, Depends(current_user)]) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Admin permission required")
    return user

@app.get("/admin", dependencies=[Depends(require_admin)])
def admin():
    return {"message": "Admin access"}

def revoke_family(family: str):
    for record in refresh_records.values():
        if record["family"] == family:
            record["revoked"] = True

@app.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshInput, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    with lock:
        record = refresh_records.get(digest(data.refresh_token))
        if record is None:
            raise unauthorized()
        if record["used"]:
            revoke_family(record["family"])
            raise unauthorized()
        if record["revoked"] or record["expires"] <= datetime.now(timezone.utc):
            raise unauthorized()
        user = next((entry for entry in users.values() if entry["id"] == record["user_id"]), None)
        if user is None or user["disabled"]:
            raise unauthorized()
        record["used"] = True
        return issue_pair(user, request.app.state.signing_key, record["family"])

@app.post("/logout", status_code=204, response_class=Response)
def logout(data: RefreshInput):
    with lock:
        record = refresh_records.get(digest(data.refresh_token))
        if record:
            revoke_family(record["family"])
    return Response(status_code=204)
```

## Code Explanation

### Line 1

Digest high-entropy refresh tokens for storage, not human passwords.

### Line 2

Read the signing secret from process configuration.

### Line 3

Generate cryptographically unpredictable refresh credentials.

### Line 4

Validate configuration during app startup.

### Line 5

Use timezone-aware UTC times for token claims and expiry.

### Line 6

Make this learning store's multi-step transitions atomic within one process.

### Line 7

Attach dependency declarations to types.

### Line 8

Generate stable opaque account and token-family identifiers.

### Line 9

Import PyJWT's signing and verification functions.

### Line 10

Catch expected JWT verification failures.

### Line 11

Import routing, dependencies, request state and response metadata.

### Line 12

Read bearer headers and username/password form input; these helpers do not verify tokens themselves.

### Line 13

Validate registration and refresh input, and filter public output.

### Line 14

Use Argon2-capable password hashing rather than home-grown cryptography.

### Line 15

This blank line separates logical parts; Python does not execute it.

### Line 16

Initialize the installed recommended password hashing implementation.

### Line 17

Unknown-user logins still perform a verification to reduce obvious timing differences.

### Line 18

Key this disposable account store by username; production uses durable unique account records.

### Line 19

Key refresh records by digest, never by reusable plaintext token.

### Line 20

Coordinate registration and refresh state changes in this process.

### Line 21

Identify the trusted issuer this service accepts.

### Line 22

Restrict tokens to this intended API audience.

### Line 23

This blank line separates logical parts; Python does not execute it.

### Line 24

Permit only public account-creation fields.

### Line 25

Reject role/admin/verified fields submitted by a caller.

### Line 26

Use a simple explicitly lowercase identifier policy for this lesson.

### Line 27

Bound password length without truncation; never log the model.

### Line 28

This blank line separates logical parts; Python does not execute it.

### Line 29

Define safe account output fields.

### Line 30

Expose the server-generated subject ID.

### Line 31

Expose the chosen identifier.

### Line 32

Expose a server-controlled role, not the hash.

### Line 33

This blank line separates logical parts; Python does not execute it.

### Line 34

Define the two distinct credentials returned after a successful exchange.

### Line 35

Short-lived signed credential for resource access.

### Line 36

Opaque credential usable only for refresh/logout.

### Line 37

Tell clients how the access credential is transported.

### Line 38

This blank line separates logical parts; Python does not execute it.

### Line 39

Accept only the credential intended for rotation/revocation.

### Line 40

Reject unsupported fields instead of silently ignoring them.

### Line 41

Bound input size before hashing/lookup.

### Line 42

This blank line separates logical parts; Python does not execute it.

### Line 43

Attach fail-fast configuration to startup.

### Line 44

Run before this worker accepts requests.

### Line 45

Read the external secret; no insecure fallback exists.

### Line 46

Reject absent or obviously weak-length configuration.

### Line 47

Stop startup rather than silently issuing forgeable tokens.

### Line 48

Keep the configured key on this running app's state.

### Line 49

Serve requests; no external resource requires shutdown closure here.

### Line 50

This blank line separates logical parts; Python does not execute it.

### Line 51

Build the authentication lesson app.

### Line 52

Extract bearer credentials and describe the token endpoint to Swagger UI; the relative URL supports path prefixes.

### Line 53

This blank line separates logical parts; Python does not execute it.

### Line 54

Centralize the public authentication failure contract.

### Line 55

Include the standard bearer challenge without exposing which check failed.

### Line 56

This blank line separates logical parts; Python does not execute it.

### Line 57

Derive a lookup key for random refresh credentials.

### Line 58

Encode text to bytes, hash it and store hex text; tokens already have high entropy.

### Line 59

This blank line separates logical parts; Python does not execute it.

### Line 60

Called only while holding the store lock, so token-state changes are serialized.

### Line 61

Use an aware UTC clock.

### Line 62

Sign bounded, audience-specific access claims using a fixed algorithm.

### Line 63

Generate an unpredictable opaque refresh token, not another access JWT.

### Line 64

Store only its digest-indexed state; descendants share a family for reuse detection.

### Line 65

Return plaintext credentials only to the authorized client over HTTPS in real use.

### Line 66

This blank line separates logical parts; Python does not execute it.

### Line 67

Create an account while filtering the stored password hash.

### Line 68

Synchronous handlers keep expensive password hashing off the event loop.

### Line 69

Hash before acquiring the short store lock, avoiding blocking all other store operations during the calculation.

### Line 70

Check-and-insert atomically in this local process.

### Line 71

Enforce uniqueness in the lesson store; a database must enforce this too.

### Line 72

Registration discloses availability here; production should choose an enumeration policy deliberately.

### Line 73

Set role and status on the server, never from untrusted input.

### Line 74

Save the account for later authentication.

### Line 75

Return a snapshot; the public response model excludes hash/status.

### Line 76

This blank line separates logical parts; Python does not execute it.

### Line 77

Expose the local credential-exchange endpoint.

### Line 78

Read form-encoded username/password and app/response context.

### Line 79

Snapshot account state while protected from store writers.

### Line 80

Look up the supplied account identifier.

### Line 81

Avoid holding the lock during the costly hash verification.

### Line 82

Bound expensive input processing at this endpoint too; front-door body limits remain necessary.

### Line 83

Return the same authentication failure contract.

### Line 84

Verify known-user hashes or perform comparable dummy work for unknown users.

### Line 85

Reject wrong credentials and disabled/nonexistent accounts alike.

### Line 86

Never explain which credential component failed.

### Line 87

Tell compliant caches not to store credential-bearing responses.

### Line 88

Atomically store refresh state while issuing the pair.

### Line 89

Recheck mutable account status after the expensive verification gap.

### Line 90

Do not issue new credentials for a newly disabled account.

### Line 91

Sign access and store refresh credentials for this login.

### Line 92

This blank line separates logical parts; Python does not execute it.

### Line 93

Combine bearer extraction with actual cryptographic and account verification.

### Line 94

Treat expected token failures as authentication failures.

### Line 95

Verify signature, algorithm, required claims, audience, issuer and registered time checks.

### Line 96

Reject wrong token purpose or malformed subject even if the signature is valid.

### Line 97

Refresh credentials are never accepted as access credentials.

### Line 98

Includes expiry, malformed token, signature and claim failures.

### Line 99

Present a stable 401 without token contents.

### Line 100

Consult current server-owned identity and role state.

### Line 101

Find by stable subject; a real database uses an indexed primary-key lookup.

### Line 102

Signed tokens do not override deleted/disabled account policy.

### Line 103

Stop before business logic runs.

### Line 104

Return a snapshot for permission checks and response filtering.

### Line 105

This blank line separates logical parts; Python does not execute it.

### Line 106

A protected identity endpoint.

### Line 107

Require complete bearer verification, not just extraction.

### Line 108

The response contract excludes internal fields.

### Line 109

This blank line separates logical parts; Python does not execute it.

### Line 110

Authorization depends on successful authentication.

### Line 111

Check the server-stored current role.

### Line 112

Authenticated but insufficiently privileged differs from 401.

### Line 113

Pass the authorized identity to consumers if needed.

### Line 114

This blank line separates logical parts; Python does not execute it.

### Line 115

Execute an access check even though the handler does not need its returned user.

### Line 116

Only authorized requests reach this function.

### Line 117

Return privileged content after the check, not before.

### Line 118

This blank line separates logical parts; Python does not execute it.

### Line 119

Called under the lock so all family records change together.

### Line 120

Iterate this tiny learning store; a database would use an indexed update.

### Line 121

Select the compromised/logged-out login family.

### Line 122

Invalidate all its known refresh descendants.

### Line 123

This blank line separates logical parts; Python does not execute it.

### Line 124

Exchange a refresh credential exactly once.

### Line 125

Read the opaque credential, not a username/password or access JWT.

### Line 126

Do not cache the new pair.

### Line 127

Make checking, consuming and creating a successor one atomic local transition.

### Line 128

Lookup by digest without storing the reusable token.

### Line 129

Unknown credentials must not create sessions.

### Line 130

Reject generically.

### Line 131

Reuse of a consumed credential can indicate theft or an unsafe client retry.

### Line 132

Revoke the successor family before reporting failure.

### Line 133

Do not issue another descendant from the same old token.

### Line 134

Enforce revocation and time limits.

### Line 135

Require a fresh login when the refresh capability is invalid.

### Line 136

Resolve current identity, not a client-selected account.

### Line 137

Prevent refreshing disabled/deleted accounts.

### Line 138

Refuse new credentials.

### Line 139

Consume the old credential before creating its successor.

### Line 140

Return a rotated pair tied to the same login family.

### Line 141

This blank line separates logical parts; Python does not execute it.

### Line 142

Revoke a login family's refresh capability.

### Line 143

Possession of the refresh credential is required to identify its family.

### Line 144

Keep revocation atomic in this process.

### Line 145

Lookup without revealing existence in the result.

### Line 146

Unknown tokens are a harmless no-op for this logout contract.

### Line 147

Revoke descendants, including already rotated credentials.

### Line 148

No body and no promise that already issued access JWTs were immediately revoked.

## Test the complete flow

In `/docs`:

1. POST `/register` with `{"username":"asha","password":"a-long-example-passphrase"}`. Expect 201 and only public fields. Adding `"role":"admin"` fails with 422.
2. POST `/token` using form fields username=asha and password=a-long-example-passphrase. Expect access\_token, refresh\_token and token\_type=bearer. Wrong password → 401.
3. Click **Authorize** in Swagger UI and use the same credentials; its OAuth helper obtains an access token for protected calls. GET `/me` → 200. A raw client sends `Authorization: Bearer ACCESS_TOKEN`.
4. GET `/admin` as this reader → 403. No bearer header or a modified token → 401. No public endpoint promotes users; production role changes require trusted administration and audit.
5. POST `/refresh` with `{"refresh_token":"the returned refresh value"}`. Save the new pair. Reusing the old value → 401 and revokes the family; the new refresh value now also fails. This deliberately strict policy means clients must serialize refresh attempts and handle uncertain network outcomes.
6. On a fresh login, POST `/logout` with its refresh credential → 204. Refresh now fails. Existing access token may remain accepted until its fifteen-minute expiration because this example does not maintain an access-token denylist.

Never paste real credentials/tokens into issue trackers or shared screenshots. `/docs` sends real requests; it is not a mock interface.

## What happens internally?

Registration validates allowed fields and hashes off the event loop. Login verifies the password, then issues a signed access token and stores digest-indexed refresh state. Each protected request extracts the bearer token, verifies its cryptographic/time/audience/issuer contract, loads current account state, then authorizes the action. Refresh takes a lock around read/check/consume/create, preventing two successful exchanges of the same credential in one process. Logout changes server refresh state.

A production SQL implementation uses unique digest keys and a transaction/conditional update (or locking row read) for the refresh transition. Check that exactly one unused valid record was consumed, retain reuse evidence, and revoke a family atomically on replay. Merely moving the dictionary values into SQL without fixing transaction boundaries is insufficient.

The lesson uses a rolling seven-day refresh expiry. Production often also sets an absolute maximum family lifetime and an idle timeout. Otherwise continuously active refreshes can extend a login indefinitely. Prune expired records without deleting evidence still needed for live families.

## Ownership checks: authorization goes beyond roles

For an order read, fetch using both order ID and current owner ID, for example an ORM condition `Order.id == order_id` **and** `Order.owner_id == user_id`. Do not load by ID and forget ownership merely because authentication succeeded. Multi-tenant systems similarly scope reads, writes, joins and caches to the tenant. Decide whether unauthorized resources return 403 or concealed 404 consistently.

FastAPI also offers `Security` and `SecurityScopes` to declare required OAuth scopes in dependencies and OpenAPI. They help describe/collect requirements; your code still compares required permissions against a trusted token/account policy. A displayed lock icon does not implement authorization by itself.

## When to use / when not to use; common mistakes

Use JWT when self-contained verifiable claims fit the trust model and you can manage key rotation/expiry. Prefer opaque server sessions when simple centralized revocation is more important. Use an identity provider for delegated login and MFA rather than treating this exercise as an OAuth product.

Mistakes: decoding without verification; selecting allowed algorithms from an untrusted header; missing audience/issuer checks; accepting refresh credentials as access; using email as a mutable stable ID without a plan; storing refresh plaintext; letting users choose admin; hashing passwords on an event loop; treating CORS as authorization; storing all refresh state in one worker while running many workers.

Best practices: HTTPS, minimal claims, short access lifetime, strong keys, secret rotation, bounded input/body size, credential redaction, no-store responses, rate limits and durable audited account administration. Database-backed role checks trade some statelessness for immediate policy updates; acknowledge that design choice.

## Practice

**Beginner:** Register and read your own profile without seeing the password hash. **Intermediate:** Show 401 versus 403 using missing credentials and a reader token at `/admin`. **Challenge:** Rotate a refresh token, replay its predecessor, and prove the successor is revoked while explaining the access-token limitation.

## Expected Result / Solution

The complete app above implements all three tasks. The sequence is register → token → me (200), no-token me (401), reader admin (403), refresh (200), predecessor replay (401), successor refresh (401). Chapter 18 includes executable tests for these exact behaviours, including tampered tokens and missing/incorrect claims. The key explanation is that refresh-family revocation affects future issuance, not the validity of an already signed access token unless the access verifier checks additional revocation state.

## Summary

Token verification proves signed claims, account checks establish current identity status, and authorization checks the requested action/resource. A production login system must also own issuance, renewal, revocation, recovery and abuse resistance.
