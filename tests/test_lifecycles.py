"""Additional lifecycle/configuration tests; no real outbound HTTP calls."""
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from examples import async_lifespan, settings_app


def test_async_client_lifecycle_and_upstream(monkeypatch):
    original = httpx.AsyncClient
    created = []

    def build_client(**kwargs):
        client = original(transport=httpx.MockTransport(lambda request: httpx.Response(200)), **kwargs)
        created.append(client)
        return client

    monkeypatch.setattr(async_lifespan.httpx, "AsyncClient", build_client)
    with TestClient(async_lifespan.app) as client:
        assert client.get("/wait").json() == {"ready": True}
        assert client.get("/upstream").json() == {"upstream_status": 200}
        assert not created[0].is_closed
    assert created[0].is_closed


@pytest.mark.parametrize("failure,status", [(httpx.ReadTimeout, 504), (httpx.ConnectError, 502)])
def test_upstream_failures_are_translated(monkeypatch, failure, status):
    original = httpx.AsyncClient

    def fail(request):
        raise failure("test-only network failure", request=request)

    monkeypatch.setattr(async_lifespan.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(fail), **kwargs))
    with TestClient(async_lifespan.app) as client:
        result = client.get("/upstream")
        assert result.status_code == status
        assert "test-only" not in result.text


def test_settings_parsing_and_secrets(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # Ignore any learner-created repository .env.
    monkeypatch.setenv("CATALOG_DEBUG", "false")
    monkeypatch.setenv("CATALOG_PAGE_LIMIT", "5")
    monkeypatch.setenv("CATALOG_WEBHOOK_SECRET", "test-only-private-value")
    settings_app.get_settings.cache_clear()
    try:
        assert settings_app.get_settings().debug is False
        with TestClient(settings_app.app) as client:
            result = client.get("/info")
            assert result.json()["page_limit"] == 5
            assert "test-only-private-value" not in result.text
        monkeypatch.setenv("CATALOG_PAGE_LIMIT", "0")
        settings_app.get_settings.cache_clear()
        with pytest.raises(ValidationError):
            settings_app.get_settings()
    finally:
        settings_app.get_settings.cache_clear()
