import os
from contextlib import asynccontextmanager
from typing import Annotated
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from pymongo import AsyncMongoClient

class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)

class ProductPublic(ProductCreate):
    id: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient(os.getenv("MONGODB_URL", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=3000)
    try:
        await client.admin.command("ping")
        app.state.products = client.catalog.products
        yield
    finally:
        await client.close()

app = FastAPI(lifespan=lifespan)

def parse_id(product_id: str) -> ObjectId:
    if not ObjectId.is_valid(product_id):
        raise HTTPException(422, "Invalid product ID")
    return ObjectId(product_id)

def public(document: dict) -> dict:
    return {"id": str(document["_id"]), "name": document["name"], "price_minor": document["price_minor"]}

@app.post("/products", response_model=ProductPublic, status_code=201)
async def create_product(data: ProductCreate, request: Request):
    document = data.model_dump()
    result = await request.app.state.products.insert_one(document)
    document["_id"] = result.inserted_id
    return public(document)

@app.get("/products", response_model=list[ProductPublic])
async def list_products(request: Request, limit: Annotated[int, Query(ge=1, le=100)] = 10):
    cursor = request.app.state.products.find({}).sort("_id", 1).limit(limit)
    return [public(document) async for document in cursor]

@app.get("/products/{product_id}", response_model=ProductPublic)
async def get_product(product_id: str, request: Request):
    document = await request.app.state.products.find_one({"_id": parse_id(product_id)})
    if document is None:
        raise HTTPException(404, "Product not found")
    return public(document)

@app.put("/products/{product_id}", response_model=ProductPublic)
async def replace_product(product_id: str, data: ProductCreate, request: Request):
    oid = parse_id(product_id)
    document = data.model_dump()
    result = await request.app.state.products.replace_one({"_id": oid}, document)
    if result.matched_count == 0:
        raise HTTPException(404, "Product not found")
    return public({"_id": oid, **document})

@app.delete("/products/{product_id}", status_code=204, response_class=Response)
async def delete_product(product_id: str, request: Request):
    result = await request.app.state.products.delete_one({"_id": parse_id(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Product not found")
    return Response(status_code=204)
