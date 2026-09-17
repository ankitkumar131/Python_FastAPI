from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
class PublicProduct(BaseModel):
    id: int
    name: str
app = FastAPI()
@app.get("/products/{product_id}", response_model=PublicProduct)
def product(product_id: int):
    if product_id != 1:
        raise HTTPException(404, "Product not found")
    return {"id": 1, "name": "Pen", "cost_minor": 100}
