from typing import Annotated
from fastapi import Depends, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

def make_engine(url: str):
    return create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False} if url.startswith("sqlite:") else {})

def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session

Db = Annotated[Session, Depends(get_session)]
