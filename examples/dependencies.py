from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends, FastAPI, Query

@dataclass
class Pagination:
    limit: int
    offset: int

def pagination(limit: Annotated[int, Query(ge=1, le=100)] = 10, offset: Annotated[int, Query(ge=0)] = 0) -> Pagination:
    return Pagination(limit, offset)

def page_label(page: Annotated[Pagination, Depends(pagination)]) -> str:
    return f"offset={page.offset};limit={page.limit}"

app = FastAPI()

@app.get("/products")
def products(page: Annotated[Pagination, Depends(pagination)], label: Annotated[str, Depends(page_label)]):
    return {"limit": page.limit, "offset": page.offset, "label": label}

@app.get("/orders")
def orders(page: Annotated[Pagination, Depends(pagination)]):
    return {"limit": page.limit, "offset": page.offset}
