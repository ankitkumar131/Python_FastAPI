from fastapi import FastAPI
from examples.pydantic_models import ProductCreate
app = FastAPI()
@app.post("/products", response_model=ProductCreate)
def create(product: ProductCreate):
    return product
