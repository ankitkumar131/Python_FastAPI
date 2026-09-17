from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from examples.sqlalchemy_app import Base, Product, ProductCreate, ProductPublic

@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine("sqlite+aiosqlite:///./async-products.db")
    app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield
    finally:
        await engine.dispose()

app = FastAPI(lifespan=lifespan)

async def get_session(request: Request):
    async with request.app.state.sessions() as session:
        yield session

Db = Annotated[AsyncSession, Depends(get_session)]

@app.post("/products", response_model=ProductPublic, status_code=201)
async def create(data: ProductCreate, db: Db):
    product = Product(**data.model_dump())
    db.add(product)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(409, "Product conflicts with stored data") from error
    await db.refresh(product)
    return product

@app.get("/products/{product_id}", response_model=ProductPublic)
async def retrieve(product_id: int, db: Db):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product
