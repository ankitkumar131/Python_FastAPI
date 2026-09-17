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
