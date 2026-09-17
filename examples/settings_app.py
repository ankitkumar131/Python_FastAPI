import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated, Literal
from fastapi import Depends, FastAPI
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="CATALOG_", extra="ignore")
    app_name: str = "Catalogue"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    page_limit: int = Field(default=20, ge=1, le=100)
    webhook_secret: SecretStr | None = None

@lru_cache
def get_settings() -> Settings:
    return Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger(__name__).info("application started")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/info")
def info(settings: Annotated[Settings, Depends(get_settings)]):
    return {"name": settings.app_name, "page_limit": settings.page_limit}
