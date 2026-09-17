"""Advanced labs: explicit async units of work, scopes/ownership and HTTP validators."""
from itertools import count
from fastapi.testclient import TestClient
from examples import async_sql, auth, conditional, scoped_access


def test_async_sql_persistence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(async_sql.app) as client:
        created = client.post('/products', json={'name': 'Pen', 'price_minor': 2000})
        assert created.status_code == 201
        product_id = created.json()['id']
        assert client.post('/products', json={'name': 'Pen', 'price_minor': 2000}).status_code == 409
        assert client.post('/products', json={'name': 'Book', 'price_minor': 3000}).status_code == 201
    with TestClient(async_sql.app) as client:
        assert client.get(f'/products/{product_id}').json()['name'] == 'Pen'
        assert client.get('/products/999').status_code == 404


def test_scopes_and_cross_account_ownership(monkeypatch):
    monkeypatch.setenv('JWT_SECRET', 'test-only-' + 's' * 40)
    auth.users.clear()
    auth.refresh_records.clear()
    scoped_access.orders.clear()
    scoped_access.ids = count(1)
    try:
        with TestClient(scoped_access.app) as client:
            credentials = []
            for username in ['asha', 'bela']:
                assert client.post('/register', json={'username': username, 'password': 'long-example-password'}).status_code == 201
                pair = client.post('/token', data={'username': username, 'password': 'long-example-password'}).json()
                credentials.append({'Authorization': 'Bearer ' + pair['access_token']})
            first, second = credentials
            result = client.post('/orders', headers=first)
            assert result.status_code == 201
            order_id = result.json()['id']
            assert client.get(f'/orders/{order_id}', headers=first).status_code == 200
            assert client.get(f'/orders/{order_id}', headers=second).status_code == 404
            assert client.post('/inventory/recount', headers=first).status_code == 403
            assert client.get(f'/orders/{order_id}').status_code == 401
    finally:
        auth.users.clear()
        auth.refresh_records.clear()
        scoped_access.orders.clear()


def test_conditional_get():
    with TestClient(conditional.app) as client:
        initial = client.get('/catalogue-info')
        assert initial.status_code == 200
        assert initial.json() == {'service': 'catalogue', 'version': 1}
        tag = initial.headers['etag']
        for candidate in [tag, 'W/' + tag, '*', '"other", ' + tag]:
            cached = client.get('/catalogue-info', headers={'If-None-Match': candidate})
            assert cached.status_code == 304 and cached.content == b''
        assert client.get('/catalogue-info', headers={'If-None-Match': '"old"'}).status_code == 200
