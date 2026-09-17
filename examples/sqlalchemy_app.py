from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import CheckConstraint, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("price_minor >= 0", name="ck_products_price"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    price_minor: Mapped[int]

class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)

class ProductPublic(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int

engine = create_engine("sqlite:///./products.db", connect_args={"check_same_thread": False})

def get_session():
    with Session(engine) as session:
        yield session

Db = Annotated[Session, Depends(get_session)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    try:
        yield
    finally:
        engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.post("/products", response_model=ProductPublic, status_code=201)
def create_product(data: ProductCreate, db: Db):
    product = Product(**data.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Product conflicts with stored data") from error
    db.refresh(product)
    return product

@app.get("/products", response_model=list[ProductPublic])
def list_products(db: Db, limit: Annotated[int, Query(ge=1, le=100)] = 10, offset: Annotated[int, Query(ge=0)] = 0):
    return db.scalars(select(Product).order_by(Product.id).offset(offset).limit(limit)).all()

def require_product(product_id: int, db: Session) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product

@app.get("/products/{product_id}", response_model=ProductPublic)
def get_product(product_id: int, db: Db):
    return require_product(product_id, db)

@app.put("/products/{product_id}", response_model=ProductPublic)
def replace_product(product_id: int, data: ProductCreate, db: Db):
    product = require_product(product_id, db)
    product.name = data.name
    product.price_minor = data.price_minor
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Product conflicts with stored data") from error
    db.refresh(product)
    return product

@app.delete("/products/{product_id}", status_code=204, response_class=Response)
def delete_product(product_id: int, db: Db):
    db.delete(require_product(product_id, db))
    db.commit()
    return Response(status_code=204)
