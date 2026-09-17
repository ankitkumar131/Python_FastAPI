from itertools import count
from threading import Lock
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)
    description: str | None = Field(default=None, max_length=500)

class ProductPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=80)
    price_minor: int | None = Field(default=None, ge=0, strict=True)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name", "price_minor")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("Omit this field instead of sending null")
        return value

class ProductPublic(ProductCreate):
    id: int

app = FastAPI()
store: dict[int, ProductPublic] = {}
ids = count(1)
lock = Lock()

@app.post("/products", response_model=ProductPublic, status_code=201)
def create_product(data: ProductCreate, response: Response):
    with lock:
        product = ProductPublic(id=next(ids), **data.model_dump())
        store[product.id] = product
    response.headers["Location"] = f"/products/{product.id}"
    return product

@app.get("/products", response_model=list[ProductPublic])
def list_products(limit: Annotated[int, Query(ge=1, le=100)] = 10, offset: Annotated[int, Query(ge=0)] = 0):
    with lock:
        return [store[key] for key in sorted(store)][offset:offset + limit]

@app.get("/products/{product_id}", response_model=ProductPublic)
def get_product(product_id: int):
    with lock:
        if product_id not in store:
            raise HTTPException(404, "Product not found")
        return store[product_id]

@app.put("/products/{product_id}", response_model=ProductPublic)
def replace_product(product_id: int, data: ProductCreate):
    with lock:
        if product_id not in store:
            raise HTTPException(404, "Product not found")
        store[product_id] = ProductPublic(id=product_id, **data.model_dump())
        return store[product_id]

@app.patch("/products/{product_id}", response_model=ProductPublic)
def patch_product(product_id: int, data: ProductPatch):
    with lock:
        if product_id not in store:
            raise HTTPException(404, "Product not found")
        merged = {**store[product_id].model_dump(), **data.model_dump(exclude_unset=True)}
        store[product_id] = ProductPublic.model_validate(merged)
        return store[product_id]

@app.delete("/products/{product_id}", status_code=204, response_class=Response)
def delete_product(product_id: int):
    with lock:
        if product_id not in store:
            raise HTTPException(404, "Product not found")
        del store[product_id]
    return Response(status_code=204)
