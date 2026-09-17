import asyncio
import logging
from typing import Annotated
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

app = FastAPI()
logger = logging.getLogger(__name__)
MAX_UPLOAD = 1024 * 1024

def record_upload(size: int):
    logger.info("upload accepted size=%s", size)

@app.post("/uploads")
async def upload(background: BackgroundTasks, file: Annotated[UploadFile, File()], label: Annotated[str, Form(min_length=1, max_length=80)]):
    size = 0
    try:
        if file.content_type != "text/plain":
            raise HTTPException(415, "Only text/plain accepted in this lesson")
        while chunk := await file.read(65536):
            size += len(chunk)
            if size > MAX_UPLOAD:
                raise HTTPException(413, "File too large")
    finally:
        await file.close()
    background.add_task(record_upload, size)
    return {"label": label, "bytes": size}

async def number_chunks():
    for number in range(3):
        yield f"{number}\n"
        await asyncio.sleep(0.01)

@app.get("/numbers")
async def numbers():
    return StreamingResponse(number_chunks(), media_type="text/plain")

@app.websocket("/ws/echo")
async def echo(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            if len(text) > 1000:
                await websocket.close(code=1009)
                return
            await websocket.send_text(f"echo: {text}")
    except WebSocketDisconnect:
        return
