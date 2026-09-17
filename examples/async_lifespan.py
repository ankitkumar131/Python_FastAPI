import asyncio
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, Request

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
        app.state.http = client
        yield

app = FastAPI(lifespan=lifespan)

@app.get("/wait")
async def wait():
    await asyncio.sleep(0.01)
    return {"ready": True}

@app.get("/upstream")
async def upstream(request: Request):
    try:
        response = await request.app.state.http.get("https://example.com")
        response.raise_for_status()
    except httpx.TimeoutException as error:
        raise HTTPException(504, "Upstream timed out") from error
    except httpx.HTTPError as error:
        raise HTTPException(502, "Upstream unavailable") from error
    return {"upstream_status": response.status_code}
