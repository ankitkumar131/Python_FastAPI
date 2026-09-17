import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .database import make_engine
from .models import Base
from .routes.products import router
from .services import ProductConflict, ProductMissing

def create_app(database_url: str | None = None) -> FastAPI:
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./catalog.db")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(url)
        app.state.engine = engine
        try:
            Base.metadata.create_all(engine)
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Catalogue workshop", lifespan=lifespan)
    app.include_router(router)

    @app.exception_handler(ProductMissing)
    async def missing(request: Request, error: ProductMissing):
        return JSONResponse(status_code=404, content={"detail": "Product not found"})

    @app.exception_handler(ProductConflict)
    async def conflict(request: Request, error: ProductConflict):
        return JSONResponse(status_code=409, content={"detail": "Product conflicts with stored data"})

    @app.get("/health/live", tags=["health"])
    def live():
        return {"status": "ok"}

    return app

app = create_app()
