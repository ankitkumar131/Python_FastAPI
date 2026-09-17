from typing import Annotated
from fastapi import Body, Cookie, FastAPI, Header, Path, Query
from pydantic import BaseModel, Field

app = FastAPI()

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0)

@app.get("/products/featured")
def featured():
    return {"id": 1, "name": "Notebook"}

@app.get("/products/{product_id}")
def get_product(
    product_id: Annotated[int, Path(ge=1)],
    currency: Annotated[str, Query(pattern="^(INR|USD)$")] = "INR",
    user_agent: Annotated[str | None, Header()] = None,
    theme: Annotated[str | None, Cookie()] = None,
):
    return {"id": product_id, "currency": currency, "agent": user_agent, "theme": theme}

@app.get("/products")
def list_products(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    tags: Annotated[list[str] | None, Query()] = None,
):
    return {"limit": limit, "tags": tags or []}

@app.post("/products", status_code=201)
def create_product(product: ProductCreate):
    return product

@app.post("/discount")
def discount(percent: Annotated[int, Body(ge=0, le=100, embed=True)]):
    return {"percent": percent}
