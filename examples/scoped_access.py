from itertools import count
from threading import Lock
from typing import Annotated
from fastapi import Depends, HTTPException, Security
from fastapi.security import SecurityScopes
from examples.auth import app, current_user

permissions = {"reader": {"orders:read", "orders:create"}, "admin": {"orders:read", "orders:create", "products:write"}}
orders: dict[int, dict] = {}
ids = count(1)
order_lock = Lock()

def permitted(required: SecurityScopes, user: Annotated[dict, Depends(current_user)]) -> dict:
    allowed = permissions.get(user["role"], set())
    if not set(required.scopes).issubset(allowed):
        raise HTTPException(403, "Insufficient permission")
    return user

@app.post("/orders", status_code=201)
def create_order(user: Annotated[dict, Security(permitted, scopes=["orders:create"])]):
    with order_lock:
        order_id = next(ids)
        orders[order_id] = {"id": order_id, "owner_id": user["id"], "status": "new"}
        return orders[order_id].copy()

@app.get("/orders/{order_id}")
def get_order(order_id: int, user: Annotated[dict, Security(permitted, scopes=["orders:read"])]):
    with order_lock:
        order = orders.get(order_id)
        if order is None or order["owner_id"] != user["id"]:
            raise HTTPException(404, "Order not found")
        return order.copy()

@app.post("/inventory/recount", dependencies=[Security(permitted, scopes=["products:write"])])
def recount():
    return {"accepted": True}
