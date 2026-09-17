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
