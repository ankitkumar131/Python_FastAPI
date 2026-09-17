from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from ..database import Db
from ..schemas import ProductRead, ProductWrite
from ..services import ProductService

router = APIRouter(prefix="/products", tags=["products"])

def get_service(db: Db) -> ProductService:
    return ProductService(db)

Service = Annotated[ProductService, Depends(get_service)]

@router.post("", response_model=ProductRead, status_code=201)
def create(data: ProductWrite, service: Service, response: Response):
    product = service.create(data)
    response.headers["Location"] = f"/products/{product.id}"
    return product

@router.get("", response_model=list[ProductRead])
def listing(service: Service, limit: Annotated[int, Query(ge=1, le=100)] = 10, offset: Annotated[int, Query(ge=0)] = 0):
    return service.repo.list(limit, offset)

@router.get("/{product_id}", response_model=ProductRead)
def retrieve(product_id: int, service: Service):
    return service.get(product_id)

@router.put("/{product_id}", response_model=ProductRead)
def replace(product_id: int, data: ProductWrite, service: Service):
    return service.replace(product_id, data)

@router.delete("/{product_id}", status_code=204, response_class=Response)
def delete(product_id: int, service: Service):
    service.delete(product_id)
    return Response(status_code=204)
