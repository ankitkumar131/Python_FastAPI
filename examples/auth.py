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
