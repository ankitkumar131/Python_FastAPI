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
