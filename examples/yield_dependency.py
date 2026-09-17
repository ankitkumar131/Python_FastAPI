from io import StringIO
from typing import Annotated
from fastapi import Depends, FastAPI
app = FastAPI()
def get_buffer():
    buffer = StringIO()
    try:
        yield buffer
    finally:
        buffer.close()
@app.get("/message")
def message(buffer: Annotated[StringIO, Depends(get_buffer)]):
    buffer.write("hello")
    return {"message": buffer.getvalue()}
