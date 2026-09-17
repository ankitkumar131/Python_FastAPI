from typing import Annotated
from fastapi import FastAPI, Path, Query
app = FastAPI()
@app.get("/orders/{order_id}")
def order(order_id: Annotated[int, Path(ge=1)], limit: Annotated[int, Query(ge=1, le=20)] = 5):
    return {"order_id": order_id, "limit": limit}
